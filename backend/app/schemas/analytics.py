from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AnalyticsActivityItem(BaseModel):
    """Recent verification request summary for the analytics activity feed."""
    id: int
    request_type: str
    status: str
    verdict: Optional[str] = None
    confidence: Optional[float] = None
    confidence_percentage: Optional[float] = None
    created_at: Optional[str] = None
    claims_count: int = 0


class AnalyticsOverviewResponse(BaseModel):
    """Macro-level operational health and verification volume summary."""
    total_requests: int
    completed_count: int
    failed_count: int
    processing_count: int
    partial_count: int
    completion_rate: float = Field(..., description="Percentage of requests completed (0.0 to 100.0)")
    total_claims: int
    average_confidence: Optional[float] = Field(None, description="Average evidence confidence score (0.0 to 1.0) for evaluated records")
    average_confidence_percentage: Optional[float] = Field(None, description="Average evidence confidence formatted as percentage")
    total_sources: int
    total_evidence_items: int
    reports_generated: int
    reports_failed: int
    time_range: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    recent_activity: List[AnalyticsActivityItem] = Field(default_factory=list)


class TimelinePoint(BaseModel):
    """Time-series data point representing verification volume and metrics."""
    date: str
    total: int = 0
    completed: int = 0
    failed: int = 0
    text: int = 0
    url: int = 0
    image: int = 0
    audio: int = 0
    video: int = 0
    avg_confidence: Optional[float] = None


class AnalyticsTimelineResponse(BaseModel):
    """Temporal time-series distribution of verification volume."""
    interval: str
    total_requests: int
    data_points: List[TimelinePoint]
    from_date: Optional[str] = None
    to_date: Optional[str] = None


class TypeBreakdownItem(BaseModel):
    """Modality breakdown item (text, url, image, audio, video)."""
    type: str
    count: int
    percentage: float
    completed_count: int
    avg_confidence: Optional[float] = None


class AnalyticsVerificationTypesResponse(BaseModel):
    """Distribution of requests across different media and input modalities."""
    total_requests: int
    breakdown: List[TypeBreakdownItem]
    from_date: Optional[str] = None
    to_date: Optional[str] = None


class VerdictCountItem(BaseModel):
    """Verdict categorization count and percentage."""
    verdict: str
    count: int
    percentage: float


class AnalyticsVerdictDistributionResponse(BaseModel):
    """
    Categorical distribution of verification findings.
    Strictly separates request-level verdicts from claim-level verdicts.
    """
    total_evaluated_requests: int
    pending_evaluation_requests: int
    request_verdicts: List[VerdictCountItem]
    total_evaluated_claims: int
    claim_verdicts: List[VerdictCountItem]
    methodological_note: str = Field(
        default="The proportion of supported or contradicted claims reflects the specific corpus of queries submitted by users to TruthLens AI and should not be interpreted as a general measure of misinformation prevalence in the broader information ecosystem."
    )
    from_date: Optional[str] = None
    to_date: Optional[str] = None


class DomainCoverageItem(BaseModel):
    """Aggregated information about discovered source domains."""
    domain: str
    sources_count: int
    publisher: Optional[str] = None
    source_type: Optional[str] = None


class AnalyticsSourceCoverageResponse(BaseModel):
    """Transparency metrics regarding external evidence discovery and source corroboration."""
    unique_sources_count: int
    unique_domains_count: int
    total_evidence_passages: int
    avg_sources_per_claim: float
    avg_evidence_per_claim: float
    primary_source_count: int
    primary_source_percentage: float
    top_domains: List[DomainCoverageItem]
    evidence_direction_distribution: Dict[str, int]
    source_independence: Dict[str, int]
    evidence_consistency: Dict[str, int]
    notes: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None
