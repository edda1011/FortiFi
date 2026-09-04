import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

from app.schemas.analysis import (
    ClaimAnalysisResponse,
    ConsensusAnalysis,
    EvidenceItem,
    FinalAssessment,
    ModelAnalysis,
)
from app.services.analysis_store import AnalysisStore
from app.services.analysis_job_service import AnalysisJobService


OWNER = "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"


def _analysis(analysis_id: str = "analysis-1") -> ClaimAnalysisResponse:
    model = ModelAnalysis(
        model="Test model",
        request_id="chatcmpl-test-123",
        credibility_score=0.6,
        confidence=0.7,
        verdict="UNCERTAIN",
        market_impact="MEDIUM",
        reasoning_summary="More evidence is required.",
    )
    return ClaimAnalysisResponse(
        analysis_id=analysis_id,
        claim="ETH may fall 20% this month.",
        consensus=ConsensusAnalysis(
            credibility_score=0.6,
            confidence=0.7,
            verdict="UNCERTAIN",
            market_impact="MEDIUM",
            disagreement=0.0,
            reasoning_summary="One model responded.",
            model_results=[model],
        ),
        final_assessment=FinalAssessment(
            verdict="UNCERTAIN",
            analysis="The prediction cannot be confirmed.",
        ),
    )


def test_history_store_lists_and_reads_saved_analysis(tmp_path: Path):
    store = AnalysisStore(tmp_path / "fortifi.db")
    result = _analysis()

    store.save(result, OWNER)

    summaries = store.list_history(OWNER)
    detail = store.get("analysis-1", OWNER)

    assert len(summaries) == 1
    assert summaries[0].analysis_id == "analysis-1"
    assert summaries[0].verdict == "UNCERTAIN"
    assert summaries[0].credibility_score == 0.6
    assert summaries[0].model_count == 1
    assert detail is not None
    assert detail.analysis.claim == result.claim
    assert detail.analysis.consensus.model_results[0].request_id == "chatcmpl-test-123"
    assert detail.follow_ups == []


def test_model_analysis_accepts_legacy_result_without_request_id():
    legacy = _analysis().consensus.model_results[0].model_dump()
    legacy.pop("request_id")

    assert ModelAnalysis.model_validate(legacy).request_id is None


def test_history_store_persists_follow_up(tmp_path: Path):
    store = AnalysisStore(tmp_path / "fortifi.db")
    store.save(_analysis(), OWNER)

    saved = store.save_follow_up(
        analysis_id="analysis-1",
        owner_address=OWNER,
        question="What evidence is missing?",
        answer="A dated primary source and market data are missing.",
    )

    detail = store.get("analysis-1", OWNER)

    assert saved.question == "What evidence is missing?"
    assert detail is not None
    assert detail.follow_ups == [saved]


def test_history_store_returns_none_for_unknown_analysis(tmp_path: Path):
    store = AnalysisStore(tmp_path / "fortifi.db")

    assert store.get("missing", OWNER) is None


def test_guest_analysis_is_not_saved(tmp_path: Path):
    store = AnalysisStore(tmp_path / "fortifi.db")
    store.save(_analysis())

    assert store.list_history(OWNER) == []


def test_recent_analysis_is_scoped_to_wallet(tmp_path: Path):
    store = AnalysisStore(tmp_path / "fortifi.db")
    other_owner = "0x0000000000000000000000000000000000000001"
    store.save(_analysis("owner-analysis"), OWNER)
    store.save(_analysis("other-analysis"), other_owner)

    recent = store.recent(OWNER, limit=1)

    assert [analysis.analysis_id for analysis in recent] == ["owner-analysis"]


def test_recent_identical_claim_can_be_reused(tmp_path: Path):
    store = AnalysisStore(tmp_path / "fortifi.db")
    store.save(_analysis(), OWNER)

    match = store.find_recent_claim(OWNER, "ETH may fall 20% this month.")

    assert match is not None
    assert match.analysis.analysis_id == "analysis-1"
    assert store.find_recent_claim(OWNER, "ETH may rise 20% this month.") is None
    assert store.find_recent_claim(
        "0x0000000000000000000000000000000000000001",
        "ETH may fall 20% this month.",
    ) is None


