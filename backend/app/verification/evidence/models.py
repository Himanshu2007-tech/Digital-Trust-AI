from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """Categorization of how evidence relates to a specific claim."""
    SUPPORTING = "SUPPORTING"
    CONTRADICTING = "CONTRADICTING"
    CONTEXTUAL = "CONTEXTUAL"
    INSUFFICIENT = "INSUFFICIENT"


class EvidenceRelevance(str, Enum):
    """How closely the source material pertains to the claim."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SourceRelationship(str, Enum):
    """Inter-source independence and provenance relationship."""
    INDEPENDENT = "INDEPENDENT"
    POSSIBLY_SYNDICATED = "POSSIBLY_SYNDICATED"
    DUPLICATE = "DUPLICATE"
    UNKNOWN = "UNKNOWN"


class EvidenceConsistency(str, Enum):
    """Whether sources report consistent or conflicting information."""
    CONSISTENT_EVIDENCE = "CONSISTENT_EVIDENCE"
    CONFLICTING_INFORMATION = "CONFLICTING_INFORMATION"
    COMPLEMENTARY = "COMPLEMENTARY"
    INSUFFICIENT = "INSUFFICIENT"


class ExtractedEvidenceItem(BaseModel):
    """Domain model representing an item of evidence extracted from a source."""
    id: Optional[int] = Field(default=None, description="Database ID if persisted")
    claim_id: int = Field(..., description="ID of the claim being evaluated")
    source_id: Optional[int] = Field(default=None, description="ID of the source")
    
    # Exact snippet/quote directly from source - NO SYNTHETIC QUOTES
    evidence_text: str = Field(..., description="Exact textual excerpt from source content or snippet")
    snippet: str = Field(..., description="Excerpt preserved for backwards compatibility")
    
    evidence_type: EvidenceType = Field(..., description="SUPPORTING, CONTRADICTING, CONTEXTUAL, INSUFFICIENT")
    direction: str = Field(default="CONTEXTUAL", description="Direction string matching evidence_type")
    
    relevance: EvidenceRelevance = Field(default=EvidenceRelevance.MEDIUM, description="HIGH, MEDIUM, LOW")
    relevance_score: float = Field(default=0.5, description="Normalized relevance metric from 0.0 to 1.0")
    
    confidence_in_extraction: float = Field(default=1.0, description="Confidence in the extraction process, NOT claim truth")
    stance_confidence: float = Field(default=0.5, description="Stance classification confidence")
    
    source_location: Optional[str] = Field(default="snippet", description="Location within the source e.g. snippet, headline")
    extraction_method: str = Field(default="rule_based", description="rule_based, llm, hybrid")
    extracted_at: Optional[datetime] = Field(default=None, description="Timestamp of extraction")
    
    url: str = Field(..., description="Original URL of the source")
    article_title: Optional[str] = Field(default=None, description="Source article title")
    publisher: Optional[str] = Field(default=None, description="Publisher name")
    domain: Optional[str] = Field(default=None, description="Publisher web domain")
    publish_date: Optional[str] = Field(default=None, description="Published date string")
    
    explanation: Optional[str] = Field(default=None, description="Objective explanation of the evidence relationship")


class SourceComparisonItem(BaseModel):
    """Domain model representing pairwise or group comparison of sources."""
    id: Optional[int] = Field(default=None, description="Database ID if persisted")
    claim_id: int = Field(..., description="ID of the claim evaluated")
    source_a_id: Optional[int] = Field(default=None, description="Source A ID")
    source_b_id: Optional[int] = Field(default=None, description="Source B ID")
    
    source_a_title: Optional[str] = Field(default=None, description="Title of Source A")
    source_b_title: Optional[str] = Field(default=None, description="Title of Source B")
    source_a_domain: Optional[str] = Field(default=None, description="Domain of Source A")
    source_b_domain: Optional[str] = Field(default=None, description="Domain of Source B")
    
    comparison_type: str = Field(default="PAIRWISE", description="PAIRWISE or GROUP_SYNTHESIS")
    source_relationship: SourceRelationship = Field(default=SourceRelationship.UNKNOWN, description="INDEPENDENT, POSSIBLY_SYNDICATED, DUPLICATE, UNKNOWN")
    evidence_consistency: EvidenceConsistency = Field(default=EvidenceConsistency.CONSISTENT_EVIDENCE, description="CONSISTENT_EVIDENCE, CONFLICTING_INFORMATION, COMPLEMENTARY, INSUFFICIENT")
    details: Optional[str] = Field(default=None, description="Explanation of source overlap, agreement, or contradiction")
    
    supporting_sources_count: int = Field(default=0, description="Count of supporting sources in group")
    contradicting_sources_count: int = Field(default=0, description="Count of contradicting sources in group")
    neutral_sources_count: int = Field(default=0, description="Count of contextual/insufficient sources in group")
    consensus_verdict: str = Field(default="ANALYZED", description="Consensus status - NOT final truth verdict")
    analysis_summary: Optional[str] = Field(default=None, description="Factual synthesis of source findings")
