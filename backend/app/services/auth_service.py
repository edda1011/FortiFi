import secrets
import time

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_checksum_address


class AuthError(ValueError):
    pass


class AuthService:
    NONCE_TTL = 300
    SESSION_TTL = 8 * 60 * 60

    def __init__(self) -> None:
        self.nonces: dict[str, tuple[str, float]] = {}
        self.sessions: dict[str, tuple[str, float]] = {}

    @staticmethod
    def normalize(address: str) -> str:
        try:
            return to_checksum_address(address)
        except (TypeError, ValueError) as exc:
            raise AuthError("Invalid Base wallet address.") from exc

    def issue_nonce(self, address: str) -> tuple[str, str]:
        address = self.normalize(address)
        nonce = secrets.token_urlsafe(24)
        self.nonces[address] = (nonce, time.time() + self.NONCE_TTL)
        message = (
            "Sign in to FortiFi\n\n"
            f"Wallet: {address}\n"
            f"Nonce: {nonce}\n\n"
            "This request does not trigger a blockchain transaction or cost gas."
        )
        return address, message

    def verify(self, address: str, signature: str) -> str:
        address = self.normalize(address)
        nonce_data = self.nonces.pop(address, None)
        if nonce_data is None or nonce_data[1] < time.time():
            raise AuthError("Login request expired. Connect the wallet again.")
        message = (
            "Sign in to FortiFi\n\n"
            f"Wallet: {address}\n"
            f"Nonce: {nonce_data[0]}\n\n"
            "This request does not trigger a blockchain transaction or cost gas."
        )
        try:
            recovered = Account.recover_message(
                encode_defunct(text=message), signature=signature
            )
        except Exception as exc:
            raise AuthError("Wallet signature could not be verified.") from exc
        if recovered.lower() != address.lower():
            raise AuthError("Wallet signature does not match this address.")

        token = secrets.token_urlsafe(32)
        self.sessions[token] = (address, time.time() + self.SESSION_TTL)
        return token

    def address_for_token(self, token: str | None) -> str | None:
        if not token:
            return None
        session = self.sessions.get(token)
        if session is None or session[1] < time.time():
            self.sessions.pop(token, None)
            return None
        return session[0]


auth_service = AuthService()
