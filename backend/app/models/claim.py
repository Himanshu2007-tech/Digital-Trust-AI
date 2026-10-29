from typing import Optional, List
from sqlalchemy import String, Text, Float, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class Claim(Base, TimestampMixin):
    """
    Individual claim extracted from a verification request.
    Enables claim-level verification decomposition.
    """
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("verification_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    claim_type: Mapped[str] = mapped_column(String(50), default="FACTUAL", nullable=False)
    verifiability: Mapped[str] = mapped_column(String(50), default="VERIFIABLE", nullable=False)
    importance: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    
    # Structured entities and extracted context
    entities: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    dates: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    locations: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    numbers: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    source_attributions: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    original_sentence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    speaker_or_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    claim_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Method by which this claim was obtained (e.g. rule_based, llm, hybrid)
    extraction_method: Mapped[str] = mapped_column(String(50), default="rule_based", nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Status: extracted, searching, verified, inconclusive
    status: Mapped[str] = mapped_column(String(50), default="extracted", nullable=False)

    # Relationships
    request: Mapped["VerificationRequest"] = relationship("VerificationRequest", back_populates="claims")
    evidence: Mapped[List["Evidence"]] = relationship("Evidence", back_populates="claim", cascade="all, delete-orphan")
    source_comparisons: Mapped[List["SourceComparison"]] = relationship("SourceComparison", back_populates="claim", cascade="all, delete-orphan")
    search_queries: Mapped[List["SearchQuery"]] = relationship("SearchQuery", back_populates="claim", cascade="all, delete-orphan")
    sources: Mapped[List["Source"]] = relationship("Source", secondary="claim_sources", back_populates="claims")
    verification_result: Mapped[Optional["VerificationResult"]] = relationship("VerificationResult", back_populates="claim", uselist=False, cascade="all, delete-orphan", foreign_keys="VerificationResult.claim_id")
    occurrences: Mapped[List["ClaimOccurrence"]] = relationship("ClaimOccurrence", back_populates="claim", cascade="all, delete-orphan")

