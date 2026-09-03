import { apiFetch } from "./client";


/**
 * Analyze the risk for a wallet under a downside scenario.
 *
 * @param {string} address - public wallet address
 * @param {number} scenarioDownside - e.g. 0.20 for a 20% drop
 */
export async function analyzeRisk(address, scenarioDownside) {
  return apiFetch("/api/risk/analyze", {
    method: "POST",
    body: JSON.stringify({
      address,
      scenario_downside: scenarioDownside,
    }),
  });
}
