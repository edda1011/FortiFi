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


export function findRecentClaim(claim) {
  return apiFetch("/api/claims/history-match", {
    method: "POST",
    body: JSON.stringify({ claim }),
  });
}


export function fetchTrash(limit = 50) {
  return apiFetch(`/api/claims/history-trash?limit=${limit}`);
}


export function deleteHistory(analysisId) {
  return apiFetch(`/api/claims/history/${analysisId}`, { method: "DELETE" });
}


export function restoreHistory(analysisId) {
  return apiFetch(`/api/claims/history/${analysisId}/restore`, { method: "POST" });
}


export function permanentlyDeleteHistory(analysisId) {
  return apiFetch(`/api/claims/history/${analysisId}/permanent`, { method: "DELETE" });
}

export function saveHedgeExecution(analysisId, execution) {
  return apiFetch(`/api/claims/history/${analysisId}/hedge`, {
    method: "POST",
    body: JSON.stringify(execution),
  });
}
