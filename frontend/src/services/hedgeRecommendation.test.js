import test from "node:test";
import assert from "node:assert/strict";
import { buildProtectionChoices } from "./hedgeRecommendation.js";

const candidates = [
  { orderKey: "a", strike: 2050, expiry: "2026-09-19T00:00:00Z", pricePerContract: 80, availableAmount: 10, maxSpend: 25 },
  { orderKey: "b", strike: 2250, expiry: "2026-09-19T00:00:00Z", pricePerContract: 100, availableAmount: 10, maxSpend: 25 },
  { orderKey: "c", strike: 2425, expiry: "2026-09-19T00:00:00Z", pricePerContract: 130, availableAmount: 10, maxSpend: 25 },
];

test("builds distinct, deterministic choices within the maximum budget", () => {
  const input = { maxBudget: 25, preference: "balanced", spotPrice: 2500, now: Date.parse("2026-09-05T00:00:00Z") / 1000 };
  const first = buildProtectionChoices(candidates, input);
  const second = buildProtectionChoices(candidates, input);
  assert.deepEqual(first, second);
  assert.equal(new Set(first.map((item) => item.orderKey)).size, first.length);
  assert.ok(first.every((item) => item.spend <= 25));
  assert.equal(first.filter((item) => item.recommended).length, 1);
});

test("does not invent missing alternatives", () => {
  const choices = buildProtectionChoices(candidates.slice(0, 1), { maxBudget: 5, preference: "balanced", spotPrice: 2500 });
  assert.equal(choices.length, 1);
});

test("supports a one USDC demo budget", () => {
  const choices = buildProtectionChoices(candidates, { maxBudget: 1, preference: "balanced", spotPrice: 2500 });
  assert.ok(choices.length > 0);
  assert.ok(choices.every((item) => item.spend > 0 && item.spend <= 1));
});
