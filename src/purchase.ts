import { env } from "./config.js";
import type { Listing, Watch } from "./types.js";

/**
 * Purchase hook. Three modes (see docs/LEGAL.md):
 *   notify  — do nothing (notification already sent by the caller).
 *   assist  — log/emit the deep-link for one-tap manual checkout.
 *   auto    — headless checkout. DISABLED unless I_UNDERSTAND_THE_RISKS=1.
 *             Not implemented and not recommended against major US venues.
 */
export async function handlePurchase(listing: Listing, watch: Watch): Promise<void> {
  const mode = watch.purchaseMode ?? env.purchaseMode;

  if (mode === "notify") return;

  if (mode === "assist") {
    console.log(`[assist] one-tap checkout ready → ${listing.url}`);
    return;
  }

  if (mode === "auto") {
    if (!env.acceptRisks) {
      console.warn(
        "[auto] purchaseMode=auto but I_UNDERSTAND_THE_RISKS!=1 — refusing. See docs/LEGAL.md.",
      );
      return;
    }
    // Intentionally NOT implemented. Automating checkout that circumvents access
    // controls violates the BOTS Act and venue ToS, and detected orders get voided.
    // If you enable this, you assume full legal responsibility. See docs/LEGAL.md.
    console.warn(
      "[auto] auto-checkout is a deliberate no-op in this scaffold. " +
        "Implement per-venue at your own risk after reading docs/LEGAL.md.",
    );
    return;
  }
}
