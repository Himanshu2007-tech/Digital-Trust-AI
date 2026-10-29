from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class VerdictType(str, Enum):
    """Supported claim-level and request-level verification classifications."""
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    MISLEADING = "MISLEADING"
    UNVERIFIED = "UNVERIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    MIXED = "MIXED"


class EvidenceStrength(str, Enum):
    """Evidentiary weight based on directness, specificity, and source authority."""
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    INSUFFICIENT = "INSUFFICIENT"


class ConfidenceLevel(str, Enum):
    """Categorical confidence level reflecting evidence strength and consistency."""
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


class ClaimVerdictItem(BaseModel):
    """Domain model representing a verified atomic claim verdict dossier."""
    id: Optional[int] = Field(default=None, description="Database VerificationResult ID")
    claim_id: int = Field(..., description="ID of the verified claim")
    claim_text: str = Field(..., description="Exact claim assertion")
    verdict: VerdictType = Field(..., description="Classification category")
    confidence: float = Field(..., description="0.0 to 1.0 evidence confidence score")
    confidence_level: ConfidenceLevel = Field(default=ConfidenceLevel.MODERATE, description="HIGH, MODERATE, or LOW")
    evidence_strength: EvidenceStrength = Field(default=EvidenceStrength.MODERATE, description="STRONG, MODERATE, WEAK, INSUFFICIENT")
    explanation: str = Field(..., description="Factual, human-readable justification referencing evidence")
    
    # Traceable evidence references
    supporting_evidence_ids: List[int] = Field(default_factory=list, description="IDs of corroborating evidence items")
    contradicting_evidence_ids: List[int] = Field(default_factory=list, description="IDs of conflicting evidence items")
    contextual_evidence_ids: List[int] = Field(default_factory=list, description="IDs of contextual evidence items")
    
    # Limitations and caveats
    limitations: List[str] = Field(default_factory=list, description="Active empirical limitations")
    methodology_version: str = Field(default="truthlens-v1.0", description="Methodology version string")
    generated_at: Optional[datetime] = Field(default=None, description="Timestamp of determination")


class RequestVerdictResult(BaseModel):
    """Domain model representing the overall verification dossier for a verification request."""
    id: Optional[int] = Field(default=None, description="Database VerificationResult ID for overall request")
    request_id: int = Field(..., description="VerificationRequest ID")
    overall_verdict: VerdictType = Field(..., description="Overall synthesized classification")
    overall_confidence: float = Field(..., description="Aggregated evidence confidence (0.0 to 1.0)")
    summary: str = Field(..., description="Executive factual synthesis of findings")
    
    claims: List[ClaimVerdictItem] = Field(default_factory=list, description="Claim-by-claim verdict breakdown")
    claims_count: int = Field(default=0, description="Total atomic claims evaluated")
    supported_count: int = Field(default=0, description="Count of supported claims")
    contradicted_count: int = Field(default=0, description="Count of contradicted claims")
    misleading_count: int = Field(default=0, description="Count of misleading claims")
    unverified_count: int = Field(default=0, description="Count of unverified claims")
    insufficient_count: int = Field(default=0, description="Count of insufficient evidence claims")
    
    limitations: List[str] = Field(default_factory=list, description="Aggregated limitations across claims")
    methodology_notes: Optional[str] = Field(default=None, description="Notes on decision methodology")
    generated_at: Optional[datetime] = Field(default=None, description="Timestamp of overall synthesis")
