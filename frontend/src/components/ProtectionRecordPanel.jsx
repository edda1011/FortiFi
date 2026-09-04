import { useState } from "react";

import { createProtectionRecord, prepareProtectionRecord } from "../api/protection";


function ProtectionRecordPanel({ analysisId, account, baseTransaction = "" }) {
  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!account) return null;

  async function anchor() {
    setLoading(true);
    setError("");
    try {
      const prepared = await prepareProtectionRecord(analysisId, baseTransaction);
      const { ethers } = await import("ethers");
      const signer = await new ethers.BrowserProvider(window.ethereum).getSigner();
      const signature = await signer.signMessage(prepared.message);
      setRecord(await createProtectionRecord(analysisId, signature, baseTransaction));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sui recording failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="protection-record">
      <span className="dashboard-eyebrow">Sui integrity layer</span>
      <h3>Protection record</h3>
      <p>Sign this report hash, then FortiFi will sponsor its Sui testnet record.</p>
      {!record && <button type="button" onClick={anchor} disabled={loading}>{loading ? "Recording…" : "Anchor on Sui"}</button>}
      {error && <p className="thetanuts-error" role="alert">{error}</p>}
      {record && (
        <div className="protection-success">
          <strong>Integrity anchored</strong>
          <code>{record.report_hash}</code>
          <a href={record.explorer_url} target="_blank" rel="noreferrer">View Sui transaction</a>
        </div>
      )}
    </section>
  );
}


export default ProtectionRecordPanel;
