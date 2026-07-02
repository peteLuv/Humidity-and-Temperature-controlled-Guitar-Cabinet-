# Legal & Compliance — read before enabling auto-buy

This is a practical summary written by an engineer, **not legal advice**. If you
plan to run the auto-buy module, get a real lawyer's read for your situation.

## The three constraints

### 1. The BOTS Act (US, 2016)
The federal *Better Online Ticket Sales Act* makes it unlawful to:
- **circumvent** a security measure, access-control system, or other technical
  control a ticket seller uses to enforce posted purchase limits or maintain the
  order of an online queue; or
- **sell** tickets you know were obtained that way.

A bot that automates a public checkout to beat purchase limits or the queue is
squarely what this targets. The FTC has brought enforcement actions with large
penalties. This is the single biggest reason the plan defaults to
**notify + one-tap human checkout** rather than hands-off automation.

### 2. Platform Terms of Service
SeatGeek, StubHub, and Ticketmaster all prohibit, in their ToS:
- automated access / scraping / crawling of their sites,
- using bots or scripts to purchase, and
- circumventing rate limits, CAPTCHAs, or access controls.

Violating ToS can get your account and API keys banned and purchases voided —
even where it isn't itself illegal. Their **official APIs / partner programs** are
the sanctioned path; use those and stay within their rules.

### 3. State law
Several US states (NY included — relevant for MSG) have their own ticket-bot
statutes and resale rules layered on top of federal law. New York has been
particularly active on ticket-bot enforcement.

## What this means for the design

| Approach | Status | In this plan |
|----------|--------|--------------|
| Watch official/partner APIs, notify you, you tap to buy | Clean if within each API's ToS | **Default (M1–M4)** |
| Programmatic purchase via an API/agreement that *permits* it | Allowed within that agreement | **Preferred auto-buy path (M5)** |
| Headless-browser bot automating the public checkout UI | ToS violation; BOTS-Act risk | **Not implemented / not recommended** |
| Scraping listing pages you have no API access to | ToS violation | **Avoid** |

## Guardrails baked into the (opt-in) purchase module
Even on a sanctioned path, the `PurchaseModule` is wrapped with:
- **Global kill switch** and `--dry-run` (default on until you flip it).
- **Daily + per-run spend cap** — refuses to exceed it.
- **Exactly-once purchase lock** — an idempotency key so a retry never double-buys.
- **Strict quantity/price** — exactly 2 contiguous seats, `price <= threshold`,
  then stop.
- **Confirmation push** on every attempt (success or failure) so nothing happens
  silently.

## Bottom line
You can build something genuinely useful and fully above-board today: **fast
detection + instant push + one-tap manual checkout**. Treat true automation as a
narrow, opt-in extension you only turn on where a provider explicitly permits
programmatic purchase — not by scripting a public checkout page.
