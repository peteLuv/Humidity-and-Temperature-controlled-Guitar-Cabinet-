# Getting Your Credentials — Step-by-Step

Everything the service needs lives in `.env` (copy `.env.example` → `.env`).
This guide walks through obtaining each credential, in the order you'll want
them. Times are rough; the two "apply and wait" ones (StubHub, Ticketmaster
partner) are worth kicking off on day one.

> URLs and program names change — if a link 404s, search the provider's site
> for "developer" or "API". Nothing here requires a company; a personal
> account works for the prototype tier everywhere except the partner programs.

## Order of operations (what to do today)

| # | Credential | Effort | Blocking? |
|---|-----------|--------|-----------|
| 1 | ntfy topic (notifications) | 2 min | No — instant |
| 2 | SeatGeek client ID/secret | ~10 min | No — self-serve |
| 3 | Ticketmaster Discovery API key | ~10 min | No — self-serve |
| 4 | StubHub developer application | 15 min + wait | Yes — approval queue |
| 5 | Ticketmaster partner/resale access | 15 min + wait | Yes — partner review |
| 6 | (Optional) Pushover / Telegram / Twilio | 10–20 min | No |

---

## 1. ntfy (push notifications) — 2 minutes, free, no account

1. Install the **ntfy** app ([iOS](https://apps.apple.com/us/app/ntfy/id1625396347) / [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy)).
2. Pick a topic name that's long and unguessable — the topic *is* the password
   on the public server. Something like `rush-msg-x7Qp2vR9tK`.
3. In the app: **Subscribe to topic** → enter your topic name.
4. Put the topic in `config.yaml` under `notifications.ntfy.topic`.
   Leave `NTFY_SERVER=https://ntfy.sh` in `.env` (or point it at a self-hosted
   instance later).
5. Test from any terminal:
   ```bash
   curl -d "hello from the ticket watcher" ntfy.sh/rush-msg-x7Qp2vR9tK
   ```
   Your phone should buzz. That's the whole integration.

## 2. SeatGeek — ~10 minutes, self-serve

1. Create/sign in to a normal SeatGeek account at [seatgeek.com](https://seatgeek.com).
2. Go to the developer/apps page: **seatgeek.com/account/develop**
   (also reachable via the SeatGeek Platform docs at platform.seatgeek.com).
3. **Register a new app**. Name it anything (e.g. "rush-msg-watcher"); for the
   website/redirect fields a placeholder like your GitHub repo URL is fine —
   we use server-to-server calls, not OAuth redirects.
4. Copy the **Client ID** and **Client Secret** it issues.
5. Add to `.env`:
   ```
   SEATGEEK_CLIENT_ID=your_client_id
   SEATGEEK_CLIENT_SECRET=your_client_secret
   ```
6. Smoke-test (should return JSON with MSG events):
   ```bash
   curl "https://api.seatgeek.com/2/events?venue.name=madison+square+garden&client_id=$SEATGEEK_CLIENT_ID"
   ```

**Note:** this self-serve tier gives event data + price stats (`lowest_price`
etc.). Per-listing inventory is a partner/affiliate feature — if you want it,
contact their partnerships team (partners@seatgeek.com / the "Partner with us"
page) and describe the use case. Not required for M1–M3.

## 3. Ticketmaster Discovery API — ~10 minutes, self-serve

1. Go to [developer.ticketmaster.com](https://developer.ticketmaster.com).
2. **Create an account** (personal email is fine), verify it.
3. In **My Apps**, create a new app → you get a **Consumer Key** immediately.
   That key *is* the API key for the Discovery API.
4. Add to `.env`:
   ```
   TICKETMASTER_API_KEY=your_consumer_key
   ```
5. Smoke-test:
   ```bash
   curl "https://app.ticketmaster.com/discovery/v2/events.json?keyword=rush&venueId=KovZpZA7AAEA&apikey=$TICKETMASTER_API_KEY"
   ```
   (`KovZpZA7AAEA` is MSG's venue id in Discovery; verify with a venue search
   if it doesn't return.)
6. Default quota is generous for our polling (~5000 calls/day, 5 req/s) —
   fine at a 30s interval.

**Partner/resale access (the gated part):** live resale inventory and anything
transactional requires the partner program. On the same developer portal, find
the **Partner APIs / "Get Access"** section and submit the form (they ask what
you're building, expected volume, company info — be honest that it's a
personal purchase-assistant; approval is not guaranteed for individuals).
This can take weeks; the Discovery-based watcher works without it.

## 4. StubHub — apply, then wait

1. Go to [developer.stubhub.com](https://developer.stubhub.com).
2. Create an account and submit the **API access application** — they ask for
   your use case; describe it as a personal price-watch/notification tool.
3. Once approved, create an application in the portal to get your **app token**
   (their OAuth client credentials; the portal shows how to exchange them for
   an access token).
4. Add to `.env`:
   ```
   STUBHUB_APP_TOKEN=your_token
   ```
5. Until approval lands, keep `sources.stubhub.enabled: false` in `config.yaml`
   — the service runs fine on SeatGeek + Ticketmaster Discovery alone.

## 5. Optional notification channels

### Pushover (~$5 one-time, very reliable)
1. Sign up at [pushover.net](https://pushover.net); buy the mobile app.
2. Your **User Key** is on the dashboard after login.
3. **Create an Application/API Token** (dashboard → "Create an Application") →
   copy the **API Token**.
4. `.env`: `PUSHOVER_TOKEN=...` and `PUSHOVER_USER=...`;
   enable in `config.yaml`.

### Telegram bot (free, has buttons)
1. In Telegram, message **@BotFather** → `/newbot` → follow prompts →
   copy the **bot token**.
2. Send your new bot any message (this opens the chat).
3. Get your **chat id**:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
   ```
   → find `"chat":{"id":123456789,...}` in the response.
4. `.env`: `TELEGRAM_BOT_TOKEN=...`; put the chat id in
   `config.yaml` under `notifications.telegram.chat_id`.

### Twilio SMS (per-message cost, most reliable delivery)
1. Sign up at [twilio.com](https://www.twilio.com/try-twilio); verify your
   personal number.
2. From the Console dashboard copy **Account SID** and **Auth Token**.
3. Buy a phone number (Console → Phone Numbers → Buy, ~$1/mo) — that's your
   `TWILIO_FROM_NUMBER`.
4. `.env`: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`;
   your own cell goes in `config.yaml` as `to_number`.
5. Note: trial accounts can only text verified numbers and prefix messages
   with a trial notice — fine for this use.

## 6. Wire it all up

```bash
cd rush-ticket-buyer
cp .env.example .env          # paste in the keys from above
cp config.example.yaml config.yaml
# edit config.yaml: your ntfy topic, thresholds, enable sources you have keys for
npm install
npm run dev
```

> ⚠️ **Do not leave the placeholder date.** `config.example.yaml` ships
> `event_dates: ["2026-XX-XX"]`. If you copy it without pinning the real show
> date(s), the date filter matches nothing and the service will run "healthy"
> while silently discarding every listing. Replace it with the actual ISO
> date(s), or an empty list `[]` to match any date at the venue.

## Security hygiene

- `.env` and `config.yaml` are already in `.gitignore` — **never commit them**.
- Treat the ntfy topic name like a password (anyone who knows it can read
  your alerts and send you fakes). Use a random suffix; rotate if leaked.
- If a key ever lands in a commit or a paste, revoke and reissue it — all
  four portals let you regenerate credentials.
- The purchase-path credentials (payment methods, venue account logins) are
  deliberately NOT part of this setup — see `LEGAL-AND-COMPLIANCE.md` before
  going anywhere near auto-buy.
