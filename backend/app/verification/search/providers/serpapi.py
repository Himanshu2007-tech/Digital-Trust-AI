import logging
from typing import List
import httpx

from app.core.config import settings
from app.verification.search.base import SearchProvider
from app.verification.search.models import NormalizedSearchResult
from app.verification.search.normalizer import validate_and_normalize_result

logger = logging.getLogger(__name__)


class SerpApiSearchProvider(SearchProvider):
    """
    SerpApi search provider for Google Search scraping.
    Requires SEARCH_API_KEY.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.SEARCH_API_KEY
        self.timeout = settings.SEARCH_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "serpapi"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5) -> List[NormalizedSearchResult]:
        if not self.is_configured():
            raise ValueError("SerpApi search requires SEARCH_API_KEY to be configured.")

        url = "https://serpapi.com/search"
        params = {
            "api_key": self.api_key,
            "q": query,
            "engine": "google",
            "num": max_results
        }

        results: List[NormalizedSearchResult] = []
        try:
            logger.info(f"Executing SerpApi search: '{query}'")
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, params=params)
                res.raise_for_status()
                data = res.json()

            for item in data.get("organic_results", []):
                title = item.get("title", "")
                res_url = item.get("link", "")
                snippet = item.get("snippet", "")
                published_at = item.get("date")

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
            logger.warning(f"SerpApi search error for query '{query}': {exc}")
            raise

        return results
