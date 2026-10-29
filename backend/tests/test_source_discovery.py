import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import ConfigurationException
from app.database.session import SessionLocal
from app.models.claim import Claim
from app.models.source import Source
from app.models.search_query import SearchQuery
from app.models.verification_request import VerificationRequest
from app.verification.search.base import SearchProvider
from app.verification.search.models import SourceType, NormalizedSearchResult, SearchQueryAudit
from app.verification.search.normalizer import (
    normalize_url,
    extract_domain,
    classify_source,
    detect_syndication,
    validate_and_normalize_result
)
from app.verification.search.query_generator import SearchQueryGenerator
from app.verification.search.providers.mock import MockSearchProvider
from app.verification.search.providers.factory import get_search_provider
from app.verification.search.discovery_service import SourceDiscoveryService


# ==========================================
# 1. URL Normalization & Validation Tests
# ==========================================

def test_url_normalization_strips_tracking_params():
    raw_url = "https://www.reuters.com/business/finance/rbi-rate-decision?utm_source=twitter&utm_medium=social&fbclid=12345#overview"
    normalized = normalize_url(raw_url)
    assert "utm_source" not in normalized
    assert "fbclid" not in normalized
    assert normalized == "https://www.reuters.com/business/finance/rbi-rate-decision"


def test_url_normalization_enforces_scheme_and_ports():
    raw_url = "http://example.com:80/news/article/"
    normalized = normalize_url(raw_url)
    assert normalized == "http://example.com/news/article"

    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        normalize_url("file:///etc/passwd")

    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        normalize_url("javascript:alert(1)")


def test_invalid_url_and_ssrf_rejection():
    # Loopback IP
    res = validate_and_normalize_result(
        title="Localhost Admin",
        url="http://127.0.0.1:8000/secret",
        snippet="Private content",
        query="test",
        provider="mock"
    )
    assert res is None

    # Link-local cloud metadata
    res_meta = validate_and_normalize_result(
        title="AWS Metadata",
        url="http://169.254.169.254/latest/meta-data/",
        snippet="Metadata",
        query="test",
        provider="mock"
    )
    assert res_meta is None


# ==========================================
# 2. Source Classification & Syndication Tests
# ==========================================

def test_source_classification():
    # Official / Primary
    st, pub, country = classify_source("rbi.org.in")
    assert st == SourceType.PRIMARY
    assert country == "India"
    assert pub == "Reserve Bank of India"

    # Fact checker
    st, pub, _ = classify_source("altnews.in")
    assert st == SourceType.FACT_CHECK

    # Reliable news
    st, pub, _ = classify_source("reuters.com")
    assert st == SourceType.RELIABLE_NEWS
    assert pub == "Reuters"

    # Social media
    st, _, _ = classify_source("twitter.com")
    assert st == SourceType.SOCIAL_MEDIA

    # Blog
    st, _, _ = classify_source("substack.com")
    assert st == SourceType.BLOG


def test_syndication_detection():
    title = "Market rallies after rate hike"
    snippet = "The central bank maintained liquidity, Reuters reported on Monday."
    agency = detect_syndication(title, snippet)
    assert agency == "Reuters Wire"

    no_agency = detect_syndication("Exclusive interview with minister", "Our correspondent reports.")
    assert no_agency is None


# ==========================================
# 3. Query Generation & Deduplication Tests
# ==========================================

def test_search_query_generation_levels():
    generator = SearchQueryGenerator()
    queries = generator.generate_queries(
        claim_text="RBI increased the repo rate to 7% in June 2026.",
        entities=["RBI", "Reserve Bank of India"],
        dates=["June 2026"],
        numbers=["7%"],
        max_queries=3
    )

    assert len(queries) >= 2
    query_texts = [q.query_text for q in queries]
    strategies = [q.strategy_level for q in queries]

    # Must contain Level 1 exact/core and Level 2 or Level 3
    assert "LEVEL_1_EXACT" in strategies
    assert any("7%" in qt or "repo rate" in qt.lower() for qt in query_texts)
    assert any("RBI" in qt for qt in query_texts)


