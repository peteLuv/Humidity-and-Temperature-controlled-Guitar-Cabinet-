# Rush @ MSG — Ticket Watcher & Buyer

A service that watches secondary-market ticket venues (SeatGeek, StubHub,
Ticketmaster/Ticketmaster Resale) for **Rush at Madison Square Garden**, pushes
a notification the moment a matching listing appears, and — when you opt in —
can attempt to buy **2 tickets** automatically once a listing drops below a
price threshold you set.

> **Read this first:** Fully automated ticket purchasing on these platforms is a
> legal and Terms-of-Service minefield (see
> [`docs/LEGAL-AND-COMPLIANCE.md`](docs/LEGAL-AND-COMPLIANCE.md)). The plan below
> ships a **safe default** — instant push notification + one-tap assisted
> checkout — and treats fully-automatic buying as an opt-in module you enable
> only where it is permitted and where you have credentials/authorization.

## What's in this folder

| File | Purpose |
|------|---------|
| [`docs/PLAN.md`](docs/PLAN.md) | The build plan: milestones, scope, decisions, effort |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How the pieces fit together |
| [`docs/DATA-SOURCES.md`](docs/DATA-SOURCES.md) | Each venue's API/feed options, auth, and limits |
| [`docs/LEGAL-AND-COMPLIANCE.md`](docs/LEGAL-AND-COMPLIANCE.md) | ToS, the BOTS Act, and what "auto-buy" really means |
| [`docs/CREDENTIALS.md`](docs/CREDENTIALS.md) | Step-by-step: getting every API key and notification credential |
| [`config.example.yaml`](config.example.yaml) | Watch targets, thresholds, notification channels |
| [`src/`](src) | Starter scaffold (TypeScript) with the interfaces to fill in |

## The idea in one diagram

```
 ┌─────────────┐   ┌─────────────┐   ┌───────────────┐
 │ SeatGeek     │   │ StubHub      │   │ Ticketmaster   │   poll / webhook
 │ source       │   │ source       │   │ source         │
 └──────┬───────┘   └──────┬───────┘   └───────┬────────┘
        │  normalized Listing events            │
        └───────────────┬──────────────────────┘
                        ▼
                ┌───────────────┐
                │ Rule engine    │  match event? under threshold?
                │ (per watch)    │  dedupe? already alerted?
                └───────┬───────┘
              match     │        under-threshold + auto-buy on
        ┌───────────────┴───────────────┐
        ▼                                ▼
 ┌───────────────┐              ┌──────────────────┐
 │ Notifier       │              │ Purchase module   │  (opt-in, gated)
 │ push/SMS/TG    │              │ deep-link or bot  │
 └───────────────┘              └──────────────────┘
```

## Quick start (once implemented)

```bash
cd rush-ticket-buyer
cp config.example.yaml config.yaml   # add your watch + channels
npm install
npm run dev                          # starts the watchers
```

See [`docs/PLAN.md`](docs/PLAN.md) for the milestone-by-milestone build order.
