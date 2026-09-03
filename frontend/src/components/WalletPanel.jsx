import { useState } from "react";

import { checkWallet } from "../api/wallet";


function formatUsd(value) {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
}


function truncateAddress(address) {
  if (!address || address.length < 12) {
    return address;
  }

  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}


function WalletPanel() {
  const [address, setAddress] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedAddress = address.trim();

    if (!trimmedAddress) {
      setError("Please enter a wallet address.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const snapshot =
        await checkWallet(trimmedAddress);

      setResult(snapshot);
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


  return (
    <div className="wallet-panel">

      <section className="claim-section">

        <div className="section-heading">
          <h2>Check a Wallet</h2>

          <p>
            Enter a public wallet address to read
            its ETH and USDC balances on Base.
            Read-only — FortiFi never asks for a
            private key or seed phrase.
          </p>
        </div>


        <form onSubmit={handleSubmit}>

          <label htmlFor="address">
            Wallet address
          </label>

          <input
            id="address"
            type="text"
            value={address}
            onChange={(event) =>
              setAddress(event.target.value)
            }
            placeholder="0x..."
            disabled={loading}
            maxLength={100}
          />


          <div className="input-footer">

            <span>
              Base mainnet
            </span>

            <button
              type="submit"
              disabled={loading}
            >
              {loading
                ? "Checking..."
                : "Check Wallet"}
            </button>

          </div>

        </form>

      </section>


      {error && (
        <section className="error">
          <strong>Wallet check failed</strong>
          <p>{error}</p>
        </section>
      )}


      {loading && (
        <section className="loading">
          <p>
            Reading balances from Base...
          </p>
        </section>
      )}


      {result && !loading && (
        <section className="results">

          <div className="results-header">
            <div>
              <h2>Portfolio Snapshot</h2>

              <p
                className="wallet-address"
                title={result.address}
              >
                {truncateAddress(result.address)}
                {" · "}
                {result.network}
              </p>
            </div>

            <span className="verdict verdict-likely_true">
              Valid Address
            </span>
          </div>


          <div className="consensus-grid">

            <div className="metric-card">
              <span>ETH Balance</span>
              <strong>
                {result.eth_balance.toFixed(4)} ETH
              </strong>
            </div>

            <div className="metric-card">
              <span>ETH Price</span>
              <strong>
                {formatUsd(result.eth_price)}
              </strong>
            </div>

            <div className="metric-card">
              <span>USDC Balance</span>
              <strong>
                {formatUsd(result.usdc_balance)}
              </strong>
            </div>

            <div className="metric-card">
              <span>Total Value</span>
              <strong>
                {formatUsd(result.total_value)}
              </strong>
            </div>

          </div>


          <div className="summary">
            <h3>ETH Exposure</h3>

            <div className="exposure-bar">
              <div
                className="exposure-fill"
                style={{
                  width: `${result.eth_exposure_percent}%`,
                }}
              />
            </div>

            <p>
              {result.eth_exposure_percent.toFixed(1)}% of
              this wallet's tracked value
              ({formatUsd(result.eth_value)}) is in ETH.
              A sharp move in ETH's price is the main
              thing that would move this portfolio.
            </p>
          </div>

        </section>
      )}

    </div>
  );
}


export default WalletPanel;