def test_search_query_deduplication():
    generator = SearchQueryGenerator()
    # Identical repetitive input should not generate duplicate queries
    queries = generator.generate_queries(
        claim_text="RBI repo rate 7% RBI repo rate 7%",
        entities=["RBI"],
        numbers=["7%"],
        max_queries=4
    )
    texts = [q.query_text.lower() for q in queries]
    assert len(texts) == len(set(texts))


# ==========================================
# 4. Search Provider & Factory Tests
# ==========================================

def test_search_provider_interface():
    mock_provider = MockSearchProvider()
    assert isinstance(mock_provider, SearchProvider)
    assert mock_provider.provider_name == "mock"
    assert mock_provider.is_configured() is True


def test_factory_missing_or_unknown_provider():
    with pytest.raises(ConfigurationException, match="Unknown search provider"):
        get_search_provider("invalid_search_engine_name")

    with pytest.raises(ConfigurationException, match="No web search provider configured"):
        get_search_provider("none")


# ==========================================
# 5. Discovery Service & Database Persistence
# ==========================================

def test_discovery_service_with_mock_provider():
    db = SessionLocal()
    try:
        # Create a test VerificationRequest & Claim
        vr = VerificationRequest(request_type="text", content="Test verification for source discovery", status="extracted")
        db.add(vr)
        db.flush()

        claim = Claim(
            request_id=vr.id,
            claim_text="ISRO launched 3 satellites in August 2025.",
            normalized_text="ISRO launched 3 satellites in August 2025.",
            entities=["ISRO"],
            dates=["August 2025"],
            numbers=["3"],
            claim_type="FACTUAL",
            verifiability="VERIFIABLE",
            importance="HIGH",
            original_sentence="ISRO launched 3 satellites in August 2025."
        )
        db.add(claim)
        db.commit()

        # Mock results
        mock_results = [
            NormalizedSearchResult(
                title="ISRO Satellite Launch Press Release",
                url="https://www.isro.gov.in/press-release-satellites-2025",
                canonical_url="https://isro.gov.in/press-release-satellites-2025",
                domain="isro.gov.in",
                snippet="Official statement regarding satellite launch into geostationary orbit.",
                published_at="2025-08-15",
                publisher="Indian Space Research Organisation (ISRO)",
                source_type=SourceType.PRIMARY,
                query="ISRO satellites August 2025",
                retrieved_at="2026-09-16T08:00:00",
                provider="mock"
            ),
            NormalizedSearchResult(
                title="India launches satellites, Reuters reports",
                url="https://www.reuters.com/technology/space/isro-launch-2025",
                canonical_url="https://reuters.com/technology/space/isro-launch-2025",
                domain="reuters.com",
                snippet="Three satellites successfully deployed by Indian space agency.",
                published_at="2025-08-15",
                publisher="Reuters",
                source_type=SourceType.RELIABLE_NEWS,
                query="ISRO satellites August 2025",
                retrieved_at="2026-09-16T08:00:00",
                provider="mock"
            )
        ]

        mock_provider = MockSearchProvider(mock_results=mock_results)
        service = SourceDiscoveryService(provider=mock_provider)

        audits, sources = service.discover_sources_for_claim(claim_id=claim.id, db=db, max_queries=2, max_results_per_query=2)

        assert len(audits) >= 1
        assert len(sources) == 2
        assert audits[0].status == "success"

        # Verify database persistence in SearchQuery and Source tables
        sq_records = db.query(SearchQuery).filter_by(claim_id=claim.id).all()
        assert len(sq_records) >= 1
        assert sq_records[0].results_count == 2
        assert sq_records[0].status == "success"

        # Verify Source records and relationship
        claim_refreshed = db.query(Claim).filter_by(id=claim.id).first()
        assert len(claim_refreshed.sources) == 2
        domains = [s.domain for s in claim_refreshed.sources]
        assert "isro.gov.in" in domains
        assert "reuters.com" in domains
        # Assert no fake credibility score was assigned
        for s in claim_refreshed.sources:
            assert s.credibility_score is None

    finally:
        db.close()


