"""SQLite persistence for completed claim analyses and their evidence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.schemas.analysis import (
    ClaimAnalysisResponse,
    FollowUpEntry,
    DeletedHistorySummary,
    HistoryDetail,
    HistorySummary,
)
from app.schemas.protection import ProtectionRecordResponse


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
                    owner_address TEXT,
                    claim TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(claim_analyses)")
            }
            if "owner_address" not in columns:
                connection.execute("ALTER TABLE claim_analyses ADD COLUMN owner_address TEXT")
            if "deleted_at" not in columns:
                connection.execute("ALTER TABLE claim_analyses ADD COLUMN deleted_at TEXT")
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
            connection.execute("""
                CREATE TABLE IF NOT EXISTS protection_records (
                    analysis_id TEXT PRIMARY KEY,
                    owner_address TEXT NOT NULL,
                    report_hash TEXT NOT NULL UNIQUE,
                    sui_digest TEXT NOT NULL,
                    sui_object_id TEXT,
                    anchored_at TEXT NOT NULL,
                    FOREIGN KEY (analysis_id)
                        REFERENCES claim_analyses (analysis_id)
                        ON DELETE CASCADE
                )
            """)
            self._purge_expired(connection)

    @staticmethod
    def _purge_expired(connection: sqlite3.Connection) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        connection.execute(
            "DELETE FROM claim_analyses WHERE deleted_at IS NOT NULL AND deleted_at < ?",
            (cutoff,),
        )

    def save(self, result: ClaimAnalysisResponse, owner_address: str | None = None) -> None:
        if owner_address is None:
            return
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO claim_analyses "
                "(analysis_id, owner_address, claim, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    result.analysis_id,
                    owner_address.lower(),
                    result.claim,
                    result.model_dump_json(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def recent(self, owner_address: str, limit: int = 5) -> list[ClaimAnalysisResponse]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM claim_analyses WHERE owner_address = ? "
                "AND deleted_at IS NULL "
                "ORDER BY created_at DESC LIMIT ?",
                (owner_address.lower(), limit),
            ).fetchall()
        return [ClaimAnalysisResponse.model_validate_json(row[0]) for row in rows]

    def find_recent_claim(
        self,
        owner_address: str,
        claim: str,
        hours: int = 24,
    ) -> HistoryDetail | None:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT analysis_id, payload, created_at FROM claim_analyses "
                "WHERE owner_address = ? AND claim = ? AND deleted_at IS NULL "
                "AND created_at >= ?",
                (owner_address.lower(), claim, cutoff),
            ).fetchall()
        if not rows:
            return None
        best = max(
            rows,
            key=lambda row: (
                len(ClaimAnalysisResponse.model_validate_json(row[1]).consensus.model_results),
                row[2],
            ),
        )
        return self.get(best[0], owner_address)

    def list_history(self, owner_address: str, limit: int = 50) -> list[HistorySummary]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload, created_at FROM claim_analyses "
                "WHERE owner_address = ? AND deleted_at IS NULL "
                "ORDER BY created_at DESC",
                (owner_address.lower(),),
            ).fetchall()

        best_by_claim: dict[str, tuple[ClaimAnalysisResponse, str]] = {}
        for payload, created_at in rows:
            analysis = ClaimAnalysisResponse.model_validate_json(payload)
            current = best_by_claim.get(analysis.claim)
            if current is None or (
                len(analysis.consensus.model_results),
                created_at,
            ) > (
                len(current[0].consensus.model_results),
                current[1],
            ):
                best_by_claim[analysis.claim] = (analysis, created_at)

        selected = sorted(
            best_by_claim.values(), key=lambda item: item[1], reverse=True
        )[:limit]
        return [
                HistorySummary(
                    analysis_id=analysis.analysis_id,
                    claim=analysis.claim,
                    verdict=analysis.final_assessment.verdict,
                    credibility_score=analysis.consensus.credibility_score,
                    confidence=analysis.consensus.confidence,
                    model_count=len(analysis.consensus.model_results),
                    created_at=created_at,
                    anchored=self.get_protection_record(analysis.analysis_id, owner_address) is not None,
                )
            for analysis, created_at in selected
        ]

    def list_trash(self, owner_address: str, limit: int = 50) -> list[DeletedHistorySummary]:
        with self._connect() as connection:
            self._purge_expired(connection)
            rows = connection.execute(
                "SELECT payload, created_at, deleted_at FROM claim_analyses "
                "WHERE owner_address = ? AND deleted_at IS NOT NULL "
                "ORDER BY deleted_at DESC LIMIT ?",
                (owner_address.lower(), limit),
            ).fetchall()
        return [
            DeletedHistorySummary(
                analysis_id=(analysis := ClaimAnalysisResponse.model_validate_json(payload)).analysis_id,
                claim=analysis.claim,
                verdict=analysis.final_assessment.verdict,
                credibility_score=analysis.consensus.credibility_score,
                confidence=analysis.consensus.confidence,
                model_count=len(analysis.consensus.model_results),
                created_at=created_at,
                deleted_at=deleted_at,
            )
            for payload, created_at, deleted_at in rows
        ]

    def soft_delete(self, analysis_id: str, owner_address: str) -> bool:
        with self._connect() as connection:
            result = connection.execute(
                "UPDATE claim_analyses SET deleted_at = ? "
                "WHERE analysis_id = ? AND owner_address = ? AND deleted_at IS NULL",
                (datetime.now(timezone.utc).isoformat(), analysis_id, owner_address.lower()),
            )
        return result.rowcount > 0

    def restore(self, analysis_id: str, owner_address: str) -> bool:
        with self._connect() as connection:
            self._purge_expired(connection)
            result = connection.execute(
                "UPDATE claim_analyses SET deleted_at = NULL "
                "WHERE analysis_id = ? AND owner_address = ? AND deleted_at IS NOT NULL",
                (analysis_id, owner_address.lower()),
            )
        return result.rowcount > 0

    def permanently_delete(self, analysis_id: str, owner_address: str) -> bool:
        with self._connect() as connection:
            result = connection.execute(
                "DELETE FROM claim_analyses "
                "WHERE analysis_id = ? AND owner_address = ? AND deleted_at IS NOT NULL",
                (analysis_id, owner_address.lower()),
            )
        return result.rowcount > 0

    def get(self, analysis_id: str, owner_address: str) -> HistoryDetail | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload, created_at FROM claim_analyses "
                "WHERE analysis_id = ? AND owner_address = ? AND deleted_at IS NULL",
                (analysis_id, owner_address.lower()),
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
            protection_record=self.get_protection_record(analysis_id, owner_address),
        )

    def get_protection_record(
        self, analysis_id: str, owner_address: str
    ) -> ProtectionRecordResponse | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT report_hash, sui_digest, sui_object_id, anchored_at "
                "FROM protection_records WHERE analysis_id = ? AND owner_address = ?",
                (analysis_id, owner_address.lower()),
            ).fetchone()
        if row is None:
            return None
        report_hash, digest, object_id, anchored_at = row
        return ProtectionRecordResponse(
            report_hash=report_hash,
            sui_digest=digest,
            sui_object_id=object_id,
            explorer_url=f"https://suiscan.xyz/testnet/tx/{digest}",
            anchored_at=anchored_at,
        )

    def save_protection_record(
        self,
        analysis_id: str,
        owner_address: str,
        report_hash: str,
        sui_digest: str,
        sui_object_id: str | None,
    ) -> ProtectionRecordResponse:
        anchored_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO protection_records "
                "(analysis_id, owner_address, report_hash, sui_digest, sui_object_id, anchored_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (analysis_id, owner_address.lower(), report_hash, sui_digest, sui_object_id, anchored_at),
            )
        return self.get_protection_record(analysis_id, owner_address)

    def save_follow_up(
        self,
        analysis_id: str,
        owner_address: str,
        question: str,
        answer: str,
    ) -> FollowUpEntry:
        if self.get(analysis_id, owner_address) is None:
            raise ValueError("Analysis history entry was not found.")
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
