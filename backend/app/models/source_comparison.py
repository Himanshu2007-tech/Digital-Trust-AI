from typing import Optional
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class SourceComparison(Base, TimestampMixin):
    """Synthesis and pairwise analysis comparing sources, independence, and stance consensus."""
    __tablename__ = "source_comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Optional pairwise source references
    source_a_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True, index=True)
    source_b_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Comparison category: PAIRWISE, GROUP_SYNTHESIS
    comparison_type: Mapped[str] = mapped_column(String(50), default="PAIRWISE", nullable=False)
    
    # Source independence: INDEPENDENT, POSSIBLY_SYNDICATED, DUPLICATE, UNKNOWN
    source_relationship: Mapped[str] = mapped_column(String(50), default="UNKNOWN", nullable=False)
    
    # Consistency: CONSISTENT_EVIDENCE, CONFLICTING_INFORMATION, COMPLEMENTARY, INSUFFICIENT
    evidence_consistency: Mapped[str] = mapped_column(String(50), default="CONSISTENT_EVIDENCE", nullable=False)
    
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Stance counts across sources
    supporting_sources_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    contradicting_sources_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    neutral_sources_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Stance consensus descriptor (evaluated/disputed/consistent/insufficient - NOT final truth verdict)
    consensus_verdict: Mapped[str] = mapped_column(String(50), default="ANALYZED", nullable=False)
    analysis_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="source_comparisons")
    source_a: Mapped[Optional["Source"]] = relationship("Source", foreign_keys=[source_a_id])
    source_b: Mapped[Optional["Source"]] = relationship("Source", foreign_keys=[source_b_id])

