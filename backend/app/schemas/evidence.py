from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.verification.evidence.models import (
    EvidenceType,
    EvidenceRelevance,
    SourceRelationship,
    EvidenceConsistency
)


class EvidenceItemSchema(BaseModel):
    """Schema representing an extracted piece of evidence for API responses."""
    id: Optional[int] = None
    claim_id: int
    source_id: Optional[int] = None
    
    evidence_text: str = Field(..., description="Exact textual excerpt from source")
    snippet: str = Field(..., description="Excerpt preserved for backwards compatibility")
    
    evidence_type: str = Field(..., description="SUPPORTING, CONTRADICTING, CONTEXTUAL, INSUFFICIENT")
    direction: str = Field(..., description="Direction matching evidence_type")
    
    relevance: str = Field(..., description="HIGH, MEDIUM, LOW")
    relevance_score: float = Field(..., description="0.0 to 1.0 relevance metric")
    
    confidence_in_extraction: float = Field(..., description="Confidence in the extraction process (NOT claim truth)")
    stance_confidence: float = Field(..., description="Stance classification confidence")
    
    source_location: Optional[str] = "snippet"
    extraction_method: str = "rule_based"
    extracted_at: Optional[datetime] = None
    
    url: str
    article_title: Optional[str] = None
    publisher: Optional[str] = None
    domain: Optional[str] = None
    publish_date: Optional[str] = None
    explanation: Optional[str] = None


class SourceComparisonSchema(BaseModel):
    """Schema representing pairwise and synthesis relationships between sources."""
    id: Optional[int] = None
    claim_id: int
    source_a_id: Optional[int] = None
    source_b_id: Optional[int] = None
    
    source_a_title: Optional[str] = None
    source_b_title: Optional[str] = None
    source_a_domain: Optional[str] = None
    source_b_domain: Optional[str] = None
    
    comparison_type: str = "PAIRWISE"
    source_relationship: str = "UNKNOWN"
    evidence_consistency: str = "CONSISTENT_EVIDENCE"
    details: Optional[str] = None
    
    supporting_sources_count: int = 0
    contradicting_sources_count: int = 0
    neutral_sources_count: int = 0
    consensus_verdict: str = "ANALYZED"
    analysis_summary: Optional[str] = None


class ClaimEvidenceRequest(BaseModel):
    """Request payload to analyze evidence for a specific claim."""
    claim_id: int
    force_refresh: bool = False


class ClaimEvidenceResponse(BaseModel):
    """Response payload with extracted evidence and source comparisons for a claim."""
    status: str = "success"
    claim_id: int
    claim_text: str
    evidence_count: int
    evidence: List[EvidenceItemSchema]
    comparisons_count: int
    source_comparisons: List[SourceComparisonSchema]
    message: str


class RequestEvidenceAnalysisResponse(BaseModel):
    """Response payload for bulk verification request evidence analysis."""
    status: str = "success"
    request_id: int
    claims_analyzed: int
    total_evidence: int
    total_comparisons: int
    claims: List[Dict[str, Any]]
    message: str
