import "dotenv/config";
import { readFileSync } from "node:fs";
import type { Watch } from "./types.js";

export const env = {
  ticketmasterKey: process.env.TICKETMASTER_API_KEY ?? "",
  seatgeekClientId: process.env.SEATGEEK_CLIENT_ID ?? "",
  seatgeekClientSecret: process.env.SEATGEEK_CLIENT_SECRET ?? "",
  stubhubToken: process.env.STUBHUB_APP_TOKEN ?? "",

  notifyProvider: (process.env.NOTIFY_PROVIDER ?? "ntfy") as "ntfy" | "pushover",
  ntfyTopic: process.env.NTFY_TOPIC ?? "",
  ntfyServer: process.env.NTFY_SERVER ?? "https://ntfy.sh",
  pushoverToken: process.env.PUSHOVER_TOKEN ?? "",
  pushoverUser: process.env.PUSHOVER_USER ?? "",

  purchaseMode: (process.env.PURCHASE_MODE ?? "notify") as "notify" | "assist" | "auto",
  acceptRisks: process.env.I_UNDERSTAND_THE_RISKS === "1",

  watchFile: process.env.WATCH_FILE ?? "config/watch.json",
  useMock: process.env.USE_MOCK === "1",
};

export function loadWatch(path = env.watchFile): Watch {
  const raw = readFileSync(path, "utf8");
  return JSON.parse(raw) as Watch;
}
