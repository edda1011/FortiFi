import { useState } from "react";

import { analyzeClaim } from "./api/claims";
import Dashboard from "./components/Dashboard.jsx";
import HistoryPanel from "./components/HistoryPanel.jsx";
import WalletPanel from "./components/WalletPanel.jsx";


function formatPercentage(value) {
  return `${(value * 100).toFixed(1)}%`;
}


function VerdictBadge({ verdict }) {
  return (
    <span className={`verdict verdict-${verdict.toLowerCase()}`}>
      {verdict.replace("_", " ")}
    </span>
  );
}


function ModelResult({ result }) {
  return (
    <div className="model-result">
      <div className="model-header">
        <h3>{result.model}</h3>

        <VerdictBadge verdict={result.verdict} />
      </div>

      <div className="model-metrics">
        <div>
          <span>Credibility</span>
          <strong>
            {formatPercentage(
              result.credibility_score
            )}
          </strong>
        </div>

        <div>
          <span>Confidence</span>
          <strong>
            {formatPercentage(result.confidence)}
          </strong>
        </div>

        <div>
          <span>Market Impact</span>
          <strong>
            {result.market_impact}
          </strong>
        </div>
      </div>

      <p className="model-reasoning">
        {result.reasoning_summary}
      </p>
    </div>
  );
}


function AnalysisProgress({ progress }) {
  if (!progress) return null;

  const completed = progress.models.filter(
    (model) => model.status === "completed"
  ).length;

  return (
    <section className="analysis-progress" aria-live="polite">
      <div className="progress-heading">
        <div>
          <h2>Analyzing claim</h2>
          <p>{progress.phase}</p>
        </div>
        <strong>{completed} of 3 complete</strong>
      </div>

      <div className="progress-track" aria-hidden="true">
        <span style={{ width: `${(completed / 3) * 100}%` }} />
      </div>

      <div className="model-progress-list">
        {progress.models.map((model) => (
          <div className="model-progress-row" key={model.model}>
            <span className={`model-status-dot model-status-${model.status}`} />
            <strong>{model.model}</strong>
            <span>{model.error || model.status.replace("_", " ")}</span>
          </div>
        ))}
      </div>

      <p className="progress-note">
        {progress.wait_for_all
          ? "Complete mode waits for all three independent assessments."
          : "Fast mode returns when two independent assessments are ready."}
      </p>
    </section>
  );
}


