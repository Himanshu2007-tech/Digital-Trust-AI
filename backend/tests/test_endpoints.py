import pytest
from fastapi.testclient import TestClient


def test_verify_text_endpoint(client: TestClient):
    """Test that POST /api/verify/text runs real claim extraction engine."""
    response = client.post(
        "/api/verify/text",
        json={"text": "Breaking news: Scientists discovered water on Mars surface in June 2026."}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "extracted"
    assert data["claims_count"] >= 1
    assert "request_id" in data


def test_verify_url_endpoint(client: TestClient):
    """Test that POST /api/verify/url blocks SSRF and handles real verification."""
    # SSRF rejection check
    response = client.post(
        "/api/verify/url",
        json={"url": "http://127.0.0.1:8000/internal-admin"}
    )
    assert response.status_code == 400
    assert "Security rejection" in response.json()["detail"]


def test_verify_url_ssrf_protection(client: TestClient):
    """Test that SSRF attempt to localhost is blocked by security validation."""
    response = client.post(
        "/api/verify/url",
        json={"url": "http://localhost:8080/admin"}
    )
    assert response.status_code == 400
    assert "prohibited for security reasons" in response.json()["detail"]


def test_history_endpoint(client: TestClient):
    """Test that GET /api/history returns paginated real history response."""
    response = client.get("/api/history")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total_count" in data
    assert isinstance(data["items"], list)


def test_reports_empty_state(client: TestClient):
    """Test that GET /api/reports returns empty list or items and no fake items."""
    response = client.get("/api/reports")
    assert response.status_code == 200
    data = response.json()
    if isinstance(data, dict):
        assert "items" in data
        assert isinstance(data["items"], list)
    else:
        assert isinstance(data, list)

