from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class Evidence(Base, TimestampMixin):
    """Specific evidence item extracted from a source to support or refute a claim."""
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Evidence stance: SUPPORTING, CONTRADICTING, CONTEXTUAL, INSUFFICIENT
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(50), default="CONTEXTUAL", nullable=False)
    
    # Traceable evidence passage actually present in the source
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Legacy snippet field preserved for backwards compatibility
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    article_title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    publish_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relevance (HIGH, MEDIUM, LOW) and normalized relevance score (0.0 to 1.0)
    relevance: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Confidence in extraction process (NOT final truth score)
    confidence_in_extraction: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    stance_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    extraction_method: Mapped[str] = mapped_column(String(50), default="rule_based", nullable=False)
    extracted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="evidence")
    source: Mapped[Optional["Source"]] = relationship("Source", back_populates="evidence_items")