def test_discovery_service_empty_results():
    db = SessionLocal()
    try:
        vr = VerificationRequest(request_type="text", content="Test empty search", status="extracted")
        db.add(vr)
        db.flush()

        claim = Claim(
            request_id=vr.id,
            claim_text="Obscure fictional statement with no web trace.",
            normalized_text="Obscure fictional statement with no web trace.",
            claim_type="FACTUAL",
            verifiability="VERIFIABLE",
            importance="LOW",
            original_sentence="Obscure fictional statement with no web trace."
        )
        db.add(claim)
        db.commit()

        mock_provider = MockSearchProvider(mock_results=[])
        service = SourceDiscoveryService(provider=mock_provider)

        audits, sources = service.discover_sources_for_claim(claim_id=claim.id, db=db, max_queries=1)
        assert len(sources) == 0
        assert len(audits) == 1
        assert audits[0].status == "empty"
        assert audits[0].results_count == 0

        # Verify no sources were fabricated
        claim_refreshed = db.query(Claim).filter_by(id=claim.id).first()
        assert len(claim_refreshed.sources) == 0

    finally:
        db.close()


def test_discovery_service_provider_failure():
    db = SessionLocal()
    try:
        vr = VerificationRequest(request_type="text", content="Test failure handling", status="extracted")
        db.add(vr)
        db.flush()

        claim = Claim(
            request_id=vr.id,
            claim_text="Policy update announced yesterday.",
            normalized_text="Policy update announced yesterday.",
            claim_type="POLICY",
            verifiability="VERIFIABLE",
            importance="MEDIUM",
            original_sentence="Policy update announced yesterday."
        )
        db.add(claim)
        db.commit()

        mock_provider = MockSearchProvider(should_fail=True)
        service = SourceDiscoveryService(provider=mock_provider)

        audits, sources = service.discover_sources_for_claim(claim_id=claim.id, db=db, max_queries=1)
        assert len(sources) == 0
        assert len(audits) == 1
        assert audits[0].status == "failed"
        assert audits[0].error_message is not None

        # Verify query logged error in DB
        sq_record = db.query(SearchQuery).filter_by(claim_id=claim.id).first()
        assert sq_record.status == "failed"
        assert "simulated failure" in sq_record.error_message

    finally:
        db.close()


# ==========================================
# 6. API Endpoints Tests
# ==========================================

def test_api_search_claim_endpoint(client: TestClient):
    payload = {
        "claim_text": "RBI announced monetary policy meeting in Mumbai.",
        "max_queries": 2,
        "max_results_per_query": 3
    }
    response = client.post("/api/search/claim", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "queries" in data
    assert "sources" in data
    assert "provider" in data
    assert data["queries_count"] >= 1
    # Verify no verdict or confidence score is included
    assert "verdict" not in data
    assert "confidence_score" not in data


def test_api_search_audit_endpoint(client: TestClient):
    db = SessionLocal()
    try:
        vr = VerificationRequest(request_type="text", content="Audit test", status="extracted")
        db.add(vr)
        db.flush()

        claim = Claim(
            request_id=vr.id,
            claim_text="Finance Ministry announced subsidy.",
            normalized_text="Finance Ministry announced subsidy.",
            claim_type="POLICY",
            verifiability="VERIFIABLE",
            importance="MEDIUM",
            original_sentence="Finance Ministry announced subsidy."
        )
        db.add(claim)
        db.flush()

        sq = SearchQuery(
            claim_id=claim.id,
            query_text="Finance Ministry subsidy",
            search_engine="duckduckgo",
            results_count=4,
            status="success"
        )
        db.add(sq)
        db.commit()

        claim_id = claim.id
    finally:
        db.close()

    response = client.get(f"/api/search/audit/{claim_id}")
    assert response.status_code == 200
    audits = response.json()
    assert len(audits) >= 1
    assert audits[0]["query_text"] == "Finance Ministry subsidy"
    assert audits[0]["results_count"] == 4
    assert audits[0]["status"] == "success"
