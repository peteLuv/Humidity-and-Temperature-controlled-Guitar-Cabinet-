# Build Plan — ticket-sentry

Goal: get a **push notification (and optional assisted checkout)** the instant a
resale listing for **Rush @ Madison Square Garden** appears under your thresholds,
across SeatGeek / StubHub / Ticketmaster.

---

## 1. Architecture

```
                 ┌─────────────────────────────────────────────┐
                 │                  Scheduler                    │
                 │   (poll every N sec  +  webhook receivers)    │
                 └───────────────┬───────────────┬──────────────┘
                                 │               │
                 ┌───────────────▼───┐   ┌───────▼───────────┐   ┌──────────────┐
   Venue         │ Ticketmaster      │   │ SeatGeek          │   │ StubHub      │
   adapters      │ Discovery API     │   │ Platform API      │   │ Partner API  │
   (pluggable)   └───────────────┬───┘   └───────┬───────────┘   └──────┬───────┘
                                 │               │                       │
                                 ▼               ▼                       ▼
                        ┌────────────────────────────────────────────────────┐
                        │  Normalizer  →  Listing { venue, price, qty, ... }   │
                        └───────────────────────────┬────────────────────────┘
                                                    ▼
                        ┌────────────────────────────────────────────────────┐
                        │  Dedup store (SQLite/Redis)  — "have I seen this?"   │
                        └───────────────────────────┬────────────────────────┘
                                                    ▼
                        ┌────────────────────────────────────────────────────┐
                        │  Rules engine  — max price, qty==2, sections,        │
                        │                  seats-together, fees-included       │
                        └──────────────┬──────────────────────┬──────────────┘
                                MATCH  │                       │  NO MATCH → drop
                                       ▼                       
                        ┌────────────────────────┐   ┌────────────────────────┐
                        │  Notifier              │   │  Auto-buy hook          │
                        │  push + deep-link      │   │  (OFF by default;       │
                        │  (ntfy/Pushover/APNs)  │   │   assisted checkout)    │
                        └────────────────────────┘   └────────────────────────┘
```

**Design principles**
- **Adapters are pluggable.** Each venue implements one `Adapter` interface. Adding
  a venue = adding one file. Venues you lack API access to are simply disabled.
- **Everything normalizes to one `Listing` type** so rules/notify/store are
  venue-agnostic.
- **Idempotent.** A listing is notified at most once (dedup store keyed by a stable
  listing fingerprint).
- **Threshold logic lives in data** (`config/watch.json`), not code — tune without
  redeploying.

---

## 2. Data sources — access reality

| Venue         | API                         | Gets resale listings + price? | Access        |
|---------------|-----------------------------|-------------------------------|---------------|
| Ticketmaster  | Discovery API v2            | Event/price ranges; resale is limited | Free dev key, instant |
| SeatGeek      | Platform API                | Yes — listings, `lowest_price`, stats | Free client_id; new signups gated |
| StubHub       | Partner/Catalog API         | Yes — inventory + prices      | Partner approval required |

Notes:
- **Ticketmaster Discovery** is the easy on-ramp (instant key) but its *resale*
  granularity is thin — better for the primary-sale/on-sale signal and event metadata.
- **SeatGeek Platform API** is the best free source for resale listing prices if you
  can still get a `client_id`.
- **StubHub** requires partner approval; treat as phase 2.
- If an official API isn't available, the adapter interface still supports a
  **user-provided feed** (e.g. a browser extension you run that posts listings to a
  local webhook) — this keeps *you* in the driver's seat and avoids server-side
  scraping. See `docs/LEGAL.md` before scraping anything.

---

## 3. Components

### 3.1 Venue adapters (`src/adapters/`)
Each exports an object implementing:
```ts
interface Adapter {
  id: 'ticketmaster' | 'seatgeek' | 'stubhub';
  enabled(): boolean;                          // has creds?
  findListings(watch: Watch): Promise<Listing[]>;
}
```
- `ticketmaster.ts` — Discovery API: resolve event by keyword+venue+date, read price ranges / offers.
- `seatgeek.ts` — Platform API: `/events` + listing stats, map to `Listing[]`.
- `stubhub.ts` — Partner API stub (phase 2).

