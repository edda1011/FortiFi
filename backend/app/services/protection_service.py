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
        self, analysis_id: str, owner: str, record_type: str = "analysis"
    ) -> tuple[str, str, str]:
        detail = self.store.get(analysis_id, owner)
        if detail is None:
            raise ProtectionError("Saved analysis was not found for this wallet.")
        analysis_payload = {
            "schema_version": 1,
            "record_type": "analysis",
            "base_wallet": owner.lower(),
            "analysis": detail.analysis.model_dump(mode="json"),
            "created_at": detail.created_at,
        }
        analysis_canonical = json.dumps(analysis_payload, sort_keys=True, separators=(",", ":"))
        analysis_hash = "0x" + keccak(text=analysis_canonical).hex()
        if record_type == "analysis":
            payload = analysis_payload
        elif record_type == "protection":
            if detail.hedge_execution is None:
                raise ProtectionError("Purchase protection before anchoring a protection report.")
            payload = {
                "schema_version": 1,
                "record_type": "protection",
                "base_wallet": owner.lower(),
                "analysis_id": analysis_id,
                "analysis_report_hash": analysis_hash,
                "hedge_execution": detail.hedge_execution.model_dump(mode="json"),
            }
        else:
            raise ProtectionError("Unsupported integrity record type.")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        report_hash = "0x" + keccak(text=canonical).hex()
        label = "Analysis" if record_type == "analysis" else "Protection"
        message = f"FortiFi {label} Integrity Record\nReport hash: {report_hash}"
        return canonical, report_hash, message

    def record(
        self,
        analysis_id: str,
        owner: str,
        signature: str,
        record_type: str = "analysis",
    ) -> tuple[str, str, str | None]:
        existing = self.store.get_integrity_record(analysis_id, owner, record_type)
        if existing is not None:
            return existing.report_hash, existing.sui_digest, existing.sui_object_id
        _, report_hash, message = self.prepare(analysis_id, owner, record_type)
        try:
            recovered = Account.recover_message(
                encode_defunct(text=message), signature=signature
            )
        except Exception as exc:
            raise ProtectionError("Protection signature could not be verified.") from exc
        if recovered.lower() != owner.lower():
            raise ProtectionError("Protection signature does not match the connected wallet.")
        detail = self.store.get(analysis_id, owner)
        base_transaction = detail.hedge_execution.transaction_hash if record_type == "protection" else ""
        digest, object_id = self.sui.record(
            report_hash, owner, signature, record_type, base_transaction
        )
        self.store.save_integrity_record(
            analysis_id, owner, record_type, report_hash, digest, object_id
        )
        return report_hash, digest, object_id

    def status(self, analysis_id: str, owner: str, record_type: str = "analysis"):
        return self.store.get_integrity_record(analysis_id, owner, record_type)
