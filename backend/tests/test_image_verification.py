import io
import pytest
from PIL import Image, ExifTags
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.session import get_db, SessionLocal
from app.core.exceptions import SecurityRiskException
from app.verification.image.security import (
    validate_image_security,
    extract_and_sanitize_exif,
    detect_image_magic_bytes
)
from app.verification.image.ocr.patterns import (
    extract_detected_urls,
    extract_social_handles,
    extract_metrics,
    extract_dates
)
from app.verification.image.ocr.engine import (
    FallbackOCREngine,
    UnifiedOCREngine,
    normalize_ocr_text
)
from app.verification.image.preprocessor import ImagePreprocessor
from app.verification.image.service import ImageVerificationService
from app.verification.search.discovery_service import SourceDiscoveryService
from app.verification.search.providers.mock import MockSearchProvider
from app.verification.evidence.service import EvidenceAnalysisService
from app.verification.verdict.service import VerdictService


def create_sample_png_bytes(width: int = 200, height: int = 100, color: str = "white") -> bytes:
    """Creates in-memory PNG bytes for testing."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_sample_jpeg_bytes() -> bytes:
    """Creates in-memory JPEG bytes for testing."""
    img = Image.new("RGB", (300, 150), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_magic_bytes_detection_valid_and_invalid():
    # Valid PNG
    png_bytes = create_sample_png_bytes()
    detected = detect_image_magic_bytes(png_bytes)
    assert detected is not None
    assert detected[0] == "image/png"

    # Valid JPEG
    jpg_bytes = create_sample_jpeg_bytes()
    detected_jpg = detect_image_magic_bytes(jpg_bytes)
    assert detected_jpg is not None
    assert detected_jpg[0] == "image/jpeg"

    # Invalid executable or script pretending to be an image
    fake_img = b"MZ\x90\x00\x03\x00\x00\x00This is a fake windows binary"
    assert detect_image_magic_bytes(fake_img) is None

    with pytest.raises(SecurityRiskException, match="magic byte"):
        validate_image_security(fake_img, "malware.png")


def test_decompression_bomb_rejection():
    # Construct bytes exceeding limits
    png_bytes = create_sample_png_bytes(10, 10)
    
    # Passing an oversized dimension check directly
    from unittest.mock import patch
    with patch("PIL.Image.open") as mock_open:
        mock_img = Image.new("RGB", (10000, 10000))
        mock_open.return_value.__enter__.return_value = mock_img
        
        with pytest.raises(SecurityRiskException, match="exceeds decompression bomb threshold"):
            validate_image_security(png_bytes, "huge.png")


def test_ocr_patterns_extraction():
    sample_text = (
        "Breaking: The Ministry of Finance announced a 15% reduction in corporate taxes. "
        "Source confirmed at https://reuters.com/world/economy-tax-cut. "
        "Official post by @FinMinIndia received 14.5K Reposts and 82.1K Likes on Sep 28, 2026."
    )

    urls = extract_detected_urls(sample_text)
    assert len(urls) == 1
    assert "https://reuters.com/world/economy-tax-cut" in urls[0]

    handles = extract_social_handles(sample_text)
    assert "@FinMinIndia" in handles

    metrics = extract_metrics(sample_text)
    assert metrics.get("reposts") == "14.5K"
    assert metrics.get("likes") == "82.1K"

    dates = extract_dates(sample_text)
    assert any("Sep 28, 2026" in d for d in dates)


def test_ocr_text_normalization():
    raw_ocr = "The govern-\nment announced new regula-\ntions yesterday.\n\nAll firms must comply."
    normalized = normalize_ocr_text(raw_ocr)
    assert "government" in normalized
    assert "regulations" in normalized
    assert "govern-\nment" not in normalized


def test_exif_sanitization_privacy():
    # Create image with dummy EXIF info
    img = Image.new("RGB", (100, 100), color="red")
    exif = img.getexif()
    # Tag 271: Make
    exif[271] = "Sony"
    # Tag 34853: GPSInfo (simulating sensitive GPS coordinates)
    exif[34853] = {1: "N", 2: (40, 44, 0)}

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    sanitized = extract_and_sanitize_exif(buf.getvalue())

    assert sanitized["has_exif"] is True
    assert sanitized["gps_removed"] is True
    # GPS data must NOT be present in technical tags
    assert "GPSInfo" not in sanitized["technical_tags"]
    assert "GPS" not in sanitized["technical_tags"]


def test_fallback_ocr_engine():
    img = Image.new("RGB", (300, 150), color="white")
    simulated = "NASA confirmed discovery of liquid water on Mars surface."
    engine = FallbackOCREngine(simulated_text=simulated)
    result = engine.extract(img)

    assert result.engine_used == "fallback"
    assert "NASA confirmed discovery" in result.normalized_text
    assert result.overall_confidence > 80.0
    assert len(result.blocks) > 0
    assert result.word_count == len(simulated.split())


def test_image_verification_service_full_pipeline(db_session: Session):
    simulated_claim_text = "The Central Bank announced an immediate 2% interest rate cut on September 28."
    ocr_engine = FallbackOCREngine(simulated_text=simulated_claim_text)
    
    # Configure mock search provider for reliable deterministic testing
    from app.verification.search.models import NormalizedSearchResult, SourceType
    mock_results = [
        NormalizedSearchResult(
            title="Central Bank Lowers Benchmark Interest Rate by 2%",
            url="https://financialtimes.com/news/bank-cut",
            canonical_url="https://financialtimes.com/news/bank-cut",
            domain="financialtimes.com",
            snippet="The Central Bank today announced an immediate 2% interest rate cut following policy meetings.",
            published_at="2026-09-28",
            publisher="Financial Times",
            source_type=SourceType.RELIABLE_NEWS,
            query="Central Bank interest rate cut",
            retrieved_at="2026-09-28T12:00:00",
            provider="mock"
        )
    ]
    mock_provider = MockSearchProvider(mock_results=mock_results)
    discovery_service = SourceDiscoveryService(provider=mock_provider)

    service = ImageVerificationService(
        ocr_engine=UnifiedOCREngine(engine=ocr_engine),
        discovery_service=discovery_service,
        evidence_service=EvidenceAnalysisService(),
        verdict_service=VerdictService()
    )

    image_bytes = create_sample_png_bytes(400, 200)
    result = service.verify_image(
        file_bytes=image_bytes,
        original_filename="breaking_news_screenshot.png",
        db=db_session,
        perform_search=True,
        extract_evidence=True,
        finalize_verdicts=True
    )

    assert result["status"] == "completed"
    assert result["forensics"]["image_format"] == "PNG"
    assert result["forensics"]["file_hash_sha256"] is not None
    assert "ocr" in result
    assert result["ocr"]["ocr_confidence"] > 0
    assert len(result["ocr"]["blocks"]) > 0

    # Ensure claims extracted
    assert result["claims_count"] >= 1
    extracted_claim = result["claims"][0]
    assert "Central Bank" in extracted_claim["text"] or "interest rate" in extracted_claim["text"]

    # Ensure disclaimer is included
    assert "visual manipulation" in result["authenticity_disclaimer"]


def test_api_verify_image_endpoint():
    client = TestClient(app)
    image_bytes = create_sample_png_bytes(300, 150)

    response = client.post(
        "/api/verify/image",
        files={"file": ("screenshot.png", image_bytes, "image/png")},
        data={"perform_search": "false", "extract_evidence": "false", "finalize_verdicts": "false"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "forensics" in data
    assert "ocr" in data
    assert data["forensics"]["image_format"] == "PNG"
    assert data["forensics"]["file_hash_sha256"] is not None
    assert "authenticity_disclaimer" in data


def test_api_verify_image_security_rejection():
    client = TestClient(app)
    # Send shell script / invalid header
    malicious_bytes = b"#!/bin/bash\nrm -rf /"

    response = client.post(
        "/api/verify/image",
        files={"file": ("exploit.jpg", malicious_bytes, "image/jpeg")}
    )

    assert response.status_code == 400
    data = response.json()
    assert "Security rejection" in data["detail"]
