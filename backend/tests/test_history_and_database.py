import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.verification_request import VerificationRequest
from app.models.verification_result import VerificationResult
from app.models.verification_event import VerificationEvent
from app.models.claim import Claim
from app.verification.history.service import compute_content_hash, record_verification_event, HistoryService


def test_compute_content_hash():
    """Verify deterministic SHA-256 computation."""
    hash1 = compute_content_hash("India lunar rover discovered water ice.")
    hash2 = compute_content_hash("India lunar rover discovered water ice.")
    hash3 = compute_content_hash("Different claim text.")

    assert hash1 == hash2
    assert len(hash1) == 64
    assert hash1 != hash3

    # Bytes hashing
    b_hash1 = compute_content_hash(b"binary data payload")
    b_hash2 = compute_content_hash(b"binary data payload")
    assert b_hash1 == b_hash2


def test_history_list_pagination(client: TestClient, db_session: Session):
    """Test GET /api/history pagination parameters and structure."""
    # Create test verification requests
    req = VerificationRequest(
        request_type="text",
        content="Test claim text for pagination verification 101",
        content_hash=compute_content_hash("Test claim text for pagination verification 101"),
        status="completed",
        is_archived=False,
    )
    db_session.add(req)
    db_session.commit()

    response = client.get("/api/history?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total_count" in data
    assert "page" in data
    assert "page_size" in data
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) <= 5
    assert data["total_count"] >= 1

    # Check HistoryItem fields
    item = data["items"][0]
    assert "id" in item
    assert "request_type" in item
    assert "status" in item
    assert "is_archived" in item
    assert "created_at" in item


def test_history_filters_endpoint(client: TestClient):
    """Test GET /api/history/filters returns valid taxonomy."""
    response = client.get("/api/history/filters")
    assert response.status_code == 200
    data = response.json()
    assert "request_types" in data
    assert "statuses" in data
    assert "verdicts" in data
    assert "text" in data["request_types"]
    assert "completed" in data["statuses"]


def test_history_filtering_by_type_and_status(client: TestClient, db_session: Session):
    """Test filtering by request_type and status."""
    content = "Unique filter text test " + str(datetime.now().timestamp())
    req = VerificationRequest(
        request_type="url",
        content=content,
        content_hash=compute_content_hash(content),
        status="completed",
        is_archived=False,
    )
    db_session.add(req)
    db_session.commit()

    response = client.get("/api/history?request_type=url&status=completed")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] >= 1
    for item in data["items"]:
        assert item["request_type"] == "url"
        assert item["status"] == "completed"


