import { useEffect, useState } from "react";
import { loadHedgeRecommendations, purchaseRecommendedHedge } from "../services/thetanuts";

function formatUsd(value) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value);
}

function TechnicalDetails({ recommendation }) {
  return (
    <details className="hedge-technical">
      <summary>View technical details</summary>
      <dl>
        <div><dt>Product</dt><dd>ETH {recommendation.product.replaceAll("_", " ")}</dd></div>
        <div><dt>Option quantity</dt><dd>{recommendation.contracts.toFixed(6)}</dd></div>
        <div><dt>Price per contract</dt><dd>{formatUsd(recommendation.pricePerContract)}</dd></div>
        <div><dt>Settlement</dt><dd>{recommendation.settlement}</dd></div>
        <div><dt>Collateral</dt><dd>{recommendation.collateral}</dd></div>
        <div><dt>OptionBook</dt><dd><code>{recommendation.optionBook}</code></dd></div>
      </dl>
      <p>Exact underlying coverage depends on the selected contract mechanics.</p>
    </details>
  );
}

function defaultPreference(riskLevel, ethExposurePercent, hasWallet) {
  if (!hasWallet) return "balanced";
  if (riskLevel === "HIGH" && ethExposurePercent >= 50) return "stronger";
  if (riskLevel === "LOW" || ethExposurePercent < 20) return "lower_cost";
  return "balanced";
}

