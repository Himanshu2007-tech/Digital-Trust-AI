import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.verification_request import VerificationRequest
from app.models.verification_result import VerificationResult
from app.models.claim import Claim
from app.models.source import Source
from app.models.evidence import Evidence
from app.models.source_comparison import SourceComparison
from app.models.report import Report
from app.verification.history.service import compute_content_hash


@pytest.fixture
def analytics_test_data(db_session: Session):
    """Seed comprehensive test data for analytics testing."""
    now = datetime.now(timezone.utc)

    # 1. Verification Request: Text, completed, TRUE
    req_text = VerificationRequest(
        request_type="text",
        content="NASA confirms water ice deposits inside shadowed lunar craters.",
        content_hash=compute_content_hash(f"NASA confirms water ice deposits {uuid.uuid4().hex}"),
        status="completed",
        is_archived=False,
        created_at=now - timedelta(days=2),
    )
    db_session.add(req_text)
    db_session.flush()

    res_text = VerificationResult(
        request_id=req_text.id,
        claim_id=None,  # Request-level verdict
        verdict="TRUE",
        overall_verdict="TRUE",
        confidence=0.92,
        confidence_score=0.92,
        explanation="Confirmed by multiple peer-reviewed observations.",
        created_at=now - timedelta(days=2),
    )
    db_session.add(res_text)

    # Claim for req_text
    claim1 = Claim(
        request_id=req_text.id,
        claim_text="NASA found water ice on the moon.",
        confidence_score=0.94,
        created_at=now - timedelta(days=2),
    )
    db_session.add(claim1)
    db_session.flush()

    res_claim1 = VerificationResult(
        request_id=req_text.id,
        claim_id=claim1.id,  # Claim-level verdict
        verdict="TRUE",
        overall_verdict="TRUE",
        confidence=0.94,
        confidence_score=0.94,
        explanation="Direct NASA mission data.",
        created_at=now - timedelta(days=2),
    )
    db_session.add(res_claim1)

    # Source 1 (NASA) - Primary
    source_nasa = Source(
        name="NASA",
        url="https://nasa.gov/missions/artemis/water-ice",
        domain="nasa.gov",
        title="Lunar Water Ice Confirmation",
        source_type="PRIMARY",
        created_at=now - timedelta(days=2),
    )
    db_session.add(source_nasa)
    db_session.flush()

    claim1.sources.append(source_nasa)

    # Evidence for claim1
    ev1 = Evidence(
        claim_id=claim1.id,
        source_id=source_nasa.id,
        evidence_type="SUPPORTING",
        direction="SUPPORTING",
        evidence_text="Spectrometer readings verify water molecules.",
        snippet="Spectrometer readings verify water molecules.",
        url="https://nasa.gov/missions/artemis/water-ice",
        relevance_score=0.95,
        stance_confidence=0.98,
        created_at=now - timedelta(days=2),
    )
    db_session.add(ev1)

    # 2. Verification Request: URL, completed, FALSE
    req_url = VerificationRequest(
        request_type="url",
        content="https://fake-news-weekly.com/aliens-in-antarctica",
        content_hash=compute_content_hash(f"https://fake-news-weekly.com/aliens-in-antarctica {uuid.uuid4().hex}"),
        status="completed",
        is_archived=False,
        created_at=now - timedelta(days=1),
    )
    db_session.add(req_url)
    db_session.flush()

    res_url = VerificationResult(
        request_id=req_url.id,
        claim_id=None,
        verdict="FALSE",
        overall_verdict="FALSE",
        confidence=0.88,
        confidence_score=0.88,
        explanation="Fabricated tabloid article with zero corroboration.",
        created_at=now - timedelta(days=1),
    )
    db_session.add(res_url)

    claim2 = Claim(
        request_id=req_url.id,
        claim_text="Alien pyramid discovered in Antarctica.",
        confidence_score=0.88,
        created_at=now - timedelta(days=1),
    )
    db_session.add(claim2)
    db_session.flush()

    res_claim2 = VerificationResult(
        request_id=req_url.id,
        claim_id=claim2.id,
        verdict="FALSE",
        overall_verdict="FALSE",
        confidence=0.88,
        confidence_score=0.88,
        explanation="Disproven satellite imagery analysis.",
        created_at=now - timedelta(days=1),
    )
    db_session.add(res_claim2)

    # Source 2 (Reuters) - Secondary / fact check
    source_reuters = Source(
        name="Reuters",
        url="https://reuters.com/fact-check/antarctica-pyramid-debunked",
        domain="reuters.com",
        title="Fact Check: Antarctica Pyramids",
        source_type="SECONDARY",
        created_at=now - timedelta(days=1),
    )
    db_session.add(source_reuters)
    db_session.flush()

    claim2.sources.append(source_reuters)

    ev2 = Evidence(
        claim_id=claim2.id,
        source_id=source_reuters.id,
        evidence_type="CONTRADICTING",
        direction="CONTRADICTING",
        evidence_text="Geologists confirm natural mountain peak formations.",
        snippet="Geologists confirm natural mountain peak formations.",
        url="https://reuters.com/fact-check/antarctica-pyramid-debunked",
        relevance_score=0.92,
        stance_confidence=0.95,
        created_at=now - timedelta(days=1),
    )
    db_session.add(ev2)

    # Source comparison
    comparison = SourceComparison(
        claim_id=claim2.id,
        source_a_id=source_nasa.id,
        source_b_id=source_reuters.id,
        source_relationship="INDEPENDENT",
        evidence_consistency="CONSISTENT_EVIDENCE",
        created_at=now - timedelta(days=1),
    )
    db_session.add(comparison)

    # 3. Verification Request: Image, failed
    req_image = VerificationRequest(
        request_type="image",
        content="=1+1; Fake image metadata with formula injection test",
        content_hash=compute_content_hash(f"formula_injection_image_test_{uuid.uuid4().hex}"),
        status="failed",
        error_message="Corrupt JPEG header encountered.",
        is_archived=False,
        created_at=now,
    )
    db_session.add(req_image)
    db_session.flush()

    # 4. Report for req_text
    rep = Report(
        report_uuid=f"rep-{uuid.uuid4().hex}",
        request_id=req_text.id,
        title="Lunar Water Ice Fact Sheet",
        format="pdf",
        status="completed",
        file_path="reports/nasa_moon_report.pdf",
        created_at=now - timedelta(days=1),
    )
    db_session.add(rep)

    db_session.commit()

    return {
        "req_text": req_text,
        "req_url": req_url,
        "req_image": req_image,
        "source_nasa": source_nasa,
        "source_reuters": source_reuters,
    }


