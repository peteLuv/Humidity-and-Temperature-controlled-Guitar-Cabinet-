import type { TicketSource, Listing, Watch } from '../types.js';

/**
 * SeatGeek source — the recommended first implementation (see docs/DATA-SOURCES.md).
 *
 * NOTE: SeatGeek's Platform API gives event metadata and event-level price stats
 * easily; full per-listing inventory is partner-gated. Start by resolving the
 * event id and alerting on `lowest_price`; upgrade to per-listing once you have
 * partner access.
 *
 * TODO(M1): wire the real HTTP calls with SEATGEEK_CLIENT_ID/SECRET.
 */
export class SeatGeekSource implements TicketSource {
  readonly name = 'seatgeek' as const;

  constructor(private clientId = process.env.SEATGEEK_CLIENT_ID ?? '') {}

  async poll(watch: Watch): Promise<Listing[]> {
    if (!this.clientId) {
      // Fail soft so the rest of the service keeps running.
      console.warn('[seatgeek] SEATGEEK_CLIENT_ID not set — skipping poll');
      return [];
    }
    // TODO(M1):
    //   1. Resolve event id: GET /events?venue.name=...&q=Rush&datetime_utc.gte=...
    //   2. Pull price/listing data for that event.
    //   3. Map each into the normalized Listing shape below.
    //
    // Example of the shape a real listing would take:
    // return [{
    //   source: 'seatgeek', listingId, eventId, eventName: 'Rush',
    //   venue: watch.venue, eventDate, section, row, quantity, seatsTogether,
    //   pricePerTicket, currency: 'USD', feesIncluded: false, url,
    //   seenAt: new Date().toISOString(),
    // }];
    return [];
  }
}
