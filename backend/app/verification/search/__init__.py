"""
TruthLens AI - Search & Source Discovery Engine (Part 4)
Provides:
- SearchProvider abstract base class
- Providers: DuckDuckGo, Tavily, Google, SerpApi, Brave, Mock
- SearchQueryGenerator (Multi-level search strategies)
- URL Normalization & Source Categorization (PRIMARY, RELIABLE_NEWS, FACT_CHECK, etc.)
- SourceDiscoveryService
- ArticleContentExtractor
"""

from app.verification.search.models import (
    SourceType,
    NormalizedSearchResult,
    SearchQueryAudit
)
from app.verification.search.base import SearchProvider
from app.verification.search.query_generator import SearchQueryGenerator, GeneratedQuery
from app.verification.search.normalizer import (
    normalize_url,
    extract_domain,
    classify_source,
    detect_syndication,
    validate_and_normalize_result
)
from app.verification.search.content_extractor import (
    ArticleContentExtractor,
    WebPageContentExtractor
)
from app.verification.search.providers.factory import get_search_provider
from app.verification.search.discovery_service import SourceDiscoveryService

__all__ = [
    "SourceType",
    "NormalizedSearchResult",
    "SearchQueryAudit",
    "SearchProvider",
    "SearchQueryGenerator",
    "GeneratedQuery",
    "normalize_url",
    "extract_domain",
    "classify_source",
    "detect_syndication",
    "validate_and_normalize_result",
    "ArticleContentExtractor",
    "WebPageContentExtractor",
    "get_search_provider",
    "SourceDiscoveryService",
]
