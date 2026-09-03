import { apiFetch } from "./client";


/**
 * Fetch the current FortiFi dashboard summary.
 */
export async function fetchDashboard() {
  return apiFetch("/api/dashboard/summary");
}
