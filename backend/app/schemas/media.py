from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.schemas.verify import ExtractedClaimSchema
from app.schemas.search import DiscoveredSourceSchema, SearchQueryAuditSchema
from app.schemas.evidence import EvidenceItemSchema, SourceComparisonSchema
from app.schemas.verdict import RequestVerdictResponse


class TranscriptSegmentSchema(BaseModel):
    """Timestamped speech segment with confidence and seek target."""
    id: Optional[int] = Field(default=None, description="Segment record ID")
    sequence: int = Field(default=0, description="Sequential ordering")
    start_time: float = Field(..., description="Start timestamp in seconds")
    end_time: float = Field(..., description="End timestamp in seconds")
    formatted_timestamp: str = Field(..., description="Human-readable timestamp range, e.g. 00:15 - 00:28")
    text: str = Field(..., description="Spoken transcript text for this segment")
    confidence: Optional[float] = Field(default=None, description="Acoustic/transcription confidence (0.0 - 1.0 or 0-100)")


class VideoFrameSchema(BaseModel):
    """Extracted key video frame with timestamp, hash, and OCR observations."""
    id: Optional[int] = Field(default=None, description="Frame record ID")
    frame_number: int = Field(default=0, description="Sequential frame index")
    timestamp: float = Field(..., description="Timestamp in seconds")
    formatted_timestamp: str = Field(..., description="Timestamp label, e.g. 00:15")
    selection_method: str = Field(default="FIXED_INTERVAL", description="Selection reason: FIXED_INTERVAL, SCENE_CHANGE, HIGH_TEXT_DENSITY")
    image_hash: str = Field(..., description="Cryptographic SHA-256 fingerprint")
    stored_path: Optional[str] = Field(default=None, description="Local stored keyframe image path")
    width: int = Field(default=0, description="Frame width")
    height: int = Field(default=0, description="Frame height")
    ocr_text: Optional[str] = Field(default=None, description="On-screen recognized text")
    ocr_confidence: Optional[float] = Field(default=None, description="OCR text recognition confidence (0-100)")
    ocr_blocks: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Word bounding boxes")
    visual_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Observations: document, chart, logo, person")


class ClaimOccurrenceSchema(BaseModel):
    """Multimodal occurrence tracking where and when a claim appears in audio or video."""
    id: Optional[int] = Field(default=None)
    claim_id: Optional[int] = Field(default=None)
    source_type: str = Field(..., description="AUDIO_TRANSCRIPT or VISUAL_OCR")
    timestamp_start: float = Field(default=0.0)
    timestamp_end: float = Field(default=0.0)
    formatted_timestamp: Optional[str] = Field(default=None)
    frame_id: Optional[int] = Field(default=None)
    frame_number: Optional[int] = Field(default=None)
    transcript_segment_id: Optional[int] = Field(default=None)
    text: str = Field(...)
    confidence: Optional[float] = Field(default=None)


class TimelineEventSchema(BaseModel):
    """Chronological event across speech, keyframes, visible graphics, and claims."""
    timestamp: float = Field(...)
    timestamp_end: Optional[float] = Field(default=None)
    formatted_timestamp: str = Field(...)
    event_type: str = Field(..., description="AUDIO_SPEECH, KEYFRAME_SCENE, VISUAL_TEXT, VERIFIABLE_CLAIM")
    label: str = Field(...)
    description: str = Field(...)
    confidence: Optional[float] = Field(default=None)
    frame_id: Optional[int] = Field(default=None)
    claim_id: Optional[int] = Field(default=None)
    badge_color: Optional[str] = Field(default="slate")


class AudioVisualAlignmentSchema(BaseModel):
    """Thematic alignment and context discrepancy report."""
    summary_status: str = Field(...)
    summary_note: str = Field(...)
    alignments_count: int = Field(default=0)
    mismatches_count: int = Field(default=0)
    alignments: List[Dict[str, Any]] = Field(default_factory=list)
    mismatches: List[Dict[str, Any]] = Field(default_factory=list)
    disclaimer: str = Field(...)


class ReusedFootageReportSchema(BaseModel):
    """Internal database duplicate frame match report."""
    reused_footage_detected: bool = Field(default=False)
    matching_frames_count: int = Field(default=0)
    matched_prior_requests: List[Dict[str, Any]] = Field(default_factory=list)
    source_origin_note: str = Field(default="Source origin could not be established.")
    reverse_image_search_status: str = Field(default="External reverse image search is not available in this analysis.")
    disclaimer: str = Field(...)


class MediaForensicDetailsSchema(BaseModel):
    """Technical container, stream inspection, and security details."""
    media_type: str = Field(..., description="'audio' or 'video'")
    duration_seconds: float = Field(..., description="Total duration in seconds")
    file_size_bytes: int = Field(..., description="Size in bytes")
    file_hash_sha256: str = Field(..., description="Cryptographic SHA-256 fingerprint")
    original_filename: str = Field(..., description="Client upload filename")
    stored_filename: str = Field(..., description="Internal storage identifier")
    mime_type: str = Field(..., description="MIME container type")
    width: Optional[int] = Field(default=None, description="Frame width for video")
    height: Optional[int] = Field(default=None, description="Frame height for video")
    video_codec: Optional[str] = Field(default=None, description="Video codec name")
    audio_codec: Optional[str] = Field(default=None, description="Audio codec name")
    sample_rate: Optional[int] = Field(default=None, description="Audio sample rate (Hz)")
    channels: Optional[int] = Field(default=None, description="Audio channels count")
    bitrate: Optional[int] = Field(default=None, description="Bitrate (bps)")
    has_audio_track: bool = Field(default=True, description="Whether audio stream is present")
    technical_indicators: Dict[str, Any] = Field(
        default_factory=dict,
        description="Non-accusatory stream inspection observations"
    )


