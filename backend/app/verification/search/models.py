from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SourceType(str, Enum):
    """Classification of retrieved web sources for evidence evaluation."""
    PRIMARY = "PRIMARY"
    RELIABLE_NEWS = "RELIABLE_NEWS"
    FACT_CHECK = "FACT_CHECK"
    SECONDARY = "SECONDARY"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    BLOG = "BLOG"
    UNKNOWN = "UNKNOWN"


class NormalizedSearchResult(BaseModel):
    """Normalized internal representation of a search result across all providers."""
    title: str = Field(..., description="Cleaned title of the article or page")
    url: str = Field(..., description="Original retrieved URL")
    canonical_url: str = Field(..., description="Sanitized, canonical URL without tracking parameters")
    domain: str = Field(..., description="Root domain host (e.g., rbi.org.in, reuters.com)")
    snippet: str = Field(default="", description="Search engine snippet or meta description")
    published_at: Optional[str] = Field(default=None, description="Reported publication date if available (null if unknown)")
    publisher: Optional[str] = Field(default=None, description="Identified publishing organization or news outlet")
    author: Optional[str] = Field(default=None, description="Article author if available")
    country: Optional[str] = Field(default=None, description="Country of origin based on domain TLD or metadata")
    source_type: SourceType = Field(default=SourceType.UNKNOWN, description="Classified source category")
    query: str = Field(..., description="The exact search query that retrieved this result")
    retrieved_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO timestamp of retrieval")
    provider: str = Field(..., description="Search provider name (e.g., duckduckgo, tavily, google)")
    syndication_source: Optional[str] = Field(default=None, description="Detected syndication origin (e.g., Reuters wire, AP)")


class SearchQueryAudit(BaseModel):
    """Audit record for a search query executed during investigation."""
    claim_id: Optional[int] = Field(default=None, description="ID of the claim being investigated")
    query_text: str = Field(..., description="Search query string")
    strategy_level: str = Field(default="LEVEL_1", description="Strategy level: LEVEL_1_EXACT, LEVEL_2_ENTITY_DATE, LEVEL_3_OFFICIAL, LEVEL_4_FACT_CHECK")
    search_engine: str = Field(..., description="Search provider used")
    results_count: int = Field(default=0, description="Number of results retrieved")
    status: str = Field(default="success", description="Execution status: success, empty, failed")
    error_message: Optional[str] = Field(default=None, description="Error details if search failed")
    raw_response_json: Optional[Dict[str, Any]] = Field(default=None, description="Raw provider response for transparency")