def test_analytics_overview(client: TestClient, analytics_test_data):
    """Test GET /api/analytics/overview metrics and calculations."""
    resp = client.get("/api/analytics/overview?date_range=all")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_requests"] >= 3
    assert data["completed_count"] >= 2
    assert data["failed_count"] >= 1
    assert data["completion_rate"] is not None
    assert 0.0 <= data["completion_rate"] <= 100.0

    assert data["average_confidence"] is not None
    assert 0.0 <= data["average_confidence"] <= 1.0

    assert data["total_claims"] >= 2
    assert data["reports_generated"] >= 1

    # Check recent activity structure
    assert "recent_activity" in data
    assert isinstance(data["recent_activity"], list)
    if data["recent_activity"]:
        act = data["recent_activity"][0]
        assert "id" in act
        assert "request_type" in act
        assert "status" in act
        assert "created_at" in act


def test_analytics_date_range_validation(client: TestClient):
    """Test parameter validation for date ranges."""
    # Valid ranges
    for r in ["7d", "30d", "90d", "all"]:
        res = client.get(f"/api/analytics/overview?date_range={r}")
        assert res.status_code == 200

    # Invalid preset
    res = client.get("/api/analytics/overview?date_range=1year")
    assert res.status_code == 400
    assert "Invalid date_range" in res.json()["detail"]

    # Invalid custom date format
    res = client.get("/api/analytics/overview?date_range=custom&start_date=invalid-date")
    assert res.status_code in (400, 422)

    # Start date after end date
    res = client.get("/api/analytics/overview?date_range=custom&start_date=2026-10-15T00:00:00Z&end_date=2026-10-10T00:00:00Z")
    assert res.status_code == 400
    assert "start_date cannot be after end_date" in res.json()["detail"]


