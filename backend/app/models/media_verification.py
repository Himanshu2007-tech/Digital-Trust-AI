from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Integer, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class MediaVerification(Base, TimestampMixin):
    """
    Audio and video verification record.
    Tracks media container properties, audio/video streams,
    transcription quality, timestamped speech, detected quotes/URLs,
    and technical authenticity indicators.
    """
    __tablename__ = "media_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("verification_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_file_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("media_files.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Media Type: "audio" or "video"
    media_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Video properties (nullable for audio)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Audio properties
    audio_codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sample_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    channels: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bitrate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_audio_track: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Cryptographic integrity fingerprint
    media_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Transcription & Language
    language: Mapped[Optional[str]] = mapped_column(String(20), default="en", nullable=True)
    raw_transcript: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_transcript: Mapped[str] = mapped_column(Text, nullable=False)

    # Transcription Recognition Confidence (0.0 to 1.0 or 0-100) - kept strictly separate from verdict evidence confidence
    transcription_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Context & Artifacts
    detected_urls: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    detected_quotes: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)

    # Technical Authenticity Indicators (NOT proof of manipulation)
    technical_indicators: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    request: Mapped["VerificationRequest"] = relationship("VerificationRequest", back_populates="media_verification")
    media_file: Mapped[Optional["MediaFile"]] = relationship("MediaFile")
    segments: Mapped[List["TranscriptSegment"]] = relationship(
        "TranscriptSegment",
        back_populates="media_verification",
        cascade="all, delete-orphan",
        order_by="TranscriptSegment.sequence"
    )
    frames: Mapped[List["VideoFrame"]] = relationship(
        "VideoFrame",
        back_populates="media_verification",
        cascade="all, delete-orphan",
        order_by="VideoFrame.timestamp"
    )
    claim_occurrences: Mapped[List["ClaimOccurrence"]] = relationship(
        "ClaimOccurrence",
        back_populates="media_verification",
        cascade="all, delete-orphan"
    )

