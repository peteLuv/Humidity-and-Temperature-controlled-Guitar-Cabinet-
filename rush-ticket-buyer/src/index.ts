import 'dotenv/config';
import { readFileSync } from 'node:fs';
import { parse } from 'yaml';
import type { TicketSource, Notifier, Watch, SourceName } from './types.js';
import { Store } from './core/store.js';
import { evaluate } from './core/engine.js';
import { SeatGeekSource } from './sources/seatgeek.js';
import { NtfyNotifier } from './notify/ntfy.js';

/**
 * Entry point. Loads config, wires enabled sources + notifiers, then polls on
 * a per-source interval. Notify-first; auto-buy is intentionally NOT wired in
 * here yet (see docs/PLAN.md M5 and the LEGAL doc before enabling it).
 */

interface Config {
  watches: any[];
  sources: Record<string, { enabled: boolean; poll_interval_seconds: number }>;
  notifications: Record<string, any>;
}

function loadConfig(path = 'config.yaml'): Config {
  return parse(readFileSync(path, 'utf8')) as Config;
}

function toWatch(w: any): Watch {
  return {
    name: w.name,
    venue: w.venue,
    eventDates: w.event_dates ?? [],
    sourceEventIds: w.source_event_ids ?? {},
    criteria: {
      quantity: w.criteria.quantity,
      minSeatsTogether: w.criteria.min_seats_together,
      maxPricePerTicket: w.criteria.max_price_per_ticket,
      sections: {
        allow: w.criteria.sections?.allow ?? [],
        deny: w.criteria.sections?.deny ?? [],
      },
    },
  };
}

function buildSources(cfg: Config): TicketSource[] {
  const out: TicketSource[] = [];
  if (cfg.sources.seatgeek?.enabled) out.push(new SeatGeekSource());
  // TODO(M4): push StubHubSource / TicketmasterSource once implemented.
  return out;
}

function buildNotifiers(cfg: Config): Notifier[] {
  const out: Notifier[] = [];
  if (cfg.notifications.ntfy?.enabled) out.push(new NtfyNotifier(cfg.notifications.ntfy.topic));
  // TODO(M3): pushover / telegram / twilio.
  return out;
}

async function pollOnce(source: TicketSource, watches: Watch[], store: Store, notifiers: Notifier[]) {
  const now = new Date().toISOString();
  for (const watch of watches) {
    let listings;
    try {
      listings = await source.poll(watch);
    } catch (err) {
      console.error(`[${source.name}] poll failed:`, err);
      continue; // one source failing must not take down the others
    }
    for (const listing of listings) {
      const decision = evaluate(listing, watch);
      if (decision.kind !== 'notify') continue;
      if (!store.isFreshOrCheaper(listing, now)) continue; // dedupe
      for (const n of notifiers) {
        try {
          await n.send(decision.alert);
        } catch (err) {
          console.error(`[notify:${n.name}] failed:`, err);
        }
      }
      console.log(`[alert] ${decision.alert.title}${decision.underThreshold ? ' (UNDER THRESHOLD)' : ''}`);
    }
  }
}

async function main() {
  const cfg = loadConfig();
  const watches = cfg.watches.map(toWatch);
  const store = new Store();
  const sources = buildSources(cfg);
  const notifiers = buildNotifiers(cfg);

  if (!sources.length) console.warn('No sources enabled — check config.yaml');
  if (!notifiers.length) console.warn('No notifiers enabled — you will not be alerted');

  console.log(`Watching ${watches.length} target(s) across ${sources.length} source(s). Ctrl-C to stop.`);

  for (const source of sources) {
    const interval = (cfg.sources[source.name as SourceName]?.poll_interval_seconds ?? 30) * 1000;
    const jitter = () => Math.floor(interval * 0.2 * Math.random());
    const loop = async () => {
      await pollOnce(source, watches, store, notifiers);
      setTimeout(loop, interval + jitter());
    };
    setTimeout(loop, jitter()); // stagger sources so they don't all fire at once
  }
}

main().catch((err) => {
  console.error('fatal:', err);
  process.exit(1);
});