function ThetanutsHedgePanel({ detectedAssets = [], detectionSources = [], account, wallet, riskLevel = "MEDIUM", ethExposurePercent = 0, onPurchased }) {
  const [maxBudget, setMaxBudget] = useState("1");
  const [preference, setPreference] = useState("balanced");
  const [market, setMarket] = useState(null);
  const [selectedKey, setSelectedKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [buying, setBuying] = useState(false);
  const [error, setError] = useState("");
  const [purchase, setPurchase] = useState(null);
  const isEthClaim = detectedAssets.includes("ETH");
  const hasWalletContext = Boolean(wallet);
  const selectedRecommendation = market?.recommendations.find((item) => item.orderKey === selectedKey);
  const usdcShortfall = wallet && selectedRecommendation
    ? Math.max(0, selectedRecommendation.budget - wallet.usdc_balance)
    : 0;

  useEffect(() => {
    setMarket(null); setSelectedKey(""); setPurchase(null); setError("");
  }, [account]);

  useEffect(() => {
    setPreference(defaultPreference(riskLevel, ethExposurePercent, hasWalletContext));
  }, [riskLevel, ethExposurePercent, hasWalletContext]);

  if (!isEthClaim) return null;

  async function updateRecommendations() {
    const budget = Number(maxBudget);
    if (!Number.isFinite(budget) || budget < 1) {
      setError("Enter a maximum protection budget of at least 1 USDC.");
      return;
    }
    setLoading(true); setError(""); setPurchase(null);
    try {
      const result = await loadHedgeRecommendations({ maxBudget: budget, preference });
      setMarket(result);
      setSelectedKey(result.recommendations.find((item) => item.recommended)?.orderKey || result.recommendations[0]?.orderKey || "");
    } catch (err) {
      setMarket(null);
      setError(err instanceof Error ? err.message : "Could not update protection recommendations.");
    } finally { setLoading(false); }
  }

  async function buyHedge() {
    const selected = market?.recommendations.find((item) => item.orderKey === selectedKey);
    setBuying(true); setError("");
    try {
      const receipt = await purchaseRecommendedHedge(selected, account);
      setPurchase(receipt);
      onPurchased?.(receipt.transactionHash, receipt.execution);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Hedge purchase failed.");
    } finally { setBuying(false); }
  }

  return (
    <section className="thetanuts-hedge">
      <div className="thetanuts-heading">
        <div><span className="dashboard-eyebrow">Live protocol integration</span><h3>ETH Protection Recommendation</h3></div>
        <span className="thetanuts-network">Base Mainnet</span>
      </div>
      <p>Set the most you are willing to spend. FortiFi will compare live Thetanuts ETH puts and explain the suitable choices.</p>
      {detectionSources.includes("article_content") && <p className="hedge-detection-note">ETH exposure detected from the article content.</p>}

      <div className="hedge-preferences">
        <label>Maximum protection budget
          <span className="hedge-budget-input"><input type="number" min="1" step="1" value={maxBudget} onChange={(event) => setMaxBudget(event.target.value)} disabled={loading || buying} /> USDC</span>
        </label>
        <fieldset disabled={loading || buying}>
          <legend>Protection preference</legend>
          {[['lower_cost', 'Lower Cost'], ['balanced', 'Balanced'], ['stronger', 'Stronger Protection']].map(([value, label]) => (
            <label key={value}><input type="radio" name="hedge-preference" value={value} checked={preference === value} onChange={() => setPreference(value)} />{label}</label>
          ))}
        </fieldset>
        <button type="button" onClick={updateRecommendations} disabled={loading || buying}>{loading ? "Analysing live orders…" : market ? "Update Recommendations" : "Find Protection"}</button>
      </div>

      {!account && <p className="hedge-context-note">You can review recommendations now. Connect a Base wallet before purchasing.</p>}
      {account && wallet && <p className="hedge-context-note">Connected wallet context: {wallet.eth_balance.toFixed(4)} ETH and {wallet.usdc_balance.toFixed(2)} USDC on Base. FortiFi starts from a {preference.replace("_", " ")} profile using {riskLevel.toLowerCase()} claim impact and {ethExposurePercent.toFixed(1)}% ETH allocation; you can change it above.</p>}
      {error && <p className="thetanuts-error" role="alert">{error}</p>}

      {market && (
        <div className="hedge-results">
          <div className="hedge-market-summary">
            <span>ETH spot <strong>{formatUsd(market.spotPrice)}</strong></span>
            <span>Orders analysed <strong>{market.scannedOrders}</strong></span>
            <span>Eligible ETH puts <strong>{market.eligibleOrders}</strong></span>
            <span>Updated <strong>{new Date(market.updatedAt).toLocaleTimeString("en-MY")}</strong></span>
          </div>
          <div className="hedge-choice-grid">
            {market.recommendations.map((item) => (
              <article className={`hedge-choice ${selectedKey === item.orderKey ? "hedge-choice-selected" : ""}`} key={item.orderKey}>
                <div className="hedge-preview-head"><div><span>FortiFi protection profile</span><h4>{item.profile.label}</h4></div>{item.recommended && <strong>Recommended</strong>}</div>
                <div className="hedge-choice-metrics">
                  <div><span>Amount to spend</span><strong>{formatUsd(item.budget)}</strong></div>
                  <div><span>Protection strike</span><strong>{formatUsd(item.strike)}</strong></div>
                  <div><span>Expires</span><strong>{new Date(item.expiry).toLocaleDateString("en-MY")}</strong></div>
                </div>
                <p>{item.reason}</p>
                <TechnicalDetails recommendation={item} />
                <button type="button" className={selectedKey === item.orderKey ? "secondary-button" : "button-secondary"} onClick={() => setSelectedKey(item.orderKey)}>{selectedKey === item.orderKey ? "Selected" : "Choose this protection"}</button>
              </article>
            ))}
          </div>
          {!purchase && <div className="hedge-purchase">
            <p>FortiFi will refresh this exact order before execution. Your wallet may request USDC approval and purchase confirmations.</p>
            {account && wallet && usdcShortfall > 0 && <p className="thetanuts-error" role="status">Insufficient Base USDC. This protection costs about {formatUsd(selectedRecommendation.budget)}; your wallet has {formatUsd(wallet.usdc_balance)}. You need about {formatUsd(usdcShortfall)} more, plus a small amount of Base ETH for gas.</p>}
            <button type="button" onClick={buyHedge} disabled={!account || buying || !selectedKey || usdcShortfall > 0}>{!account ? "Connect Wallet to Buy" : buying ? "Checking latest terms…" : "Protect My ETH"}</button>
          </div>}
          {purchase && <p className="protection-success"><strong>Hedge confirmed</strong><a href={`https://basescan.org/tx/${purchase.transactionHash}`} target="_blank" rel="noreferrer">View Base transaction</a></p>}
        </div>
      )}
    </section>
  );
}

export default ThetanutsHedgePanel;
