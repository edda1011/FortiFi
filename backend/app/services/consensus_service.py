from collections import Counter

from app.schemas.analysis import (
    ConsensusAnalysis,
    ModelAnalysis,
)


class ConsensusService:
    """
    Combines the independent AI analyses into a single
    FortiFi consensus result.
    """

    def calculate(
        self,
        analyses: list[ModelAnalysis],
    ) -> ConsensusAnalysis:

        if not analyses:
            raise ValueError(
                "At least one model analysis is required."
            )

        credibility_score = round(
            self._average(
                analysis.credibility_score
                for analysis in analyses
            ),
            4,
        )

        model_confidence = round(
            self._average(
                analysis.confidence
                for analysis in analyses
            ),
            4,
        )

        disagreement = round(
            self._calculate_disagreement(analyses),
            4,
        )

        # Confidence is reduced when models disagree.
        confidence = round(
            max(
                0.0,
                min(
                    1.0,
                    model_confidence * (1.0 - disagreement),
                ),
            ),
            4,
        )

        verdict = self._consensus_verdict(analyses)

        market_impact = self._consensus_market_impact(
            analyses
        )

        reasoning_summary = self._build_summary(
            analyses=analyses,
            credibility=credibility_score,
            confidence=confidence,
            disagreement=disagreement,
        )

        return ConsensusAnalysis(
            credibility_score=credibility_score,
            confidence=confidence,
            verdict=verdict,
            market_impact=market_impact,
            disagreement=disagreement,
            reasoning_summary=reasoning_summary,
            model_results=analyses,
        )

    @staticmethod
    def _average(values) -> float:
        values = list(values)

        if not values:
            return 0.0

        return sum(values) / len(values)

    @staticmethod
    def _calculate_disagreement(
        analyses: list[ModelAnalysis],
    ) -> float:

        if len(analyses) <= 1:
            return 0.0

        scores = [
            analysis.credibility_score
            for analysis in analyses
        ]

        # Simple MVP disagreement metric:
        # difference between highest and lowest model score.
        spread = max(scores) - min(scores)

        return min(1.0, spread)

    @staticmethod
    def _consensus_verdict(
        analyses: list[ModelAnalysis],
    ):

        counts = Counter(
            analysis.verdict
            for analysis in analyses
        )

        return counts.most_common(1)[0][0]

    @staticmethod
    def _consensus_market_impact(
        analyses: list[ModelAnalysis],
    ):

        impact_rank = {
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
        }

        average = sum(
            impact_rank[analysis.market_impact]
            for analysis in analyses
        ) / len(analyses)

        if average >= 2.5:
            return "HIGH"

        if average >= 1.5:
            return "MEDIUM"

        return "LOW"

    @staticmethod
    def _build_summary(
        analyses: list[ModelAnalysis],
        credibility: float,
        confidence: float,
        disagreement: float,
    ) -> str:

        model_count = len(analyses)

        if disagreement >= 0.30:
            disagreement_text = (
                "The models show substantial disagreement."
            )

        elif disagreement >= 0.15:
            disagreement_text = (
                "The models show moderate disagreement."
            )

        else:
            disagreement_text = (
                "The models show relatively strong agreement."
            )

        return (
            f"{model_count} AI model(s) analyzed the claim. "
            f"Consensus credibility score: {credibility:.2f}. "
            f"Consensus confidence: {confidence:.2f}. "
            f"{disagreement_text}"
        )