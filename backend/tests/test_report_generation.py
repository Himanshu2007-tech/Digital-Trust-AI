import os
import hashlib
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.verification_request import VerificationRequest
from app.models.claim import Claim
from app.models.source import Source
from app.models.evidence import Evidence
from app.models.verification_result import VerificationResult
from app.models.media_verification import MediaVerification
from app.models.transcript_segment import TranscriptSegment
from app.models.video_frame import VideoFrame
from app.models.report import Report
from app.verification.reports.service import report_service
from app.core.exceptions import TruthLensException


@pytest.fixture
def sample_text_request(db_session: Session) -> VerificationRequest:
    """Fixture creating a fully populated text verification request with claims and verdict."""
    vr = VerificationRequest(
        request_type="text",
        content="NASA confirms Perseverance rover landed on Mars in February 2021 and extracted oxygen.",
        status="completed",
        content_hash="test_content_hash_12345",
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(vr)
    db_session.flush()

    # Verdict
    vres = VerificationResult(
        request_id=vr.id,
        claim_id=None,
        overall_verdict="SUPPORTED",
        confidence=0.92,
        explanation="Direct official corroboration confirmed the landing date and oxygen generation experiment.",
        methodology_version="1.0.0",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(vres)

    # Claim 1
    c1 = Claim(
        request_id=vr.id,
        claim_text="NASA Perseverance rover touched down on Mars in February 2021.",
        claim_type="factual",
        verifiability="high",
        importance=1,
        status="verified",
    )
    db_session.add(c1)
    db_session.flush()

    c1_res = VerificationResult(
        request_id=vr.id,
        claim_id=c1.id,
        verdict="SUPPORTED",
        confidence=0.95,
        explanation="Official NASA flight data confirms landing on Feb 18, 2021.",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(c1_res)

    # Source & Evidence
    src = Source(
        name="NASA Mars 2020 Mission Log",
        url="https://mars.nasa.gov/perseverance",
        domain="nasa.gov",
        publisher="NASA",
        source_type="official",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(src)
    db_session.flush()

    ev = Evidence(
        claim_id=c1.id,
        source_id=src.id,
        evidence_type="SUPPORTING",
        direction="SUPPORTING",
        evidence_text="Perseverance touched down safely on Mars at 20:55 UTC on 18 February 2021.",
        snippet="Perseverance touched down safely on Mars.",
        url="https://mars.nasa.gov/perseverance",
        relevance="HIGH",
        relevance_score=0.98,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(ev)

    db_session.commit()
    db_session.refresh(vr)
    return vr


@pytest.fixture
def sample_video_request(db_session: Session) -> VerificationRequest:
    """Fixture creating a video verification request with segments and keyframes."""
    vr = VerificationRequest(
        request_type="video",
        content="News broadcast claiming unexpected solar eclipse occurred yesterday.",
        status="completed",
        content_hash="test_video_hash_98765",
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(vr)
    db_session.flush()

    mv = MediaVerification(
        request_id=vr.id,
        media_type="video",
        duration_seconds=95.0,
        raw_transcript="Astronomers say an unexpected eclipse darkened the sky across the nation yesterday.",
        normalized_transcript="Astronomers say an unexpected eclipse darkened the sky across the nation yesterday.",
        transcription_confidence=0.89,
        language="en",
        media_hash="hash_video_test_123",
        detected_quotes=["unexpected eclipse darkened the sky"],
        detected_urls=[],
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(mv)

    db_session.flush()

    seg = TranscriptSegment(
        media_verification_id=mv.id,
        sequence=1,
        start_time=0.0,
        end_time=5.0,
        text="Astronomers say an unexpected eclipse darkened the sky.",
        confidence=0.91,
    )
    db_session.add(seg)


    frm = VideoFrame(
        media_verification_id=mv.id,
        frame_number=1,
        timestamp=2.5,
        selection_method="interval",
        image_hash="frame_hash_1",
        ocr_text="BREAKING NEWS: SOLAR ECLIPSE",
        visual_context="News desk presenter with graphic banner",
    )
    db_session.add(frm)

    vres = VerificationResult(
        request_id=vr.id,
        claim_id=None,
        overall_verdict="CONTRADICTED",
        confidence=0.94,
        explanation="Solar eclipses are strictly astronomical calculations; no unpredicted eclipse occurred.",
        methodology_version="1.0.0",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(vres)
    db_session.commit()
    db_session.refresh(vr)
    return vr


def test_generate_text_verification_report(db_session: Session, sample_text_request: VerificationRequest):
    """Test generating, saving, and hashing a PDF dossier for a text verification request."""
    report = report_service.generate_report(
        db=db_session,
        request_id=sample_text_request.id,
        title="Custom Test Report Title"
    )

    assert report.id is not None
    assert report.report_uuid.startswith("rep_")
    assert report.request_id == sample_text_request.id
    assert report.status == "generated"
    assert report.format == "pdf"
    assert report.mime_type == "application/pdf"
    assert report.file_size_bytes > 0
    assert report.sha256_hash is not None
    assert report.file_path is not None
    assert os.path.exists(report.file_path)

    # Verify physical file integrity
    with open(report.file_path, "rb") as f:
        file_bytes = f.read()

    assert file_bytes.startswith(b"%PDF-1.4")
    assert file_bytes.endswith(b"%%EOF\n")
    assert hashlib.sha256(file_bytes).hexdigest() == report.sha256_hash


def test_generate_multimedia_verification_report(db_session: Session, sample_video_request: VerificationRequest):
    """Test generating a comprehensive dossier for a multimedia video request with segments & frames."""
    report = report_service.generate_report(
        db=db_session,
        request_id=sample_video_request.id
    )

    assert report.status == "generated"
    assert report.file_size_bytes > 1000
    assert os.path.isfile(report.file_path)

    with open(report.file_path, "rb") as f:
        content = f.read()
    assert b"%PDF-1.4" in content
    assert b"%%EOF" in content


def test_generate_report_nonexistent_request(db_session: Session):
    """Test that requesting a report for an invalid request ID raises a 404 TruthLensException."""
    with pytest.raises(TruthLensException) as excinfo:
        report_service.generate_report(db=db_session, request_id=9999999)
    assert excinfo.value.status_code == 404


def test_api_report_lifecycle(client: TestClient, sample_text_request: VerificationRequest):
    """Test full API lifecycle: generate, list, get metadata, download, and delete."""
    # 1. POST /api/reports - Generate
    post_resp = client.post(
        "/api/reports",
        json={"request_id": sample_text_request.id, "title": "API Lifecycle Dossier"}
    )
    assert post_resp.status_code == 201
    rep_data = post_resp.json()
    rep_id = rep_data["id"]
    rep_uuid = rep_data["report_uuid"]
    assert rep_data["status"] == "generated"
    assert rep_data["format"] == "pdf"
    assert rep_data["sha256_hash"] is not None
    assert rep_data["file_size_bytes"] > 0
    assert f"/api/reports/{rep_id}/download" in rep_data["download_url"]

    # 2. GET /api/reports - List
    list_resp = client.get(f"/api/reports?request_id={sample_text_request.id}")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total_count"] >= 1
    matching = [item for item in list_data["items"] if item["id"] == rep_id]
    assert len(matching) == 1

    # 3. GET /api/reports/{report_id} - Metadata
    get_resp = client.get(f"/api/reports/{rep_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == rep_id
    assert get_resp.json()["report_uuid"] == rep_uuid

    # 4. GET /api/reports/{report_id}/download - Download
    dl_resp = client.get(f"/api/reports/{rep_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "application/pdf"
    assert "attachment" in dl_resp.headers["content-disposition"]
    dl_bytes = dl_resp.content
    assert hashlib.sha256(dl_bytes).hexdigest() == rep_data["sha256_hash"]

    # 5. DELETE /api/reports/{report_id} - Safe Delete
    del_resp = client.delete(f"/api/reports/{rep_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # Confirm 404 after deletion
    get_after_del = client.get(f"/api/reports/{rep_id}")
    assert get_after_del.status_code == 404


def test_download_path_traversal_prevention(client: TestClient, db_session: Session, sample_text_request: VerificationRequest):
    """Test security: Report with path pointing outside storage directory is rejected."""
    # Create malicious report row pointing to unauthorized location
    malicious_report = Report(
        report_uuid="rep_malicious_test",
        request_id=sample_text_request.id,
        title="Unauthorized Traversal Test",
        format="pdf",
        file_path="../../../../../etc/passwd",
        file_size_bytes=100,
        status="generated",
    )
    db_session.add(malicious_report)
    db_session.commit()
    db_session.refresh(malicious_report)

    # Attempt download
    resp = client.get(f"/api/reports/{malicious_report.id}/download")
    # Must be 403 or 404
    assert resp.status_code in (403, 404)

    # Clean up test row
    db_session.delete(malicious_report)
    db_session.commit()


def test_generate_image_verification_report(db_session: Session):
    """Test generating a dossier for an image request with OCR findings."""
    from app.models.image_verification import ImageVerification

    vr = VerificationRequest(
        request_type="image",
        status="completed",
        content_hash="test_image_hash_112233",
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(vr)
    db_session.flush()

    img_v = ImageVerification(
        request_id=vr.id,
        image_width=1920,
        image_height=1080,
        image_format="PNG",
        raw_ocr_text="BREAKING: Official statement released by health agency regarding summer advisory.",
        normalized_ocr_text="BREAKING: Official statement released by health agency regarding summer advisory.",
        ocr_confidence=94.5,
        ocr_blocks=[{"text": "BREAKING: Official statement", "confidence": 95}],
        detected_urls=["https://health.gov/advisory"],
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(img_v)

    vres = VerificationResult(
        request_id=vr.id,
        claim_id=None,
        overall_verdict="SUPPORTED",
        confidence=0.91,
        explanation="OCR text matched official public health ministry advisory release.",
        methodology_version="1.0.0",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(vres)
    db_session.commit()

    report = report_service.generate_report(db=db_session, request_id=vr.id)
    assert report.status == "generated"
    assert report.file_size_bytes > 0
    assert os.path.isfile(report.file_path)


def test_generate_url_verification_report(db_session: Session):
    """Test generating a dossier for a web article URL request."""
    from app.models.article import Article

    vr = VerificationRequest(
        request_type="url",
        status="completed",
        content="https://news.example.com/2026/energy-breakthrough",
        content_hash="test_url_hash_445566",
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(vr)
    db_session.flush()

    art = Article(
        request_id=vr.id,
        original_url="https://news.example.com/2026/energy-breakthrough",
        canonical_url="https://news.example.com/2026/energy-breakthrough",
        domain="news.example.com",
        title="Researchers Announce High Efficiency Solar Cells",
        publisher="Global Science Daily",
        author="Dr. Jane Doe",
        published_at="2026-05-12",
        article_text="Researchers at the National Lab demonstrated 42% conversion efficiency in lab conditions.",
        content_hash="article_hash_abc",
        content_length=95,
        word_count=13,
        retrieved_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(art)

    vres = VerificationResult(
        request_id=vr.id,
        claim_id=None,
        overall_verdict="SUPPORTED",
        confidence=0.88,
        explanation="Article corroborated by laboratory press release.",
        methodology_version="1.0.0",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(vres)
    db_session.commit()

    report = report_service.generate_report(db=db_session, request_id=vr.id)
    assert report.status == "generated"
    assert report.file_size_bytes > 0
    assert os.path.isfile(report.file_path)

