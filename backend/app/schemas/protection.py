from typing import Literal

from pydantic import BaseModel


RecordType = Literal["analysis", "protection"]


class ProtectionPrepareRequest(BaseModel):
    analysis_id: str
    record_type: RecordType = "analysis"
    base_transaction: str = ""


class ProtectionPrepareResponse(BaseModel):
    canonical_report: str
    report_hash: str
    message: str


class ProtectionRecordRequest(ProtectionPrepareRequest):
    signature: str


class ProtectionRecordResponse(BaseModel):
    record_type: RecordType
    report_hash: str
    sui_digest: str
    sui_object_id: str | None = None
    explorer_url: str
    anchored_at: str | None = None
