from typing import List, Optional
from app.verification.search.base import SearchProvider
from app.verification.search.models import NormalizedSearchResult, SourceType


class MockSearchProvider(SearchProvider):
    """
    MockSearchProvider strictly for automated unit tests.
    Never exposed in production. Allows tests to run deterministically.
    """

    def __init__(
        self,
        mock_results: Optional[List[NormalizedSearchResult]] = None,
        should_fail: bool = False,
        error_to_raise: Optional[Exception] = None
    ):
        self.mock_results = mock_results if mock_results is not None else []
        self.should_fail = should_fail
        self.error_to_raise = error_to_raise or RuntimeError("Mock search provider simulated failure")
        self.executed_queries: List[str] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    def is_configured(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 5) -> List[NormalizedSearchResult]:
        self.executed_queries.append(query)
        if self.should_fail:
            raise self.error_to_raise
        return self.mock_results[:max_results]
