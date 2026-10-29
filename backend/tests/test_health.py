import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test the root endpoint returns correct application metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "TruthLens AI"
    assert "health_check" in data


def test_health_check_endpoint(client: TestClient):
    """
    Test GET /api/health:
    - Must return HTTP 200
    - Must return status: 'ok'
    - Must return service: 'TruthLens AI'
    - Must report database connection
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "ok"
    assert data["service"] == "TruthLens AI"
    assert data["version"] == "1.0.0"
    assert "database" in data
    assert data["database"]["connected"] is True
    assert "features" in data
