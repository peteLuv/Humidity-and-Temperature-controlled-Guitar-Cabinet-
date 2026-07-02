import { env, loadWatch } from "./config.js";
import { activeAdapters } from "./adapters/index.js";
import { evaluate } from "./rules.js";
import { SeenStore } from "./store.js";
import { notify } from "./notify.js";
import { handlePurchase } from "./purchase.js";
import type { Watch } from "./types.js";

const store = new SeenStore();

/** One polling pass across all active venues. */
async function pass(watch: Watch): Promise<void> {
  const adapters = activeAdapters();
  for (const adapter of adapters) {
    let listings;
    try {
      listings = await adapter.findListings(watch);
    } catch (err) {
      console.warn(`[${adapter.id}] fetch failed:`, (err as Error).message);
      continue;
    }
    for (const listing of listings) {
      if (store.has(listing)) continue; // already alerted
      const { match, reasons } = evaluate(listing, watch.rules);
      if (!match) {
        console.log(`[skip] ${listing.venue} ${listing.section ?? ""}: ${reasons.join("; ")}`);
        store.add(listing); // remember so we don't re-log every poll
        continue;
      }
      store.add(listing);
      await notify(listing);
      await handlePurchase(listing, watch);
    }
  }
}

async function main(): Promise<void> {
  const watch = loadWatch();
  const adapters = activeAdapters();
  console.log(
    `[ticket-sentry] watching "${watch.name}" via [${adapters.map((a) => a.id).join(", ")}] ` +
      `every ${watch.pollSeconds}s (mode=${watch.purchaseMode}, mock=${env.useMock})`,
  );

  const baseMs = Math.max(5, watch.pollSeconds) * 1000;

  // Self-scheduling loop with ±20% jitter to avoid a fixed polling fingerprint.
  const loop = async (): Promise<void> => {
    await pass(watch);
    const jitter = 1 + (Math.random() * 0.4 - 0.2);
    setTimeout(() => void loop(), Math.round(baseMs * jitter));
  };
  void loop();
}

main().catch((err) => {
  console.error("fatal:", err);
  process.exit(1);
});