function App() {
  const [view, setView] = useState("dashboard");

  const [claim, setClaim] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [waitForAll, setWaitForAll] = useState(false);
  const [progress, setProgress] = useState(null);

  const completedModels = progress?.models.filter(
    (model) => model.status === "completed"
  ).length ?? 0;
  const fastConsensusFailed = Boolean(
    error && progress && !progress.wait_for_all && completedModels < 2
  );
  const retryableAnalysisFailure = Boolean(
    error && progress?.status === "failed"
  );
  const failedModelNames = progress?.models
    .filter((model) => ["failed", "timed_out"].includes(model.status))
    .map((model) => model.model) ?? [];


  async function handleSubmit(event) {
    event?.preventDefault();

    const trimmedClaim = claim.trim();

    if (!trimmedClaim) {
      setError("Please enter a claim.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setProgress(null);

    try {
      const analysis =
        await analyzeClaim(trimmedClaim, waitForAll, setProgress);

      setResult(analysis);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleHeadlineForClaimCheck(headline) {
    setClaim(headline);
    setResult(null);
    setError("");
    setView("claim");
  }


  return (
    <div className="app">

      <header className="header">
        <div>
          <h1>FortiFi</h1>
        </div>

      

        <nav className="nav-tabs">
          <button
            type="button"
            className={
              view === "dashboard"
                ? "tab tab-active"
                : "tab"
            }
            onClick={() => setView("dashboard")}
          >
            Dashboard
          </button>

          <button
            type="button"
            className={
              view === "history"
                ? "tab tab-active"
                : "tab"
            }
            onClick={() => setView("history")}
          >
            History
          </button>
          
          <button
            type="button"
            className={
              view === "claim"
                ? "tab tab-active"
                : "tab"
            }
            onClick={() => setView("claim")}
          >
            Claim Check
          </button>

          <button
            type="button"
            className={
              view === "wallet"
                ? "tab tab-active"
                : "tab"
            }
            onClick={() => setView("wallet")}
          >
            Wallet
          </button>

          
        </nav>
      </header>


      <main className="main">

        {view === "dashboard" && <Dashboard onCheckHeadline={handleHeadlineForClaimCheck} />}

        {view === "wallet" && <WalletPanel />}

        {view === "history" && <HistoryPanel />}

        {view === "claim" && (
        <>
        <section className="claim-section">

          <div className="section-heading">
            <h2>Check a Claim</h2>

            <p>
              Analyze potentially misleading
              financial information using
              multiple independent AI models.
            </p>
          </div>


          <form onSubmit={handleSubmit}>

            <label htmlFor="claim">
              Financial claim
            </label>

            <textarea
              id="claim"
              value={claim}
              onChange={(event) =>
                setClaim(event.target.value)
              }
              placeholder="Paste a financial claim, headline, or statement here..."
              disabled={loading}
              maxLength={10000}
            />

            <label className="analysis-mode-option">
              <input
                type="checkbox"
                checked={waitForAll}
                onChange={(event) => setWaitForAll(event.target.checked)}
                disabled={loading}
              />
              <span className="analysis-mode-control" aria-hidden="true" />
              <span>
                <strong>Wait for all 3 models</strong>
                <small>More complete consensus, but it may take longer.</small>
              </span>
            </label>


            <div className="input-footer">

              <span>
                {claim.length} / 10,000
              </span>

              <button
                type="submit"
                disabled={loading}
              >
                {loading
                  ? "Analyzing..."
                  : "Analyze Claim"}
              </button>

            </div>

          </form>

        </section>


        {error && (
          <section
            className={retryableAnalysisFailure ? "error error-retry" : "error"}
            role="alert"
          >
            <strong>
              {fastConsensusFailed
                ? "Fast consensus could not be completed"
                : retryableAnalysisFailure && progress.wait_for_all
                  ? "Complete analysis could not be completed"
                : "Analysis failed"}
            </strong>
            <p>
              {fastConsensusFailed
                ? "Fewer than 2 AI models responded within 35 seconds. Gonka may be busy—please try the analysis again."
                : retryableAnalysisFailure && progress.wait_for_all && failedModelNames.length
                  ? `${failedModelNames.join(", ")} did not complete. Retry to request all three models again.`
                : error}
            </p>
            {retryableAnalysisFailure && (
              <button type="button" onClick={() => handleSubmit()}>
                Retry Analysis
              </button>
            )}
          </section>
        )}


        {progress && (loading || error) && (
          <AnalysisProgress progress={progress} />
        )}


        {result && !loading && (
          <section className="results">

            <div className="results-header">
              <div>
                <h2>Analysis Result</h2>

                <p>
                  {result.consensus.model_results.length} of 3
                  AI models responded.
                </p>
              </div>

              <VerdictBadge
                verdict={result.final_assessment.verdict}
              />
            </div>


            <div className="consensus-grid">

              <div className="metric-card">
                <span>
                  Credibility
                </span>

                <strong>
                  {formatPercentage(
                    result.consensus.credibility_score
                  )}
                </strong>
              </div>


              <div className="metric-card">
                <span>
                  AI Confidence
                </span>

                <strong>
                  {formatPercentage(
                    result.consensus.confidence
                  )}
                </strong>
              </div>


              <div className="metric-card">
                <span>
                  Market Impact
                </span>

                <strong>
                  {result.consensus.market_impact}
                </strong>
              </div>


              <div className="metric-card">
                <span>
                  Model Disagreement
                </span>

                <strong>
                  {formatPercentage(
                    result.consensus.disagreement
                  )}
                </strong>
              </div>

            </div>


            <div className="summary">

              <h3>Consensus Assessment</h3>

              <p>
                {result.final_assessment.analysis}
              </p>

              <small className="summary-source">
                Locally synthesized from {result.consensus.model_results.length} of 3
                independent AI assessments. No additional AI request was used.
              </small>

            </div>


            <div className="models">

              <h3>
                Individual Model Results
              </h3>

              {result.consensus.model_results.map(
                (modelResult) => (
                  <ModelResult
                    key={modelResult.model}
                    result={modelResult}
                  />
                )
              )}

              {result.evidence.length > 0 && (
                <div className="evidence-list">
                  <h3>Retrieved Evidence</h3>
                  {result.evidence.map((item) => (
                    <a
                      key={item.url}
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="evidence-item"
                    >
                      <strong>{item.title}</strong>
                      <span>{item.source}</span>
                    </a>
                  ))}
                </div>
              )}

              {result.portfolio_exposure && (
                <div className="summary exposure-result">
                  <h3>Portfolio Scenario Exposure</h3>
                  <p>
                    {result.portfolio_exposure.portfolio_percentage}% ETH exposure ×{" "}
                    {result.portfolio_exposure.scenario_change}% scenario ={" "}
                    <strong>
                      {result.portfolio_exposure.estimated_portfolio_impact}% estimated portfolio impact.
                    </strong>
                  </p>
                </div>
              )}

              <section className="recommendation-section">
                <div className="recommendation-heading">
                  <div>
                    <span className="dashboard-eyebrow">Next-step plan</span>
                    <h3>Recommendations</h3>
                  </div>
                  <span className="recommendation-status">
                    {result.portfolio_context?.wallet_connected ? "Wallet context included" : "Review required"}
                  </span>
                </div>
                <p className="recommendation-context">
                  {result.portfolio_context?.wallet_connected
                    ? `Recommendations considered your ${result.portfolio_context.network} portfolio allocation locally. No wallet address was sent to an AI model.`
                    : "No wallet is connected, so these recommendations are based only on the claim and evidence."}
                </p>
                {result.recommendations.length > 0 ? result.recommendations.map((recommendation, index) => (
                  <article className="recommendation-card" key={`${recommendation.title}-${index}`}>
                    <div className="recommendation-card-head">
                      <h4>{recommendation.title}</h4>
                      <span>{recommendation.automation_eligible ? "Automation-ready plan" : "Manual plan"}</span>
                    </div>
                    {recommendation.rationale && <p>{recommendation.rationale}</p>}
                    {recommendation.steps.length > 0 && <ol>{recommendation.steps.map((step, stepIndex) => <li key={`${step}-${stepIndex}`}>{step}</li>)}</ol>}
                    <small>No action is performed here. Any future automation must show this plan and get explicit user confirmation.</small>
                  </article>
                )) : <p className="recommendation-empty">No next-step plan was generated. Review the evidence and model assessment before taking action.</p>}
              </section>

            </div>

          </section>
        )}

        </>
        )}

      </main>

    </div>
  );
}


export default App;
