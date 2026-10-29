import logging
from typing import List
import httpx

from app.core.config import settings
from app.verification.search.base import SearchProvider
from app.verification.search.models import NormalizedSearchResult
from app.verification.search.normalizer import validate_and_normalize_result

logger = logging.getLogger(__name__)


class TavilySearchProvider(SearchProvider):
    """
    Tavily search provider tailored for factual research and verification.
    Requires SEARCH_API_KEY.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.SEARCH_API_KEY
        self.timeout = settings.SEARCH_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "tavily"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def search(self, query: str, max_results: int = 5) -> List[NormalizedSearchResult]:
        if not self.is_configured():
            raise ValueError("Tavily search requires SEARCH_API_KEY to be configured in .env.")

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_raw_content": False
        }

        results: List[NormalizedSearchResult] = []
        try:
            logger.info(f"Executing Tavily web search: '{query}'")
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()

            for item in data.get("results", []):
                title = item.get("title", "")
                res_url = item.get("url", "")
                snippet = item.get("content", "")
                published_at = item.get("published_date")

                norm = validate_and_normalize_result(
                    title=title,
                    url=res_url,
                    snippet=snippet,
                    query=query,
                    provider=self.provider_name,
                    published_at=published_at
                )
                if norm:
                    results.append(NormalizedSearchResult(**norm))
        except Exception as exc:
            logger.warning(f"Tavily search error for query '{query}': {exc}")
            raise

        return results
