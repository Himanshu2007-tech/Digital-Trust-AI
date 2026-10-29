from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class VideoFrame(Base, TimestampMixin):
    """
    Extracted key video frame for visual information extraction and OCR analysis.
    Tracks frame timestamp, selection method (scene change / interval / high text),
    SHA-256 hash for duplicate detection, recognized on-screen text, and visual context observations.
    """
    __tablename__ = "video_frames"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    media_verification_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("media_verifications.id", ondelete="CASCADE"), nullable=False, index=True
    )

    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    frame_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Selection reason: FIXED_INTERVAL, SCENE_CHANGE, HIGH_TEXT_DENSITY, USER_SELECTED
    selection_method: Mapped[str] = mapped_column(String(50), default="FIXED_INTERVAL", nullable=False)

    # SHA-256 hash of frame image for duplicate detection and internal database matching
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stored_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # On-screen text and OCR metrics
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ocr_blocks: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)

    # Visual context observations (document/screenshot, person, logo, chart/numbers)
    visual_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    media_verification: Mapped["MediaVerification"] = relationship("MediaVerification", back_populates="frames")
    claim_occurrences: Mapped[List["ClaimOccurrence"]] = relationship(
        "ClaimOccurrence",
        back_populates="video_frame",
        cascade="all, delete-orphan"
    )