def test_history_search(client: TestClient, db_session: Session):
    """Test searching by content text or ID."""
    unique_keyword = f"UniqueKeyword{int(datetime.now().timestamp())}"
    req = VerificationRequest(
        request_type="text",
        content=f"Report containing {unique_keyword} to be discovered by search.",
        content_hash=compute_content_hash(f"Report containing {unique_keyword} to be discovered by search."),
        status="completed",
        is_archived=False,
    )
    db_session.add(req)
    db_session.commit()

    # Search by keyword
    response = client.get(f"/api/history?search={unique_keyword}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] >= 1
    assert any(unique_keyword in (item["content_preview"] or "") for item in data["items"])

    # Search by specific ID
    response_id = client.get(f"/api/history?search={req.id}")
    assert response_id.status_code == 200
    data_id = response_id.json()
    assert data_id["total_count"] >= 1
    assert any(item["id"] == req.id for item in data_id["items"])


def test_history_archive_toggle(client: TestClient, db_session: Session):
    """Test archiving and unarchiving a verification request."""
    req = VerificationRequest(
        request_type="text",
        content="Archive test verification request",
        content_hash=compute_content_hash("Archive test verification request"),
        status="completed",
        is_archived=False,
    )
    db_session.add(req)
    db_session.commit()

    # Archive it
    res_archive = client.post(f"/api/history/{req.id}/archive", json={"archive": True})
    assert res_archive.status_code == 200
    assert res_archive.json()["is_archived"] is True

    # Check that is_archived=false excludes it
    res_unarchived_list = client.get(f"/api/history?search={req.id}&is_archived=false")
    assert res_unarchived_list.status_code == 200
    assert res_unarchived_list.json()["total_count"] == 0

    # Check that is_archived=true includes it
    res_archived_list = client.get(f"/api/history?search={req.id}&is_archived=true")
    assert res_archived_list.status_code == 200
    assert res_archived_list.json()["total_count"] == 1

    # Unarchive it
    res_unarchive = client.post(f"/api/history/{req.id}/archive", json={"archive": False})
    assert res_unarchive.status_code == 200
    assert res_unarchive.json()["is_archived"] is False


def test_history_detail_endpoint(client: TestClient, db_session: Session):
    """Test GET /api/history/{request_id} retrieves full verification dossier."""
    req = VerificationRequest(
        request_type="text",
        content="Detail verification request with claim and verdict.",
        content_hash=compute_content_hash("Detail verification request with claim and verdict."),
        status="completed",
        is_archived=False,
    )
    db_session.add(req)
    db_session.flush()

    claim = Claim(
        request_id=req.id,
        claim_text="The earth revolves around the sun.",
        normalized_text="earth revolves sun",
        claim_type="factual",
        verifiability="verifiable",
        importance="high",
        status="completed",
    )
    db_session.add(claim)
    db_session.flush()

    result = VerificationResult(
        request_id=req.id,
        claim_id=None,
        verdict="SUPPORTED",
        overall_verdict="SUPPORTED",
        confidence=0.95,
        confidence_score=0.95,
        truth_score=0.95,
        summary="Verified true by astronomical consensus.",
        explanation="Verified true by astronomical consensus.",
        limitations=[],
    )
    db_session.add(result)

    event = VerificationEvent(
        request_id=req.id,
        stage_name="testing",
        event_type="TEST_EVENT",
        status="success",
        details={"note": "test event note"},
    )
    db_session.add(event)
    db_session.commit()

    response = client.get(f"/api/history/{req.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == req.id
    assert data["request_type"] == "text"
    assert len(data["claims"]) >= 1
    assert data["claims"][0]["claim_text"] == "The earth revolves around the sun."
    assert data["verdict"] == "SUPPORTED"
    assert data["confidence"] == 0.95
    assert len(data["events"]) >= 1
    assert data["events"][0]["event_type"] == "TEST_EVENT"


def test_history_detail_not_found(client: TestClient):
    """Test GET /api/history/999999 returns 404."""
    response = client.get("/api/history/999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_history_duplicate_check(client: TestClient, db_session: Session):
    """Test GET /api/history/check-duplicate."""
    duplicate_text = "Exact text that has been verified previously."
    h = compute_content_hash(duplicate_text)

    req = VerificationRequest(
        request_type="text",
        content=duplicate_text,
        content_hash=h,
        status="completed",
        is_archived=False,
    )
    db_session.add(req)
    db_session.commit()

    # Check by hash
    res_hash = client.get(f"/api/history/check-duplicate?content_hash={h}")
    assert res_hash.status_code == 200
    data_hash = res_hash.json()
    assert data_hash["has_duplicate"] is True
    assert data_hash["matched_request"]["id"] == req.id
    assert data_hash["match_type"] == "exact"

    # Check by content
    res_content = client.get(f"/api/history/check-duplicate?content={duplicate_text}")
    assert res_content.status_code == 200
    data_content = res_content.json()
    assert data_content["has_duplicate"] is True
    assert data_content["matched_request"]["id"] == req.id

    # Check non-duplicate
    res_fresh = client.get("/api/history/check-duplicate?content=Completely fresh and never seen text 987654")
    assert res_fresh.status_code == 200
    data_fresh = res_fresh.json()
    assert data_fresh["has_duplicate"] is False


def test_history_reverify_text(client: TestClient, db_session: Session):
    """Test POST /api/history/{request_id}/reverify creates a child verification request."""
    # Create original request
    orig_req = VerificationRequest(
        request_type="text",
        content="Breaking news: James Webb Space Telescope observed atmospheric water on K2-18b.",
        content_hash=compute_content_hash("Breaking news: James Webb Space Telescope observed atmospheric water on K2-18b."),
        status="completed",
        is_archived=False,
    )
    db_session.add(orig_req)
    db_session.commit()

    response = client.post(f"/api/history/{orig_req.id}/reverify")
    assert response.status_code == 200
    data = response.json()
    assert data["original_request_id"] == orig_req.id
    assert "new_request_id" in data
    assert data["new_request_id"] != orig_req.id
    assert "re-verification" in data["message"].lower()

    # Verify in DB that new request has parent_request_id set
    new_req = db_session.query(VerificationRequest).filter_by(id=data["new_request_id"]).first()
    assert new_req is not None
    assert new_req.parent_request_id == orig_req.id

    # Verify original request remains intact
    db_session.refresh(orig_req)
    assert orig_req.status == "completed"
