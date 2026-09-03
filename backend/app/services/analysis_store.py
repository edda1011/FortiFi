"""SQLite persistence for completed claim analyses and their evidence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.schemas.analysis import (
    ClaimAnalysisResponse,
    FollowUpEntry,
    HistoryDetail,
    HistorySummary,
)


class AnalysisStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parents[3] / "data" / "fortifi.db"
        self._initialize()

    def _initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS claim_analyses (
                    analysis_id TEXT PRIMARY KEY,
                    claim TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS analysis_follow_ups (
                    follow_up_id TEXT PRIMARY KEY,
                    analysis_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (analysis_id)
                        REFERENCES claim_analyses (analysis_id)
                        ON DELETE CASCADE
                )
            """)

    def save(self, result: ClaimAnalysisResponse) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO claim_analyses VALUES (?, ?, ?, ?)",
                (result.analysis_id, result.claim, result.model_dump_json(), datetime.now(timezone.utc).isoformat()),
            )

    def recent(self, limit: int = 5) -> list[ClaimAnalysisResponse]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM claim_analyses ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [ClaimAnalysisResponse.model_validate_json(row[0]) for row in rows]

    def list_history(self, limit: int = 50) -> list[HistorySummary]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload, created_at FROM claim_analyses "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

        summaries = []
        for payload, created_at in rows:
            analysis = ClaimAnalysisResponse.model_validate_json(payload)
            summaries.append(
                HistorySummary(
                    analysis_id=analysis.analysis_id,
                    claim=analysis.claim,
                    verdict=analysis.final_assessment.verdict,
                    credibility_score=analysis.consensus.credibility_score,
                    confidence=analysis.consensus.confidence,
                    created_at=created_at,
                )
            )
        return summaries

    def get(self, analysis_id: str) -> HistoryDetail | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload, created_at FROM claim_analyses "
                "WHERE analysis_id = ?",
                (analysis_id,),
            ).fetchone()
            if row is None:
                return None

            follow_up_rows = connection.execute(
                "SELECT follow_up_id, question, answer, created_at "
                "FROM analysis_follow_ups WHERE analysis_id = ? "
                "ORDER BY created_at ASC",
                (analysis_id,),
            ).fetchall()

        return HistoryDetail(
            analysis=ClaimAnalysisResponse.model_validate_json(row[0]),
            created_at=row[1],
            follow_ups=[
                FollowUpEntry(
                    follow_up_id=follow_up_id,
                    question=question,
                    answer=answer,
                    created_at=created_at,
                )
                for follow_up_id, question, answer, created_at in follow_up_rows
            ],
        )

    def save_follow_up(
        self,
        analysis_id: str,
        question: str,
        answer: str,
    ) -> FollowUpEntry:
        entry = FollowUpEntry(
            follow_up_id=str(uuid4()),
            question=question,
            answer=answer,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO analysis_follow_ups VALUES (?, ?, ?, ?, ?)",
                (
                    entry.follow_up_id,
                    analysis_id,
                    entry.question,
                    entry.answer,
                    entry.created_at,
                ),
            )
        return entry

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
