import type { Listing, BuyOptions, PurchaseModule, PurchaseResult } from '../types.js';
import type { Store } from '../core/store.js';

/**
 * Wraps any PurchaseModule with the safety rails from docs/LEGAL-AND-COMPLIANCE.md:
 * kill switch, spend caps, exactly-once, dry-run. NEVER purchase without going
 * through this guard.
 */
export class SpendGuard {
  constructor(
    private store: Store,
    private opts: {
      enabled: boolean;
      dailyCap: number;
      perRunCap: number;
      today: string; // 'YYYY-MM-DD', injected (no Date.now in pure code paths)
    },
  ) {}

  async attempt(
    inner: PurchaseModule,
    listing: Listing,
    buy: BuyOptions,
  ): Promise<PurchaseResult> {
    if (!this.opts.enabled) return { status: 'skipped', reason: 'auto_buy disabled (kill switch)' };

    const total = listing.pricePerTicket * buy.quantity;
    if (total > this.opts.perRunCap)
      return { status: 'skipped', reason: `exceeds per-run cap (${total} > ${this.opts.perRunCap})` };

    const spent = this.store.spentToday(this.opts.today);
    if (spent + total > this.opts.dailyCap)
      return { status: 'skipped', reason: `exceeds daily cap (${spent}+${total} > ${this.opts.dailyCap})` };

    // Exactly-once: reserve the idempotency key before we ever touch a checkout.
    if (!this.store.reservePurchase(buy.idempotencyKey, listing.listingId, this.opts.today))
      return { status: 'skipped', reason: 'already attempted (idempotency)' };

    const result = await inner.buy(listing, buy);
    this.store.recordPurchase(
      buy.idempotencyKey,
      result.amount ?? total,
      result.status === 'dry_run' ? 'dry_run' : result.status,
      this.opts.today,
    );
    return result;
  }
}
