import pytest
from sqlalchemy import inspect
from app.database.session import engine
from app.models import (
    User, MediaFile, VerificationRequest, Claim, Source,
    Evidence, SourceComparison, VerificationResult, SearchQuery, Report
)


def test_all_tables_exist():
    """Verify that all 10 core tables are properly registered and created."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    
    expected_tables = {
        "users",
        "media_files",
        "verification_requests",
        "claims",
        "sources",
        "evidence",
        "source_comparisons",
        "verification_results",
        "search_queries",
        "reports"
    }
    
    missing_tables = expected_tables - table_names
    assert not missing_tables, f"Missing database tables: {missing_tables}"
