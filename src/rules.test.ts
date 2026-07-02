import { test } from "node:test";
import assert from "node:assert/strict";
import { evaluate } from "./rules.js";
import type { Listing, Rules } from "./types.js";

const base: Listing = {
  id: "1",
  venue: "seatgeek",
  eventId: "e",
  eventName: "Rush @ MSG",
  section: "112",
  row: "8",
  quantity: 2,
  pricePerTicket: 200,
  totalPrice: 400,
  seatsTogether: true,
  currency: "USD",
  url: "https://example.com",
  seenAt: "2026-07-02T00:00:00Z",
};

const rules: Rules = {
  quantity: 2,
  maxPricePerTicket: 250,
  requireSeatsTogether: true,
  excludeSections: ["Obstructed View"],
};

test("matches a good listing", () => {
  assert.equal(evaluate(base, rules).match, true);
});

test("rejects wrong quantity", () => {
  assert.equal(evaluate({ ...base, quantity: 4 }, rules).match, false);
});

test("rejects over-price", () => {
  assert.equal(evaluate({ ...base, pricePerTicket: 300 }, rules).match, false);
});

test("rejects split seats when together required", () => {
  assert.equal(evaluate({ ...base, seatsTogether: false }, rules).match, false);
});

test("rejects excluded section", () => {
  assert.equal(evaluate({ ...base, section: "Obstructed View" }, rules).match, false);
});
