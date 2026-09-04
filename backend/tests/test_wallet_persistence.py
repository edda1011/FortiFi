"""
Unit tests for wallet persistence, retrieval, and exposure.

These never touch the real network or the real data/fortifi.db. They
use an in-memory SQLite database created per-test, and mock Base RPC
calls so the suite runs with zero network access.
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database.database import Base
from app.database.repositories.wallet_repository import WalletRepository
from app.main import app
from app.schemas.wallet import WalletCheckResponse
from app.services.wallet_service import (
    NoSnapshotError,
    WalletService,
    get_current_exposure,
)


ADDRESS = "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"


@pytest.fixture()
def db_session(monkeypatch, tmp_path):
    """
    A temp-file SQLite session with a fresh schema per test, wired
    into the app's SessionLocal so routes and services share it.
    """

    db_path = tmp_path / "test.db"

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    # Point the app's session factory at this isolated DB so the
    # routes' get_session() and the repository share the same data.
    import app.database.database as database_module

    monkeypatch.setattr(database_module, "SessionLocal", TestingSession)

    session = TestingSession()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture()
def client(db_session):
    """
    A TestClient whose wallet routes use the isolated temp-file DB.
    """

    with TestClient(app) as test_client:
        yield test_client


def make_snapshot(
    address: str = ADDRESS,
    eth_balance: float = 2.41,
    eth_price: float = 4000.0,
    usdc_balance: float = 1250.0,
) -> WalletCheckResponse:
    eth_value = eth_balance * eth_price
    total_value = eth_value + usdc_balance
    exposure = (
        float(eth_value / total_value * 100)
        if total_value > 0
        else 0.0
    )

    return WalletCheckResponse(
        address=address,
        network="base",
        valid=True,
        eth_balance=eth_balance,
        eth_price=eth_price,
        eth_value=eth_value,
        usdc_balance=usdc_balance,
        total_value=total_value,
        eth_exposure_percent=round(exposure, 2),
    )


# --- Repository: save + read back --------------------------------------

def test_repository_saves_and_reads_snapshot(db_session):
    repo = WalletRepository(db_session)

    saved = repo.save_snapshot(make_snapshot())

    assert saved.id is not None
    assert saved.wallet_address == ADDRESS

    latest = repo.get_latest(ADDRESS)

    assert latest is not None
    assert latest.eth_balance == 2.41
    assert latest.usdc_balance == 1250.0
    assert latest.total_value == pytest.approx(2.41 * 4000.0 + 1250.0)


def test_repository_get_latest_returns_none_when_empty(db_session):
    repo = WalletRepository(db_session)

    assert repo.get_latest(ADDRESS) is None


def test_repository_list_by_address_orders_most_recent_first(db_session):
    repo = WalletRepository(db_session)

    repo.save_snapshot(make_snapshot(usdc_balance=1000.0))
    repo.save_snapshot(make_snapshot(usdc_balance=2000.0))

    snapshots = repo.list_by_address(ADDRESS)

    assert len(snapshots) == 2
    # Most recent first.
    assert snapshots[0].usdc_balance == 2000.0
    assert snapshots[1].usdc_balance == 1000.0


def test_repository_list_by_address_respects_limit(db_session):
    repo = WalletRepository(db_session)

    for i in range(5):
        repo.save_snapshot(make_snapshot(usdc_balance=float(i)))

    snapshots = repo.list_by_address(ADDRESS, limit=3)

    assert len(snapshots) == 3


# --- GET /latest --------------------------------------------------------

def test_get_latest_returns_saved_snapshot(client, db_session):
    repo = WalletRepository(db_session)
    repo.save_snapshot(make_snapshot())

    response = client.get(f"/api/wallet/{ADDRESS}/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["address"] == ADDRESS
    assert body["eth_balance"] == 2.41
    assert body["total_value"] == pytest.approx(2.41 * 4000.0 + 1250.0)


def test_get_latest_404_when_no_snapshot(client):
    response = client.get(f"/api/wallet/{ADDRESS}/latest")

    assert response.status_code == 404


def test_get_latest_rejects_invalid_address(client):
    response = client.get("/api/wallet/not-an-address/latest")

    assert response.status_code == 400


# --- GET /history -------------------------------------------------------

def test_get_history_returns_snapshots(client, db_session):
    repo = WalletRepository(db_session)
    repo.save_snapshot(make_snapshot(usdc_balance=1000.0))
    repo.save_snapshot(make_snapshot(usdc_balance=2000.0))

    response = client.get(f"/api/wallet/{ADDRESS}/history")

    assert response.status_code == 200
    body = response.json()
    assert body["address"] == ADDRESS
    assert len(body["snapshots"]) == 2
    # Most recent first.
    assert body["snapshots"][0]["usdc_balance"] == 2000.0


def test_get_history_empty_when_no_snapshots(client):
    response = client.get(f"/api/wallet/{ADDRESS}/history")

    assert response.status_code == 200
    assert response.json()["snapshots"] == []


# --- GET /exposure ------------------------------------------------------

def test_get_exposure_404_when_no_snapshot(client):
    response = client.get(f"/api/wallet/{ADDRESS}/exposure")

    assert response.status_code == 404


def test_get_exposure_returns_values(client, db_session):
    repo = WalletRepository(db_session)
    repo.save_snapshot(make_snapshot())

    response = client.get(f"/api/wallet/{ADDRESS}/exposure")

    assert response.status_code == 200
    body = response.json()
    assert body["address"] == ADDRESS
    assert body["eth_value"] == pytest.approx(2.41 * 4000.0)
    assert body["total_value"] == pytest.approx(2.41 * 4000.0 + 1250.0)
    assert 0.0 <= body["eth_exposure_percent"] <= 100.0
    assert body["as_of"] is not None


def test_get_current_exposure_raises_when_no_snapshot(db_session):
    with pytest.raises(NoSnapshotError):
        get_current_exposure(ADDRESS)


# --- DB write failure during check() still returns a valid response -----

def test_check_returns_response_even_if_persistence_fails(
    db_session,
    monkeypatch,
):
    service = WalletService()
    service.client.get_eth_balance = AsyncMock(return_value=Decimal("2.41"))
    service.client.get_erc20_balance = AsyncMock(return_value=Decimal("1250"))

    def boom(response):
        raise RuntimeError("disk full")

    monkeypatch.setattr(service, "_persist_snapshot", boom)

    result = asyncio.run(
        service.check("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed")
    )

    assert result.valid is True
    assert result.eth_balance == 2.41
    assert result.total_value == pytest.approx(2.41 * 4000.0 + 1250.0)
