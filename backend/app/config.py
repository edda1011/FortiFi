from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gonka_api_key: str
    gonka_api_url: str = "https://api.gonkarouter.io/v1"

    gonka_model_deepseek: str
    gonka_model_minimax: str
    gonka_model_kimi: str

    # --- Wallet / Base -------------------------------------------------
    #
    # Read-only RPC access. FortiFi never holds a private key, so
    # there is nothing sensitive in this section.

    base_rpc_url: str = "https://mainnet.base.org"

    # Native USDC on Base mainnet (Circle-issued, 6 decimals).
    # https://basescan.org/token/0x833589fcd6edb6e08f4c7c32d4f71b54bda02913
    usdc_contract_address: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    usdc_decimals: int = 6

    # Fixed demo price so the wallet/risk demo doesn't depend on an
    # external price API being up. Update this before a live demo.
    # TODO: replace with a live price source post-hackathon.
    eth_usd_price: float = 4000.0

    # --- Persistence ---------------------------------------------------
    #
    # SQLite only (spec constraint: no other infrastructure). The
    # database file lives under ./data/ relative to the process CWD.

    database_url: str = "sqlite:///./data/fortifi.db"

    # Sui testnet sponsored protection records. The CLI uses its own backend-only
    # keystore; no Sui secret is ever exposed to the browser.
    sui_rpc_url: str = "https://fullnode.testnet.sui.io:443"
    sui_cli_path: str = "sui"
    sui_package_id: str = ""
    sui_registry_id: str = ""
    sui_gas_budget: int = 10_000_000

    # --- Risk engine thresholds ----------------------------------------
    #
    # Demo parameters, not financial advice. Kept in configuration so
    # they can be changed without rewriting the engine (spec section 23).

    # Estimated-loss thresholds (USD) that separate risk levels.
    risk_low_max: float = 500.0
    risk_moderate_max: float = 1500.0
    risk_high_max: float = 5000.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
