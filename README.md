# ticket-sentry

A watcher that monitors second-hand ticket venues (SeatGeek, StubHub, Ticketmaster)
for a target show, and fires a **push notification with a one-tap checkout deep-link**
the moment a listing appears under your price/quantity thresholds.

Built initially to grab **2 tickets to Rush at Madison Square Garden**, but the
event is fully configurable.

---

## What it does

1. **Listens** to multiple resale venues via their official APIs (and optional
   webhooks), normalizing every listing to a common shape.
2. **Filters** each new listing through a rules engine — max price, quantity
   (e.g. exactly 2), section/row allowlists, "seats must be together", etc.
3. **Alerts** you within seconds via push notification (ntfy / Pushover / APNs),
   including a **deep-link straight to that listing's checkout**.
4. **(Optional, off by default)** hands a matching listing to an assisted- or
   auto-checkout module.

## Why not just auto-buy everything?

Read [`docs/LEGAL.md`](docs/LEGAL.md). Short version: fully-automated checkout that
circumvents access controls (CAPTCHAs, queues, purchase limits) violates the US
**BOTS Act** and every venue's ToS, and detected bot orders get **voided and the
account banned**. For a 2-ticket personal buy the real bottleneck is *reaction
time*, and fast notification + one-tap checkout solves that inside the rules.
The auto-buy hook exists but ships **disabled** and requires an explicit opt-in.

## Status

Early scaffold. See [`docs/PLAN.md`](docs/PLAN.md) for the full build plan and
current phase.

## Quick start

```bash
cp .env.example .env        # add your API keys + push channel
npm install
npm run dev                 # starts the poll loop against config/watch.json
```

See [`docs/PLAN.md`](docs/PLAN.md) for how to get each venue's API access.
