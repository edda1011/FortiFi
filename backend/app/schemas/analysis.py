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


class EvidenceItem(BaseModel):
    """A source retained with an analysis so its conclusion is auditable."""

    title: str
    url: str
    source: str
    excerpt: str
    published_at: str | None = None


class PortfolioExposure(BaseModel):
    affected_assets: list[str]
    portfolio_percentage: float = Field(ge=0.0, le=100.0)
    scenario_change: float
    estimated_portfolio_impact: float
    risk_level: MarketImpact
    disclaimer: str


class FinalAssessment(BaseModel):
    verdict: Verdict
    analysis: str


class ClaimAnalysisResponse(BaseModel):
    """The complete evidence → consensus → risk contract for the UI."""

    analysis_id: str
    claim: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    consensus: ConsensusAnalysis
    final_assessment: FinalAssessment
    portfolio_exposure: PortfolioExposure | None = None
    recommendations: list[str] = Field(default_factory=list)


class NewsItem(BaseModel):
    title: str
    url: str
    source: str
    excerpt: str
    published_at: str | None = None


class ClaimAnalysisRequest(BaseModel):
    claim: str = Field(
        min_length=1,
        max_length=10000,
    )


class HistorySummary(BaseModel):
    analysis_id: str
    claim: str
    verdict: Verdict
    credibility_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: str


class FollowUpRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class FollowUpEntry(BaseModel):
    follow_up_id: str
    question: str
    answer: str
    created_at: str


class HistoryDetail(BaseModel):
    analysis: ClaimAnalysisResponse
    created_at: str
    follow_ups: list[FollowUpEntry] = Field(default_factory=list)
