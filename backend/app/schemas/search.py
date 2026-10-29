from typing import List, Optional
from pydantic import BaseModel, Field


class DiscoveredSourceSchema(BaseModel):
    """Schema representing an individual discovered web source."""
    id: Optional[int] = Field(default=None, description="Database record ID if persisted")
    title: str = Field(..., description="Cleaned title of the source")
    url: str = Field(..., description="Original URL")
    canonical_url: str = Field(..., description="Sanitized canonical URL")
    domain: str = Field(..., description="Root domain host")
    snippet: str = Field(default="", description="Search snippet or summary")
    published_at: Optional[str] = Field(default=None, description="Publication date if available")
    publisher: Optional[str] = Field(default=None, description="Publishing organization")
    author: Optional[str] = Field(default=None, description="Article author")
    country: Optional[str] = Field(default=None, description="Country of origin")
    source_type: str = Field(default="UNKNOWN", description="Source classification: PRIMARY, RELIABLE_NEWS, FACT_CHECK, etc.")
    source_role: str = Field(default="INDEPENDENT_SOURCE", description="Source role: USER_SUBMITTED_ARTICLE or INDEPENDENT_SOURCE")
    query: str = Field(..., description="Query used to discover this source")
    retrieved_at: str = Field(..., description="Retrieval timestamp")
    provider: str = Field(..., description="Search provider name")
    syndication_source: Optional[str] = Field(default=None, description="Detected syndication agency")


class SearchQueryAuditSchema(BaseModel):
    """Schema representing an executed search query audit log."""
    query_text: str = Field(..., description="Search query string")
    strategy_level: str = Field(..., description="Search strategy level")
    search_engine: str = Field(..., description="Search engine/provider used")
    results_count: int = Field(..., description="Number of results found")
    status: str = Field(..., description="Query status: success, empty, failed")
    error_message: Optional[str] = Field(default=None, description="Error details if search failed")


class ClaimSearchRequest(BaseModel):
    """Request payload to discover web sources for a claim."""
    claim_id: Optional[int] = Field(default=None, description="Database ID of an existing claim")
    claim_text: Optional[str] = Field(default=None, min_length=5, max_length=1000, description="Ad-hoc claim text to search if claim_id not provided")
    max_queries: int = Field(default=3, ge=1, le=5, description="Maximum queries to generate")
    max_results_per_query: int = Field(default=5, ge=1, le=10, description="Maximum results per query")


class ClaimSearchResponse(BaseModel):
    """Response payload containing discovered web sources and search query audit trail."""
    status: str = Field(default="success", description="Response status")
    claim_id: Optional[int] = Field(default=None, description="Target claim ID")
    claim_text: Optional[str] = Field(default=None, description="Target claim text")
    queries_count: int = Field(..., description="Total queries executed")
    sources_count: int = Field(..., description="Total unique sources discovered")
    queries: List[SearchQueryAuditSchema] = Field(default_factory=list, description="Executed search queries audit")
    sources: List[DiscoveredSourceSchema] = Field(default_factory=list, description="Discovered web sources")
    provider: str = Field(..., description="Active search provider")
    message: str = Field(
        default="Sources discovered successfully. Evidence stance and verdict analysis will be performed in a future phase.",
        description="Phase status notice"
    )
