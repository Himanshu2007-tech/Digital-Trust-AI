from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ClaimVerdictResponse(BaseModel):
    """Schema representing an explainable claim verification verdict dossier."""
    id: Optional[int] = Field(default=None, description="Database VerificationResult ID")
    claim_id: int = Field(..., description="ID of the verified claim")
    claim_text: str = Field(..., description="Claim statement")
    verdict: str = Field(..., description="Classification (SUPPORTED, CONTRADICTED, MISLEADING, UNVERIFIED, INSUFFICIENT_EVIDENCE)")
    confidence: float = Field(..., description="Evidence confidence score (0.0 to 1.0)")
    confidence_level: str = Field(..., description="Categorical confidence (HIGH, MODERATE, LOW)")
    evidence_strength: str = Field(..., description="Evidentiary weight (STRONG, MODERATE, WEAK, INSUFFICIENT)")
    explanation: str = Field(..., description="Traceable factual reasoning")
    supporting_evidence_ids: List[int] = Field(default_factory=list, description="IDs of corroborating evidence")
    contradicting_evidence_ids: List[int] = Field(default_factory=list, description="IDs of conflicting evidence")
    contextual_evidence_ids: List[int] = Field(default_factory=list, description="IDs of background context evidence")
    limitations: List[str] = Field(default_factory=list, description="Specific factual limitations")
    methodology_version: str = Field(default="truthlens-v1.0", description="Evaluation protocol version")
    generated_at: Optional[datetime] = None


class RequestVerdictResponse(BaseModel):
    """Schema representing the overall request verification dossier."""
    id: Optional[int] = Field(default=None, description="VerificationResult ID for overall request")
    request_id: int = Field(..., description="VerificationRequest ID")
    overall_verdict: str = Field(..., description="Synthesized overall classification (SUPPORTED, CONTRADICTED, MISLEADING, UNVERIFIED, INSUFFICIENT_EVIDENCE, MIXED)")
    overall_confidence: float = Field(..., description="Aggregated evidence confidence (0.0 to 1.0)")
    summary: str = Field(..., description="Factual executive summary")
    claims: List[ClaimVerdictResponse] = Field(default_factory=list, description="Claim breakdown")
    claims_count: int = Field(default=0)
    supported_count: int = Field(default=0)
    contradicted_count: int = Field(default=0)
    misleading_count: int = Field(default=0)
    unverified_count: int = Field(default=0)
    insufficient_count: int = Field(default=0)
    limitations: List[str] = Field(default_factory=list)
    methodology_notes: Optional[str] = None
    generated_at: Optional[datetime] = None


class FinalizeRequestOptions(BaseModel):
    """Optional parameters when finalizing request verdicts."""
    reevaluate_claims: bool = Field(default=False, description="Re-run claim verification even if results already exist")