def test_history_groups_identical_claims_and_prefers_full_consensus(tmp_path: Path):
    store = AnalysisStore(tmp_path / "fortifi.db")
    fast = _analysis("fast-analysis").model_copy(deep=True)
    fast.consensus.model_results.append(
        fast.consensus.model_results[0].model_copy(update={"model": "Second model"})
    )
    full = _analysis("full-analysis").model_copy(deep=True)
    full.consensus.model_results.extend(
        [
            full.consensus.model_results[0].model_copy(update={"model": "Second model"}),
            full.consensus.model_results[0].model_copy(update={"model": "Third model"}),
        ]
    )

    store.save(full, OWNER)
    store.save(fast, OWNER)

    summaries = store.list_history(OWNER)
    match = store.find_recent_claim(OWNER, full.claim)

    assert len(summaries) == 1
    assert summaries[0].analysis_id == "full-analysis"
    assert summaries[0].model_count == 3
    assert match is not None
    assert match.analysis.analysis_id == "full-analysis"


def test_deleted_analysis_can_be_restored(tmp_path: Path):
    store = AnalysisStore(tmp_path / "fortifi.db")
    store.save(_analysis(), OWNER)

    assert store.soft_delete("analysis-1", OWNER) is True
    assert store.list_history(OWNER) == []
    assert len(store.list_trash(OWNER)) == 1

    assert store.restore("analysis-1", OWNER) is True
    assert len(store.list_history(OWNER)) == 1
    assert store.list_trash(OWNER) == []


def test_trash_is_permanently_deleted_after_30_days(tmp_path: Path):
    database = tmp_path / "fortifi.db"
    store = AnalysisStore(database)
    store.save(_analysis(), OWNER)
    store.soft_delete("analysis-1", OWNER)
    expired = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE claim_analyses SET deleted_at = ? WHERE analysis_id = ?",
            (expired, "analysis-1"),
        )

    assert store.list_trash(OWNER) == []


def test_trashed_analysis_can_be_permanently_deleted(tmp_path: Path):
    store = AnalysisStore(tmp_path / "fortifi.db")
    store.save(_analysis(), OWNER)
    store.soft_delete("analysis-1", OWNER)

    assert store.permanently_delete("analysis-1", OWNER) is True
    assert store.list_trash(OWNER) == []
    assert store.restore("analysis-1", OWNER) is False


def test_claim_result_uses_a_local_consensus_conclusion(tmp_path: Path):
    service = AnalysisJobService().claim_service
    service.store = AnalysisStore(tmp_path / "local-consensus.db")
    uncertain = _analysis().consensus.model_results[0]
    likely_true = uncertain.model_copy(
        update={"model": "Other model", "verdict": "LIKELY_TRUE"}
    )

    result = service.build_result(
        claim="ETH may fall 20%",
        evidence=[],
        analyses=[uncertain, uncertain.model_copy(), likely_true],
    )

    assert result.final_assessment.verdict == "UNCERTAIN"
    assert "FortiFi verdict: The claim remains unverified." in result.final_assessment.analysis
    assert "2 of 3 models reached this conclusion" in result.final_assessment.analysis
    assert "More evidence is required." in result.final_assessment.analysis
    assert "not a verified trading signal" in result.final_assessment.analysis


def test_claim_result_detects_eth_from_retrieved_article_content(tmp_path: Path):
    service = AnalysisJobService().claim_service
    service.store = AnalysisStore(tmp_path / "asset-detection.db")
    model = _analysis().consensus.model_results[0].model_copy(
        update={"reasoning_summary": "The report needs verification."}
    )
    evidence = [
        EvidenceItem(
            title="Market outlook",
            url="https://example.com/outlook",
            source="Example",
            excerpt="Ethereum demand increased during the quarter.",
        )
    ]

    result = service.build_result(
        claim="https://example.com/outlook",
        evidence=evidence,
        analyses=[model, model.model_copy()],
    )

    assert result.detected_assets == ["ETH"]
    assert result.asset_detection_sources == ["article_content"]


def test_asset_detection_does_not_match_eth_inside_unrelated_words(tmp_path: Path):
    service = AnalysisJobService().claim_service
    service.store = AnalysisStore(tmp_path / "asset-false-positive.db")
    model = _analysis().consensus.model_results[0].model_copy(
        update={"reasoning_summary": "The method needs verification."}
    )

    result = service.build_result(
        claim="A new method may improve returns.",
        evidence=[],
        analyses=[model, model.model_copy()],
    )

    assert result.detected_assets == []
    assert result.asset_detection_sources == []


async def _wait_for_job(service: AnalysisJobService, job_id: str):
    for _ in range(100):
        job = service.get(job_id)
        if job.status in {"completed", "failed"}:
            return job
        await asyncio.sleep(0.01)
    raise AssertionError("Analysis job did not finish")