### 3.2 Normalizer → `Listing` (`src/types.ts`)
```ts
type Listing = {
  id: string;          // stable per-venue listing id
  venue: string;
  eventId: string;
  section?: string; row?: string;
  quantity: number;
  pricePerTicket: number;   // fees included where the API exposes them
  totalPrice: number;
  seatsTogether?: boolean;
  url: string;              // deep-link to checkout/listing
  seenAt: string;           // ISO
};
```

### 3.3 Dedup store (`src/store.ts`)
- SQLite (better-sqlite3) locally; Redis in prod. Key = `${venue}:${id}` or a hash of
  `(venue, section, row, qty, price)` when ids aren't stable.
- Prevents re-notifying the same listing on every poll.

### 3.4 Rules engine (`src/rules.ts`)
Evaluates a `Listing` against a `Watch`:
- `maxPricePerTicket`, `maxTotal`
- `quantity` (exact, e.g. 2) or `minQuantity`
- `sections` allowlist / `excludeSections`
- `requireSeatsTogether`
- returns `{ match: boolean, reasons: string[] }`

### 3.5 Notifier (`src/notify.ts`)
- Providers: **ntfy** (free, dead-simple, self-hostable — default), **Pushover**,
  **APNs** (later, for a native iOS app).
- Payload: title `2 Rush tix @ $XYZ — Section 112`, body with seat details, and a
  **click action = the listing deep-link** so it's one tap to checkout.
- Rate-limited / de-duped so a listing storm doesn't spam you.

### 3.6 Purchase hook (`src/purchase.ts`) — **disabled by default**
Three modes, chosen in config:
- `notify` (default) — do nothing but notify.
- `assist` — additionally deep-link + optionally pre-open checkout; **you** tap buy.
- `auto` — headless checkout. **Ships disabled, requires `I_UNDERSTAND_THE_RISKS=1`.**
  Documented risks in `docs/LEGAL.md`; not recommended.

### 3.7 Scheduler (`src/index.ts`)
- `setInterval` poll loop (configurable, respect each API's rate limits) +
  optional Express webhook receiver for push-style feeds.
- Jittered polling to avoid thundering-herd / detection.

---

## 4. Config (`config/watch.json`)
```json
{
  "name": "Rush @ MSG",
  "venues": ["ticketmaster", "seatgeek"],
  "match": {
    "keyword": "Rush",
    "venueName": "Madison Square Garden",
    "dateFrom": "2026-07-01",
    "dateTo": "2026-12-31"
  },
  "rules": {
    "quantity": 2,
    "maxPricePerTicket": 250,
    "requireSeatsTogether": true,
    "excludeSections": ["Obstructed View"]
  },
  "pollSeconds": 30,
  "purchaseMode": "notify"
}
```

---

## 5. Delivery phases

- **Phase 0 — scaffold (this repo):** types, adapter interface, rules engine, ntfy
  notifier, SQLite dedup, poll loop, config. Runnable end-to-end with mock data.
- **Phase 1 — Ticketmaster live:** wire Discovery API, get a real "on-sale / price"
  signal + event resolution. Free key → fastest path to a working alert.
- **Phase 2 — SeatGeek live:** best free resale price feed; add listing-level rules.
- **Phase 3 — StubHub:** apply for partner API; add adapter.
- **Phase 4 — reliability:** deploy (small always-on container or serverless cron),
  jittered polling, health checks, per-venue backoff, Redis dedup.
- **Phase 5 — assisted checkout:** deep-link + optional pre-open; measure end-to-end
  reaction time. Auto-buy stays gated.

---

## 6. Deployment
- **Local:** `npm run dev` for testing.
- **Always-on:** cheap VPS / Fly.io / Railway container (needs to run 24/7 near
  on-sale windows). Serverless cron (e.g. Vercel/Cloud Scheduler every 30–60s) works
  for polling but not for sub-second reaction.
- **Secrets** via env (`.env`), never committed. See `.env.example`.

---

## 7. Open questions to confirm
- Which venues do you already have (or can get) API keys for?
- Push channel preference: ntfy (free, install one app) vs Pushover ($5 one-time)?
- Hard ceiling per ticket, and is "seats together" a must-have or nice-to-have?
- Auto-buy: do you want the gated hook wired at all, or notify + one-tap only?
