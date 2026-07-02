import { env } from "../config.js";
import type { Adapter } from "../types.js";
import { ticketmaster } from "./ticketmaster.js";
import { seatgeek } from "./seatgeek.js";
import { stubhub } from "./stubhub.js";
import { mock } from "./mock.js";

/** Returns the active adapters based on config + available credentials. */
export function activeAdapters(): Adapter[] {
  if (env.useMock) return [mock];
  return [ticketmaster, seatgeek, stubhub].filter((a) => a.enabled());
}
