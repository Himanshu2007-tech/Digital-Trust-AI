import io
import struct
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import get_db
from app.core.exceptions import SecurityRiskException
from app.verification.media.security import detect_media_container, validate_media_security, save_media_file
from app.verification.media.metadata import parse_wav_header, parse_mp4_mov_header, extract_media_metadata
from app.verification.media.transcription.base import TranscriptSegmentItem, TranscriptionResult
from app.verification.media.transcription.patterns import extract_spoken_urls, extract_direct_quotes
from app.verification.media.transcription.engine import (
    normalize_transcript_text,
    detect_language_and_codeswitching,
    FallbackTranscriptionEngine,
    UnifiedTranscriptionEngine,
)
from app.verification.media.service import MediaVerificationService, correlate_claim_with_segment


def create_minimal_wav(duration_seconds: float = 1.0, sample_rate: int = 44100, channels: int = 1) -> bytes:
    """Generates a valid PCM 16-bit mono/stereo WAV byte stream."""
    bits_per_sample = 16
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    num_samples = int(sample_rate * duration_seconds)
    data_size = num_samples * block_align
    chunk_size = 36 + data_size

    buf = io.BytesIO()
    # RIFF header
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", chunk_size))
    buf.write(b"WAVE")
    # fmt subchunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))  # Subchunk1Size
    buf.write(struct.pack("<H", 1))   # AudioFormat (1 = PCM)
    buf.write(struct.pack("<H", channels))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", byte_rate))
    buf.write(struct.pack("<H", block_align))
    buf.write(struct.pack("<H", bits_per_sample))
    # data subchunk
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    # Null PCM audio samples
    buf.write(b"\x00" * data_size)

    return buf.getvalue()


def create_minimal_mp4() -> bytes:
    """Generates a minimal MP4 container with ftyp atom."""
    buf = io.BytesIO()
    # ftyp atom (size=20, type=ftyp, major_brand=isom, minor_version=512, compatible_brand=mp41)
    buf.write(struct.pack(">I", 20))
    buf.write(b"ftyp")
    buf.write(b"isom")
    buf.write(struct.pack(">I", 512))
    buf.write(b"mp41")
    # moov atom placeholder
    buf.write(struct.pack(">I", 16))
    buf.write(b"moov")
    buf.write(b"\x00" * 8)
    return buf.getvalue()


# 1. Container and Security Detection Tests
def test_media_security_container_detection():
    wav_bytes = create_minimal_wav(1.0)
    detected = detect_media_container(wav_bytes, "sample.wav")
    assert detected is not None
    assert detected[0] == "audio/wav"
    assert detected[1] == "wav"
    assert detected[2] == "audio"

    mp4_bytes = create_minimal_mp4()
    detected_mp4 = detect_media_container(mp4_bytes, "video.mp4")
    assert detected_mp4 is not None
    assert detected_mp4[0] == "video/mp4"
    assert detected_mp4[1] == "mp4"
    assert detected_mp4[2] == "video"

    # MP3 with ID3 header
    mp3_bytes = b"ID3\x03\x00\x00\x00\x00\x00\x00" + (b"\x00" * 32)
    detected_mp3 = detect_media_container(mp3_bytes, "song.mp3")
    assert detected_mp3 is not None
    assert detected_mp3[0] == "audio/mpeg"

    # Disguised executable (MZ header)
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
    assert detect_media_container(exe_bytes, "fake.wav") is None

    with pytest.raises(SecurityRiskException) as exc_info:
        validate_media_security(exe_bytes, "fake.wav")
    assert "INVALID_FILE" in str(exc_info.value)


def test_media_security_size_limits(monkeypatch):
    wav_bytes = create_minimal_wav(1.0)
    # Monkeypatch MAX_AUDIO_SIZE_BYTES to very small size
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_AUDIO_SIZE_BYTES", 100)

    with pytest.raises(SecurityRiskException) as exc_info:
        validate_media_security(wav_bytes, "audio.wav")
    assert "FILE_TOO_LARGE" in str(exc_info.value)


# 2. Metadata & Stream Inspection Tests
def test_wav_metadata_extraction():
    wav_bytes = create_minimal_wav(duration_seconds=2.5, sample_rate=44100, channels=2)
    info = parse_wav_header(wav_bytes)
    assert info["sample_rate"] == 44100
    assert info["channels"] == 2
    assert info["duration_seconds"] >= 2.4
    assert info["has_audio_track"] is True


def test_silent_video_indicator():
    # Video container with 'vide' atom but lacking 'soun' or 'mp4a'
    video_bytes = create_minimal_mp4() + b"vide" + (b"\x00" * 64)
    info = parse_mp4_mov_header(video_bytes)
    assert info["has_audio_track"] is False
    assert info["audio_codec"] is None


