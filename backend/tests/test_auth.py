import time

import pytest
from fastapi import HTTPException
from eth_account import Account
from eth_account.messages import encode_defunct

from app.services.auth_service import AuthError, AuthService
from app.api.auth import optional_wallet


def test_signed_nonce_creates_session():
    service = AuthService()
    account = Account.create()
    address, message = service.issue_nonce(account.address)
    signature = Account.sign_message(
        encode_defunct(text=message), account.key
    ).signature.hex()

    token = service.verify(address, signature)

    assert service.address_for_token(token) == address


def test_signature_from_another_wallet_is_rejected():
    service = AuthService()
    account = Account.create()
    address, message = service.issue_nonce(account.address)
    signature = Account.sign_message(
        encode_defunct(text=message), Account.create().key
    ).signature.hex()

    with pytest.raises(AuthError, match="does not match"):
        service.verify(address, signature)


def test_expired_session_is_rejected():
    service = AuthService()
    service.sessions["expired"] = (Account.create().address, time.time() - 1)

    assert service.address_for_token("expired") is None


def test_invalid_optional_session_is_not_treated_as_guest():
    with pytest.raises(HTTPException) as error:
        optional_wallet("Bearer invalid")

    assert error.value.status_code == 401
