import asyncio

from app.config import settings
from app.integrations.gonka.client import GonkaClient
from app.integrations.gonka.prompts import (
    SYSTEM_PROMPT,
    build_claim_prompt,
)
from app.schemas.analysis import ModelAnalysis


class GonkaService:
    """
    Handles communication between FortiFi and the three
    Gonka AI models.
    """

    def __init__(self) -> None:
        self.client = GonkaClient()

        self.models = {
            "DeepSeek-V4-Flash": settings.gonka_model_deepseek,
            "MiniMax-M2.7": settings.gonka_model_minimax,
            "Kimi-K2.6": settings.gonka_model_kimi,
        }

    async def analyze_claim(
        self,
        claim: str,
        evidence: list[dict] | None = None,
    ) -> list[ModelAnalysis]:

        user_prompt = build_claim_prompt(claim, evidence)

        tasks = [
            self._analyze_with_model(
                display_name=display_name,
                model=model,
                user_prompt=user_prompt,
            )
            for display_name, model in self.models.items()
        ]

        # Run all three models concurrently.
        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        analyses: list[ModelAnalysis] = []
        errors: list[str] = []

        for display_name, result in zip(
            self.models.keys(),
            results,
        ):
            if isinstance(result, Exception):
                error_message = (
                    f"{display_name}: "
                    f"{type(result).__name__}: "
                    f"{result}"
                )

                errors.append(error_message)
                continue

            analyses.append(result)

        # Print failed models during development so that
        # failures are not silently hidden.
        if errors:
            print("\nGonka model errors:")

            for error in errors:
                print(f"  - {error}")

            print()

        # We need at least one successful model response.
        if not analyses:
            raise RuntimeError(
                "All Gonka models failed to analyze the claim."
            )

        return analyses

    async def _analyze_with_model(
        self,
        display_name: str,
        model: str,
        user_prompt: str,
    ) -> ModelAnalysis:

        raw_result = await self.client.analyze_claim(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        return ModelAnalysis(
            model=display_name,
            **raw_result,
        )

    async def finalize_claim(self, claim: str, consensus, evidence: list[dict]) -> dict:
        finalizer_system = """You are FortiFi's final assessment editor. Return ONLY valid JSON.
Use only the supplied consensus and evidence. Never invent facts, sources, prices, or calculations.
The JSON must have exactly: verdict (LIKELY_TRUE, LIKELY_FALSE, or UNCERTAIN), analysis (string), recommendations (array).
Each recommendation must have title, rationale, steps (array of short strings), automation_eligible (boolean), and requires_confirmation (true)."""
        prompt = f"""Synthesize a final FortiFi assessment. Return ONLY JSON with keys verdict, analysis, recommendations.
CLAIM: {claim}
DETERMINISTIC CONSENSUS: {consensus.model_dump_json()}
EVIDENCE: {evidence}
Recommendations must be cautious, actionable considerations, never financial advice. They are plans only: never claim an action was executed and always set requires_confirmation to true. Do not alter consensus scores or invent facts."""
        return await self.client.analyze_claim(
            model=self.models["DeepSeek-V4-Flash"], system_prompt=finalizer_system, user_prompt=prompt
        )
