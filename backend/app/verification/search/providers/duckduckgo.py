import logging
from typing import List
from app.verification.search.base import SearchProvider
from app.verification.search.models import NormalizedSearchResult
from app.verification.search.normalizer import validate_and_normalize_result

logger = logging.getLogger(__name__)


class DuckDuckGoSearchProvider(SearchProvider):
    """
    DuckDuckGo search provider utilizing the official DDGS python client.
    Executes live web searches without requiring an API key.
    """

    @property
    def provider_name(self) -> str:
        return "duckduckgo"

    def is_configured(self) -> bool:
        try:
            try:
                from ddgs import DDGS  # noqa: F401
            except ImportError:
                from duckduckgo_search import DDGS  # noqa: F401
            return True
        except ImportError:
            return False

    def search(self, query: str, max_results: int = 5) -> List[NormalizedSearchResult]:
        if not self.is_configured():
            raise RuntimeError("DuckDuckGo search library ('ddgs' or 'duckduckgo_search') is not installed.")

        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        results: List[NormalizedSearchResult] = []
        try:
            logger.info(f"Executing DuckDuckGo web search: '{query}' (max={max_results})")
            raw_results = list(DDGS().text(query, max_results=max_results))
            for item in raw_results:
                title = item.get("title", "")
                url = item.get("href", "")
                snippet = item.get("body", "")

                norm = validate_and_normalize_result(
                    title=title,
                    url=url,
                    snippet=snippet,
                    query=query,
                    provider=self.provider_name
                )
                if norm:
                    results.append(NormalizedSearchResult(**norm))
        except Exception as exc:
            logger.warning(f"DuckDuckGo search encountered an error for query '{query}': {exc}")
            raise

        return results
