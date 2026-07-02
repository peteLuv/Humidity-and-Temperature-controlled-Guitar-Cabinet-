// Shared types. See docs/ARCHITECTURE.md for the full picture.

export interface Watch {
  name: string;
  venue: string;
  eventDates: string[];
  sourceEventIds: Partial<Record<SourceName, string>>;
  criteria: {
    quantity: number;
    minSeatsTogether: number;
    maxPricePerTicket: number;
    sections: { allow: string[]; deny: string[] };
  };
}

export type SourceName = 'seatgeek' | 'stubhub' | 'ticketmaster';

/** Normalized listing every source must produce. */
export interface Listing {
  source: SourceName;
  listingId: string;
  eventId: string;
  eventName: string;
  venue: string;
  eventDate: string; // ISO
  section: string;
  row?: string;
  quantity: number;
  seatsTogether: number;
  pricePerTicket: number;
  currency: string;
  feesIncluded: boolean;
  url: string;
  seenAt: string; // ISO
}

export interface TicketSource {
  readonly name: SourceName;
  poll(watch: Watch): Promise<Listing[]>;
}

export interface Alert {
  title: string;
  body: string;
  url: string;
  listing: Listing;
}

export interface Notifier {
  readonly name: string;
  send(alert: Alert): Promise<void>;
}

export interface BuyOptions {
  quantity: number;
  maxPricePerTicket: number;
  dryRun: boolean;
  idempotencyKey: string;
}

export interface PurchaseResult {
  status: 'purchased' | 'skipped' | 'failed' | 'dry_run';
  amount?: number;
  reason?: string;
}

export interface PurchaseModule {
  readonly source: SourceName;
  buy(listing: Listing, opts: BuyOptions): Promise<PurchaseResult>;
}
