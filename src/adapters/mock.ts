import type { Adapter, Listing, Watch } from "../types.js";

/**
 * Mock adapter for local end-to-end testing (USE_MOCK=1).
 * Emits one listing that satisfies a typical Rush@MSG watch so you can verify the
 * rules → dedup → notify → purchase pipeline without any real API keys.
 */
export const mock: Adapter = {
  id: "seatgeek", // pretend to be a real venue for display purposes
  enabled() {
    return true;
  },
  async findListings(watch: Watch): Promise<Listing[]> {
    const qty = watch.rules.quantity ?? 2;
    const price = Math.max(1, (watch.rules.maxPricePerTicket ?? 250) - 25);
    return [
      {
        id: "mock-listing-1",
        venue: "seatgeek",
        eventId: "mock-event",
        eventName: watch.name,
        section: "112",
        row: "8",
        quantity: qty,
        pricePerTicket: price,
        totalPrice: price * qty,
        seatsTogether: true,
        currency: "USD",
        url: "https://seatgeek.com/rush-tickets",
        seenAt: new Date().toISOString(),
      },
    ];
  },
};
