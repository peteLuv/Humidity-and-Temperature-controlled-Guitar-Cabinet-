import type { Listing, Watch, Alert } from '../types.js';

export type MatchDecision =
  | { kind: 'ignore'; reason: string }
  | { kind: 'notify'; alert: Alert; underThreshold: boolean };

/**
 * Decide what to do with a single listing for a single watch.
 * Freshness/dedupe is handled by the Store (caller); this is pure matching.
 */
export function evaluate(listing: Listing, watch: Watch): MatchDecision {
  const c = watch.criteria;

  if (listing.venue !== watch.venue) return ignore('venue mismatch');
  if (watch.eventDates.length && !watch.eventDates.some((d) => listing.eventDate.startsWith(d)))
    return ignore('date not in watch');
  if (listing.quantity < c.quantity) return ignore('not enough tickets');
  if (listing.seatsTogether < c.minSeatsTogether) return ignore('seats not contiguous');

  const sec = listing.section.toLowerCase();
  if (c.sections.deny.some((s) => sec.includes(s.toLowerCase()))) return ignore('section denied');
  if (c.sections.allow.length && !c.sections.allow.some((s) => sec.includes(s.toLowerCase())))
    return ignore('section not in allow-list');

  const underThreshold = listing.pricePerTicket <= c.maxPricePerTicket;
  const price = `${listing.currency} ${listing.pricePerTicket}/tkt${listing.feesIncluded ? ' (all-in)' : ' (+fees)'}`;
  const alert: Alert = {
    title: `${watch.name}: ${listing.section}${listing.row ? ' row ' + listing.row : ''} — ${price}`,
    body:
      `${listing.quantity} tickets on ${listing.source} • ${listing.seatsTogether} together • ${price}` +
      (underThreshold ? ' • ✅ under threshold' : ''),
    url: listing.url,
    listing,
  };
  return { kind: 'notify', alert, underThreshold };
}

function ignore(reason: string): MatchDecision {
  return { kind: 'ignore', reason };
}
