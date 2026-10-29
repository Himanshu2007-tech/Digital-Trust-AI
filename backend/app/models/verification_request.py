from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Integer, ForeignKey, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class VerificationRequest(Base, TimestampMixin):
    """Core tracking entity for each user-submitted verification task."""
    __tablename__ = "verification_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Type: text, url, image, audio, video
    request_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Raw input content (e.g. claim text, article text, or target URL)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Cryptographic SHA-256 fingerprint of input for duplicate detection
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    # Associated media file if request is image, audio, or video
    media_file_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("media_files.id", ondelete="SET NULL"), nullable=True)
    
    # Status: created, processing, completed, partial, failed
    status: Mapped[str] = mapped_column(String(50), default="created", nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Lifecycle completion timestamp
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Soft archival flag (archived records excluded from default history view)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Re-verification lineage: child request points to parent original request
    parent_request_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("verification_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Error diagnostics if pipeline failed or had partial errors
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="verification_requests")
    media_file: Mapped[Optional["MediaFile"]] = relationship("MediaFile", back_populates="verification_requests")
    claims: Mapped[List["Claim"]] = relationship("Claim", back_populates="request", cascade="all, delete-orphan")
    verification_results: Mapped[List["VerificationResult"]] = relationship("VerificationResult", back_populates="request", cascade="all, delete-orphan", foreign_keys="VerificationResult.request_id")
    verification_result: Mapped[Optional["VerificationResult"]] = relationship("VerificationResult", primaryjoin="and_(VerificationRequest.id==VerificationResult.request_id, VerificationResult.claim_id.is_(None))", uselist=False, viewonly=True)
    reports: Mapped[List["Report"]] = relationship("Report", back_populates="request", cascade="all, delete-orphan")
    article: Mapped[Optional["Article"]] = relationship("Article", back_populates="request", uselist=False, cascade="all, delete-orphan")
    image_verification: Mapped[Optional["ImageVerification"]] = relationship("ImageVerification", back_populates="request", uselist=False, cascade="all, delete-orphan")
    media_verification: Mapped[Optional["MediaVerification"]] = relationship("MediaVerification", back_populates="request", uselist=False, cascade="all, delete-orphan")
    events: Mapped[List["VerificationEvent"]] = relationship(
        "VerificationEvent",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="VerificationEvent.created_at.asc()"
    )
    parent_request: Mapped[Optional["VerificationRequest"]] = relationship(
        "VerificationRequest",
        remote_side=[id],
        backref="child_requests"
    )

    __table_args__ = (
        Index("ix_verification_requests_created_at", "created_at"),
        Index("ix_verification_requests_type_status", "request_type", "status"),
    )
