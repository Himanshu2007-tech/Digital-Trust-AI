import io
import struct
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.video_frame import VideoFrame
from app.models.claim_occurrence import ClaimOccurrence
from app.models.claim import Claim
from app.models.media_verification import MediaVerification
from app.verification.multimedia.sampling import (
    VideoFrameSampler,
    ExtractedFrameItem,
    format_seconds_to_timestamp,
)
from app.verification.multimedia.visual_extractor import (
    FrameVisualExtractor,
    detect_visual_context_observations,
)
from app.verification.multimedia.deduplication import (
    MultimodalClaimDeduplicator,
    calculate_claim_similarity,
)
from app.verification.multimedia.alignment import (
    TimelineAndAlignmentAnalyzer,
    extract_content_keywords,
)
from app.verification.multimedia.reused_footage import check_reused_footage_in_database
from app.verification.multimedia.service import MultimediaAnalysisService
from app.verification.media.service import MediaVerificationService
from app.verification.media.transcription.base import TranscriptSegmentItem
from app.verification.media.transcription.engine import (
    FallbackTranscriptionEngine,
    UnifiedTranscriptionEngine,
)


def create_minimal_mp4_bytes() -> bytes:
    """Generates a minimal valid MP4 container with ftyp and moov atoms."""
    buf = io.BytesIO()
    buf.write(struct.pack(">I", 20))
    buf.write(b"ftyp")
    buf.write(b"isom")
    buf.write(struct.pack(">I", 512))
    buf.write(b"mp41")
    buf.write(struct.pack(">I", 16))
    buf.write(b"moov")
    buf.write(b"\x00" * 8)
    return buf.getvalue()


# 1. Video Frame Sampler Tests
def test_video_frame_sampler_fallback_and_hash():
    sampler = VideoFrameSampler(interval_seconds=5.0, max_frames=4)
    frames = sampler.sample_frames("dummy_nonexistent_video.mp4", duration_seconds=20.0)

    assert len(frames) == 4
    for frm in frames:
        assert isinstance(frm, ExtractedFrameItem)
        assert frm.image_hash is not None
        assert len(frm.image_hash) == 64  # SHA-256 length
        assert frm.selection_method in ["FIXED_INTERVAL", "SCENE_CHANGE", "HIGH_TEXT_DENSITY"]
        assert frm.width == 640
        assert frm.height == 360
        assert ":" in frm.formatted_timestamp


def test_format_seconds_to_timestamp():
    assert format_seconds_to_timestamp(0) == "00:00"
    assert format_seconds_to_timestamp(65.5) == "01:05"
    assert format_seconds_to_timestamp(360) == "06:00"


# 2. Visual Information & Context Extraction Tests
def test_detect_visual_context_observations():
    # Document indicators
    obs_doc = detect_visual_context_observations(
        ocr_text="Ministry of Finance Gazette Notification Order 2026",
        frame_width=1280,
        frame_height=720,
        ocr_blocks=[]
    )
    assert obs_doc["is_possible_document"] is True
    assert any("DOCUMENT" in o for o in obs_doc["observations"])
    assert "disclaimer" in obs_doc

    # Ticker / lower third indicator
    blocks = [{"text": "Breaking News: Policy update", "bbox": [50, 600, 800, 50]}]
    obs_ticker = detect_visual_context_observations(
        ocr_text="Breaking News: Policy update",
        frame_width=1280,
        frame_height=720,
        ocr_blocks=blocks
    )
    assert obs_ticker["is_broadcast_ticker"] is True


def test_frame_visual_extractor_with_injected_text():
    extractor = FrameVisualExtractor()
    sample_frame = ExtractedFrameItem(
        frame_number=25,
        timestamp=1.0,
        formatted_timestamp="00:01",
        selection_method="SCENE_CHANGE",
        image_hash="a" * 64,
        stored_path="/tmp/sample.jpg",
        image_bytes=b"\x00" * 100,
        width=1280,
        height=720,
    )

    injected = "Breaking: Inflation dropped to 4.5% in January 2026. Visit https://rbi.org.in"
    res = extractor.analyze_frame(sample_frame, injected_ocr_text=injected)

    assert res["ocr_text"] == injected
    assert len(res["detected_urls"]) == 1
    assert res["detected_urls"][0] == "https://rbi.org.in"
    assert res["selection_method"] == "SCENE_CHANGE"
    assert "visual_context" in res


