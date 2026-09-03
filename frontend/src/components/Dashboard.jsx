import { useEffect, useState } from "react";

import { fetchDashboard, fetchDashboardNews } from "../api/dashboard";


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


function RiskCard({ risk }) {
  if (!risk) {
    return (
      <section className="dash-card">
        <div className="dash-card-header">
          <h3>Risk Assessment</h3>
          <span className="dash-card-sub">Scenario analysis</span>
        </div>
        <EmptyState
          title="No risk assessed yet"
          message="Run a risk analysis to estimate potential loss under a downside scenario."
        />
      </section>
    );
  }

  return (
    <section className="dash-card">
      <div className="dash-card-header">
        <h3>Risk Assessment</h3>
        <RiskBadge level={risk.risk_level} />
      </div>

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
          <span>Scenario</span>
          <strong>{formatPercent(risk.scenario_downside)}</strong>
          <em>assumed downside</em>
        </div>
      </div>

      <div className="dash-formula">
        {formatUsd(risk.exposure)} ×{" "}
        {formatPercent(risk.scenario_downside)} ={" "}
        <strong>{formatUsd(risk.estimated_loss)}</strong>
      </div>
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

function NewsCard({ news }) {
  return <section className="dash-card news-card">
    <div className="dash-card-header"><h3>Market News</h3><span className="dash-card-sub">Live search</span></div>
    {news.length === 0 ? <EmptyState title="News is unavailable" message="Try again when the search service is reachable." /> : <div className="news-list">{news.map((item) => (
      <a className="news-item" key={item.url} href={item.url} target="_blank" rel="noreferrer"><span>{item.source}</span><strong>{item.title}</strong><p>{item.excerpt}</p></a>
    ))}</div>}
  </section>;
}


function ProtectionCard() {
  // Placeholder for the protection recommendation summary.
  // The Thetanuts milestone will populate this.
  return (
    <section className="dash-card">
      <div className="dash-card-header">
        <h3>Protection</h3>
        <span className="dash-card-sub">Recommended hedge</span>
      </div>
      <EmptyState
        title="No protection recommended yet"
        message="Once risk is assessed, FortiFi will suggest a defined-risk hedge."
      />
    </section>
  );
}


function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [news, setNews] = useState([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
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

    return () => {
      cancelled = true;
    };
  }, []);

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
          <PortfolioCard wallet={summary?.wallet} />
          <RiskCard risk={summary?.risk} />
          <AIConsensusCard analysis={summary?.latest_analysis} />
          <ProtectionCard />
          <NewsCard news={news} />
        </div>
      )}
    </div>
  );
}


export default Dashboard;