def test_analytics_timeline(client: TestClient, analytics_test_data):
    """Test GET /api/analytics/timeline with contiguous buckets."""
    resp = client.get("/api/analytics/timeline?date_range=7d&interval=day")
    assert resp.status_code == 200
    data = resp.json()

    assert "data_points" in data
    assert data["interval"] == "day"
    assert len(data["data_points"]) in (7, 8)  # 7-8 inclusive days

    for point in data["data_points"]:
        assert "date" in point
        assert "total" in point
        assert "completed" in point
        assert "failed" in point
        assert "text" in point
        assert "url" in point
        assert "image" in point
        assert "audio" in point
        assert "video" in point


def test_analytics_verification_types(client: TestClient, analytics_test_data):
    """Test GET /api/analytics/verification-types modality breakdowns."""
    resp = client.get("/api/analytics/verification-types?date_range=all")
    assert resp.status_code == 200
    data = resp.json()

    assert "breakdown" in data
    assert data["total_requests"] >= 3

    breakdown_types = {item["type"]: item for item in data["breakdown"]}
    assert "text" in breakdown_types
    assert "url" in breakdown_types
    assert "image" in breakdown_types

    assert breakdown_types["text"]["count"] >= 1
    assert breakdown_types["url"]["count"] >= 1
    assert breakdown_types["image"]["count"] >= 1


def test_analytics_verdict_distribution(client: TestClient, analytics_test_data):
    """Test segregated request-level vs claim-level verdict breakdowns."""
    resp = client.get("/api/analytics/verdict-distribution?date_range=all")
    assert resp.status_code == 200
    data = resp.json()

    assert "request_verdicts" in data
    assert "claim_verdicts" in data
    assert "methodological_note" in data
    assert "corpus" in data["methodological_note"].lower() or "query" in data["methodological_note"].lower()

    assert data["total_evaluated_requests"] >= 2
    verdict_names = {v["verdict"] for v in data["request_verdicts"]}
    assert "TRUE" in verdict_names
    assert "FALSE" in verdict_names

    assert data["total_evaluated_claims"] >= 2
    claim_verdict_names = {v["verdict"] for v in data["claim_verdicts"]}
    assert "TRUE" in claim_verdict_names
    assert "FALSE" in claim_verdict_names


def test_analytics_source_coverage(client: TestClient, analytics_test_data):
    """Test GET /api/analytics/source-coverage metrics."""
    resp = client.get("/api/analytics/source-coverage?date_range=all")
    assert resp.status_code == 200
    data = resp.json()

    assert data["unique_sources_count"] >= 2
    assert data["unique_domains_count"] >= 2
    assert data["primary_source_percentage"] is not None

    assert "top_domains" in data
    top_domain_names = [d["domain"] for d in data["top_domains"]]
    assert "nasa.gov" in top_domain_names or "reuters.com" in top_domain_names

    assert "evidence_direction_distribution" in data
    assert "SUPPORTING" in data["evidence_direction_distribution"]
    assert "CONTRADICTING" in data["evidence_direction_distribution"]
    assert data["evidence_direction_distribution"]["SUPPORTING"] >= 1
    assert data["evidence_direction_distribution"]["CONTRADICTING"] >= 1


def test_analytics_csv_export_and_sanitization(client: TestClient, analytics_test_data):
    """Test CSV export and formula injection sanitization."""
    resp = client.get("/api/analytics/export/csv?date_range=all")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "truthlens_analytics_export" in resp.headers["content-disposition"]

    csv_content = resp.text
    assert "Investigation ID,Modality,Status" in csv_content

    # Verify formula injection sanitization:
    # req_image had content starting with "=1+1"
    # It must be prepended with a single quote "'"
    assert "'=1+1;" in csv_content


def test_history_export_and_source_domain_filtering(client: TestClient, analytics_test_data):
    """Test GET /api/history/export and source_domain filter."""
    # 1. History CSV export
    resp = client.get("/api/history/export?date_range=all")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "truthlens_history_export" in resp.headers["content-disposition"]
    assert "'=1+1;" in resp.text

    # 2. History filter by source_domain
    resp_reuters = client.get("/api/history?source_domain=reuters.com")
    assert resp_reuters.status_code == 200
    data_reuters = resp_reuters.json()
    assert data_reuters["total_count"] >= 1
    # Check that returned request has URL type
    assert any(item["request_type"] == "url" for item in data_reuters["items"])

    # Filter with nonexistent domain
    resp_none = client.get("/api/history?source_domain=nonexistent-news-domain-xyz.org")
    assert resp_none.status_code == 200
    data_none = resp_none.json()
    assert data_none["total_count"] == 0
