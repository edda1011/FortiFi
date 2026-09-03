import { apiFetch } from "./client";


/**
 * Fetch the current FortiFi dashboard summary.
 */
export async function fetchDashboard() {
  return apiFetch("/api/dashboard/summary");
}

export async function fetchDashboardNews() {
  return apiFetch("/api/dashboard/news");
}
