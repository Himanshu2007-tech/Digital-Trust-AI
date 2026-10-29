import logging
from typing import Optional

from app.core.config import settings
from app.core.exceptions import ConfigurationException
from app.verification.search.base import SearchProvider
from app.verification.search.providers.duckduckgo import DuckDuckGoSearchProvider
from app.verification.search.providers.tavily import TavilySearchProvider
from app.verification.search.providers.google import GoogleCustomSearchProvider
from app.verification.search.providers.serpapi import SerpApiSearchProvider
from app.verification.search.providers.brave import BraveSearchProvider
from app.verification.search.providers.mock import MockSearchProvider

logger = logging.getLogger(__name__)


def get_search_provider(provider_name: Optional[str] = None) -> SearchProvider:
    """
    Factory function returning the configured SearchProvider instance.
    Raises ConfigurationException if the provider is misconfigured or missing credentials.
    """
    target = (provider_name or settings.SEARCH_PROVIDER or "duckduckgo").strip().lower()

    if target in ("duckduckgo", "ddg"):
        provider = DuckDuckGoSearchProvider()
        if not provider.is_configured():
            raise ConfigurationException("DuckDuckGo search provider requires 'duckduckgo_search' dependency.")
        return provider

    elif target == "tavily":
        provider = TavilySearchProvider()
        if not provider.is_configured():
            raise ConfigurationException("Tavily search provider requires SEARCH_API_KEY to be configured in .env.")
        return provider

    elif target == "google":
        provider = GoogleCustomSearchProvider()
        if not provider.is_configured():
            raise ConfigurationException("Google search provider requires SEARCH_API_KEY and SEARCH_ENGINE_ID in .env.")
        return provider

    elif target == "serpapi":
        provider = SerpApiSearchProvider()
        if not provider.is_configured():
            raise ConfigurationException("SerpApi search provider requires SEARCH_API_KEY in .env.")
        return provider

    elif target == "brave":
        provider = BraveSearchProvider()
        if not provider.is_configured():
            raise ConfigurationException("Brave search provider requires SEARCH_API_KEY in .env.")
        return provider

    elif target == "mock":
        return MockSearchProvider()

    elif target in ("none", ""):
        raise ConfigurationException("No web search provider configured. Set SEARCH_PROVIDER in .env.")

    else:
        raise ConfigurationException(
            f"Unknown search provider: '{target}'. Supported options: duckduckgo, tavily, google, serpapi, brave."
        )
