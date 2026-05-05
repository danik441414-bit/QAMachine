from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Run(Base):
    """One Machine execution — corresponds to one user task message."""
    __tablename__ = "runs"

    id:            Mapped[str]          = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id:       Mapped[str]          = mapped_column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id:       Mapped[str]          = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_url:    Mapped[str]          = mapped_column(String(2048), nullable=False)
    task:          Mapped[str]          = mapped_column(Text, nullable=False)
    status:        Mapped[str]          = mapped_column(String(32), default="queued", nullable=False, index=True)
    mode:          Mapped[str | None]   = mapped_column(String(64), nullable=True)
    step_count:    Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    max_steps:     Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    issue_count:   Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    summary:       Mapped[str | None]   = mapped_column(Text, nullable=True)
    report_path:   Mapped[str | None]   = mapped_column(String(1024), nullable=True)
    error_message: Mapped[str | None]   = mapped_column(Text, nullable=True)
    artifacts:     Mapped[list | None]  = mapped_column(JSON, default=list, nullable=False)
    created_at:    Mapped[datetime]     = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    started_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    message: Mapped["Message | None"] = relationship(
        "Message", back_populates="run",
        foreign_keys="Message.run_id",
        uselist=False,
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id:                   Mapped[str]          = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id:              Mapped[str]          = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan:                 Mapped[str]          = mapped_column(String(32), default="free", nullable=False)
    status:               Mapped[str]          = mapped_column(String(32), default="active", nullable=False)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_customer_id:   Mapped[str | None]   = mapped_column(String(255), nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool]         = mapped_column(default=False, nullable=False)
    created_at:           Mapped[datetime]     = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="subscription")
