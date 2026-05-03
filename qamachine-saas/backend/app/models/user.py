from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id:             Mapped[str]            = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email:          Mapped[str]            = mapped_column(String(255), unique=True, nullable=False, index=True)
    name:           Mapped[str | None]     = mapped_column(String(255), nullable=True)
    hashed_password:Mapped[str]            = mapped_column(String(255), nullable=False)
    avatar_url:     Mapped[str | None]     = mapped_column(String(512), nullable=True)
    plan:            Mapped[str]            = mapped_column(String(32), default="free", nullable=False)
    usage_credits:   Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    tutor_credits:   Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    is_active:       Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)

    # Email verification — new users start unverified; existing rows default TRUE via migration
    email_verified:       Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    email_verify_token:   Mapped[str | None]   = mapped_column(String(64), nullable=True, index=True)
    email_verify_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # OAuth
    google_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True, unique=True)

    # Password reset
    reset_password_token:   Mapped[str | None]      = mapped_column(String(64), nullable=True, index=True)
    reset_password_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Magic link (passwordless email login)
    magic_token:         Mapped[str | None]      = mapped_column(String(64), nullable=True, index=True)
    magic_token_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:     Mapped[datetime]       = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at:     Mapped[datetime]       = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    chats:        Mapped[list["Chat"]]        = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    subscription: Mapped["Subscription | None"] = relationship("Subscription", back_populates="user", uselist=False)

    @property
    def usage_cap(self) -> int:
        from app.core.config import settings
        caps = {
            "free":       settings.FREE_RUNS_CAP,
            "pro":        settings.PRO_RUNS_CAP,
            "team":       settings.TEAM_RUNS_CAP,
            "enterprise": 9999,
        }
        return caps.get(self.plan, settings.FREE_RUNS_CAP)

    @property
    def chat_cap(self) -> int:
        from app.core.config import settings
        if self.plan == "free":
            return settings.FREE_CHATS_CAP
        return 9999

    @property
    def tutor_cap(self) -> int:
        from app.core.config import settings
        if self.plan == "free":
            return settings.FREE_TUTOR_CAP
        return 9999

    @property
    def is_free(self) -> bool:
        return self.plan == "free"
