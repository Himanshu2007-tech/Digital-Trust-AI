from datetime import datetime, timezone
from typing import Optional, Any, Dict, List
from sqlalchemy import String, Text, Float, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class VerificationResult(Base, TimestampMixin):
    """Final explainable verification verdict produced for a claim or verification request."""
    __tablename__ = "verification_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("verification_requests.id", ondelete="CASCADE"), nullable=True, index=True)
    claim_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Verdict rating: SUPPORTED, CONTRADICTED, MISLEADING, UNVERIFIED, INSUFFICIENT_EVIDENCE, MIXED
    verdict: Mapped[str] = mapped_column(String(50), default="UNVERIFIED", nullable=False, index=True)
    overall_verdict: Mapped[str] = mapped_column(String(50), default="UNVERIFIED", nullable=False, index=True)
    
    # Evidence confidence (0.0 to 1.0) - measures evidence strength, NOT truth probability
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    truth_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Human-readable justification and executive summary
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    
    # Traceable evidence citations
    supporting_evidence_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    contradicting_evidence_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    contextual_evidence_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    
    # Factual constraints and limitations
    limitations: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Detailed structured findings: e.g. claim breakdowns, source matrices
    key_findings_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    methodology_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    methodology_version: Mapped[str] = mapped_column(String(50), default="truthlens-v1.0", nullable=False)
    
    generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=True
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    request: Mapped[Optional["VerificationRequest"]] = relationship("VerificationRequest", back_populates="verification_results", foreign_keys=[request_id])
    claim: Mapped[Optional["Claim"]] = relationship("Claim", back_populates="verification_result", foreign_keys=[claim_id])

