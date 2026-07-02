import type { Listing, Rules, MatchResult } from "./types.js";

/** Pure function: does this listing satisfy the watch's rules? */
export function evaluate(listing: Listing, rules: Rules): MatchResult {
  const reasons: string[] = [];

  if (rules.quantity != null && listing.quantity !== rules.quantity) {
    reasons.push(`quantity ${listing.quantity} != required ${rules.quantity}`);
  }
  if (rules.minQuantity != null && listing.quantity < rules.minQuantity) {
    reasons.push(`quantity ${listing.quantity} < min ${rules.minQuantity}`);
  }
  if (rules.maxPricePerTicket != null && listing.pricePerTicket > rules.maxPricePerTicket) {
    reasons.push(`$${listing.pricePerTicket}/tix > max $${rules.maxPricePerTicket}`);
  }
  if (rules.maxTotal != null && listing.totalPrice > rules.maxTotal) {
    reasons.push(`total $${listing.totalPrice} > max $${rules.maxTotal}`);
  }
  if (rules.sections && listing.section && !rules.sections.includes(listing.section)) {
    reasons.push(`section ${listing.section} not in allowlist`);
  }
  if (rules.excludeSections && listing.section && rules.excludeSections.includes(listing.section)) {
    reasons.push(`section ${listing.section} excluded`);
  }
  if (rules.requireSeatsTogether && listing.seatsTogether === false) {
    reasons.push("seats not together");
  }

  return { match: reasons.length === 0, reasons };
}