# 3. Multimodal Claim Fusion & Deduplication Tests
def test_multimodal_claim_deduplication():
    deduplicator = MultimodalClaimDeduplicator(similarity_threshold=0.45)

    audio_claims = [{
        "text": "The Ministry of Health allocated 5000 crore for rural hospitals.",
        "normalized_text": "the ministry of health allocated 5000 crore for rural hospitals.",
        "start_time": 10.0,
        "end_time": 18.0,
        "formatted_timestamp": "00:10 - 00:18",
        "segment_id": 1,
    }]

    # Visual claim matching the audio claim closely
    matching_visual_claim = {
        "text": "Ministry of Health allocates 5000 crore for rural healthcare.",
        "timestamp": 12.0,
        "formatted_timestamp": "00:12",
        "frame_id": 101,
        "frame_number": 300,
        "ocr_confidence": 94.0,
        "numbers": ["5000 crore"],
    }

    # Novel visual claim that wasn't in audio
    novel_visual_claim = {
        "text": "Global crude oil prices rose by 8% this morning.",
        "timestamp": 25.0,
        "formatted_timestamp": "00:25",
        "frame_id": 102,
        "frame_number": 625,
        "ocr_confidence": 91.0,
        "numbers": ["8%"],
    }

    fused = deduplicator.fuse_and_deduplicate(
        audio_claims=audio_claims,
        visual_claims=[matching_visual_claim, novel_visual_claim],
        max_claims=5
    )

    # Should have 2 unique claims, NOT 3
    assert len(fused) == 2

    # First claim should have 2 occurrences (AUDIO_TRANSCRIPT and VISUAL_OCR)
    first_claim = fused[0]
    assert len(first_claim["occurrences"]) == 2
    sources = [occ["source_type"] for occ in first_claim["occurrences"]]
    assert "AUDIO_TRANSCRIPT" in sources
    assert "VISUAL_OCR" in sources
    assert first_claim["primary_origin"] == "MULTIMODAL (AUDIO + VISUAL)"

    # Second claim is novel visual claim
    second_claim = fused[1]
    assert len(second_claim["occurrences"]) == 1
    assert second_claim["occurrences"][0]["source_type"] == "VISUAL_OCR"


# 4. Timeline Construction & Audio-Visual Alignment Tests
def test_timeline_construction_chronological_order():
    analyzer = TimelineAndAlignmentAnalyzer()
    segments = [
        TranscriptSegmentItem(start_time=5.0, end_time=12.0, text="Welcome to today's news.", sequence=0),
        TranscriptSegmentItem(start_time=15.0, end_time=22.0, text="Government announced new policies.", sequence=1),
    ]
    frames = [
        {"id": 1, "timestamp": 0.5, "frame_number": 12, "selection_method": "FIXED_INTERVAL", "ocr_text": ""},
        {"id": 2, "timestamp": 16.0, "frame_number": 400, "selection_method": "SCENE_CHANGE", "ocr_text": "Govt Policy Update 2026"},
    ]
    claims = [
        {
            "id": 10,
            "text": "Government announced new policies.",
            "occurrences": [{"source_type": "AUDIO_TRANSCRIPT", "timestamp_start": 15.0, "timestamp_end": 22.0}]
        }
    ]

    timeline = analyzer.build_timeline(duration_seconds=30.0, segments=segments, frames=frames, claims=claims)
    assert len(timeline) >= 4

    # Check timestamps are monotonically non-decreasing
    timestamps = [evt["timestamp"] for evt in timeline]
    assert timestamps == sorted(timestamps)


def test_audio_visual_alignment_match_and_mismatch():
    analyzer = TimelineAndAlignmentAnalyzer()

    # Thematic match at t=10s
    segments_match = [
        TranscriptSegmentItem(start_time=8.0, end_time=15.0, text="Finance ministry presented annual economic budget.", sequence=0)
    ]
    frames_match = [
        {"timestamp": 10.0, "frame_number": 250, "ocr_text": "Finance Ministry Economic Budget Presentation"}
    ]
    report_match = analyzer.evaluate_audio_visual_alignment(segments_match, frames_match)
    assert report_match["summary_status"] == "CONSISTENT_ALIGNMENT"
    assert report_match["alignments_count"] >= 1

    # Thematic mismatch at t=10s
    segments_mismatch = [
        TranscriptSegmentItem(start_time=8.0, end_time=15.0, text="Sports minister inaugurated national cricket stadium.", sequence=0)
    ]
    frames_mismatch = [
        {"timestamp": 10.0, "frame_number": 250, "ocr_text": "Severe Earthquake Strikes Northern Region Today"}
    ]
    report_mismatch = analyzer.evaluate_audio_visual_alignment(segments_mismatch, frames_mismatch)
    assert report_mismatch["summary_status"] == "CONTEXT_DIVERGENCE_OBSERVED"
    assert report_mismatch["mismatches_count"] >= 1


# 5. Reused Footage Internal Database Matcher Tests
def test_reused_footage_database_matching(db_session):
    # Store a prior video frame with a known hash
    known_hash = "f" * 64
    prior_frame = VideoFrame(
        media_verification_id=99999,  # Belongs to a different prior verification
        timestamp=12.5,
        frame_number=312,
        width=1280,
        height=720,
        selection_method="SCENE_CHANGE",
        image_hash=known_hash,
    )
    db_session.add(prior_frame)
    db_session.commit()

    # Check matching when current_media_verification_id is different (e.g. 123)
    result_matched = check_reused_footage_in_database(
        frame_hashes=[known_hash, "a" * 64],
        current_media_verification_id=123,
        db=db_session
    )
    assert result_matched["reused_footage_detected"] is True
    assert result_matched["matching_frames_count"] >= 1
    assert "MATCHING FRAME FOUND IN PREVIOUS ANALYSIS" in result_matched["matched_prior_requests"][0]["match_label"]
    assert "not available" in result_matched["reverse_image_search_status"]
    assert "could not be established" in result_matched["source_origin_note"]


