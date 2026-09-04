import { apiFetch } from "./client";


export function prepareProtectionRecord(analysisId, baseTransaction = "") {
  return apiFetch("/api/protection/prepare", {
    method: "POST",
    body: JSON.stringify({ analysis_id: analysisId, base_transaction: baseTransaction }),
  });
}


export function fetchProtectionRecord(analysisId) {
  return apiFetch(`/api/protection/${analysisId}`);
}


export function createProtectionRecord(analysisId, signature, baseTransaction = "") {
  return apiFetch("/api/protection/record", {
    method: "POST",
    body: JSON.stringify({
      analysis_id: analysisId,
      signature,
      base_transaction: baseTransaction,
    }),
  });
}
