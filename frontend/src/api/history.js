import { apiFetch } from "./client";


export function fetchHistory(limit = 50) {
  return apiFetch(`/api/claims/history?limit=${limit}`);
}


export function fetchHistoryDetail(analysisId) {
  return apiFetch(`/api/claims/history/${analysisId}`);
}


export function askHistoryFollowUp(analysisId, question) {
  return apiFetch(`/api/claims/history/${analysisId}/follow-up`, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
