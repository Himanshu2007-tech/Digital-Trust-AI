import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.session import SessionLocal
from app.models.verification_request import VerificationRequest
from app.models.article import Article
from app.models.source import Source
from app.core.exceptions import SecurityRiskException
from app.utils.security_helpers import validate_url_for_ssrf
from app.verification.article.base import ExtractedArticle
from app.verification.article.fetcher import SafeArticleFetcher
from app.verification.article.extractor import ReadabilityArticleExtractor
from app.verification.article.service import ArticleVerificationService


SAMPLE_VALID_ARTICLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>RBI Raises Repo Rate by 25 Basis Points to 6.75 Percent | Reuters</title>
    <meta property="og:title" content="RBI Raises Repo Rate by 25 Basis Points to 6.75 Percent" />
    <meta property="og:site_name" content="Reuters" />
    <meta name="author" content="Jane Doe" />
    <meta property="article:published_time" content="2026-06-15T09:30:00Z" />
    <meta property="og:description" content="The Reserve Bank of India raised its key repo rate to curb persistent core inflation." />
    <link rel="canonical" href="https://www.reuters.com/markets/asia/rbi-raises-repo-rate-2026-06-15/" />
</head>
<body>
    <header><nav><a href="/">Home</a><a href="/news">News</a></nav></header>
    <article>
        <h1>RBI Raises Repo Rate by 25 Basis Points to 6.75 Percent</h1>
        <div class="byline">By Jane Doe</div>
        <p class="ad">Buy our sponsored subscription now!</p>
        <p>The Reserve Bank of India increased the benchmark repo rate by 25 basis points to 6.75 percent on Monday to contain ongoing inflationary pressures across consumer goods and commodities.</p>
        <p>Governor Shaktikanta Das announced that the monetary policy committee voted unanimously in favor of the rate hike following elevated headline numbers over the previous two quarters.</p>
        <p>The central bank also reiterated its commitment to bring consumer price inflation back to the sustainable 4 percent target while maintaining support for economic growth momentum.</p>
        <p>Financial analysts had largely anticipated the monetary policy adjustment given persistent geopolitical uncertainties and volatile food supply chains throughout the region.</p>
    </article>
    <footer>Copyright 2026 Reuters. All rights reserved.</footer>
