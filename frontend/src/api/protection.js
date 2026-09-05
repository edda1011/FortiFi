import { apiFetch } from "./client";


export function prepareProtectionRecord(analysisId, recordType) {
  return apiFetch("/api/protection/prepare", {
    method: "POST",
    body: JSON.stringify({ analysis_id: analysisId, record_type: recordType }),
  });
}


export function fetchProtectionRecord(analysisId, recordType) {
  return apiFetch(`/api/protection/${analysisId}/${recordType}`);
}


export function createProtectionRecord(analysisId, recordType, signature) {
  return apiFetch("/api/protection/record", {
    method: "POST",
    body: JSON.stringify({
      analysis_id: analysisId,
      record_type: recordType,
      signature,
    }),
  });
}
