from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    """Exported investigation report document (PDF, HTML, JSON)."""
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    report_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("verification_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # Format: pdf, json, html
    format: Mapped[str] = mapped_column(String(20), default="pdf", nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf", nullable=False)
    sha256_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Status: pending, generated, failed
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generation_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    request: Mapped["VerificationRequest"] = relationship("VerificationRequest", back_populates="reports")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="reports")

