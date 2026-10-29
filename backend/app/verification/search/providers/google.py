import logging
from typing import List
import httpx

from app.core.config import settings
from app.verification.search.base import SearchProvider
from app.verification.search.models import NormalizedSearchResult
from app.verification.search.normalizer import validate_and_normalize_result

logger = logging.getLogger(__name__)


class GoogleCustomSearchProvider(SearchProvider):
    """
    Google Custom Search JSON API provider.
    Requires SEARCH_API_KEY and SEARCH_ENGINE_ID (cx).
    """

    def __init__(self, api_key: str = "", engine_id: str = ""):
        self.api_key = api_key or settings.SEARCH_API_KEY
        self.engine_id = engine_id or settings.SEARCH_ENGINE_ID
        self.timeout = settings.SEARCH_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "google"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.engine_id)

    def search(self, query: str, max_results: int = 5) -> List[NormalizedSearchResult]:
        if not self.is_configured():
            raise ValueError("Google Custom Search requires SEARCH_API_KEY and SEARCH_ENGINE_ID.")

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.api_key,
            "cx": self.engine_id,
            "q": query,
            "num": min(max_results, 10)
        }

        results: List[NormalizedSearchResult] = []
        try:
            logger.info(f"Executing Google Custom Search: '{query}'")
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, params=params)
                res.raise_for_status()
                data = res.json()

            for item in data.get("items", []):
                title = item.get("title", "")
                res_url = item.get("link", "")
                snippet = item.get("snippet", "")

                norm = validate_and_normalize_result(
                    title=title,
                    url=res_url,
                    snippet=snippet,
                    query=query,
                    provider=self.provider_name
                )
                if norm:
                    results.append(NormalizedSearchResult(**norm))
        except Exception as exc:
            logger.warning(f"Google search error for query '{query}': {exc}")
            raise

        return results
