const PROFILE_CONFIG = [
  { id: "basic", label: "Basic Protection", spendRatio: 0.4, strikeRatio: 0.82 },
  { id: "balanced", label: "Balanced Protection", spendRatio: 0.7, strikeRatio: 0.9 },
  { id: "strong", label: "Strong Protection", spendRatio: 1, strikeRatio: 0.97 },
];

const PREFERENCE_PROFILE = {
  lower_cost: "basic",
  balanced: "balanced",
  stronger: "strong",
};

function scoreCandidate(candidate, profile, preference, spotPrice, now) {
  const strikeDistance = Math.abs(candidate.strike / spotPrice - profile.strikeRatio);
  const days = Math.max(0, (new Date(candidate.expiry).getTime() / 1000 - now) / 86400);
  const expiryDistance = Math.abs(days - 14) / 30;
  const premiumEfficiency = candidate.pricePerContract / Math.max(candidate.strike, 1);
  const liquidityPenalty = 1 / Math.max(candidate.availableAmount, 1);
  const strikeWeight = preference === "stronger" ? 0.55 : 0.4;
  const premiumWeight = preference === "lower_cost" ? 0.35 : 0.2;
  return strikeDistance * strikeWeight
    + expiryDistance * 0.25
    + premiumEfficiency * premiumWeight
    + liquidityPenalty * 0.15;
}

export function buildProtectionChoices(candidates, { maxBudget, preference = "balanced", spotPrice, now = Date.now() / 1000 }) {
  const used = new Set();
  const choices = [];

  for (const profile of PROFILE_CONFIG) {
    const eligible = candidates
      .filter((candidate) => !used.has(candidate.orderKey))
      .map((candidate) => ({
        ...candidate,
        profile,
        spend: Math.min(maxBudget * profile.spendRatio, candidate.maxSpend),
        score: scoreCandidate(candidate, profile, preference, spotPrice, now),
      }))
      .filter((candidate) => candidate.spend >= 0.01)
      .sort((left, right) => left.score - right.score);
    if (!eligible.length) continue;
    used.add(eligible[0].orderKey);
    choices.push(eligible[0]);
  }

  const preferredProfile = PREFERENCE_PROFILE[preference] || "balanced";
  const preferred = choices.find((choice) => choice.profile.id === preferredProfile)
    || choices.find((choice) => choice.profile.id === "balanced")
    || choices[0];

  return choices.map((choice) => ({
    ...choice,
    recommended: choice.orderKey === preferred?.orderKey,
    reason: choice.profile.id === "basic"
      ? "Uses less of your budget and targets protection against a larger ETH decline."
      : choice.profile.id === "strong"
        ? "Uses more of your budget for a strike closer to the current ETH price."
        : "Balances premium cost, strike distance and time to expiry.",
  }));
}
