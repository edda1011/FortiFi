from typing import Literal

from pydantic import BaseModel, Field


Verdict = Literal[
    "LIKELY_TRUE",
    "LIKELY_FALSE",
    "UNCERTAIN",
]

MarketImpact = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
]


class ModelAnalysis(BaseModel):
    model: str

    credibility_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    verdict: Verdict

    market_impact: MarketImpact

    reasoning_summary: str

    supporting_evidence: list[str] = Field(
        default_factory=list
    )

    contradicting_evidence: list[str] = Field(
        default_factory=list
    )

    missing_context: list[str] = Field(
        default_factory=list
    )


class ConsensusAnalysis(BaseModel):
    credibility_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    verdict: Verdict

    market_impact: MarketImpact

    disagreement: float = Field(
        ge=0.0,
        le=1.0,
    )

    reasoning_summary: str

    model_results: list[ModelAnalysis]


class ClaimAnalysisRequest(BaseModel):
    claim: str = Field(
        min_length=1,
        max_length=10000,
    )