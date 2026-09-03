import asyncio
import logging
from uuid import uuid4

from app.schemas.analysis import ModelAnalysis
from app.schemas.analysis_job import AnalysisJobResponse, ModelProgress
from app.services.claim_service import ClaimService


logger = logging.getLogger(__name__)


class AnalysisJobNotFoundError(ValueError):
    pass


class AnalysisJobService:
    FAST_TIMEOUT_SECONDS = 35

    def __init__(self) -> None:
        self.claim_service = ClaimService()
        self.jobs: dict[str, AnalysisJobResponse] = {}
        self._tasks: set[asyncio.Task] = set()

    def create(self, claim: str, wait_for_all: bool) -> AnalysisJobResponse:
        job_id = str(uuid4())
        job = AnalysisJobResponse(
            job_id=job_id,
            status="queued",
            phase="Preparing analysis",
            wait_for_all=wait_for_all,
            models=[
                ModelProgress(model=name)
                for name in self.claim_service.gonka_service.models
            ],
        )
        self.jobs[job_id] = job
        task = asyncio.create_task(self._run(job_id, claim))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    def get(self, job_id: str) -> AnalysisJobResponse:
        job = self.jobs.get(job_id)
        if job is None:
            raise AnalysisJobNotFoundError("Analysis job was not found.")
        return job

    async def _run(self, job_id: str, claim: str) -> None:
        job = self.jobs[job_id]
        job.status = "running"
        job.phase = "Searching supporting evidence"

        try:
            evidence = await self.claim_service.search_service.search_evidence(claim)
            evidence_data = [item.model_dump() for item in evidence]
            job.phase = "Consulting independent AI models"

            tasks = {
                asyncio.create_task(
                    self._run_model(job, name, model, claim, evidence_data)
                ): name
                for name, model in self.claim_service.gonka_service.models.items()
            }
            completed_analyses: list[ModelAnalysis] = []

            for task in asyncio.as_completed(tasks):
                result = await task
                if result is not None:
                    completed_analyses.append(result)

                if not job.wait_for_all and len(completed_analyses) >= 2:
                    for pending in tasks:
                        if not pending.done():
                            pending.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    self._mark_cancelled_models(job)
                    break

            required = 3 if job.wait_for_all else 2
            if len(completed_analyses) < required:
                raise RuntimeError(
                    f"Only {len(completed_analyses)} of 3 AI models completed successfully."
                )

            job.phase = "Building consensus"
            job.result = self.claim_service.build_result(
                claim=claim,
                evidence=evidence,
                analyses=completed_analyses,
            )
            job.status = "completed"
            job.phase = "Analysis complete"
        except Exception as exc:
            job.status = "failed"
            job.phase = "Analysis failed"
            job.error = str(exc)

    async def _run_model(
        self,
        job: AnalysisJobResponse,
        display_name: str,
        model: str,
        claim: str,
        evidence: list[dict],
    ) -> ModelAnalysis | None:
        progress = next(item for item in job.models if item.model == display_name)
        progress.status = "analyzing"
        try:
            analysis = self.claim_service.gonka_service.analyze_with_model(
                display_name=display_name,
                model=model,
                claim=claim,
                evidence=evidence,
            )
            result = (
                await analysis
                if job.wait_for_all
                else await asyncio.wait_for(
                    analysis,
                    timeout=self.FAST_TIMEOUT_SECONDS,
                )
            )
            progress.status = "completed"
            return result
        except asyncio.TimeoutError:
            progress.status = "timed_out"
            progress.error = (
                f"No response within {self.FAST_TIMEOUT_SECONDS} seconds."
            )
            logger.warning(
                "%s timed out after %s seconds.",
                display_name,
                self.FAST_TIMEOUT_SECONDS,
            )
        except asyncio.CancelledError:
            progress.status = "cancelled"
            raise
        except Exception as exc:
            progress.status = "failed"
            progress.error = "This model could not complete the analysis."
            logger.warning(
                "%s failed: %s: %s",
                display_name,
                type(exc).__name__,
                exc,
            )
        return None

    @staticmethod
    def _mark_cancelled_models(job: AnalysisJobResponse) -> None:
        for model in job.models:
            if model.status == "analyzing":
                model.status = "cancelled"
                model.error = "Fast consensus was ready before this model finished."
