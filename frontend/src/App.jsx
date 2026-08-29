import { useState } from "react";

import { analyzeClaim } from "./api/claims";


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


function App() {
  const [claim, setClaim] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedClaim = claim.trim();

    if (!trimmedClaim) {
      setError("Please enter a claim.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const analysis =
        await analyzeClaim(trimmedClaim);

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


  return (
    <div className="app">

      <header className="header">
        <div>
          <h1>FortiFi</h1>

          <p>
            Financial Information Risk Analysis
          </p>
        </div>
      </header>


      <main className="main">

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
          <section className="error">
            <strong>Analysis failed</strong>
            <p>{error}</p>
          </section>
        )}


        {loading && (
          <section className="loading">
            <p>
              FortiFi is asking the AI models
              to independently analyze the claim...
            </p>
          </section>
        )}


        {result && !loading && (
          <section className="results">

            <div className="results-header">
              <div>
                <h2>Analysis Result</h2>

                <p>
                  {result.model_results.length} of 3
                  AI models responded.
                </p>
              </div>

              <VerdictBadge
                verdict={result.verdict}
              />
            </div>


            <div className="consensus-grid">

              <div className="metric-card">
                <span>
                  Credibility
                </span>

                <strong>
                  {formatPercentage(
                    result.credibility_score
                  )}
                </strong>
              </div>


              <div className="metric-card">
                <span>
                  AI Confidence
                </span>

                <strong>
                  {formatPercentage(
                    result.confidence
                  )}
                </strong>
              </div>


              <div className="metric-card">
                <span>
                  Market Impact
                </span>

                <strong>
                  {result.market_impact}
                </strong>
              </div>


              <div className="metric-card">
                <span>
                  Model Disagreement
                </span>

                <strong>
                  {formatPercentage(
                    result.disagreement
                  )}
                </strong>
              </div>

            </div>


            <div className="summary">

              <h3>Consensus Assessment</h3>

              <p>
                {result.reasoning_summary}
              </p>

            </div>


            <div className="models">

              <h3>
                Individual Model Results
              </h3>

              {result.model_results.map(
                (modelResult) => (
                  <ModelResult
                    key={modelResult.model}
                    result={modelResult}
                  />
                )
              )}

            </div>

          </section>
        )}

      </main>

    </div>
  );
}


export default App;