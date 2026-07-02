import { request } from "undici";
import { env } from "./config.js";
import type { Listing } from "./types.js";

/**
 * Sends a push notification whose click action deep-links straight to the listing.
 * Default provider is ntfy (free); Pushover supported too.
 */
export async function notify(listing: Listing): Promise<void> {
  const title = `${listing.quantity}x ${listing.eventName} @ $${listing.pricePerTicket}`;
  const body =
    `${listing.venue.toUpperCase()} — ` +
    [
      listing.section && `Sec ${listing.section}`,
      listing.row && `Row ${listing.row}`,
      `total $${listing.totalPrice}`,
    ]
      .filter(Boolean)
      .join(" · ");

  if (env.notifyProvider === "pushover") {
    await pushover(title, body, listing.url);
  } else {
    await ntfy(title, body, listing.url);
  }
  console.log(`[notify] ${title} — ${listing.url}`);
}

async function ntfy(title: string, body: string, url: string): Promise<void> {
  if (!env.ntfyTopic) {
    console.warn("[notify] NTFY_TOPIC unset — skipping push (logged above).");
    return;
  }
  await request(`${env.ntfyServer}/${env.ntfyTopic}`, {
    method: "POST",
    headers: {
      Title: title,
      Click: url, // tap the notification → opens the listing
      Priority: "high",
      Tags: "tickets",
    },
    body,
  });
}

async function pushover(title: string, body: string, url: string): Promise<void> {
  if (!env.pushoverToken || !env.pushoverUser) {
    console.warn("[notify] Pushover creds unset — skipping push (logged above).");
    return;
  }
  await request("https://api.pushover.net/1/messages.json", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      token: env.pushoverToken,
      user: env.pushoverUser,
      title,
      message: body,
      url,
      url_title: "Open listing",
      priority: "1",
    }).toString(),
  });
}
