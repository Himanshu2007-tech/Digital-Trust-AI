from typing import Optional, List
from sqlalchemy import String, BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class MediaFile(Base, TimestampMixin):
    """Storage tracking for multimedia uploaded for verification (images, audio, video)."""
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(50), default="local", nullable=False)

    # Relationships
    verification_requests: Mapped[List["VerificationRequest"]] = relationship(
        "VerificationRequest", back_populates="media_file"
    )
