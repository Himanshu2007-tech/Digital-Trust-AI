"""
TruthLens AI - News URL & Article Verification Engine (Part 7)
Provides:
- SSRF-safe, size-limited HTTP article fetching with per-hop redirect validation
- DOM cleaning and readability article extraction
- Integration with Part 3 (claim extraction), Part 4 (search discovery),
  Part 5 (evidence extraction & comparison), and Part 6 (final verdict)
"""

from app.verification.article.base import ExtractedArticle, ArticleExtractor
from app.verification.article.fetcher import SafeArticleFetcher
from app.verification.article.extractor import ReadabilityArticleExtractor
from app.verification.article.service import ArticleVerificationService

__all__ = [
    "ExtractedArticle",
    "ArticleExtractor",
    "SafeArticleFetcher",
    "ReadabilityArticleExtractor",
    "ArticleVerificationService",
]
