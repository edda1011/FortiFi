# FortiFi

FortiFi verifies financial claims with multiple AI models, turns detected ETH risk into live protection choices, and records tamper-evident analysis and purchase proofs on-chain.

## How it works

1. **Verify** — Gonka Router sends a claim or article to multiple AI models and FortiFi combines their verdicts, evidence, confidence, and next verification steps.
2. **Assess** — A connected Base wallet provides read-only ETH and USDC balances for portfolio exposure and downside-risk estimates.
3. **Protect** — FortiFi reads live ETH put orders through the Thetanuts SDK, filters eligible contracts, and recommends options within the user's budget and protection preference.
4. **Execute** — The user approves and purchases the selected option from their own wallet on Base mainnet. FortiFi never holds the user's keys.
5. **Prove** — The analysis report can be anchored on Sui before purchase. After a successful hedge, a separate protection record links the analysis hash to its Base transaction.

## Submitted Hackathon tracks

- **AI x Options** — AI-assisted ETH risk analysis connected to live Thetanuts option recommendations.
- **Best Product Built on the Thetanuts SDK** — Live OptionBook discovery, filtering, re-quoting, USDC approval, and purchase flow using `@thetanuts-finance/thetanuts-client`.
- **AI x Sui** — Gonka-generated analysis and completed protection records anchored through a Move contract on Sui testnet.
- **AI for Society** — Helps users evaluate financial misinformation before acting and keeps the reasoning auditable.

## Main features

- Two-model fast analysis or optional three-model consensus through Gonka Router
- URL content retrieval, evidence comparison, model reasoning, and follow-up questions
- MetaMask sign-in with wallet-scoped history; guest results remain temporary
- Base ETH and native USDC balance tracking with 10%, 20%, and 30% downside scenarios
- Budget-aware Basic, Balanced, and Strong ETH protection recommendations
- Live Thetanuts order refresh immediately before execution
- Recoverable history trash with permanent deletion after 30 days
- Separate one-time Sui anchors for analysis reports and completed protection reports

## Architecture

```text
React + MetaMask
       |
       v
FastAPI + SQLite ---- Gonka Router (multi-model analysis)
       |
       +------------- Thetanuts SDK / OptionBook (Base mainnet)
       |
       +------------- Sui CLI + Move contract (Sui testnet)
```

The Base wallet is the user's credential and transaction signer. The backend only reads public balances and verifies signed authentication messages. Sui anchoring is sponsored by FortiFi's backend testnet account, while the user's Base wallet signature authorizes the report to be anchored.

## Prerequisites

- Python 3.11+
- Node.js 20+
- MetaMask or another EIP-1193-compatible wallet
- A Gonka Router API key
- Sui CLI only if you want to create Sui integrity records

The protection purchase flow uses **Base mainnet** and creates real transactions. A purchase requires enough native Base ETH for gas and enough native Base USDC for the selected option. Claim analysis, wallet checks, and recommendation previews do not purchase anything. A transaction is only created after the user explicitly confirms the selected protection.

## Local setup

Clone the repository and open PowerShell in the project root.

### 1. Configure the backend

```powershell
Copy-Item .env.example .env
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set at least `GONKA_API_KEY` in `.env`. The included public RPC defaults are suitable for development, but a dedicated Base RPC is more reliable for a public deployment.

If `sui` is not on `PATH`, set an absolute executable path, for example:

```dotenv
SUI_CLI_PATH=C:\path\to\sui.exe
```

The Sui CLI must use `testnet`, have an active address, and own testnet SUI for sponsored anchor gas:

```powershell
sui client active-env
sui client active-address
sui client gas
```

### 2. Start the API

From the project root with the virtual environment active:

```powershell
uvicorn app.main:app --reload --app-dir backend
```

The API runs at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### 3. Start the frontend

In a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Verification

Run the backend tests from the project root:

```powershell
pytest backend/tests
```

Run the frontend tests and production build:

```powershell
Set-Location frontend
npm test
npm run build
```

Build the Move package:

```powershell
sui move build --path contracts/sui
```

## Sui deployment

The current FortiFi integrity contract is deployed on Sui testnet:

- Package: `0x352816166f738ad99cbf6d2df198076613d3b280d819d5c9ea8263ef1d76bae6`
- Shared registry: `0x1b969374d4b3fd3f07717ad1aae9d951b213498ba08e5c34163ccaea8546ee0d`
- Deployment transaction: [5SQVskZx3oYVCYPFXsHbYeAfqEsCAmpUYvuyey6peFNX](https://suiscan.xyz/testnet/tx/5SQVskZx3oYVCYPFXsHbYeAfqEsCAmpUYvuyey6peFNX)

Anchoring stores hashes and transaction references, not private report contents. Deleting a local history entry cannot delete an immutable Sui record.

## Security

- Never commit `.env`, API keys, recovery phrases, private keys, or Sui keystore files.
- Never paste a recovery phrase or private key into FortiFi.
- The Base wallet always displays and confirms approval and purchase transactions.
- The backend Sui account sponsors only Sui testnet integrity records; it is not a user credential or payment wallet.
- This prototype provides risk information and workflow assistance, not financial advice.

## Demo Flow

1. Connect a Base wallet.
2. Submit a financial claim or article.
3. Review Gonka multi-model verification and risk assessment.
4. View live ETH protection choices from Thetanuts.
5. Select a hedge and confirm the Base transaction.
6. Anchor the analysis or completed protection record on Sui.
7. Review the result in wallet-scoped History.
