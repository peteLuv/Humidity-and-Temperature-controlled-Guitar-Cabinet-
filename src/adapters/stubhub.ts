import { env } from "../config.js";
import type { Adapter, Watch, Listing } from "../types.js";

/**
 * StubHub adapter — PHASE 2 STUB.
 * StubHub's inventory API requires partner-program approval. Once you have an
 * app token, implement the catalog/inventory search here and normalize to Listing[].
 * Left disabled until credentials exist so the pipeline runs without it.
 */
export const stubhub: Adapter = {
  id: "stubhub",

  enabled() {
    return env.stubhubToken.length > 0;
  },

  async findListings(_watch: Watch): Promise<Listing[]> {
    // TODO(phase-2): call StubHub inventory API and map results to Listing[].
    return [];
  },
};
