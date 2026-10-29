import logging
from typing import List
import httpx

from app.core.config import settings
from app.verification.search.base import SearchProvider
from app.verification.search.models import NormalizedSearchResult
from app.verification.search.normalizer import validate_and_normalize_result

logger = logging.getLogger(__name__)


class BraveSearchProvider(SearchProvider):
    """
    Brave Search Web API provider.
    Requires SEARCH_API_KEY.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.SEARCH_API_KEY
        self.timeout = settings.SEARCH_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "brave"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5) -> List[NormalizedSearchResult]:
        if not self.is_configured():
            raise ValueError("Brave Search requires SEARCH_API_KEY to be configured.")

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }
        params = {
            "q": query,
            "count": max_results
        }

        results: List[NormalizedSearchResult] = []
        try:
            logger.info(f"Executing Brave search: '{query}'")
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=headers, params=params)
                res.raise_for_status()
                data = res.json()

            for item in data.get("web", {}).get("results", []):
                title = item.get("title", "")
                res_url = item.get("url", "")
                snippet = item.get("description", "")
                published_at = item.get("page_age")

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
            logger.warning(f"Brave search error for query '{query}': {exc}")
            raise

        return results