</body>
</html>
"""


def test_ssrf_validation_blocks_private_networks():
    with pytest.raises(SecurityRiskException):
        validate_url_for_ssrf("http://127.0.0.1:8000/secret")

    with pytest.raises(SecurityRiskException):
        validate_url_for_ssrf("http://localhost:3000/api")

    with pytest.raises(SecurityRiskException):
        validate_url_for_ssrf("http://169.254.169.254/latest/meta-data/")

    with pytest.raises(SecurityRiskException):
        validate_url_for_ssrf("http://10.0.0.1/admin")

    with pytest.raises(SecurityRiskException):
        validate_url_for_ssrf("http://192.168.1.1/router")

    with pytest.raises(SecurityRiskException):
        validate_url_for_ssrf("file:///etc/passwd")

    with pytest.raises(SecurityRiskException):
        validate_url_for_ssrf("ftp://example.com/test")


def test_article_extractor_success():
    extractor = ReadabilityArticleExtractor()
    extracted = extractor.extract_article(
        SAMPLE_VALID_ARTICLE_HTML,
        "https://www.reuters.com/markets/asia/rbi-raises-repo-rate-2026-06-15/"
    )

    assert extracted.domain == "reuters.com"
    assert "RBI Raises Repo Rate" in (extracted.title or "")
    assert extracted.author == "Jane Doe"
    assert extracted.publisher == "Reuters"
    assert extracted.canonical_url == "https://www.reuters.com/markets/asia/rbi-raises-repo-rate-2026-06-15/"
    assert extracted.word_count >= 50
    assert "increased the benchmark repo rate" in extracted.article_text
    # Boilerplate / ads should be stripped
    assert "Buy our sponsored subscription now" not in extracted.article_text
    assert extracted.content_hash is not None
    assert len(extracted.content_hash) == 64


def test_article_extractor_detects_paywall():
    extractor = ReadabilityArticleExtractor()
    paywall_html = """
    <html><head><title>Paywalled News</title></head>
    <body>
        <article>
            <p>Breaking story about technology developments.</p>
            <p>Subscribe to continue reading this exclusive report.</p>
        </article>
    </body></html>
    """
    with pytest.raises(ValueError, match="paywall"):
        extractor.extract_article(paywall_html, "https://example.com/story")


def test_article_extractor_detects_insufficient_content():
    extractor = ReadabilityArticleExtractor()
    short_html = """
    <html><head><title>Short page</title></head>
    <body><p>Hello world.</p></body></html>
    """
    with pytest.raises(ValueError, match="Insufficient article text"):
        extractor.extract_article(short_html, "https://example.com/short")


def test_safe_fetcher_rejects_pdf_url():
    fetcher = SafeArticleFetcher()
    with patch("app.verification.article.fetcher.validate_url_for_ssrf", return_value="https://example.com/doc.pdf"):
        with pytest.raises(ValueError, match="PDF verification is not supported"):
            fetcher.fetch("https://example.com/doc.pdf")


from app.verification.search.models import NormalizedSearchResult, SourceType, SearchQueryAudit
from app.verification.search.discovery_service import SourceDiscoveryService


def test_article_verification_service_full_pipeline():
    db = SessionLocal()
    try:
        service = ArticleVerificationService()

        # Mock fetcher to return our valid sample HTML
        service.fetcher.fetch = MagicMock(return_value=(
            SAMPLE_VALID_ARTICLE_HTML,
            "https://www.reuters.com/markets/asia/rbi-raises-repo-rate-2026-06-15/",
            200
        ))

        # Mock search discovery to return fast mock results without network calls
        mock_audit = SearchQueryAudit(
            query_text="RBI repo rate 6.75 percent",
            strategy_level="LEVEL_1",
            search_engine="mock",
            results_count=1,
            status="success"
        )
        mock_result = NormalizedSearchResult(
            title="Reserve Bank of India Monetary Policy Statement",
            url="https://rbi.org.in/press/monetary-policy-2026.html",
            canonical_url="https://rbi.org.in/press/monetary-policy-2026.html",
            domain="rbi.org.in",
            snippet="The Monetary Policy Committee decided to increase the policy repo rate by 25 basis points to 6.75 percent.",
            published_at="2026-06-15",
            publisher="Reserve Bank of India",
            source_type=SourceType.PRIMARY,
            query="RBI repo rate 6.75 percent",
            provider="mock"
        )
        service.discovery_service.discover_sources_for_claim = MagicMock(
            return_value=([mock_audit], [mock_result])
        )

        result = service.verify_url(
            url="https://www.reuters.com/markets/asia/rbi-raises-repo-rate-2026-06-15/",
            db=db,
            perform_search=True,
            extract_evidence=True,
            finalize_verdicts=True,
            max_claims=3
        )

        assert result["status"] == "completed"
        assert result["request_id"] is not None
        assert result["article"]["domain"] == "reuters.com"
        assert result["article"]["word_count"] > 40
        assert result["claims_count"] >= 1

        # Check submitted source is tagged correctly
        assert result["submitted_source"] is not None
        assert result["submitted_source"]["source_role"] == "USER_SUBMITTED_ARTICLE"

        # Check Article record in DB
        db_article = db.query(Article).filter(Article.request_id == result["request_id"]).first()
        assert db_article is not None
        assert db_article.domain == "reuters.com"
        assert db_article.content_hash == result["article"]["content_hash"]

        # Check Source record in DB
        db_src = db.query(Source).filter(Source.url == "https://www.reuters.com/markets/asia/rbi-raises-repo-rate-2026-06-15/").first()
        assert db_src is not None
        assert db_src.source_role == "USER_SUBMITTED_ARTICLE"

        # Check verdict structure exists
        assert result["verdict"] is not None
        assert "overall_verdict" in result["verdict"]
        assert "overall_confidence" in result["verdict"]

    finally:
        db.close()


def test_api_verify_url_endpoint(client: TestClient):
    # Test SSRF rejection via API
    resp = client.post("/api/verify/url", json={"url": "http://127.0.0.1:8000/health"})
    assert resp.status_code == 400
    assert "Security rejection" in resp.json()["detail"]

    # Test successful verification with mocked article fetcher and search
    mock_audit = SearchQueryAudit(
        query_text="RBI repo rate monetary policy",
        strategy_level="LEVEL_1",
        search_engine="mock",
        results_count=1,
        status="success"
    )
    mock_result = NormalizedSearchResult(
        title="Official RBI Monetary Statement",
        url="https://rbi.org.in/news/policy.html",
        canonical_url="https://rbi.org.in/news/policy.html",
        domain="rbi.org.in",
        snippet="Repo rate increased by 25 bps to 6.75 percent.",
        published_at="2026-06-15",
        publisher="RBI",
        source_type=SourceType.PRIMARY,
        query="RBI repo rate monetary policy",
        provider="mock"
    )

    with patch.object(
        SafeArticleFetcher,
        "fetch",
        return_value=(
            SAMPLE_VALID_ARTICLE_HTML,
            "https://www.thehindu.com/business/Economy/rbi-repo-rate-decision/article12345.ece",
            200
        )
    ), patch.object(
        SourceDiscoveryService,
        "discover_sources_for_claim",
        return_value=([mock_audit], [mock_result])
    ):
        resp = client.post(
            "/api/verify/url",
            json={
                "url": "https://www.thehindu.com/business/Economy/rbi-repo-rate-decision/article12345.ece",
                "perform_search": True,
                "extract_evidence": True,
                "finalize_verdicts": True
            }
        )
        if resp.status_code != 200:
            print("ERROR DETAIL:", resp.json())
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["article"]["original_url"] == "https://www.thehindu.com/business/Economy/rbi-repo-rate-decision/article12345.ece"
        assert data["article"]["domain"] == "thehindu.com"
        assert data["submitted_source"]["source_role"] == "USER_SUBMITTED_ARTICLE"
        assert len(data["claims"]) >= 1
        assert data["verdict"] is not None
