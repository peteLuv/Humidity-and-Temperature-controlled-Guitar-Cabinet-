# Data Sources

> Verify current terms and endpoints against each provider's live developer docs
> before building — programs, gating, and rate limits change. The notes below are
> the lay of the land as of this plan, not a substitute for their docs.

## Summary

| Venue | Public API for event data | Live resale listings + prices | Programmatic purchase | Practical path |
|-------|---------------------------|-------------------------------|-----------------------|----------------|
| **SeatGeek** | Yes (Platform API) | Partner-gated (affiliate/partner tier) | No public path | Best to prototype; event lookup easy, deep-link to listing |
| **StubHub** | Partner API (application/approval) | Partner-gated | Partner-gated | Apply for developer access; strong for listings if approved |
| **Ticketmaster** | Yes (Discovery API) | Limited — resale/inventory is partner-gated | No public path | Discovery gives events; resale + buy need partner status |

**Takeaway:** event *discovery* is easy on all three; the *live individual-listing
firehose with prices* and *programmatic buying* are the gated parts. Plan for an
application/approval step, and design the notify-only product to be valuable
without them.

## SeatGeek
- **API:** SeatGeek Platform API. Client ID/secret; good for resolving the Rush @
  MSG **event id**, event metadata, and stats like `lowest_price`.
- **Listings:** individual seller listings/prices are a partner/affiliate feature,
  not fully open. `lowest_price` / price ranges are available at the event level
  and are still useful for a threshold-on-cheapest strategy.
- **Purchase:** no sanctioned public "buy via API" — deep-link the user to the
  listing/checkout instead.
- **Why start here:** cleanest auth, best docs, easiest event resolution.

## StubHub
- **API:** StubHub has a developer/partner API. Access is via application and
  approval; historically OAuth-based. When approved it exposes event search and
  **listing-level inventory** (section, row, quantity, price), which is exactly
  what the rule engine wants.
- **Purchase:** any programmatic checkout is partner-gated and governed by your
  agreement — do not attempt to automate the public UI (see LEGAL doc).
- **Effort:** dominated by getting approved. Once you have keys, the source
  implementation is straightforward.

## Ticketmaster (incl. Ticketmaster Resale / Verified Resale)
- **API:** Ticketmaster **Discovery API** (API key, generous for event/venue
  search) resolves the Rush @ MSG event and its `id`. Great for the "does the
  event exist / on-sale status" side.
- **Listings/Resale:** live resale inventory and pricing are **not** fully in the
  public Discovery API — resale/inventory feeds are partner-gated (Partner API /
  commerce agreements). Primary on-sale inventory is likewise not a public buy API.
- **Purchase:** no public programmatic purchase; automating the public checkout
  is a direct BOTS-Act/ToS concern.

## Auth & secrets
Store every credential in env vars / a local `.env` (never in `config.yaml`,
never committed):

```
SEATGEEK_CLIENT_ID=...
SEATGEEK_CLIENT_SECRET=...
STUBHUB_APP_TOKEN=...
TICKETMASTER_API_KEY=...
PUSHOVER_TOKEN=...           # or TELEGRAM_BOT_TOKEN / TWILIO_*
```

## Rate limits & etiquette
- Poll at the slowest interval that still meets your speed goal (15–60s typical).
  Add jitter; back off on 429; cache event-id lookups.
- Prefer webhooks where a provider offers them (fewer calls, faster reaction).
- One well-behaved client is fine; do not run many parallel scrapers — that's how
  keys get revoked.

## Notification providers (pick one to start)
| Provider | Cost | Push to phone | Buttons/deep-link | Notes |
|----------|------|---------------|-------------------|-------|
| **ntfy.sh** | Free (self-host option) | Yes | Link actions | Simplest; no account needed |
| **Pushover** | ~one-time small fee | Yes | Supplementary URL | Very reliable, clean apps |
| **Telegram bot** | Free | Yes | Inline buttons | Great UX; "Open checkout" button |
| **Twilio SMS** | Per-message | Yes (SMS) | Link in text | Most reliable delivery, costs money |
