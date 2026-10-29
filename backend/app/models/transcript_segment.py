from typing import Optional
from sqlalchemy import Text, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class TranscriptSegment(Base, TimestampMixin):
    """
    Timestamped atomic segment of speech transcribed from an audio or video file.
    Enables claim-to-timestamp traceability (e.g., 00:15 - 00:28).
    """
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    media_verification_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("media_verifications.id", ondelete="CASCADE"), nullable=False, index=True
    )

    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    media_verification: Mapped["MediaVerification"] = relationship("MediaVerification", back_populates="segments")
