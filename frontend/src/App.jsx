import { useEffect, useRef, useState } from "react";

import { analyzeClaim } from "./api/claims";
import { findRecentClaim } from "./api/history";
import { connectBaseWallet, disconnectBaseWallet, savedWalletAddress } from "./api/auth";
import { checkConnectedWallet, checkWallet, getWalletHistory } from "./api/wallet";
import Dashboard from "./components/Dashboard.jsx";
import HistoryPanel from "./components/HistoryPanel.jsx";
import ReasoningTrace from "./components/ReasoningTrace.jsx";
import ProtectionRecordPanel from "./components/ProtectionRecordPanel.jsx";
import ThetanutsHedgePanel from "./components/ThetanutsHedgePanel.jsx";
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

      <ReasoningTrace result={result} />

      <p className="model-request-id">
        <span>Gonka Request ID</span>
        <code>{result.request_id || "Not available"}</code>
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

  // Wallet state lives here (not in WalletPanel) so it survives
  // navigating to other pages and back.
  const [walletAddress, setWalletAddress] = useState("");
  const [walletResult, setWalletResult] = useState(null);
  const [walletHistory, setWalletHistory] = useState([]);
  const [walletLoading, setWalletLoading] = useState(false);
  const [walletError, setWalletError] = useState("");
  const [account, setAccount] = useState(savedWalletAddress);
  const [connectedWallet, setConnectedWallet] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [walletMenuOpen, setWalletMenuOpen] = useState(false);
  const walletMenuRef = useRef(null);
  const analysisRequestRef = useRef(0);
  const [hedgeTransaction, setHedgeTransaction] = useState("");
  const [duplicateAnalysis, setDuplicateAnalysis] = useState(null);
  const [viewingPreviousFastReport, setViewingPreviousFastReport] = useState(false);

  function resetCredentialState() {
    analysisRequestRef.current += 1;
    setClaim("");
    setResult(null);
    setLoading(false);
    setError("");
    setProgress(null);
    setWalletAddress("");
    setWalletResult(null);
    setWalletHistory([]);
    setWalletLoading(false);
    setWalletError("");
    setConnectedWallet(null);
    setHedgeTransaction("");
    setDuplicateAnalysis(null);
    setViewingPreviousFastReport(false);
  }

  useEffect(() => {
    function closeExpiredSession() {
      resetCredentialState();
      setAccount("");
      setWalletMenuOpen(false);
    }
    function closeMenu(event) {
      if (!walletMenuRef.current?.contains(event.target)) setWalletMenuOpen(false);
    }
    function closeMenuWithEscape(event) {
      if (event.key === "Escape") setWalletMenuOpen(false);
    }
    window.addEventListener("fortifi:session-expired", closeExpiredSession);
    document.addEventListener("mousedown", closeMenu);
    document.addEventListener("keydown", closeMenuWithEscape);
    return () => {
      window.removeEventListener("fortifi:session-expired", closeExpiredSession);
      document.removeEventListener("mousedown", closeMenu);
      document.removeEventListener("keydown", closeMenuWithEscape);
    };
  }, []);

  useEffect(() => {
    if (!window.ethereum) return undefined;
    function disconnectChangedAccount(accounts) {
      if (account && !accounts.some((address) => address.toLowerCase() === account.toLowerCase())) {
        disconnectBaseWallet();
        resetCredentialState();
        setAccount("");
        setWalletMenuOpen(false);
      }
    }
    window.ethereum.on?.("accountsChanged", disconnectChangedAccount);
    return () => window.ethereum.removeListener?.("accountsChanged", disconnectChangedAccount);
  }, [account]);

  useEffect(() => {
    if (!account) {
      setConnectedWallet(null);
      return undefined;
    }

    let cancelled = false;
    async function refreshConnectedWallet() {
      try {
        const wallet = await checkConnectedWallet();
        if (!cancelled) setConnectedWallet(wallet);
      } catch {
        // Keep the last successful balance during temporary RPC failures.
      }
    }
    function refreshWhenVisible() {
      if (document.visibilityState === "visible") refreshConnectedWallet();
    }

    refreshConnectedWallet();
    const intervalId = window.setInterval(refreshConnectedWallet, 15000);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [account]);

  async function handleConnect() {
    if (account) {
      setWalletMenuOpen((open) => !open);
      return;
    }
    setConnecting(true);
    try {
      const connectedAccount = await connectBaseWallet();
      resetCredentialState();
      setAccount(connectedAccount);
      setWalletMenuOpen(false);
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Wallet connection failed.");
    } finally {
      setConnecting(false);
    }
  }

  function handleDisconnect() {
    disconnectBaseWallet();
    resetCredentialState();
    setAccount("");
    setWalletMenuOpen(false);
  }

  function handleClearClaim() {
    analysisRequestRef.current += 1;
    setClaim("");
    setResult(null);
    setError("");
    setProgress(null);
    setHedgeTransaction("");
    setDuplicateAnalysis(null);
    setViewingPreviousFastReport(false);
  }

  async function handleWalletSubmit(event) {
    event.preventDefault();

    const trimmedAddress = walletAddress.trim();

    if (!trimmedAddress) {
      setWalletError("Please enter a wallet address.");
      return;
    }

    setWalletLoading(true);
    setWalletError("");
    setWalletResult(null);
    setWalletHistory([]);

    try {
      const snapshot = await checkWallet(trimmedAddress);

      setWalletResult(snapshot);

      // After a successful check, also load the saved history for
      // this address (the snapshot we just saved is included).
      try {
        const historyData = await getWalletHistory(snapshot.address);
        setWalletHistory(historyData.snapshots ?? []);
      } catch {
        // History is a nice-to-have; don't fail the whole view if
        // it can't be loaded.
        setWalletHistory([]);
      }
    } catch (err) {
      setWalletError(
        err instanceof Error
          ? err.message
          : "Something went wrong."
      );
    } finally {
      setWalletLoading(false);
    }
  }

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


  async function runClaimAnalysis(trimmedClaim, waitMode, forceFresh = false) {
    if (!trimmedClaim) {
      setError("Please enter a claim.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setProgress(null);
    setDuplicateAnalysis(null);
    setViewingPreviousFastReport(false);
    const requestId = ++analysisRequestRef.current;

    try {
      if (account && !forceFresh) {
        const previous = await findRecentClaim(trimmedClaim);
        if (requestId !== analysisRequestRef.current) return;
        if (previous) {
          setDuplicateAnalysis(previous);
          return;
        }
      }

      const analysis =
        await analyzeClaim(trimmedClaim, waitMode, (nextProgress) => {
          if (requestId === analysisRequestRef.current) setProgress(nextProgress);
        });

      if (requestId === analysisRequestRef.current) setResult(analysis);
    } catch (err) {
      if (requestId === analysisRequestRef.current) setError(
        err instanceof Error
          ? err.message
          : "Something went wrong."
      );
    } finally {
      if (requestId === analysisRequestRef.current) setLoading(false);
    }
  }

  function handleSubmit(event, forceFresh = false) {
    event?.preventDefault();
    return runClaimAnalysis(claim.trim(), waitForAll, forceFresh);
  }

  function analyzeWithAllModels(claimText) {
    const trimmedClaim = claimText.trim();
    setClaim(trimmedClaim);
    setWaitForAll(true);
    setView("claim");
    runClaimAnalysis(trimmedClaim, true, true);
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

          <div className="wallet-menu" ref={walletMenuRef}>
            <button
              type="button"
              className="wallet-connect"
              onClick={handleConnect}
              disabled={connecting}
              aria-expanded={account ? walletMenuOpen : undefined}
              aria-haspopup={account ? "menu" : undefined}
            >
              {connecting ? "Connecting…" : account ? `${account.slice(0, 6)}…${account.slice(-4)}` : "Connect Wallet"}
            </button>
            {account && walletMenuOpen && (
              <div className="wallet-menu-popover" role="menu">
                <span>Connected to Base</span>
                <code>{`${account.slice(0, 8)}…${account.slice(-6)}`}</code>
                <button type="button" role="menuitem" onClick={handleDisconnect}>Disconnect Wallet</button>
              </div>
            )}
          </div>

          
        </nav>
      </header>


      <main className="main">

        {view === "dashboard" && <Dashboard account={account} wallet={connectedWallet} onCheckHeadline={handleHeadlineForClaimCheck} />}

        {view === "wallet" && (
          <WalletPanel
            address={walletAddress}
            setAddress={setWalletAddress}
            result={walletResult}
            history={walletHistory}
            loading={walletLoading}
            error={walletError}
            onSubmit={handleWalletSubmit}
          />
        )}

        {view === "history" && <HistoryPanel key={account || "guest"} connected={Boolean(account)} onAnalyzeWithAll={analyzeWithAllModels} />}

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
              Financial claim or article URL
            </label>

            <textarea
              id="claim"
              value={claim}
              onChange={(event) =>
                {
                  setClaim(event.target.value);
                  setDuplicateAnalysis(null);
                }
              }
              placeholder="Paste a financial claim, headline, statement, or public article URL..."
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

              <div className="claim-actions">
                <button
                  type="button"
                  className="button-secondary"
                  onClick={handleClearClaim}
                  disabled={loading || (!claim && !result && !error)}
                >
                  Clear
                </button>
                <button
                  type="submit"
                  disabled={loading}
                >
                  {loading
                    ? "Analyzing..."
                    : "Analyze Claim"}
                </button>
              </div>

            </div>

          </form>

        </section>

        {duplicateAnalysis && (
          <section className="duplicate-claim" role="status">
            <div>
              <strong>This claim was analyzed recently</strong>
              <p>Open the saved report instantly, or run a fresh Gonka analysis.</p>
            </div>
            <div className="duplicate-claim-actions">
              <button
                type="button"
                className="button-secondary"
                onClick={() => {
                  setResult(duplicateAnalysis.analysis);
                  setViewingPreviousFastReport(
                    duplicateAnalysis.analysis.consensus.model_results.length < 3
                  );
                  setDuplicateAnalysis(null);
                }}
              >
                View Previous Report
              </button>
              <button type="button" onClick={() => handleSubmit(undefined, true)}>
                Analyze Again
              </button>
            </div>
          </section>
        )}

        {viewingPreviousFastReport && result && (
          <section className="fast-report-notice" role="status">
            <div>
              <strong>This report used Fast Consensus</strong>
              <p>This saved result was based on {result.consensus.model_results.length} AI models.</p>
            </div>
            <div className="duplicate-claim-actions">
              <button type="button" className="button-secondary" onClick={() => setViewingPreviousFastReport(false)}>
                Use This Report
              </button>
              <button type="button" onClick={() => analyzeWithAllModels(result.claim)}>
                Analyze with 3 Models
              </button>
            </div>
          </section>
        )}


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
                ? "Fewer than 2 AI models completed within the 55-second total limit. Gonka may be busy—please try the analysis again."
                : retryableAnalysisFailure && progress.wait_for_all && failedModelNames.length
                  ? `${failedModelNames.join(", ")} did not complete. Retry to request all three models again.`
                : error}
            </p>
            {retryableAnalysisFailure && (
              <button type="button" onClick={() => handleSubmit(undefined, true)}>
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

              <ThetanutsHedgePanel
                detectedAssets={result.detected_assets || []}
                detectionSources={result.asset_detection_sources || []}
                account={account}
                onPurchased={setHedgeTransaction}
              />

              <ProtectionRecordPanel
                analysisId={result.analysis_id}
                account={account}
                baseTransaction={hedgeTransaction}
              />

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
