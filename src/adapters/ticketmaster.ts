import { request } from "undici";
import { env } from "../config.js";
import type { Adapter, Listing, Watch } from "../types.js";

/**
 * Ticketmaster Discovery API v2 adapter.
 * Free instant key at https://developer.ticketmaster.com.
 * Discovery is strongest for event resolution + price ranges; resale granularity
 * is limited (see docs/PLAN.md). Use it as the on-sale / price signal.
 */
export const ticketmaster: Adapter = {
  id: "ticketmaster",

  enabled() {
    return env.ticketmasterKey.length > 0;
  },

  async findListings(watch: Watch): Promise<Listing[]> {
    const params = new URLSearchParams({
      apikey: env.ticketmasterKey,
      keyword: watch.match.keyword,
      size: "50",
    });
    if (watch.match.venueName) params.set("venueName", watch.match.venueName);
    if (watch.match.dateFrom) params.set("startDateTime", `${watch.match.dateFrom}T00:00:00Z`);
    if (watch.match.dateTo) params.set("endDateTime", `${watch.match.dateTo}T23:59:59Z`);

    const res = await request(
      `https://app.ticketmaster.com/discovery/v2/events.json?${params}`,
    );
    if (res.statusCode !== 200) {
      console.warn(`[ticketmaster] HTTP ${res.statusCode}`);
      return [];
    }
    const data = (await res.body.json()) as any;
    const events: any[] = data?._embedded?.events ?? [];

    const listings: Listing[] = [];
    for (const ev of events) {
      const priceRanges: any[] = ev.priceRanges ?? [];
      const min = priceRanges[0]?.min;
      if (min == null) continue; // no price signal yet
      listings.push({
        id: ev.id,
        venue: "ticketmaster",
        eventId: ev.id,
        eventName: ev.name,
        quantity: watch.rules.quantity ?? watch.rules.minQuantity ?? 2,
        pricePerTicket: Number(min),
        totalPrice: Number(min) * (watch.rules.quantity ?? 2),
        currency: priceRanges[0]?.currency ?? "USD",
        url: ev.url,
        seenAt: new Date().toISOString(),
      });
    }
    return listings;
  },
};
