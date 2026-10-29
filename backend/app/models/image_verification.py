from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class ImageVerification(Base, TimestampMixin):
    """
    Image and screenshot verification record.
    Tracks OCR extraction results, recognized blocks, technical forensics,
    sanitized EXIF data, and detected URLs/entities.
    """
    __tablename__ = "image_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("verification_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_file_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("media_files.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Technical image properties
    image_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # OCR text representations (strict preservation of raw vs cleaned)
    raw_ocr_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_ocr_text: Mapped[str] = mapped_column(Text, nullable=False)

    # OCR extraction confidence (0.0 to 100.0) - kept strictly separate from verdict evidence confidence
    ocr_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Structured OCR blocks with bounding boxes: [{text, confidence, bbox: [x,y,w,h], block_num, ...}]
    ocr_blocks: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)

    # Context & detected artifacts
    detected_urls: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    detected_entities: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Technical metadata and sanitized EXIF (GPS and PII strictly removed)
    exif_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ocr_engine: Mapped[str] = mapped_column(String(50), default="tesseract", nullable=False)

    # Relationships
    request: Mapped["VerificationRequest"] = relationship("VerificationRequest", back_populates="image_verification")
    media_file: Mapped[Optional["MediaFile"]] = relationship("MediaFile")
