from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl
from app.verification.domain_models import ClaimType, Verifiability, Importance
from app.schemas.search import DiscoveredSourceSchema, SearchQueryAuditSchema
from app.schemas.evidence import EvidenceItemSchema, SourceComparisonSchema
from app.schemas.verdict import ClaimVerdictResponse, RequestVerdictResponse


class NotImplementedResponse(BaseModel):
    """Standardized response for endpoints planned for future phases."""
    status: str = Field(default="not_implemented", description="Status indicator")
    message: str = Field(
        default="This verification module will be implemented in a future phase.",
        description="Explanation message"
    )
    module: Optional[str] = Field(default=None, description="Module identifier")


class TextVerificationRequest(BaseModel):
    """Input payload for text claim verification."""
    text: str = Field(..., min_length=5, max_length=20000, description="Text or news article claim to verify")
    context: Optional[str] = Field(None, max_length=2000, description="Optional surrounding context or source claimer")
    perform_search: bool = Field(default=True, description="Whether to execute live web search and source discovery")
    extract_evidence: bool = Field(default=True, description="Whether to extract evidence passages and compute source comparisons")
    finalize_verdicts: bool = Field(default=False, description="Whether to finalize verdicts and calculate confidence dossiers for claims and overall request")



from app.schemas.article import ArticleSchema


class ExtractedClaimSchema(BaseModel):
    """Schema for an individual extracted claim in API responses."""
    id: str = Field(..., description="Extraction identifier")
    db_id: Optional[int] = Field(default=None, description="Database record ID")
    text: str = Field(..., description="Atomic claim statement")
    normalized_text: str = Field(..., description="Normalized text")
    claim_type: ClaimType = Field(default=ClaimType.FACTUAL, description="Claim category")
    verifiability: Verifiability = Field(default=Verifiability.VERIFIABLE, description="Verifiability classification")
    importance: Importance = Field(default=Importance.MEDIUM, description="Priority level")
    entities: List[str] = Field(default_factory=list, description="Extracted named entities")
    dates: List[str] = Field(default_factory=list, description="Extracted temporal expressions")
    locations: List[str] = Field(default_factory=list, description="Extracted geographic locations")
    numbers: List[str] = Field(default_factory=list, description="Extracted numbers and statistics")
    source_attributions: List[str] = Field(default_factory=list, description="Source or speaker attributions")
    original_sentence: str = Field(..., description="Original sentence containing this claim")
    extraction_method: str = Field(default="rule_based", description="Extraction engine used")


class TextVerificationResponse(BaseModel):
    """Response payload for text claim extraction, source discovery, and evidence extraction."""
    status: str = Field(default="extracted", description="Request status")
    request_id: int = Field(..., description="Persistent VerificationRequest ID")
    input_text: str = Field(..., description="Cleaned input text")
    sentence_count: int = Field(..., description="Total sentences detected")
    claims_count: int = Field(..., description="Total atomic claims extracted")
    claims: List[ExtractedClaimSchema] = Field(default_factory=list, description="List of extracted claims")
    extraction_method: str = Field(..., description="Extraction engine used")
    sources_count: int = Field(default=0, description="Total unique sources discovered")
    sources: List[DiscoveredSourceSchema] = Field(default_factory=list, description="List of discovered web sources")
    queries: List[SearchQueryAuditSchema] = Field(default_factory=list, description="Search queries executed for audit trail")
    search_provider: Optional[str] = Field(default=None, description="Active search provider used")
    
    # Part 5: Extracted evidence and source comparisons
    evidence_count: int = Field(default=0, description="Total evidence items extracted")
    evidence: List[EvidenceItemSchema] = Field(default_factory=list, description="Traceable evidence items from sources")
    comparisons_count: int = Field(default=0, description="Total source comparisons computed")
    source_comparisons: List[SourceComparisonSchema] = Field(default_factory=list, description="Pairwise & consensus source comparisons")
    
    # Part 6: Verdicts and Request Finalization
    verdict: Optional[RequestVerdictResponse] = Field(default=None, description="Final synthesized verdict dossier")
    claim_verdicts: List[ClaimVerdictResponse] = Field(default_factory=list, description="Claim-by-claim verdict breakdown")
    
    message: str = Field(
        default="Claims extracted, sources discovered, evidence analyzed, and final verdicts synthesized successfully.",
        description="Phase status notice"
    )


class UrlVerificationRequest(BaseModel):
    """Input payload for News URL Verification."""
    url: str = Field(..., min_length=8, max_length=2048, description="Target news article or web page URL")
    perform_search: bool = Field(default=True, description="Whether to discover independent web sources")
    extract_evidence: bool = Field(default=True, description="Whether to extract traceable evidence and compare sources")
    finalize_verdicts: bool = Field(default=True, description="Whether to compute final verdicts and confidence dossiers")


class UrlVerificationResponse(BaseModel):
    """Complete dossier response for News URL Article Verification."""
    status: str = Field(default="completed", description="Overall verification status")
    request_id: int = Field(..., description="Persistent VerificationRequest ID")
    article: ArticleSchema = Field(..., description="Extracted article metadata and content")
    claims_count: int = Field(default=0, description="Number of verifiable claims identified")
    claims: List[ExtractedClaimSchema] = Field(default_factory=list, description="Extracted atomic claims")
    
    # Sources
    sources_count: int = Field(default=0, description="Total sources registered (submitted + independent)")
    sources: List[DiscoveredSourceSchema] = Field(default_factory=list, description="All sources associated with claims")
    submitted_source: Optional[DiscoveredSourceSchema] = Field(default=None, description="The user-submitted article source (NOT counted towards corroboration)")
    independent_sources: List[DiscoveredSourceSchema] = Field(default_factory=list, description="Discovered external corroborating/refuting sources")
    
    # Audit & Search
    queries: List[SearchQueryAuditSchema] = Field(default_factory=list, description="Search queries executed for audit trail")
    search_provider: Optional[str] = Field(default=None, description="Search engine used")
    
    # Evidence & Comparisons
    evidence_count: int = Field(default=0, description="Total evidence items extracted")
    evidence: List[EvidenceItemSchema] = Field(default_factory=list, description="Traceable evidence items from sources")
    comparisons_count: int = Field(default=0, description="Total source comparisons computed")
    source_comparisons: List[SourceComparisonSchema] = Field(default_factory=list, description="Pairwise & consensus source comparisons")
    
    # Final Verdict Dossier
    verdict: Optional[RequestVerdictResponse] = Field(default=None, description="Overall article verdict dossier")
    claim_verdicts: List[ClaimVerdictResponse] = Field(default_factory=list, description="Claim-by-claim verdict breakdown")
    
    message: str = Field(
        default="Article extracted and verified through multi-source independent evidence pipeline.",
        description="Execution status summary"
    )

