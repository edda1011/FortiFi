import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

from app.schemas.analysis import (
    ClaimAnalysisResponse,
    ConsensusAnalysis,
    FinalAssessment,
    ModelAnalysis,
)
from app.services.analysis_store import AnalysisStore
from app.services.analysis_job_service import AnalysisJobService


def _analysis(analysis_id: str = "analysis-1") -> ClaimAnalysisResponse:
    model = ModelAnalysis(
        model="Test model",
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

    store.save(result)

    summaries = store.list_history()
    detail = store.get("analysis-1")

    assert len(summaries) == 1
    assert summaries[0].analysis_id == "analysis-1"
    assert summaries[0].verdict == "UNCERTAIN"
    assert summaries[0].credibility_score == 0.6
    assert detail is not None
    assert detail.analysis.claim == result.claim
    assert detail.follow_ups == []


def test_history_store_persists_follow_up(tmp_path: Path):
    store = AnalysisStore(tmp_path / "fortifi.db")
    store.save(_analysis())

    saved = store.save_follow_up(
        analysis_id="analysis-1",
        question="What evidence is missing?",
        answer="A dated primary source and market data are missing.",
    )

    detail = store.get("analysis-1")

    assert saved.question == "What evidence is missing?"
    assert detail is not None
    assert detail.follow_ups == [saved]


def test_history_store_returns_none_for_unknown_analysis(tmp_path: Path):
    store = AnalysisStore(tmp_path / "fortifi.db")

    assert store.get("missing") is None


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


def test_fast_job_fails_when_fewer_than_two_models_finish(tmp_path: Path, caplog):
    async def run():
        service = AnalysisJobService()
        service.FAST_TIMEOUT_SECONDS = 0.02
        service.claim_service.store = AnalysisStore(tmp_path / "fast-failed.db")
        service.claim_service.search_service.search_evidence = AsyncMock(return_value=[])

        async def analyze(display_name, model, claim, evidence):
            if display_name == "MiniMax-M2.7":
                raise RuntimeError("upstream unavailable")
            await asyncio.sleep(
                0.001 if display_name == "DeepSeek-V4-Flash" else 0.1
            )
            result = _analysis().consensus.model_results[0].model_copy()
            result.model = display_name
            return result

        service.claim_service.gonka_service.analyze_with_model = analyze
        created = service.create("ETH may fall 20%", wait_for_all=False)
        return await _wait_for_job(service, created.job_id)

    job = asyncio.run(run())

    assert job.status == "failed"
    assert sum(item.status == "completed" for item in job.models) == 1
    assert sum(item.status == "failed" for item in job.models) == 1
    assert sum(item.status == "timed_out" for item in job.models) == 1
    assert job.result is None
    assert "MiniMax-M2.7 failed: RuntimeError: upstream unavailable" in caplog.text
