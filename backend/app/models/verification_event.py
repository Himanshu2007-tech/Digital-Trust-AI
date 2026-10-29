from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class VerificationEvent(Base):
    """
    Audit trail event recording genuine verification pipeline lifecycle milestones.
    Never fabricates historical events.
    """
    __tablename__ = "verification_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("verification_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationship back to parent request
    request: Mapped["VerificationRequest"] = relationship("VerificationRequest", back_populates="events")
