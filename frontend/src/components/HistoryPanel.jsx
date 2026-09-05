import { useEffect, useState } from "react";

import {
  askHistoryFollowUp,
  deleteHistory,
  fetchHistory,
  fetchHistoryDetail,
  fetchTrash,
  permanentlyDeleteHistory,
  restoreHistory,
  saveHedgeExecution,
} from "../api/history";
import ReasoningTrace from "./ReasoningTrace.jsx";
import ProtectionRecordPanel from "./ProtectionRecordPanel.jsx";
import ThetanutsHedgePanel from "./ThetanutsHedgePanel.jsx";


function formatPercentage(value) {
  return `${(value * 100).toFixed(0)}%`;
}


function formatDate(value) {
  return new Intl.DateTimeFormat("en-MY", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}


function VerdictBadge({ verdict }) {
  return (
    <span className={`verdict verdict-${verdict.toLowerCase()}`}>
      {verdict.replace("_", " ")}
    </span>
  );
}


function ModelCoverageBadge({ count }) {
  return (
    <span className={`model-coverage model-coverage-${count >= 3 ? "full" : "fast"}`}>
      {count >= 3 ? "3 models · Full consensus" : `${count} models · Fast consensus`}
    </span>
  );
}


function HistoryList({ items, selectedId, onSelect }) {
  if (items.length === 0) {
    return (
      <div className="history-empty">
        <h3>No saved analyses yet</h3>
        <p>Complete a Claim Check and it will appear here automatically.</p>
      </div>
    );
  }

  return (
    <div className="history-list">
      {items.map((item) => (
        <button
          type="button"
          className={item.analysis_id === selectedId ? "history-row history-row-active" : "history-row"}
          key={item.analysis_id}
          onClick={() => onSelect(item.analysis_id)}
        >
          <span className="history-row-top">
            <span className="history-row-badges">
              <VerdictBadge verdict={item.verdict} />
              {item.anchored && <span className="sui-anchor-badge">Anchored on Sui</span>}
            </span>
            <time>{formatDate(item.created_at)}</time>
          </span>
          <strong>{item.claim}</strong>
          <span className="history-row-metrics">
            {formatPercentage(item.credibility_score)} credibility
            <span aria-hidden="true">·</span>
            {formatPercentage(item.confidence)} confidence
            <span aria-hidden="true">·</span>
            <ModelCoverageBadge count={item.model_count} />
          </span>
        </button>
      ))}
    </div>
  );
}


function HistoryDetail({ detail, loading, account, wallet, onBack, onDelete, onFollowUp, onAnalyzeWithAll, onAnchored, onHedgePurchased }) {
  const [question, setQuestion] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [showProtection, setShowProtection] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) return;

    setSubmitting(true);
    setError("");
    try {
      await onFollowUp(trimmedQuestion);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Follow-up failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading || !detail) {
    return <div className="history-detail-loading">Loading saved analysis…</div>;
  }

  const { analysis } = detail;
  const modelCount = analysis.consensus.model_results.length;
  const isEthReport = analysis.detected_assets?.includes("ETH");

  return (
    <article className="history-detail">
      <button type="button" className="history-back" onClick={onBack}>
        Back to all history
      </button>

      <div className="history-delete-control">
        {!confirmingDelete ? (
          <button type="button" className="history-delete" onClick={() => setConfirmingDelete(true)}>
            Delete analysis
          </button>
        ) : (
          <div className="history-delete-confirm" role="alert">
            <span>Move this analysis and its follow-ups to Trash?</span>
            <button type="button" className="button-secondary" onClick={() => setConfirmingDelete(false)}>Cancel</button>
            <button type="button" className="history-delete" onClick={onDelete}>Move to Trash</button>
          </div>
        )}
      </div>

      <div className="history-detail-heading">
        <div>
          <time>{formatDate(detail.created_at)}</time>
          <h2>{analysis.claim}</h2>
        </div>
        <div className="history-detail-badges">
          <ModelCoverageBadge count={modelCount} />
          <VerdictBadge verdict={analysis.final_assessment.verdict} />
        </div>
      </div>

      {modelCount < 3 && (
        <section className="fast-report-notice">
          <div>
            <strong>This report used Fast Consensus</strong>
            <p>It was based on {modelCount} AI models. Run all 3 models for a fuller assessment.</p>
          </div>
          <button type="button" onClick={() => onAnalyzeWithAll(analysis.claim)}>
            Analyze with 3 Models
          </button>
        </section>
      )}

      <div className="history-score-strip">
        <div><span>Credibility</span><strong>{formatPercentage(analysis.consensus.credibility_score)}</strong></div>
        <div><span>Confidence</span><strong>{formatPercentage(analysis.consensus.confidence)}</strong></div>
        <div><span>Market impact</span><strong>{analysis.consensus.market_impact}</strong></div>
        <div><span>Sources</span><strong>{analysis.evidence.length}</strong></div>
      </div>

      <section className="history-assessment">
        <h3>Saved assessment</h3>
        <p>{analysis.final_assessment.analysis}</p>
      </section>

      <section className="history-request-ids">
        <h3>Individual model reasoning</h3>
        {analysis.consensus.model_results.map((result) => (
          <article className="history-model-result" key={result.model}>
            <div className="history-model-heading">
              <h4>{result.model}</h4>
              <VerdictBadge verdict={result.verdict} />
            </div>
            <p>{result.reasoning_summary}</p>
            <ReasoningTrace result={result} />
            <div className="history-request-id">
              <span>Gonka Request ID</span>
              <code>{result.request_id || "Not available"}</code>
            </div>
          </article>
        ))}
      </section>

      {analysis.evidence.length > 0 && (
        <section className="history-sources">
          <h3>Evidence retained with this analysis</h3>
          {analysis.evidence.map((item) => (
            <a href={item.url} target="_blank" rel="noreferrer" key={item.url}>
              <strong>{item.title}</strong>
              <span>{item.source}</span>
            </a>
          ))}
        </section>
      )}

      {detail.hedge_execution && (
        <section className="history-assessment">
          <h3>Executed ETH protection</h3>
          <p><strong>{detail.hedge_execution.profile}</strong> · {formatPercentage(detail.hedge_execution.premium / detail.hedge_execution.max_budget)} of the selected budget used</p>
          <p>Strike {detail.hedge_execution.strike.toLocaleString("en-US", { style: "currency", currency: "USD" })} · expires {new Date(detail.hedge_execution.expiry).toLocaleDateString("en-MY")}</p>
          <p>{detail.hedge_execution.recommendation_reason}</p>
          <a href={`https://basescan.org/tx/${detail.hedge_execution.transaction_hash}`} target="_blank" rel="noreferrer">View Base transaction</a>
        </section>
      )}

      {isEthReport && (
        <section className="history-current-protection">
          <div>
            <h3>Current ETH protection</h3>
            <p>Check today’s live Thetanuts orders for this saved report. Historical quotes are never reused.</p>
          </div>
          {!showProtection && <button type="button" onClick={() => setShowProtection(true)}>Find Current Protection</button>}
          {showProtection && (
            <ThetanutsHedgePanel
              detectedAssets={analysis.detected_assets || []}
              detectionSources={analysis.asset_detection_sources || []}
              account={account}
              wallet={wallet}
              riskLevel={analysis.consensus.market_impact}
              ethExposurePercent={analysis.portfolio_context?.allocations?.ETH || 0}
              onPurchased={onHedgePurchased}
            />
          )}
        </section>
      )}

      <ProtectionRecordPanel
        analysisId={analysis.analysis_id}
        account={account}
        recordType="analysis"
        initialRecord={detail.analysis_record}
        onAnchored={onAnchored}
      />

      {detail.hedge_execution && (
        <ProtectionRecordPanel
          analysisId={analysis.analysis_id}
          account={account}
          recordType="protection"
          initialRecord={detail.protection_record}
          onAnchored={onAnchored}
        />
      )}

      <section className="follow-up-section">
        <div className="follow-up-heading">
          <h3>Ask about this assessment</h3>
          <p>Answers use only the saved analysis and its retained evidence.</p>
        </div>

        {detail.follow_ups.length > 0 && (
          <div className="follow-up-thread">
            {detail.follow_ups.map((item) => (
              <div className="follow-up-exchange" key={item.follow_up_id}>
                <p className="follow-up-question">{item.question}</p>
                <div className="follow-up-answer">
                  <span>FortiFi</span>
                  <p>{item.answer}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {error && <p className="follow-up-error" role="alert">{error}</p>}

        <form className="follow-up-form" onSubmit={handleSubmit}>
          <label htmlFor="follow-up-question">Follow-up question</label>
          <textarea
            id="follow-up-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What evidence is missing from this assessment?"
            maxLength={2000}
            disabled={submitting}
          />
          <div className="input-footer">
            <span>{question.length} / 2,000</span>
            <button type="submit" disabled={submitting || !question.trim()}>
              {submitting ? "Answering…" : "Ask follow-up"}
            </button>
          </div>
        </form>
      </section>
    </article>
  );
}


function HistoryPanel({ connected, account, wallet, onAnalyzeWithAll }) {
  const [items, setItems] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [showTrash, setShowTrash] = useState(false);
  const [trash, setTrash] = useState([]);
  const [trashLoading, setTrashLoading] = useState(false);
  const [undoId, setUndoId] = useState(null);
  const [permanentDeleteId, setPermanentDeleteId] = useState(null);

  useEffect(() => {
    if (!connected) {
      setItems([]);
      setLoading(false);
      return undefined;
    }
    setLoading(true);
    let cancelled = false;
    fetchHistory()
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load history.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [connected]);

  if (!connected) {
    return (
      <section className="history-shell">
        <div className="history-empty">
          <h3>Connect your Base wallet to save history</h3>
          <p>Guest analyses stay only on this page and disappear after refresh.</p>
        </div>
      </section>
    );
  }

  async function selectHistory(analysisId) {
    setSelectedId(analysisId);
    setDetail(null);
    setDetailLoading(true);
    setError("");
    try {
      setDetail(await fetchHistoryDetail(analysisId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this analysis.");
      setSelectedId(null);
    } finally {
      setDetailLoading(false);
    }
  }

  async function submitFollowUp(question) {
    const entry = await askHistoryFollowUp(selectedId, question);
    setDetail((current) => ({
      ...current,
      follow_ups: [...current.follow_ups, entry],
    }));
  }

  async function saveHistoryHedge(transactionHash, execution) {
    if (!selectedId || !execution) return;
    try {
      await saveHedgeExecution(selectedId, {
        profile: execution.profile.label,
        recommendation_reason: execution.reason,
        eth_spot: execution.spotPrice,
        max_budget: Number(execution.maxSpend),
        premium: execution.budget,
        strike: execution.strike,
        expiry: execution.expiry,
        option_quantity: execution.contracts,
        settlement: execution.settlement,
        market_snapshot_at: execution.updatedAt || new Date().toISOString(),
        transaction_hash: transactionHash,
      });
      setDetail(await fetchHistoryDetail(selectedId));
      window.dispatchEvent(new Event("fortifi:history-changed"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "The purchase succeeded, but its history record could not be refreshed.");
    }
  }

  function markSelectedAnchored(recordType, record) {
    setDetail((current) => ({ ...current, [`${recordType}_record`]: record }));
    if (recordType === "analysis") setItems((current) => current.map((item) => (
      item.analysis_id === selectedId ? { ...item, anchored: true } : item
    )));
    window.dispatchEvent(new Event("fortifi:history-changed"));
  }

  async function removeSelectedHistory() {
    const removedId = selectedId;
    try {
      await deleteHistory(removedId);
      setItems((current) => current.filter((item) => item.analysis_id !== removedId));
      setSelectedId(null);
      setDetail(null);
      setUndoId(removedId);
      window.dispatchEvent(new Event("fortifi:history-changed"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete this analysis.");
    }
  }

  async function undoDelete(analysisId = undoId) {
    try {
      await restoreHistory(analysisId);
      setItems(await fetchHistory());
      setTrash((current) => current.filter((item) => item.analysis_id !== analysisId));
      setUndoId(null);
      window.dispatchEvent(new Event("fortifi:history-changed"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not restore this analysis.");
    }
  }

  async function openTrash() {
    setShowTrash(true);
    setTrashLoading(true);
    setError("");
    try {
      setTrash(await fetchTrash());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load Trash.");
    } finally {
      setTrashLoading(false);
    }
  }

  async function permanentlyRemove(analysisId) {
    try {
      await permanentlyDeleteHistory(analysisId);
      setTrash((current) => current.filter((item) => item.analysis_id !== analysisId));
      setPermanentDeleteId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not permanently delete this analysis.");
    }
  }

  if (loading) {
    return <section className="loading"><p>Loading saved analyses…</p></section>;
  }

  return (
    <section className="history-shell">
      {error && <div className="error" role="alert"><strong>History unavailable</strong><p>{error}</p></div>}

      {undoId && !showTrash && (
        <div className="history-undo" role="status">
          <span>Analysis moved to Trash.</span>
          <button type="button" onClick={() => undoDelete()}>Undo</button>
        </div>
      )}

      {showTrash ? (
        <>
          <div className="history-heading">
            <div><h2>Trash</h2><p>Deleted analyses remain recoverable for 30 days.</p></div>
            <button type="button" className="button-secondary" onClick={() => setShowTrash(false)}>Back to History</button>
          </div>
          {trashLoading ? <div className="history-detail-loading">Loading Trash…</div> : trash.length === 0 ? (
            <div className="history-empty"><h3>Trash is empty</h3><p>Deleted analyses will appear here for 30 days.</p></div>
          ) : (
            <div className="history-trash-list">
              {trash.map((item) => (
                <article className="history-trash-row" key={item.analysis_id}>
                  <div><VerdictBadge verdict={item.verdict} /><strong>{item.claim}</strong><span>Deleted {formatDate(item.deleted_at)}</span></div>
                  {permanentDeleteId === item.analysis_id ? (
                    <div className="history-trash-confirm" role="alert">
                      <span>This cannot be undone. Any Sui record will remain on-chain.</span>
                      <button type="button" className="button-secondary" onClick={() => setPermanentDeleteId(null)}>Cancel</button>
                      <button type="button" className="history-delete" onClick={() => permanentlyRemove(item.analysis_id)}>Delete permanently</button>
                    </div>
                  ) : (
                    <div className="history-trash-actions">
                      <button type="button" onClick={() => undoDelete(item.analysis_id)}>Restore</button>
                      <button type="button" className="history-delete" onClick={() => setPermanentDeleteId(item.analysis_id)}>Delete permanently</button>
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
          <p className="history-trash-note">Removing a local history entry does not remove an integrity record already anchored on Sui.</p>
        </>
      ) : selectedId ? (
        <HistoryDetail
          detail={detail}
          loading={detailLoading}
          account={account}
          wallet={wallet}
          onBack={() => { setSelectedId(null); setDetail(null); setError(""); }}
          onDelete={removeSelectedHistory}
          onFollowUp={submitFollowUp}
          onAnalyzeWithAll={onAnalyzeWithAll}
          onAnchored={markSelectedAnchored}
          onHedgePurchased={saveHistoryHedge}
        />
      ) : (
        <>
          <div className="history-heading">
            <div><h2>Analysis history</h2><p>Revisit the evidence and reasoning behind every completed claim check.</p></div>
            <div className="history-heading-actions"><span>{items.length} saved</span><button type="button" className="button-secondary" onClick={openTrash}>Trash</button></div>
          </div>
          <HistoryList items={items} selectedId={selectedId} onSelect={selectHistory} />
        </>
      )}
    </section>
  );
}


export default HistoryPanel;
