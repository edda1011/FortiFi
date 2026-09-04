import json

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import keccak

from app.services.analysis_store import AnalysisStore
from app.services.sui_service import SuiService


class ProtectionError(ValueError):
    pass


class ProtectionService:
    def __init__(self) -> None:
        self.store = AnalysisStore()
        self.sui = SuiService()

    def prepare(
        self, analysis_id: str, owner: str, base_transaction: str = ""
    ) -> tuple[str, str, str]:
        detail = self.store.get(analysis_id, owner)
        if detail is None:
            raise ProtectionError("Saved analysis was not found for this wallet.")
        payload = {
            "schema_version": 1,
            "base_wallet": owner.lower(),
            "analysis": detail.analysis.model_dump(mode="json"),
            "created_at": detail.created_at,
            "base_transaction": base_transaction,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        report_hash = "0x" + keccak(text=canonical).hex()
        message = f"FortiFi Protection Record\nReport hash: {report_hash}"
        return canonical, report_hash, message

    def record(
        self,
        analysis_id: str,
        owner: str,
        signature: str,
        base_transaction: str = "",
    ) -> tuple[str, str, str | None]:
        existing = self.store.get_protection_record(analysis_id, owner)
        if existing is not None:
            return existing.report_hash, existing.sui_digest, existing.sui_object_id
        _, report_hash, message = self.prepare(analysis_id, owner, base_transaction)
        try:
            recovered = Account.recover_message(
                encode_defunct(text=message), signature=signature
            )
        except Exception as exc:
            raise ProtectionError("Protection signature could not be verified.") from exc
        if recovered.lower() != owner.lower():
            raise ProtectionError("Protection signature does not match the connected wallet.")
        digest, object_id = self.sui.record(
            report_hash, owner, signature, base_transaction
        )
        self.store.save_protection_record(
            analysis_id, owner, report_hash, digest, object_id
        )
        return report_hash, digest, object_id

    def status(self, analysis_id: str, owner: str):
        return self.store.get_protection_record(analysis_id, owner)
