import { useEffect, useState } from "react";

import { createProtectionRecord, fetchProtectionRecord, prepareProtectionRecord } from "../api/protection";


function ProtectionRecordPanel({ analysisId, account, recordType = "analysis", initialRecord = null, onAnchored }) {
  const [record, setRecord] = useState(initialRecord);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setRecord(initialRecord);
    if (!account || initialRecord) return undefined;
    let cancelled = false;
    fetchProtectionRecord(analysisId, recordType)
      .then((saved) => { if (!cancelled) setRecord(saved); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : "Could not check Sui status."); });
    return () => { cancelled = true; };
  }, [account, analysisId, initialRecord, recordType]);

  if (!account) return null;

  async function anchor() {
    setLoading(true);
    setError("");
    try {
      const prepared = await prepareProtectionRecord(analysisId, recordType);
      const { ethers } = await import("ethers");
      const signer = await new ethers.BrowserProvider(window.ethereum).getSigner();
      const signature = await signer.signMessage(prepared.message);
      const saved = await createProtectionRecord(analysisId, recordType, signature);
      setRecord(saved);
      onAnchored?.(recordType, saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sui recording failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="protection-record">
      <span className="dashboard-eyebrow">Sui integrity layer</span>
      <div className="protection-record-card">
        <h3>{recordType === "analysis" ? "Analysis integrity record" : "Protection integrity record"}</h3>
        <p>{recordType === "analysis" ? "Anchor this analysis report hash on Sui to prove the saved report has not changed. This does not purchase protection." : "Anchor the completed option purchase and its linked analysis hash on Sui. The Base transaction remains the purchase proof."}</p>
        {!record && <button type="button" onClick={anchor} disabled={loading}>{loading ? "Recording…" : `Anchor ${recordType === "analysis" ? "Analysis" : "Protection"} Report on Sui`}</button>}
        {error && <p className="thetanuts-error" role="alert">{error}</p>}
        {record && (
          <div className="protection-success">
            <div className="protection-success-heading">
              <strong>{recordType === "analysis" ? "Analysis" : "Protection"} integrity anchored</strong>
              <span>This {recordType} report hash has already been anchored and cannot be anchored again.</span>
            </div>
            <div className="protection-record-data"><span>Report hash</span><code>{record.report_hash}</code></div>
            {record.anchored_at && <div className="protection-record-data protection-record-time"><span>Anchored</span><time>{new Date(record.anchored_at).toLocaleString("en-MY")}</time></div>}
            {record.sui_object_id && <div className="protection-record-data"><span>Record object</span><code>{record.sui_object_id}</code></div>}
            <a className="protection-record-link" href={record.explorer_url} target="_blank" rel="noreferrer">View Sui transaction</a>
          </div>
        )}
      </div>
    </section>
  );
}


export default ProtectionRecordPanel;
