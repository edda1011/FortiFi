from pathlib import Path

from app.schemas.analysis import FollowUpEntry, HistoryDetail, HistorySummary
from app.services.analysis_store import AnalysisStore
from app.services.gonka_service import GonkaService


class HistoryNotFoundError(ValueError):
    pass


class HistoryService:
    def __init__(self, database_path: Path | None = None) -> None:
        self.store = AnalysisStore(database_path)
        self.gonka_service = GonkaService()

    def list(self, limit: int = 50) -> list[HistorySummary]:
        return self.store.list_history(limit=max(1, min(limit, 50)))

    def get(self, analysis_id: str) -> HistoryDetail:
        detail = self.store.get(analysis_id)
        if detail is None:
            raise HistoryNotFoundError("Analysis history entry was not found.")
        return detail

    async def answer_follow_up(
        self,
        analysis_id: str,
        question: str,
    ) -> FollowUpEntry:
        detail = self.get(analysis_id)
        answer = await self.gonka_service.answer_follow_up(
            analysis=detail.analysis,
            previous_follow_ups=detail.follow_ups,
            question=question,
        )
        return self.store.save_follow_up(
            analysis_id=analysis_id,
            question=question,
            answer=answer,
        )
