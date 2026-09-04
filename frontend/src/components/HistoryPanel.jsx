import { useEffect, useState } from "react";

import {
  askHistoryFollowUp,
  fetchHistory,
  fetchHistoryDetail,
} from "../api/history";


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
            <VerdictBadge verdict={item.verdict} />
            <time>{formatDate(item.created_at)}</time>
          </span>
          <strong>{item.claim}</strong>
          <span className="history-row-metrics">
            {formatPercentage(item.credibility_score)} credibility
            <span aria-hidden="true">·</span>
            {formatPercentage(item.confidence)} confidence
          </span>
        </button>
      ))}
    </div>
  );
}


function HistoryDetail({ detail, loading, onBack, onFollowUp }) {
  const [question, setQuestion] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

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

  return (
    <article className="history-detail">
      <button type="button" className="history-back" onClick={onBack}>
        Back to all history
      </button>

      <div className="history-detail-heading">
        <div>
          <time>{formatDate(detail.created_at)}</time>
          <h2>{analysis.claim}</h2>
        </div>
        <VerdictBadge verdict={analysis.final_assessment.verdict} />
      </div>

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
        <h3>Gonka inference requests</h3>
        {analysis.consensus.model_results.map((result) => (
          <div key={result.model}>
            <span>{result.model}</span>
            <code>{result.request_id || "Not available"}</code>
          </div>
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


function HistoryPanel() {
  const [items, setItems] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
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
  }, []);

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

  if (loading) {
    return <section className="loading"><p>Loading saved analyses…</p></section>;
  }

  return (
    <section className="history-shell">
      {error && <div className="error" role="alert"><strong>History unavailable</strong><p>{error}</p></div>}

      {selectedId ? (
        <HistoryDetail
          detail={detail}
          loading={detailLoading}
          onBack={() => { setSelectedId(null); setDetail(null); setError(""); }}
          onFollowUp={submitFollowUp}
        />
      ) : (
        <>
          <div className="history-heading">
            <div><h2>Analysis history</h2><p>Revisit the evidence and reasoning behind every completed claim check.</p></div>
            <span>{items.length} saved</span>
          </div>
          <HistoryList items={items} selectedId={selectedId} onSelect={selectHistory} />
        </>
      )}
    </section>
  );
}


export default HistoryPanel;
