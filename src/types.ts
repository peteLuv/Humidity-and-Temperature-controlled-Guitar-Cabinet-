// Core domain types. Everything venue-specific normalizes into these.

export type VenueId = "ticketmaster" | "seatgeek" | "stubhub";

/** A single resale listing, normalized across venues. */
export interface Listing {
  /** Stable per-venue listing id (or a computed fingerprint when none exists). */
  id: string;
  venue: VenueId;
  eventId: string;
  eventName: string;
  section?: string;
  row?: string;
  quantity: number;
  /** Per-ticket price with fees included where the API exposes them. */
  pricePerTicket: number;
  totalPrice: number;
  seatsTogether?: boolean;
  currency: string;
  /** Deep-link to the listing / checkout. */
  url: string;
  /** ISO timestamp of when we observed it. */
  seenAt: string;
}

/** Rules a listing must satisfy to trigger an alert. */
export interface Rules {
  /** Exact quantity required (e.g. 2). Takes precedence over minQuantity. */
  quantity?: number;
  minQuantity?: number;
  maxPricePerTicket?: number;
  maxTotal?: number;
  /** If set, section must be in this list. */
  sections?: string[];
  excludeSections?: string[];
  requireSeatsTogether?: boolean;
}

export interface Watch {
  name: string;
  venues: VenueId[];
  match: {
    keyword: string;
    venueName?: string;
    dateFrom?: string;
    dateTo?: string;
  };
  rules: Rules;
  pollSeconds: number;
  purchaseMode: "notify" | "assist" | "auto";
}

export interface Adapter {
  id: VenueId;
  /** True when required credentials are present. */
  enabled(): boolean;
  /** Fetch current listings matching the watch. */
  findListings(watch: Watch): Promise<Listing[]>;
}

export interface MatchResult {
  match: boolean;
  reasons: string[];
}
