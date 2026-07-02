# Legal & Terms-of-Service notes — read before enabling auto-buy

This tool is designed for **personal use**: watching for tickets to a show you want
to attend, and being notified fast. That use is normal and fine. The **automation of
the purchase step** is where the risk lives.

## The BOTS Act (US, 2016)
The federal **Better Online Ticket Sales (BOTS) Act** makes it unlawful to use
software to **circumvent a security measure, access-control system, or other control**
that a ticket seller uses to enforce posting/purchasing limits or maintain the order
of a purchase queue (CAPTCHAs, virtual waiting rooms, per-account purchase caps, etc.).
It also bars reselling tickets you know were obtained that way. Enforcement is by the
FTC and can carry significant civil penalties.

**What this means for us:**
- Being *notified* of a listing and buying it *yourself* — fine.
- Software that *defeats a CAPTCHA / queue / purchase-limit* to buy — not fine.

## Platform Terms of Service
Ticketmaster, SeatGeek, and StubHub each prohibit, in their ToS:
- automated access / scraping outside their official APIs,
- automated or bulk purchasing,
- circumventing rate limits or anti-bot measures.

They fingerprint traffic and, when they detect botting, **void the order and ban the
account** — so an "auto-buy bot" is not just risky, it's *unreliable*: you can win the
race and still lose the tickets.

## How this project stays on the right side
- **Use official APIs** for reading availability/prices. If no API exists for a venue,
  prefer a **user-driven feed** (a browser extension *you* run) over server-side
  scraping.
- **Respect rate limits** and each API's ToS.
- **Notification + one-tap deep-link** is the default and recommended path: it wins on
  reaction time without automating the purchase.
- The **`auto` purchase mode is disabled by default** and requires setting
  `I_UNDERSTAND_THE_RISKS=1`. It is provided for completeness and jurisdictions/uses
  where it may be permissible; **we do not recommend using it against the major US
  venues.** You are responsible for compliance with the BOTS Act, the venues' ToS, and
  your local law.

This document is not legal advice. If you plan to automate purchasing, consult a
lawyer for your jurisdiction.
