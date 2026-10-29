from typing import Optional, List
from sqlalchemy import String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User account model for authentication and audit logging."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)  # admin, analyst, user
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    verification_requests: Mapped[List["VerificationRequest"]] = relationship(
        "VerificationRequest", back_populates="user", cascade="all, delete-orphan"
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report", back_populates="user"
    )
