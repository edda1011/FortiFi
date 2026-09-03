"""SQLite persistence for completed claim analyses and their evidence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.analysis import ClaimAnalysisResponse


class AnalysisStore:
    def __init__(self) -> None:
        self.path = Path(__file__).resolve().parents[3] / "data" / "fortifi.db"
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

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)
