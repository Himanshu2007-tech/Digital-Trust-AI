from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class Article(Base, TimestampMixin):
    """Article content and metadata extracted from user-submitted news URLs."""
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("verification_requests.id", ondelete="CASCADE"), nullable=False, index=True)

    original_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_at: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    featured_image_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    article_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_length: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    extraction_method: Mapped[str] = mapped_column(String(50), default="readability_bs4", nullable=False)
    retrieval_status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    request: Mapped["VerificationRequest"] = relationship("VerificationRequest", back_populates="article")
