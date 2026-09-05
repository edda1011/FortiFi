import { useEffect, useState } from "react";

import { fetchDashboard, fetchDashboardNews } from "../api/dashboard";
import { analyzeRisk } from "../api/risk";


function formatUsd(value) {
  if (value === null || value === undefined) {
    return "—";
  }

  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
}


function formatPercent(value) {
  if (value === null || value === undefined) {
    return "—";
  }

  return `${(value * 100).toFixed(1)}%`;
}


function truncateAddress(address) {
  if (!address || address.length < 12) {
    return address;
  }

  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}


function RiskBadge({ level }) {
  if (!level) {
    return null;
  }

  return (
    <span className={`risk-badge risk-${level.toLowerCase()}`}>
      {level}
    </span>
  );
}


function EmptyState({ title, message }) {
  return (
    <div className="dashboard-empty">
      <div className="dashboard-empty-icon">◈</div>
      <h3>{title}</h3>
      <p>{message}</p>
    </div>
  );
}


function PortfolioCard({ wallet }) {
  if (!wallet) {
    return (
      <section className="dash-card">
        <div className="dash-card-header">
          <h3>Portfolio</h3>
          <span className="dash-card-sub">Wallet exposure</span>
        </div>
        <EmptyState
          title="No wallet checked yet"
          message="Check a wallet to see its ETH and USDC exposure on Base."
        />
      </section>
    );
  }

  return (
    <section className="dash-card">
      <div className="dash-card-header">
        <h3>Portfolio</h3>
        <span className="dash-card-sub">
          {truncateAddress(wallet.address)} · {wallet.network}
        </span>
      </div>

      <div className="dash-hero">
        <div className="dash-hero-label">Total Value</div>
        <div className="dash-hero-value">
          {formatUsd(wallet.total_value)}
        </div>
      </div>

      <div className="dash-stats">
        <div className="dash-stat">
          <span>ETH</span>
          <strong>{wallet.eth_balance.toFixed(4)}</strong>
          <em>{formatUsd(wallet.eth_value)}</em>
        </div>
        <div className="dash-stat">
          <span>USDC</span>
          <strong>{formatUsd(wallet.usdc_balance)}</strong>
          <em>Stable</em>
        </div>
      </div>

      <div className="dash-exposure">
        <div className="dash-exposure-head">
          <span>ETH Exposure</span>
          <strong>{wallet.eth_exposure_percent.toFixed(1)}%</strong>
        </div>
        <div className="exposure-bar">
          <div
            className="exposure-fill"
            style={{ width: `${wallet.eth_exposure_percent}%` }}
          />
        </div>
      </div>
    </section>
  );
}


