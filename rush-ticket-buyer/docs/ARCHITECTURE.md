# Architecture

## Principles

- **Sources are plugins.** Every venue implements the same `TicketSource`
  interface and emits the same normalized `Listing`. The rule engine and
  notifiers never know which venue a listing came from.
- **Notify-first, buy-optional.** The notification path is the product; the
  purchase path is an opt-in module behind a kill switch.
- **Idempotent & stateful.** Restarts must not re-alert or double-buy. All
  "have we seen / alerted / bought this" state lives in a small local DB.

## Components

```
config.yaml ─▶ Config ─▶ Scheduler ─┬▶ SeatGeekSource ─┐
                                     ├▶ StubHubSource ──┼─▶ Normalizer ─▶ Listing[]
                                     └▶ TicketmasterSrc ┘
                                                             │
                                                             ▼
                                                        RuleEngine
                                          (match watch? new/cheaper? under cap?)
                                                     │              │
                                             matches │              │ auto-buy candidate
                                                     ▼              ▼
                                                 Notifier      PurchaseModule
                                             (Pushover/TG/SMS)   (opt-in, gated)
                                                     │              │
                                                     └──────┬───────┘
                                                            ▼
                                                       Store (SQLite)
                                              seen / alerted / purchased / spend
```

### 1. Scheduler
Runs each source on its own `poll_interval`. Handles per-source rate limiting,
backoff on errors, and jitter so all sources don't fire simultaneously.
(Where a venue supports webhooks, a source can be push-driven instead of polled.)

### 2. TicketSource (the plugin interface)

```ts
interface TicketSource {
  readonly name: 'seatgeek' | 'stubhub' | 'ticketmaster';
  // Fetch current matching inventory for a watch, normalized.
  poll(watch: Watch): Promise<Listing[]>;
}
```

### 3. Normalizer → the common `Listing`

```ts
interface Listing {
  source: string;          // 'seatgeek' | 'stubhub' | 'ticketmaster'
  listingId: string;       // stable id within the source (for dedupe)
  eventId: string;
  eventName: string;
  venue: string;           // 'Madison Square Garden'
  eventDate: string;       // ISO
  section: string;
  row?: string;
  quantity: number;        // seats in this listing
  seatsTogether: number;   // max contiguous block
  pricePerTicket: number;  // all-in if the API exposes fees; note if not
  currency: string;        // 'USD'
  feesIncluded: boolean;
  url: string;             // deep link to listing / checkout
  seenAt: string;          // ISO timestamp we observed it
}
```

### 4. RuleEngine
For each `Listing`, against each `Watch`:
- **Match:** event id/name + date + venue; `quantity >= watch.quantity`;
  `seatsTogether >= watch.min_seats_together`; section passes allow/deny lists.
- **Freshness:** fire only if `listingId` is new, **or** its `pricePerTicket`
  dropped below the last-seen price for that id.
- **Threshold:** `pricePerTicket <= watch.max_price_per_ticket`.
- Emits `NotifyIntent` always-on-match, and `BuyIntent` only when threshold met
  **and** `auto_buy.enabled` for that source.

### 5. Notifier (plugin interface)

```ts
interface Notifier {
  readonly name: string;
  send(alert: Alert): Promise<void>;   // title, body, deep-link, maybe buttons
}
```
Ship Pushover **or** ntfy **or** Telegram first (see PLAN M3). Alerts always
carry the listing `url` so manual checkout is one tap.

### 6. PurchaseModule (opt-in, gated) — see PLAN M5 and LEGAL doc

```ts
interface PurchaseModule {
  readonly source: string;
  // Attempt to buy exactly `quantity` at/under `maxPricePerTicket`.
  buy(listing: Listing, opts: BuyOptions): Promise<PurchaseResult>;
}
```
Wrapped by a `SpendGuard` (daily cap), a `PurchaseLock` (exactly-once), and a
global kill switch. Every attempt produces a confirmation push.

### 7. Store (SQLite)
Tables: `seen_listings(listingId, source, lastPrice, firstSeen)`,
`alerts(listingId, channel, sentAt)`, `purchases(listingId, amount, status, at)`,
`spend(day, total)`. This is what makes the whole thing idempotent.

## Tech choices

- **Language:** TypeScript / Node — great for concurrent I/O, easy HTTP,
  first-class SDKs for Telegram/Pushover/Twilio.
- **Storage:** SQLite (via `better-sqlite3`) — zero-ops, perfect for a single
  always-on instance.
- **Scheduling:** in-process timers with jitter; no external queue needed at
  this scale.
- **Deploy:** single small container (Fly.io / Railway / a $5 VPS). One process.

## Failure modes to design for
- API key expiry / auth errors → push an operator alert, keep other sources up.
- Venue layout/API change → source returns 0 or throws; alert, don't crash.
- Rate limiting (429) → exponential backoff per source.
- Duplicate alerts on restart → prevented by the `Store`.
- Double purchase on retry → prevented by `PurchaseLock` (idempotency key).
