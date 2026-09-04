import { useState } from "react";

import { loadLiveHedgePreview, purchaseLiveHedge } from "../services/thetanuts";


function formatUsd(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}


function ThetanutsHedgePanel({ detectedAssets = [], detectionSources = [], account, onPurchased }) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [buying, setBuying] = useState(false);
  const [assisted, setAssisted] = useState(false);
  const [purchase, setPurchase] = useState(null);

  const isEthClaim = detectedAssets.some((asset) => asset === "ETH");

  if (!isEthClaim) return null;

  async function findHedge() {
    setLoading(true);
    setError("");
    try {
      setPreview(await loadLiveHedgePreview());
    } catch (err) {
      setPreview(null);
      setError(err instanceof Error ? err.message : "Could not load a live hedge.");
    } finally {
      setLoading(false);
    }
  }

  async function buyHedge() {
    setBuying(true);
    setError("");
    try {
      const receipt = await purchaseLiveHedge(account);
      setPurchase(receipt);
      onPurchased?.(receipt.transactionHash);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Hedge purchase failed.");
    } finally {
      setBuying(false);
    }
  }

  return (
    <section className="thetanuts-hedge">
      <div className="thetanuts-heading">
        <div>
          <span className="dashboard-eyebrow">Live protocol integration</span>
          <h3>Thetanuts hedge preview</h3>
        </div>
        <span className="thetanuts-network">Base Mainnet</span>
      </div>

      <p>
        FortiFi can search the live Thetanuts OptionBook for an ETH put near 90%
        of spot price and preview a small, defined-budget hedge.
      </p>

      {detectionSources.includes("article_content") && (
        <p className="hedge-detection-note">ETH exposure detected from the article content.</p>
      )}

      {!preview && (
        <button type="button" onClick={findHedge} disabled={loading}>
          {loading ? "Searching live orders…" : "Find Live Hedge"}
        </button>
      )}

      {error && <p className="thetanuts-error" role="alert">{error}</p>}

      {preview && (
        <div className="hedge-preview">
          <div className="hedge-preview-head">
            <div>
              <span>Recommended contract</span>
              <h4>ETH {preview.product.replaceAll("_", " ")}</h4>
            </div>
            <strong>Live preview</strong>
          </div>

          <div className="hedge-preview-grid">
            <div><span>ETH spot</span><strong>{formatUsd(preview.spotPrice)}</strong></div>
            <div><span>Strike</span><strong>{formatUsd(preview.strike)}</strong></div>
            <div><span>Expiry</span><strong>{new Date(preview.expiry).toLocaleDateString("en-MY")}</strong></div>
            <div><span>Preview budget</span><strong>{formatUsd(preview.budget)}</strong></div>
            <div><span>Contracts</span><strong>{preview.contracts.toFixed(6)}</strong></div>
            <div><span>Settlement</span><strong>{preview.settlement}</strong></div>
          </div>

          <p className="hedge-disclosure">
            Selected from {preview.availableOrders} active ETH put orders. Collateral:
            {` ${preview.collateral}`}. This is a read-only SDK preview; no approval,
            signature, or transaction has been requested.
          </p>

          <div className="hedge-contract-meta">
            <span>Thetanuts OptionBook</span>
            <code>{preview.optionBook}</code>
          </div>

          <button type="button" className="secondary-button" onClick={findHedge} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh Live Preview"}
          </button>

          {!purchase && (
            <div className="hedge-purchase">
              <label>
                <input type="checkbox" checked={assisted} onChange={(event) => setAssisted(event.target.checked)} />
                Enable assisted $5 hedge purchase
              </label>
              <p>FortiFi selected the contract. Your wallet will still ask you to confirm approval and purchase transactions.</p>
              <button type="button" onClick={buyHedge} disabled={!assisted || !account || buying}>
                {!account ? "Connect Wallet to Buy" : buying ? "Confirm in Wallet…" : "Approve & Buy ETH Put"}
              </button>
            </div>
          )}
          {purchase && (
            <p className="protection-success">
              <strong>Hedge confirmed</strong>
              <a href={`https://basescan.org/tx/${purchase.transactionHash}`} target="_blank" rel="noreferrer">View Base transaction</a>
            </p>
          )}
        </div>
      )}
    </section>
  );
}


export default ThetanutsHedgePanel;
