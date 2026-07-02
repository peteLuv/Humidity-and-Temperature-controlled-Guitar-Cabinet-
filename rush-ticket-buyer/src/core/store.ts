import Database from 'better-sqlite3';
import type { Listing } from '../types.js';

/**
 * Local state so restarts don't re-alert and retries don't double-buy.
 * See docs/ARCHITECTURE.md §7.
 */
export class Store {
  private db: Database.Database;

  constructor(path = 'ticketbuyer.db') {
    this.db = new Database(path);
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS seen_listings (
        listingId TEXT, source TEXT, lastPrice REAL, firstSeen TEXT,
        PRIMARY KEY (source, listingId)
      );
      CREATE TABLE IF NOT EXISTS purchases (
        idempotencyKey TEXT PRIMARY KEY, listingId TEXT, amount REAL, status TEXT, at TEXT
      );
      CREATE TABLE IF NOT EXISTS spend (day TEXT PRIMARY KEY, total REAL);
    `);
  }

  /** Returns true if this is a NEW listing or its price DROPPED (i.e. worth alerting). */
  isFreshOrCheaper(l: Listing, now: string): boolean {
    const row = this.db
      .prepare('SELECT lastPrice FROM seen_listings WHERE source=? AND listingId=?')
      .get(l.source, l.listingId) as { lastPrice: number } | undefined;

    const fresh = !row || l.pricePerTicket < row.lastPrice;
    this.db
      .prepare(
        `INSERT INTO seen_listings(listingId, source, lastPrice, firstSeen) VALUES(?,?,?,?)
         ON CONFLICT(source, listingId) DO UPDATE SET lastPrice=excluded.lastPrice`,
      )
      .run(l.listingId, l.source, l.pricePerTicket, now);
    return fresh;
  }

  /** Reserve an idempotency key. Returns false if this purchase was already attempted. */
  reservePurchase(idempotencyKey: string, listingId: string, now: string): boolean {
    try {
      this.db
        .prepare('INSERT INTO purchases(idempotencyKey, listingId, status, at) VALUES(?,?,?,?)')
        .run(idempotencyKey, listingId, 'reserved', now);
      return true;
    } catch {
      return false; // primary-key clash => already reserved
    }
  }

  recordPurchase(idempotencyKey: string, amount: number, status: string, day: string): void {
    this.db
      .prepare('UPDATE purchases SET amount=?, status=? WHERE idempotencyKey=?')
      .run(amount, status, idempotencyKey);
    if (status === 'purchased') {
      this.db
        .prepare(
          `INSERT INTO spend(day, total) VALUES(?, ?)
           ON CONFLICT(day) DO UPDATE SET total = total + excluded.total`,
        )
        .run(day, amount);
    }
  }

  spentToday(day: string): number {
    const row = this.db.prepare('SELECT total FROM spend WHERE day=?').get(day) as
      | { total: number }
      | undefined;
    return row?.total ?? 0;
  }
}
