from abc import ABC, abstractmethod
from typing import List
from app.verification.search.models import NormalizedSearchResult


class SearchProvider(ABC):
    """
    Abstract interface for web search engines.
    Decouples query execution from specific search providers (DuckDuckGo, Tavily, Google, SerpApi, Brave).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name identifier of the search provider."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Checks if required API keys, engine IDs, or dependencies are present."""
        pass

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[NormalizedSearchResult]:
        """
        Executes a real web search query and returns normalized results.

        Args:
            query (str): The search query string.
            max_results (int): Maximum number of search results to retrieve.

        Returns:
            List[NormalizedSearchResult]: List of normalized, validated search results.

        Raises:
            SearchProviderException: When search query fails, rate limits occur, or API is unreachable.
        """
        pass
