from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class ExtractedArticle(BaseModel):
    """
    Standardized extracted article representation holding sanitized
    clean text and rich journalistic provenance metadata.
    """
    original_url: str
    canonical_url: Optional[str] = None
    domain: str
    title: Optional[str] = None
    publisher: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = "en"
    featured_image_url: Optional[str] = None
    article_text: str
    content_hash: str
    content_length: int = 0
    word_count: int = 0
    extraction_method: str = "readability_bs4"
    retrieval_status: str = "success"
    retrieved_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class ArticleExtractor(ABC):
    """Abstract interface for HTML parsing and article body extraction."""

    @abstractmethod
    def extract_article(self, html: str, url: str) -> ExtractedArticle:
        """Parses HTML document into an ExtractedArticle instance."""
        pass
