from typing import Optional
from sqlalchemy import String, Text, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class ClaimOccurrence(Base, TimestampMixin):
    """
    Multimodal traceability link tracking where and when a claim occurs
    across audio speech, visual on-screen text, or user descriptions.
    Prevents duplicate claims while retaining granular timestamps, frames, and segments.
    """
    __tablename__ = "claim_occurrences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_verification_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("media_verifications.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Origin source type: AUDIO_TRANSCRIPT, VISUAL_OCR, USER_DESCRIPTION
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    timestamp_start: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    timestamp_end: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Foreign key references to origin frame or transcript segment
    frame_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("video_frames.id", ondelete="SET NULL"), nullable=True, index=True
    )
    transcript_segment_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("transcript_segments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ocr_block_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="occurrences")
    media_verification: Mapped["MediaVerification"] = relationship("MediaVerification", back_populates="claim_occurrences")
    video_frame: Mapped[Optional["VideoFrame"]] = relationship("VideoFrame", back_populates="claim_occurrences")
    transcript_segment: Mapped[Optional["TranscriptSegment"]] = relationship("TranscriptSegment")
