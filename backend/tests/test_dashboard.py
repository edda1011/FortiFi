import asyncio

from eth_account import Account

import app.api.routes.dashboard as dashboard_module
from app.schemas.analysis import HedgeExecutionRequest
from app.services.analysis_store import AnalysisStore
from test_claims import _analysis


def test_dashboard_starts_without_persisted_risk(monkeypatch, tmp_path):
    owner = Account.create()
    monkeypatch.setattr(dashboard_module, "AnalysisStore", lambda: AnalysisStore(tmp_path / "fortifi.db"))

    summary = asyncio.run(dashboard_module.dashboard_summary(owner.address))

    assert summary.has_risk is False
    assert summary.risk is None


def test_dashboard_returns_latest_executed_hedge(monkeypatch, tmp_path):
    owner = Account.create()
    store = AnalysisStore(tmp_path / "fortifi.db")
    store.save(_analysis(), owner.address)
    store.save_hedge_execution(
        "analysis-1",
        owner.address,
        HedgeExecutionRequest(
            profile="Balanced Protection", recommendation_reason="Balanced cost and strike.",
            eth_spot=2500, max_budget=1, premium=0.7, strike=2250,
            expiry="2026-09-19T00:00:00Z", option_quantity=0.01,
            settlement="Physical", market_snapshot_at="2026-09-05T00:00:00Z",
            transaction_hash="0xbase",
        ),
    )
    monkeypatch.setattr(dashboard_module, "AnalysisStore", lambda: store)

    summary = asyncio.run(dashboard_module.dashboard_summary(owner.address))

    assert summary.latest_hedge_execution.transaction_hash == "0xbase"