def test_duration_ceiling_rejection(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_AUDIO_DURATION_SECONDS", 10.0)

    wav_bytes = create_minimal_wav(duration_seconds=15.0)
    with pytest.raises(SecurityRiskException) as exc_info:
        extract_media_metadata("dummy.wav", "audio", wav_bytes)
    assert "MEDIA_TOO_LONG" in str(exc_info.value)


# 3. Transcription, Language, and Pattern Tests
def test_normalize_transcript_text():
    raw = "The  minister   announced   a “new policy”\n\nfor 2026.  "
    clean = normalize_transcript_text(raw)
    assert clean == 'The minister announced a "new policy" for 2026.'


def test_detect_language_and_codeswitching():
    # English
    lang, cs = detect_language_and_codeswitching("The GDP growth forecast was updated by the reserve bank.")
    assert lang == "en"
    assert cs is False

    # Devanagari Hindi
    lang_hi, _ = detect_language_and_codeswitching("भारत सरकार ने नई स्वास्थ्य नीति की घोषणा की है।")
    assert lang_hi == "hi"

    # Hinglish
    lang_hinglish, cs_hinglish = detect_language_and_codeswitching(
        "Sarkar ne aaj pradhan mantri yojana ke liye 5000 crore release kiya hai."
    )
    assert lang_hinglish == "hinglish"
    assert cs_hinglish is True


def test_extract_spoken_urls_and_quotes():
    transcript = (
        'The minister announced "All public hospitals will receive modern ICUs" during the press meet. '
        'For verified details, visit https://mohfw.gov.in/policies today.'
    )
    urls = extract_spoken_urls(transcript)
    assert len(urls) == 1
    assert urls[0] == "https://mohfw.gov.in/policies"

    quotes = extract_direct_quotes(transcript)
    assert len(quotes) >= 1
    assert "All public hospitals will receive modern ICUs" in [q["quote"] for q in quotes]


# 4. Claim Timestamp Correlation Tests
def test_claim_to_segment_correlation():
    segments = [
        TranscriptSegmentItem(start_time=0.0, end_time=4.5, text="Good morning everyone and welcome.", sequence=0),
        TranscriptSegmentItem(start_time=4.5, end_time=12.0, text="The Ministry of Health announced a 25% increase in healthcare subsidies.", sequence=1),
        TranscriptSegmentItem(start_time=12.0, end_time=18.0, text="Official details can be found on our website.", sequence=2),
    ]

    claim_text = "The Ministry of Health announced a 25% increase in healthcare subsidies."
    start_t, end_t, fmt_ts, seq = correlate_claim_with_segment(claim_text, segments)

    assert seq == 1
    assert start_t == 4.5
    assert end_t == 12.0
    assert fmt_ts == "00:04 - 00:12"


# 5. Media Verification Service Full Pipeline Test
def test_media_verification_service_full_pipeline(db_session):
    wav_bytes = create_minimal_wav(duration_seconds=3.0)

    # Injected test transcript with claim and source
    test_text = (
        "The Ministry of Finance allocated 10000 crore for rural electrification in 2026. "
        "The minister stated \"Every village will have 24-hour uninterrupted electricity.\""
    )
    test_segments = [
        TranscriptSegmentItem(start_time=0.0, end_time=4.0, text="The Ministry of Finance allocated 10000 crore for rural electrification in 2026.", sequence=0),
        TranscriptSegmentItem(start_time=4.0, end_time=8.0, text='The minister stated "Every village will have 24-hour uninterrupted electricity."', sequence=1),
    ]

    fallback_engine = FallbackTranscriptionEngine(
        simulated_text=test_text,
        simulated_segments=test_segments,
        simulated_confidence=0.92,
    )
    unified_engine = UnifiedTranscriptionEngine(engine=fallback_engine)
    service = MediaVerificationService(transcription_engine=unified_engine)

    result = service.verify_media(
        file_bytes=wav_bytes,
        original_filename="announcement.wav",
        db=db_session,
        perform_search=True,
        extract_evidence=True,
        finalize_verdicts=True,
        max_claims=2,
    )

    # Assertions
    assert result["status"] == "completed"
    assert result["request_id"] is not None
    assert result["media_verification_id"] is not None
    assert result["forensics"]["media_type"] == "audio"
    assert result["forensics"]["has_audio_track"] is True

    # Check Dual Confidence separation
    assert result["transcription"]["transcription_confidence"] == 92.0
    assert "High" in result["transcription"]["confidence_category"]

    # Check transcript segments and timestamps
    assert len(result["transcription"]["segments"]) == 2
    assert result["transcription"]["segments"][0]["formatted_timestamp"] == "00:00 - 00:04"

    # Check Claims with timestamp badges
    assert len(result["claims"]) >= 1
    assert result["claims"][0]["formatted_timestamp"] is not None

    # Check Evidence and Verdicts
    assert result["verdicts"] is not None
    assert result["verdicts"]["overall_verdict"] in [
        "SUPPORTED", "CONTRADICTED", "MISLEADING", "UNVERIFIED", "INSUFFICIENT_EVIDENCE", "MIXED"
    ]

    # Check Non-accusatory technical indicators
    assert "disclaimer" in result["forensics"]["technical_indicators"]
    assert "authenticity_disclaimer" in result


# 6. API Endpoints Tests
def test_api_verify_media_endpoint(db_session):
    client = TestClient(app)
    wav_bytes = create_minimal_wav(duration_seconds=2.0)

    response = client.post(
        "/api/verify/media",
        files={"file": ("test_speech.wav", wav_bytes, "audio/wav")},
        data={"perform_search": "true", "finalize_verdicts": "true", "max_claims": "2"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "forensics" in data
    assert "transcription" in data
    assert "claims" in data
    assert "verdicts" in data


def test_api_verify_audio_endpoint(db_session):
    client = TestClient(app)
    wav_bytes = create_minimal_wav(duration_seconds=1.5)

    response = client.post(
        "/api/verify/audio",
        files={"file": ("interview.wav", wav_bytes, "audio/wav")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["forensics"]["media_type"] == "audio"


def test_api_verify_video_endpoint(db_session):
    client = TestClient(app)
    mp4_bytes = create_minimal_mp4()

    response = client.post(
        "/api/verify/video",
        files={"file": ("clip.mp4", mp4_bytes, "video/mp4")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["forensics"]["media_type"] == "video"


def test_api_verify_media_security_rejection():
    client = TestClient(app)
    # Executable byte pattern masquerading as MP3
    fake_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"

    response = client.post(
        "/api/verify/media",
        files={"file": ("malicious.mp3", fake_bytes, "audio/mpeg")},
    )
    assert response.status_code == 400
    assert "Security rejection" in response.json()["detail"]
