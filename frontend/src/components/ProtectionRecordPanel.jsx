import { useEffect, useState } from "react";

import { createProtectionRecord, fetchProtectionRecord, prepareProtectionRecord } from "../api/protection";


function ProtectionRecordPanel({ analysisId, account, baseTransaction = "", initialRecord = null, onAnchored }) {
  const [record, setRecord] = useState(initialRecord);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setRecord(initialRecord);
    if (!account || initialRecord) return undefined;
    let cancelled = false;
    fetchProtectionRecord(analysisId)
      .then((saved) => { if (!cancelled) setRecord(saved); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : "Could not check Sui status."); });
    return () => { cancelled = true; };
  }, [account, analysisId, initialRecord]);

  if (!account) return null;

  async function anchor() {
    setLoading(true);
    setError("");
    try {
      const prepared = await prepareProtectionRecord(analysisId, baseTransaction);
      const { ethers } = await import("ethers");
      const signer = await new ethers.BrowserProvider(window.ethereum).getSigner();
      const signature = await signer.signMessage(prepared.message);
      const saved = await createProtectionRecord(analysisId, signature, baseTransaction);
      setRecord(saved);
      onAnchored?.(saved);
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
          <span>This report hash has already been anchored and cannot be anchored again.</span>
          <code>{record.report_hash}</code>
          {record.anchored_at && <time>Anchored {new Date(record.anchored_at).toLocaleString("en-MY")}</time>}
          {record.sui_object_id && <code>Record object: {record.sui_object_id}</code>}
          <a href={record.explorer_url} target="_blank" rel="noreferrer">View Sui transaction</a>
        </div>
      )}
    </section>
  );
}


export default ProtectionRecordPanel;