class TranscriptionSummarySchema(BaseModel):
    """Complete speech transcription output with dual confidence metrics."""
    raw_transcript: str = Field(..., description="Raw text exactly as transcribed")
    normalized_transcript: str = Field(..., description="Cleaned, normalized text used for claim extraction")
    language: str = Field(default="en", description="Detected language code (e.g. en, hi)")
    is_code_switched: bool = Field(default=False, description="Whether Hinglish/code-switching was detected")
    transcription_confidence: float = Field(
        ...,
        description="Speech recognition clarity score (0-100). Strictly separate from evidence confidence."
    )
    confidence_category: str = Field(default="High", description="High, Moderate, or Low acoustic clarity")
    low_confidence_warning: bool = Field(
        default=False,
        description="True if acoustic transcription confidence is low (< 60)"
    )
    word_count: int = Field(default=0, description="Total transcribed words")
    duration_seconds: float = Field(default=0.0, description="Transcribed audio length")
    segments: List[TranscriptSegmentSchema] = Field(
        default_factory=list,
        description="Timestamped speech segments"
    )
    detected_urls: List[str] = Field(
        default_factory=list,
        description="Web URLs spoken or mentioned in the transcript"
    )
    detected_quotes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Direct quotes spoken in the audio"
    )


class MediaExtractedClaimSchema(ExtractedClaimSchema):
    """Extracted claim with media timestamp segment traceability and multimodal occurrences."""
    start_time: Optional[float] = Field(default=None, description="Segment start timestamp in seconds")
    end_time: Optional[float] = Field(default=None, description="Segment end timestamp in seconds")
    formatted_timestamp: Optional[str] = Field(default=None, description="Human readable timestamp, e.g. 00:04 - 00:12")
    segment_sequence: Optional[int] = Field(default=None, description="Originating transcript segment index")
    primary_origin: Optional[str] = Field(default="AUDIO_TRANSCRIPT", description="AUDIO_TRANSCRIPT, VISUAL_OCR, or MULTIMODAL")
    occurrences: List[ClaimOccurrenceSchema] = Field(default_factory=list, description="All audio and visual appearances of this claim")


class MediaVerificationResponse(BaseModel):
    """Comprehensive audio/video factual verification dossier with Part 10 multimedia analysis."""
    request_id: int = Field(..., description="Verification request ID")
    media_file_id: Optional[int] = Field(default=None, description="MediaFile record ID")
    media_verification_id: Optional[int] = Field(default=None, description="MediaVerification record ID")
    status: str = Field(..., description="Pipeline execution status: completed, partial, or failed")

    # Forensics & Transcription
    forensics: MediaForensicDetailsSchema = Field(..., description="Technical container & stream forensics")
    transcription: TranscriptionSummarySchema = Field(..., description="Speech transcription & timestamped segments")

    # Part 10 Multimedia Analysis Additions
    frames: List[VideoFrameSchema] = Field(default_factory=list, description="Extracted video keyframes with OCR")
    timeline: List[TimelineEventSchema] = Field(default_factory=list, description="Unified chronological media timeline")
    alignment: Optional[AudioVisualAlignmentSchema] = Field(default=None, description="Audio-visual thematic alignment")
    reused_footage: Optional[ReusedFootageReportSchema] = Field(default=None, description="Internal database duplicate footage report")
    forensic_observations: Optional[Dict[str, Any]] = Field(default=None, description="Technical observations & AI/deepfake disclosures")
    frames_count: int = Field(default=0, description="Total sampled keyframes analyzed")

    # Verification Layers (Parts 3 - 6)
    claims: List[MediaExtractedClaimSchema] = Field(
        default_factory=list,
        description="Verifiable claims extracted from spoken transcript and on-screen graphics"
    )
    queries: List[SearchQueryAuditSchema] = Field(
        default_factory=list,
        description="Part 4 executed search queries audit trail"
    )
    sources: List[DiscoveredSourceSchema] = Field(
        default_factory=list,
        description="Web sources discovered for corroboration"
    )
    evidence: List[EvidenceItemSchema] = Field(
        default_factory=list,
        description="Traceable evidence items extracted from sources"
    )
    comparisons: List[SourceComparisonSchema] = Field(
        default_factory=list,
        description="Cross-source consistency comparisons"
    )
    verdicts: Optional[RequestVerdictResponse] = Field(
        default=None,
        description="Overall dossier and per-claim verdicts"
    )

    claims_count: int = Field(default=0)
    sources_count: int = Field(default=0)
    evidence_count: int = Field(default=0)

    # Core journalistic disclosure
    authenticity_disclaimer: str = Field(
        default=(
            "TruthLens AI verifies the factual claims spoken within audio or video recordings against authoritative "
            "web sources. High evidence credibility indicates verified factual reporting, but does not certify "
            "that the audio or video file itself is digitally authentic, unedited, or free from synthetic generation."
        ),
        description="Clear boundary distinguishing claim factual truth from media digital authenticity"
    )
