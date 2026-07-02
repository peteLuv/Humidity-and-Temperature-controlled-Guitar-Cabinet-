# Build Plan — Rush @ MSG Ticket Watcher & Buyer

## 1. Goal

Get **2 tickets** to Rush at Madison Square Garden at a price you're happy with,
by reacting to secondary-market listings faster than a human refreshing a page.

Concretely:

1. **Watch** SeatGeek, StubHub, and Ticketmaster for listings matching a
   specific event (Rush @ MSG, specific date), section/row/quantity criteria.
2. **Notify** you within seconds of a new or price-dropped listing via push.
3. **Buy** — optionally and where permitted — 2 tickets automatically when a
   listing is at/below a price threshold, or make one-tap manual checkout
   trivially fast.

## 2. Reality check (please read before building)

Three constraints shape every design decision here. Details in
[`LEGAL-AND-COMPLIANCE.md`](LEGAL-AND-COMPLIANCE.md) and
[`DATA-SOURCES.md`](DATA-SOURCES.md); the short version:

- **Fully automated checkout is restricted.** The US **BOTS Act (2016)** makes it
  unlawful to circumvent a ticket seller's access/queue/security controls, and
  all three venues' Terms of Service prohibit automated purchasing and scraping.
  A bot that races a public checkout flow is exactly what these rules target.
- **Real-time resale listing data is gated.** SeatGeek, StubHub, and Ticketmaster
  each have developer APIs, but the *live resale inventory + price* feeds are
  partner-gated (application/approval, sometimes a commercial agreement). Public
  APIs mostly give event metadata and "get me a checkout link," not a firehose
  of individual listings with prices.
- **Speed favors notification, not automation.** The winning play for a single
  fan is: detect fast → push instantly → complete a pre-authenticated,
  one-tap checkout on your phone. That stays inside ToS and is often faster in
  practice than a fragile scraping bot that breaks on every layout change.

**Recommended default scope:** ship the watcher + notifier first (Milestones
1–4). Treat true auto-buy (Milestone 5) as opt-in, per-venue, and only via a
sanctioned path (official checkout deep-link, or an API/agreement that
explicitly permits programmatic purchase).

## 3. Milestones

### M0 — Project setup (½ day)
- TypeScript + Node scaffold (already stubbed in `src/`).
- Config loader (`config.yaml`), secrets via env / `.env`.
- Structured logging, a `--dry-run` mode, and a local SQLite store for
  "listings we've already seen / already alerted on."

### M1 — Source abstraction + one working source (1–2 days)
- Define the `TicketSource` interface (see `ARCHITECTURE.md`): `poll()` returns
  normalized `Listing[]`.
- Implement **SeatGeek first** — it has the most developer-friendly public API
  and is the cleanest to prototype against.
- Normalizer maps each venue's payload → common `Listing` shape.

### M2 — Rule engine + dedupe (1 day)
- Per-watch matching: event id/name + date + venue, quantity ≥ 2 (sold as a
  contiguous pair), section/row allow-lists, max price per ticket.
- Dedupe by stable listing key; only fire on **new** or **price-decreased**
  listings. Persist state so restarts don't re-alert.

### M3 — Notifications (1 day)
- Pluggable `Notifier` interface. Ship at least one of:
  - **Pushover** or **ntfy.sh** — dead-simple mobile push, great for this.
  - **Telegram bot** — free, supports inline buttons ("Open checkout").
  - **Twilio SMS** — most reliable but costs per message.
- Every alert includes a **deep link straight to the listing/checkout**, so the
  human path from buzz → purchase is one tap.

### M4 — Add StubHub + Ticketmaster sources (2–4 days, gated on API access)
- Implement the remaining two `TicketSource`s once you have API keys /
  partner access. Same interface, so they slot in without touching the engine.
- Backpressure + rate-limit handling per venue.

### M5 — Auto-buy (opt-in, per-venue) (open-ended; do last)
- Only pursue for a venue where you have a *sanctioned* purchase path:
  - **Preferred:** an official API/partner agreement that permits programmatic
    purchase, OR a deep-link that drops you onto a pre-filled, pre-authenticated
    checkout so the final tap is instant.
  - **Not recommended:** headless-browser bots that automate the public UI —
    high legal/ToS risk (BOTS Act), brittle, and frequently CAPTCHA-walled.
- Hard safety rails regardless of path:
  - Global kill switch + `--dry-run`.
  - Per-run and per-day **spend cap**; refuse to exceed it.
  - Exactly-once purchase lock (never double-buy on a retry).
  - Always quantity = 2, contiguous seats only, price ≤ threshold, then **stop**.
  - Confirmation push after any purchase attempt (success or failure).

### M6 — Deploy & operate (1 day)
- Run as a small always-on service (a $5 VPS, Fly.io, Railway, or a home box).
- Health checks + a heartbeat push so you know it's alive.
- Alert on source failures (API key expired, layout changed, rate-limited).

## 4. Configuration model (what you'll actually tune)

See [`config.example.yaml`](../config.example.yaml). Key knobs:

- **watch**: event name/date/venue + one or more `event_id`s per source.
- **criteria**: `quantity: 2`, `max_price_per_ticket`, `sections` allow/deny,
  `min_seats_together: 2`.
- **poll_interval**: per source (respect each API's rate limit; 15–60s typical).
- **channels**: which notifiers fire.
- **auto_buy**: `enabled: false` by default; `daily_spend_cap`, per-source path.

## 5. Effort & sequencing summary

| Milestone | Output | Rough effort |
|-----------|--------|--------------|
| M0 | Scaffold, config, storage | ½ day |
| M1 | SeatGeek watcher, normalized listings | 1–2 days |
| M2 | Matching + dedupe engine | 1 day |
| M3 | Push notifications with deep links | 1 day |
| M4 | StubHub + Ticketmaster sources | 2–4 days* |
| M5 | Opt-in auto-buy w/ safety rails | open-ended |
| M6 | Deploy + monitoring | 1 day |

\* gated on getting API/partner access, which can dominate the timeline.

**A useful, ToS-clean product exists at the end of M3** (notify-only, SeatGeek).
Everything after is incremental.

## 6. Open questions to answer before M1

1. **Which exact show?** Rush has multiple MSG dates possible on a tour — pin the
   date(s) so we can resolve the right `event_id` per venue.
2. **Notification channel preference?** Pushover/ntfy (simplest) vs Telegram
   (free + buttons) vs SMS (most reliable, costs money).
3. **Do you have (or can you get) developer/partner API access** for StubHub and
   Ticketmaster resale? This decides whether M4 is days or weeks.
4. **How far do you want to go on auto-buy** given the legal picture — instant
   one-tap assisted checkout (recommended) vs true hands-off automation?
5. **Budget/threshold**: max price per ticket, and a hard daily spend cap.
