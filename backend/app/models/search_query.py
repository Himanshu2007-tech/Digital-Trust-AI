from typing import Optional, Any, Dict
from sqlalchemy import String, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class SearchQuery(Base, TimestampMixin):
    """Audit record of search queries executed during evidence gathering."""
    __tablename__ = "search_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    search_engine: Mapped[str] = mapped_column(String(50), default="serp", nullable=False)
    results_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_response_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="search_queries")
