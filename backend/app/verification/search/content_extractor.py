import logging
from abc import ABC, abstractmethod
from typing import Optional
import httpx

from app.utils.security_helpers import validate_url_for_ssrf

logger = logging.getLogger(__name__)


class ArticleContentExtractor(ABC):
    """
    Abstract interface for full-text article/webpage content extraction.
    Prepared for future evidence analysis (Part 5) without blocking Part 4.
    """

    @abstractmethod
    def extract_content(self, url: str) -> Optional[str]:
        """
        Attempts to safely retrieve readable text from a verified URL.
        Returns extracted text or None if blocked, rate-limited, or failed.
        """
        pass


class WebPageContentExtractor(ArticleContentExtractor):
    """
    Lightweight, respectful article content extractor.
    Enforces SSRF checks, short timeout, and graceful failure handling.
    """

    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "TruthLensAI/1.0 (Research Fact-Checking Bot; +https://truthlens.ai/bot)"
        }

    def extract_content(self, url: str) -> Optional[str]:
        try:
            # 1. SSRF and scheme validation
            validate_url_for_ssrf(url)

            # 2. Bounded fetch
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                res = client.get(url, headers=self.headers)
                if res.status_code != 200:
                    return None

                # Return text prefix up to 5,000 characters
                raw_text = res.text
                # Basic tag stripping fallback
                import re
                clean = re.sub(r"<[^>]+>", " ", raw_text)
                clean = re.sub(r"\s+", " ", clean).strip()
                return clean[:5000] if clean else None
        except Exception as exc:
            logger.debug(f"Article retrieval skipped for {url}: {exc}")
            return None
