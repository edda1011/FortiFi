from unittest.mock import Mock

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct

from app.services.analysis_store import AnalysisStore
from app.services.protection_service import ProtectionError, ProtectionService
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
