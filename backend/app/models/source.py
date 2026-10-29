from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, ForeignKey, Table, Column, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

# Association table linking claims to discovered sources (many-to-many)
claim_sources = Table(
    "claim_sources",
    Base.metadata,
    Column("claim_id", Integer, ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True),
    Column("source_id", Integer, ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True),
)


class Source(Base, TimestampMixin):
    """External news/reference source catalog with discovery and credibility metadata."""
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1024), index=True, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    publication_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    query_used: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    syndication_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Source categorization: PRIMARY, RELIABLE_NEWS, FACT_CHECK, SECONDARY, SOCIAL_MEDIA, BLOG, UNKNOWN
    source_type: Mapped[str] = mapped_column(String(50), default="UNKNOWN", nullable=False)
    # Source role: INDEPENDENT_SOURCE, USER_SUBMITTED_ARTICLE (critical for non-self-corroboration)
    source_role: Mapped[str] = mapped_column(String(50), default="INDEPENDENT_SOURCE", nullable=False)

    # Future credibility and reliability ratings (None by default - no arbitrary scoring)
    credibility_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    reliability_tier: Mapped[str] = mapped_column(String(50), default="unrated", nullable=False)
    bias_rating: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    claims: Mapped[List["Claim"]] = relationship("Claim", secondary=claim_sources, back_populates="sources")
    evidence_items: Mapped[List["Evidence"]] = relationship("Evidence", back_populates="source")
