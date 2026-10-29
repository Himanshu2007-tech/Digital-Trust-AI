import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.init_db import init_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure test database tables exist."""
    init_db()


@pytest.fixture(scope="module")
def client():
    """Create test client fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    """Create a database session fixture for testing."""
    from app.database.session import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

