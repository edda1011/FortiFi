from unittest.mock import Mock

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct

from app.services.analysis_store import AnalysisStore
from app.services.protection_service import ProtectionError, ProtectionService
from app.schemas.analysis import HedgeExecutionRequest
from test_claims import _analysis


def configured_service(tmp_path, account):
    service = ProtectionService()
    service.store = AnalysisStore(tmp_path / "fortifi.db")
    service.store.save(_analysis(), account.address)
    service.sui = Mock()
    service.sui.record.return_value = ("sui-digest", "0xrecord")
    return service


def test_prepare_is_deterministic(tmp_path):
    account = Account.create()
    service = configured_service(tmp_path, account)

    first = service.prepare("analysis-1", account.address)
    second = service.prepare("analysis-1", account.address)

    assert first == second
    assert first[1].startswith("0x") and len(first[1]) == 66


def test_signed_report_is_submitted_to_sui(tmp_path):
    account = Account.create()
    service = configured_service(tmp_path, account)
    _, report_hash, message = service.prepare("analysis-1", account.address)
    signature = Account.sign_message(
        encode_defunct(text=message), account.key
    ).signature.hex()

    result = service.record("analysis-1", account.address, signature)

    assert result == (report_hash, "sui-digest", "0xrecord")
    service.sui.record.assert_called_once()


def test_anchored_report_is_persisted_and_not_submitted_twice(tmp_path):
    account = Account.create()
    service = configured_service(tmp_path, account)
    _, report_hash, message = service.prepare("analysis-1", account.address)
    signature = Account.sign_message(
        encode_defunct(text=message), account.key
    ).signature.hex()

    first = service.record("analysis-1", account.address, signature)
    second = service.record("analysis-1", account.address, "unused")
    status = service.status("analysis-1", account.address)

    assert first == second == (report_hash, "sui-digest", "0xrecord")
    assert status.sui_digest == "sui-digest"
    assert status.anchored_at is not None
    assert service.store.list_history(account.address)[0].anchored is True
    assert service.store.get("analysis-1", account.address).analysis_record == status
    service.sui.record.assert_called_once()


def test_changed_wallet_fails_signature_verification(tmp_path):
    owner = Account.create()
    signer = Account.create()
    service = configured_service(tmp_path, owner)
    _, _, message = service.prepare("analysis-1", owner.address)
    signature = Account.sign_message(
        encode_defunct(text=message), signer.key
    ).signature.hex()

    with pytest.raises(ProtectionError, match="does not match"):
        service.record("analysis-1", owner.address, signature)


def test_executed_hedge_is_saved_with_its_analysis(tmp_path):
    account = Account.create()
    store = AnalysisStore(tmp_path / "fortifi.db")
    store.save(_analysis(), account.address)
    request = HedgeExecutionRequest(
        profile="Balanced Protection", recommendation_reason="Balanced cost and strike.",
        eth_spot=2500, max_budget=25, premium=17.5, strike=2250,
        expiry="2026-09-19T00:00:00Z", option_quantity=0.2,
        settlement="Physical", market_snapshot_at="2026-09-05T00:00:00Z",
        transaction_hash="0xbase",
    )

    saved = store.save_hedge_execution("analysis-1", account.address, request)

    assert saved.transaction_hash == "0xbase"
    assert store.get("analysis-1", account.address).hedge_execution == saved


def test_analysis_and_protection_can_each_be_anchored_once(tmp_path):
    account = Account.create()
    service = configured_service(tmp_path, account)
    service.store.save_hedge_execution(
        "analysis-1",
        account.address,
        HedgeExecutionRequest(
            profile="Balanced Protection", recommendation_reason="Balanced cost and strike.",
            eth_spot=2500, max_budget=1, premium=0.7, strike=2250,
            expiry="2026-09-19T00:00:00Z", option_quantity=0.01,
            settlement="Physical", market_snapshot_at="2026-09-05T00:00:00Z",
            transaction_hash="0xbase",
        ),
    )

    hashes = []
    for record_type in ("analysis", "protection"):
        _, report_hash, message = service.prepare("analysis-1", account.address, record_type)
        signature = Account.sign_message(encode_defunct(text=message), account.key).signature.hex()
        service.record("analysis-1", account.address, signature, record_type)
        service.record("analysis-1", account.address, "unused", record_type)
        hashes.append(report_hash)

    detail = service.store.get("analysis-1", account.address)
    assert hashes[0] != hashes[1]
    assert detail.analysis_record.record_type == "analysis"
    assert detail.protection_record.record_type == "protection"
    assert service.sui.record.call_count == 2


def test_protection_anchor_requires_completed_purchase(tmp_path):
    account = Account.create()
    service = configured_service(tmp_path, account)

    with pytest.raises(ProtectionError, match="Purchase protection"):
        service.prepare("analysis-1", account.address, "protection")
