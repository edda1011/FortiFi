from __future__ import annotations

from pathlib import Path

from app.schemas.analysis import DeletedHistorySummary, FollowUpEntry, HedgeExecution, HedgeExecutionRequest, HistoryDetail, HistorySummary
from app.services.analysis_store import AnalysisStore
from app.services.gonka_service import GonkaService


class HistoryNotFoundError(ValueError):
    pass


class HistoryService:
    def __init__(self, database_path: Path | None = None) -> None:
        self.store = AnalysisStore(database_path)
        self.gonka_service = GonkaService()

    def list(self, owner_address: str, limit: int = 50) -> list[HistorySummary]:
        return self.store.list_history(owner_address, limit=max(1, min(limit, 50)))

    def get(self, analysis_id: str, owner_address: str) -> HistoryDetail:
        detail = self.store.get(analysis_id, owner_address)
        if detail is None:
            raise HistoryNotFoundError("Analysis history entry was not found.")
        return detail

    def find_recent_claim(
        self, owner_address: str, claim: str, hours: int = 24
    ) -> HistoryDetail | None:
        return self.store.find_recent_claim(owner_address, claim.strip(), hours)

    def list_trash(self, owner_address: str, limit: int = 50) -> list[DeletedHistorySummary]:
        return self.store.list_trash(owner_address, limit=max(1, min(limit, 50)))

    def delete(self, analysis_id: str, owner_address: str) -> None:
        if not self.store.soft_delete(analysis_id, owner_address):
            raise HistoryNotFoundError("Analysis history entry was not found.")

    def restore(self, analysis_id: str, owner_address: str) -> None:
        if not self.store.restore(analysis_id, owner_address):
            raise HistoryNotFoundError("Deleted analysis was not found.")

    def permanently_delete(self, analysis_id: str, owner_address: str) -> None:
        if not self.store.permanently_delete(analysis_id, owner_address):
            raise HistoryNotFoundError("Deleted analysis was not found.")

    def save_hedge(self, analysis_id: str, owner_address: str, request: HedgeExecutionRequest) -> HedgeExecution:
        try:
            return self.store.save_hedge_execution(analysis_id, owner_address, request)
        except ValueError as exc:
            raise HistoryNotFoundError(str(exc)) from exc

    async def answer_follow_up(
        self,
        analysis_id: str,
        owner_address: str,
        question: str,
    ) -> FollowUpEntry:
        detail = self.get(analysis_id, owner_address)
        answer = await self.gonka_service.answer_follow_up(
            analysis=detail.analysis,
            previous_follow_ups=detail.follow_ups,
            question=question,
        )
        return self.store.save_follow_up(
            analysis_id=analysis_id,
            owner_address=owner_address,
            question=question,
            answer=answer,
        )