# 6. End-to-End Multimedia Verification Service Pipeline Test
def test_multimedia_verification_service_full_pipeline(db_session):
    mp4_bytes = create_minimal_mp4_bytes()

    # Injected test transcript with speech claim
    test_text = (
        "The Ministry of Health announced a 25% increase in healthcare subsidies for 2026. "
        "The minister stated \"District hospitals will receive modernized emergency trauma units.\""
    )
    test_segments = [
        TranscriptSegmentItem(start_time=0.0, end_time=5.0, text="The Ministry of Health announced a 25% increase in healthcare subsidies for 2026.", sequence=0),
        TranscriptSegmentItem(start_time=5.0, end_time=10.0, text='The minister stated "District hospitals will receive modernized emergency trauma units."', sequence=1),
    ]

    fallback_engine = FallbackTranscriptionEngine(
        simulated_text=test_text,
        simulated_segments=test_segments,
        simulated_confidence=0.94,
    )
    unified_engine = UnifiedTranscriptionEngine(engine=fallback_engine)
    service = MediaVerificationService(transcription_engine=unified_engine)

    # Injected keyframes for deterministic unit testing
    injected_frames = [
        ExtractedFrameItem(
            frame_number=0,
            timestamp=1.0,
            formatted_timestamp="00:01",
            selection_method="FIXED_INTERVAL",
            image_hash="b" * 64,
            stored_path="/tmp/f0.jpg",
            image_bytes=b"\x00" * 50,
            width=640,
            height=360,
        ),
        ExtractedFrameItem(
            frame_number=150,
            timestamp=6.0,
            formatted_timestamp="00:06",
            selection_method="SCENE_CHANGE",
            image_hash="c" * 64,
            stored_path="/tmp/f1.jpg",
            image_bytes=b"\x00" * 50,
            width=640,
            height=360,
        ),
    ]

    injected_ocr_map = {
        0: "Headline: Health Ministry 25% Subsidy Boost Confirmed",
        150: "Breaking: Modern Emergency Units Approved For District Hospitals",
    }

    result = service.verify_media(
        file_bytes=mp4_bytes,
        original_filename="briefing.mp4",
        db=db_session,
        perform_search=True,
        extract_evidence=True,
        finalize_verdicts=True,
        max_claims=3,
        injected_frames=injected_frames,
        injected_ocr_map=injected_ocr_map,
    )

    assert result["status"] == "completed"
    assert result["forensics"]["media_type"] == "video"

    # Part 10 Multimedia Assertions
    assert len(result["frames"]) == 2
    assert result["frames_count"] == 2
    assert result["frames"][0]["selection_method"] in ["FIXED_INTERVAL", "SCENE_CHANGE"]
    assert "visual_context" in result["frames"][0]

    # Timeline verification
    assert len(result["timeline"]) >= 3
    assert any(e["event_type"] == "AUDIO_SPEECH" for e in result["timeline"])

    # Alignment and Forensics
    assert "alignment" in result
    assert "reused_footage" in result
    assert "forensic_observations" in result
    assert "NOT ASSESSED" in result["forensic_observations"]["ai_generation_assessment"]
    assert "NOT ASSESSED" in result["forensic_observations"]["deepfake_assessment"]

    # Multimodal Claims and Occurrences
    assert len(result["claims"]) >= 1
    first_claim = result["claims"][0]
    assert "primary_origin" in first_claim
    assert len(first_claim["occurrences"]) >= 1

    # Check database persistence
    db_frames = db_session.query(VideoFrame).filter(VideoFrame.media_verification_id == result["media_verification_id"]).all()
    assert len(db_frames) == 2

    db_occurrences = db_session.query(ClaimOccurrence).filter(ClaimOccurrence.media_verification_id == result["media_verification_id"]).all()
    assert len(db_occurrences) >= 1


# 7. API Endpoint Multimedia Verification Test
def test_api_verify_media_video_multimedia():
    client = TestClient(app)
    mp4_bytes = create_minimal_mp4_bytes()

    response = client.post(
        "/api/verify/media",
        files={"file": ("news_report.mp4", mp4_bytes, "video/mp4")},
        data={"perform_search": "true", "finalize_verdicts": "true", "max_claims": "2"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "frames" in data
    assert "timeline" in data
    assert "alignment" in data
    assert "reused_footage" in data
    assert "forensic_observations" in data
    assert len(data["claims"]) >= 1
    assert "occurrences" in data["claims"][0]