def test_fast_job_returns_after_two_models_and_cancels_remaining(tmp_path: Path):
    async def run():
        service = AnalysisJobService()
        service.claim_service.store = AnalysisStore(tmp_path / "fast.db")
        service.claim_service.search_service.search_evidence = AsyncMock(return_value=[])

        async def analyze(display_name, model, claim, evidence):
            if display_name == "Kimi-K2.6":
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0.01)
            result = _analysis().consensus.model_results[0].model_copy()
            result.model = display_name
            return result

        service.claim_service.gonka_service.analyze_with_model = analyze
        created = service.create("ETH may fall 20%", wait_for_all=False)
        return await _wait_for_job(service, created.job_id)

    job = asyncio.run(run())

    assert job.status == "completed"
    assert len(job.result.consensus.model_results) == 2
    assert sum(item.status == "completed" for item in job.models) == 2
    assert sum(item.status == "cancelled" for item in job.models) == 1


def test_complete_job_waits_for_all_three_models(tmp_path: Path):
    async def run():
        service = AnalysisJobService()
        service.FAST_TIMEOUT_SECONDS = 0.001
        service.claim_service.store = AnalysisStore(tmp_path / "complete.db")
        service.claim_service.search_service.search_evidence = AsyncMock(return_value=[])

        async def analyze(display_name, model, claim, evidence):
            await asyncio.sleep(0.01)
            result = _analysis().consensus.model_results[0].model_copy()
            result.model = display_name
            return result

        service.claim_service.gonka_service.analyze_with_model = analyze
        created = service.create("ETH may fall 20%", wait_for_all=True)
        return await _wait_for_job(service, created.job_id)

    job = asyncio.run(run())

    assert job.status == "completed"
    assert len(job.result.consensus.model_results) == 3
    assert all(item.status == "completed" for item in job.models)


def test_complete_job_retries_one_transient_model_failure(tmp_path: Path, caplog):
    async def run():
        service = AnalysisJobService()
        service.claim_service.store = AnalysisStore(tmp_path / "retry.db")
        service.claim_service.search_service.search_evidence = AsyncMock(return_value=[])
        attempts = {"Kimi-K2.6": 0}

        async def analyze(display_name, model, claim, evidence):
            if display_name == "Kimi-K2.6":
                attempts[display_name] += 1
                if attempts[display_name] == 1:
                    raise ValueError(
                        "Gonka returned an empty response for model: moonshotai/Kimi-K2.6"
                    )
            result = _analysis().consensus.model_results[0].model_copy()
            result.model = display_name
            return result

        service.claim_service.gonka_service.analyze_with_model = analyze
        created = service.create("ETH may fall 20%", wait_for_all=True)
        job = await _wait_for_job(service, created.job_id)
        return job, attempts

    job, attempts = asyncio.run(run())

    assert job.status == "completed"
    assert attempts["Kimi-K2.6"] == 2
    assert all(item.status == "completed" for item in job.models)
    assert "Kimi-K2.6 attempt 1 failed; retrying once" in caplog.text


def test_fast_job_fails_when_fewer_than_two_models_finish(tmp_path: Path, caplog):
    async def run():
        service = AnalysisJobService()
        service.FAST_TIMEOUT_SECONDS = 0.02
        service.FAST_RETRY_TIMEOUT_SECONDS = 0.02
        service.claim_service.store = AnalysisStore(tmp_path / "fast-failed.db")
        service.claim_service.search_service.search_evidence = AsyncMock(return_value=[])
        attempts = {"Kimi-K2.6": 0}

        async def analyze(display_name, model, claim, evidence):
            if display_name == "MiniMax-M2.7":
                raise RuntimeError("upstream unavailable")
            if display_name == "Kimi-K2.6":
                attempts[display_name] += 1
            await asyncio.sleep(
                0.001 if display_name == "DeepSeek-V4-Flash" else 0.1
            )
            result = _analysis().consensus.model_results[0].model_copy()
            result.model = display_name
            return result

        service.claim_service.gonka_service.analyze_with_model = analyze
        created = service.create("ETH may fall 20%", wait_for_all=False)
        return await _wait_for_job(service, created.job_id), attempts

    job, attempts = asyncio.run(run())

    assert job.status == "failed"
    assert sum(item.status == "completed" for item in job.models) == 1
    assert sum(item.status == "failed" for item in job.models) == 1
    assert sum(item.status == "timed_out" for item in job.models) == 1
    assert attempts["Kimi-K2.6"] == 2
    assert job.result is None
    assert "MiniMax-M2.7 failed: RuntimeError: upstream unavailable" in caplog.text
