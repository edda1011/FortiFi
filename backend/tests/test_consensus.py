import asyncio
from unittest.mock import AsyncMock

import pytest

from app.services.history_service import HistoryNotFoundError, HistoryService

from test_claims import OWNER, _analysis


def test_follow_up_uses_saved_analysis_context(tmp_path):
    service = HistoryService(database_path=tmp_path / "fortifi.db")
    service.store.save(_analysis(), OWNER)
    service.gonka_service.answer_follow_up = AsyncMock(
        return_value="A primary announcement and dated price data are missing."
    )

    response = asyncio.run(
        service.answer_follow_up("analysis-1", OWNER, "What evidence is missing?")
    )

    assert "primary announcement" in response.answer
    service.gonka_service.answer_follow_up.assert_awaited_once()


def test_follow_up_rejects_unknown_analysis(tmp_path):
    service = HistoryService(database_path=tmp_path / "fortifi.db")

    with pytest.raises(HistoryNotFoundError):
        asyncio.run(service.answer_follow_up("missing", OWNER, "Why?"))
