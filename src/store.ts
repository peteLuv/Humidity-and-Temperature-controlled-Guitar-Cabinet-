import { existsSync, readFileSync, writeFileSync } from "node:fs";
import type { Listing } from "./types.js";

/**
 * Minimal dedup store so we notify each listing at most once.
 * File-backed Set for the scaffold; swap for SQLite/Redis in prod (see PLAN.md).
 */
export class SeenStore {
  private seen = new Set<string>();

  constructor(private path = "seen.json") {
    if (existsSync(path)) {
      try {
        this.seen = new Set(JSON.parse(readFileSync(path, "utf8")) as string[]);
      } catch {
        /* start fresh on corrupt file */
      }
    }
  }

  private key(l: Listing): string {
    // Prefer stable id; fall back to a fingerprint when ids churn between polls.
    return l.id
      ? `${l.venue}:${l.id}`
      : `${l.venue}:${l.section ?? "?"}:${l.row ?? "?"}:${l.quantity}:${l.pricePerTicket}`;
  }

  has(l: Listing): boolean {
    return this.seen.has(this.key(l));
  }

  add(l: Listing): void {
    this.seen.add(this.key(l));
    this.flush();
  }

  private flush(): void {
    writeFileSync(this.path, JSON.stringify([...this.seen]));
  }
}