function RiskCard({ risk, wallet, onCalculated }) {
  const [scenario, setScenario] = useState("0.10");
  const [calculating, setCalculating] = useState(false);
  const [calculationError, setCalculationError] = useState("");

  async function calculate() {
    setCalculating(true);
    setCalculationError("");
    try {
      onCalculated(await analyzeRisk(wallet.address, Number(scenario)));
    } catch (error) {
      setCalculationError(error instanceof Error ? error.message : "Risk calculation failed.");
    } finally {
      setCalculating(false);
    }
  }

  if (!wallet) {
    return (
      <section className="dash-card">
        <div className="dash-card-header">
          <h3>Risk Assessment</h3>
          <span className="dash-card-sub">Scenario analysis</span>
        </div>
        <EmptyState
          title="Connect a wallet to assess risk"
          message="FortiFi needs the wallet's live ETH value to estimate loss under a downside scenario."
        />
      </section>
    );
  }

  return (
    <section className="dash-card">
      <div className="dash-card-header">
        <h3>Risk Assessment</h3>
        {risk ? <RiskBadge level={risk.risk_level} /> : <span className="dash-card-sub">Scenario analysis</span>}
      </div>

      <div className="risk-controls">
        <label htmlFor="risk-scenario">Assumed ETH decline</label>
        <select id="risk-scenario" value={scenario} onChange={(event) => setScenario(event.target.value)} disabled={calculating}>
          <option value="0.10">10%</option>
          <option value="0.20">20%</option>
          <option value="0.30">30%</option>
        </select>
        <button type="button" onClick={calculate} disabled={calculating}>{calculating ? "Calculating…" : risk ? "Recalculate" : "Calculate Risk"}</button>
      </div>
      {calculationError && <p className="dashboard-inline-error" role="alert">{calculationError}</p>}

      {risk ? <>
      <div className="dash-hero">
        <div className="dash-hero-label">Estimated Loss</div>
        <div className="dash-hero-value">
          {formatUsd(risk.estimated_loss)}
        </div>
      </div>

      <div className="dash-stats">
        <div className="dash-stat">
          <span>Exposure</span>
          <strong>{formatUsd(risk.exposure)}</strong>
          <em>ETH value at risk</em>
        </div>
        <div className="dash-stat">
          <span>Portfolio impact</span>
          <strong>{risk.wallet.total_value > 0 ? formatPercent(risk.estimated_loss / risk.wallet.total_value) : "0.0%"}</strong>
          <em>of tracked value</em>
        </div>
      </div>

      <div className="dash-formula">
        {formatUsd(risk.exposure)} ×{" "}
        {formatPercent(risk.scenario_downside)} ={" "}
        <strong>{formatUsd(risk.estimated_loss)}</strong>
      </div>
      </> : <EmptyState title="Choose a scenario" message="Calculate how a possible ETH decline could affect this wallet's current portfolio." />}
    </section>
  );
}


function AIConsensusCard({ analysis }) {
  if (analysis) {
    const consensus = analysis.consensus;
    return (
      <section className="dash-card">
        <div className="dash-card-header"><h3>Latest AI Consensus</h3><RiskBadge level={consensus.market_impact} /></div>
        <p className="claim-preview">“{analysis.claim}”</p>
        <div className="dash-stats">
          <div className="dash-stat"><span>Verdict</span><strong>{analysis.final_assessment.verdict.replace("_", " ")}</strong><em>{(consensus.confidence * 100).toFixed(0)}% confidence</em></div>
          <div className="dash-stat"><span>Agreement</span><strong>{((1 - consensus.disagreement) * 100).toFixed(0)}%</strong><em>{analysis.evidence.length} sources retained</em></div>
        </div>
        <p className="dashboard-analysis">{analysis.final_assessment.analysis}</p>
      </section>
    );
  }
  return (
    <section className="dash-card">
      <div className="dash-card-header">
        <h3>AI Consensus</h3>
        <span className="dash-card-sub">Claim analysis</span>
      </div>
      <EmptyState
        title="No claims analyzed yet"
        message="Analyze a claim to see the multi-model AI consensus."
      />
    </section>
  );
}

function NewsCard({ news, onCheckHeadline }) {
  const [selectedHeadline, setSelectedHeadline] = useState(null);
  const usingBriefingFallback = news.some((item) => item.is_live === false);

  function closeChoice() {
    setSelectedHeadline(null);
  }

  function openSource() {
    if (selectedHeadline) {
      window.open(selectedHeadline.url, "_blank", "noopener,noreferrer");
    }
    closeChoice();
  }

  function sendToClaimCheck() {
    if (selectedHeadline) {
      onCheckHeadline(selectedHeadline.title);
    }
    closeChoice();
  }

  return <section className="dash-card news-card">
    <div className="dash-card-header"><h3>Market News</h3><span className="dash-card-sub">{usingBriefingFallback ? "Market briefing" : "Live search"}</span></div>
    {news.length === 0 ? <EmptyState title="News is unavailable" message="Try again when the search service is reachable." /> : <div className="news-list">{news.map((item) => (
      <button className="news-item" key={item.url} type="button" onClick={() => setSelectedHeadline(item)}><span>{item.source}</span><strong>{item.title}</strong><p>{item.excerpt}</p></button>
    ))}</div>}
    {selectedHeadline && <div className="headline-dialog-backdrop" role="presentation" onMouseDown={closeChoice}>
      <section className="headline-dialog" role="dialog" aria-modal="true" aria-labelledby="headline-choice-title" onMouseDown={(event) => event.stopPropagation()}>
        <span className="dashboard-eyebrow">Headline selected</span>
        <h3 id="headline-choice-title">{selectedHeadline.title}</h3>
        <p>Would you like to read the original source or use this headline as a claim for FortiFi to check?</p>
        <div className="headline-dialog-actions">
          <button type="button" onClick={sendToClaimCheck}>Send to Claim Check</button>
          <button type="button" className="button-secondary" onClick={openSource}>Visit source</button>
          <button type="button" className="button-secondary" onClick={closeChoice}>Cancel</button>
        </div>
      </section>
    </div>}
  </section>;
}


