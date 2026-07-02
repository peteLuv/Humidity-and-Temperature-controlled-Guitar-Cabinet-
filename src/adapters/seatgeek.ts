import { request } from "undici";
import { env } from "../config.js";
import type { Adapter, Listing, Watch } from "../types.js";

/**
 * SeatGeek Platform API adapter.
 * Client id/secret at https://seatgeek.com/account/develop (new access may be gated).
 * Best free source of resale listing prices (lowest_price / stats). Note the public
 * Platform API exposes event-level price stats more readily than per-seat listings;
 * per-listing detail may require deeper partner access.
 */
export const seatgeek: Adapter = {
  id: "seatgeek",

  enabled() {
    return env.seatgeekClientId.length > 0;
  },

  async findListings(watch: Watch): Promise<Listing[]> {
    const params = new URLSearchParams({
      client_id: env.seatgeekClientId,
      q: watch.match.keyword,
      per_page: "50",
    });
    if (env.seatgeekClientSecret) params.set("client_secret", env.seatgeekClientSecret);
    if (watch.match.venueName) params.set("venue.name", watch.match.venueName);
    if (watch.match.dateFrom) params.set("datetime_utc.gte", `${watch.match.dateFrom}T00:00:00`);
    if (watch.match.dateTo) params.set("datetime_utc.lte", `${watch.match.dateTo}T23:59:59`);

    const res = await request(`https://api.seatgeek.com/2/events?${params}`);
    if (res.statusCode !== 200) {
      console.warn(`[seatgeek] HTTP ${res.statusCode}`);
      return [];
    }
    const data = (await res.body.json()) as any;
    const events: any[] = data?.events ?? [];

    const qty = watch.rules.quantity ?? watch.rules.minQuantity ?? 2;
    const listings: Listing[] = [];
    for (const ev of events) {
      const lowest = ev?.stats?.lowest_price;
      if (lowest == null) continue;
      listings.push({
        id: String(ev.id),
        venue: "seatgeek",
        eventId: String(ev.id),
        eventName: ev.title,
        quantity: qty,
        pricePerTicket: Number(lowest),
        totalPrice: Number(lowest) * qty,
        currency: "USD",
        url: ev.url,
        seenAt: new Date().toISOString(),
      });
    }
    return listings;
  },
};
