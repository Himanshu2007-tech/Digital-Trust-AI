from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ArticleSchema(BaseModel):
    """Clean article metadata and sanitized textual content."""
    id: Optional[int] = Field(default=None, description="Database record ID")
    request_id: Optional[int] = Field(default=None, description="Associated VerificationRequest ID")
    original_url: str = Field(..., description="Original requested URL")
    canonical_url: Optional[str] = Field(default=None, description="Canonical URL from HTML metadata")
    domain: str = Field(..., description="Cleaned publisher domain")
    title: Optional[str] = Field(default=None, description="Extracted article title")
    publisher: Optional[str] = Field(default=None, description="Extracted publisher / news organization")
    author: Optional[str] = Field(default=None, description="Extracted author byline")
    published_at: Optional[str] = Field(default=None, description="Extracted publication timestamp string")
    description: Optional[str] = Field(default=None, description="Extracted article description / summary")
    language: Optional[str] = Field(default="en", description="Detected language code")
    featured_image_url: Optional[str] = Field(default=None, description="Primary lead / OG image URL")
    article_text: str = Field(..., description="Clean, readable extracted body text")
    content_hash: str = Field(..., description="SHA-256 fingerprint of article text")
    content_length: int = Field(default=0, description="Character count of article text")
    word_count: int = Field(default=0, description="Word count of article text")
    extraction_method: str = Field(default="readability_bs4", description="Extractor method used")
    retrieval_status: str = Field(default="success", description="Status of retrieval")
    retrieved_at: Optional[datetime] = Field(default=None, description="Fetch timestamp")