function ProtectionCard({ execution }) {
  if (execution) {
    return (
      <section className="dash-card">
        <div className="dash-card-header"><h3>Protection</h3><span className="protection-active">Purchased</span></div>
        <div className="dash-hero"><div className="dash-hero-label">{execution.profile}</div><div className="dash-hero-value">{formatUsd(execution.premium)}</div></div>
        <div className="dash-stats">
          <div className="dash-stat"><span>Strike</span><strong>{formatUsd(execution.strike)}</strong><em>{execution.option_quantity.toFixed(6)} contracts</em></div>
          <div className="dash-stat"><span>Expiry</span><strong>{new Date(execution.expiry).toLocaleDateString("en-MY")}</strong><em>{execution.settlement} settlement</em></div>
        </div>
        <a className="dashboard-transaction-link" href={`https://basescan.org/tx/${execution.transaction_hash}`} target="_blank" rel="noreferrer">View Base transaction</a>
      </section>
    );
  }

  return (
    <section className="dash-card">
      <div className="dash-card-header">
        <h3>Protection</h3>
        <span className="dash-card-sub">Recommended hedge</span>
      </div>
      <EmptyState
        title="No protection purchased yet"
        message="A completed Thetanuts purchase will appear here with its current contract details and Base transaction."
      />
    </section>
  );
}


function Dashboard({ account, wallet, onCheckHeadline }) {
  const [summary, setSummary] = useState(null);
  const [risk, setRisk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [news, setNews] = useState([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const [data, headlines] = await Promise.all([fetchDashboard(), fetchDashboardNews().catch(() => [])]);

        if (!cancelled) {
          setSummary(data);
          setNews(headlines);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load the dashboard."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();
    window.addEventListener("fortifi:history-changed", load);

    return () => {
      cancelled = true;
      window.removeEventListener("fortifi:history-changed", load);
    };
  }, [account]);

  useEffect(() => {
    setRisk(null);
  }, [account]);

  return (
    <div className="dashboard">
      <div className="dashboard-hero">
        <div className="dashboard-hero-inner">
          <span className="dashboard-eyebrow">FortiFi Overview</span>
          <h2>Your Financial Risk Dashboard</h2>
          <p>
            A single view of your wallet exposure, estimated risk, and
            the AI consensus behind FortiFi's analysis.
          </p>
        </div>
      </div>

      {error && (
        <section className="error">
          <strong>Dashboard unavailable</strong>
          <p>{error}</p>
        </section>
      )}

      {loading && (
        <section className="loading">
          <p>Loading your dashboard...</p>
        </section>
      )}

      {!loading && !error && (
        <div className="dash-grid">
          <PortfolioCard wallet={wallet} />
          <RiskCard risk={risk} wallet={wallet} onCalculated={setRisk} />
          <AIConsensusCard analysis={summary?.latest_analysis} />
          <ProtectionCard execution={summary?.latest_hedge_execution} />
          <NewsCard news={news} onCheckHeadline={onCheckHeadline} />
        </div>
      )}
    </div>
  );
}


export default Dashboard;
