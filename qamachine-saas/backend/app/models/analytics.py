from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PageView(Base):
    __tablename__ = "page_views"

    id:         Mapped[str]      = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    path:       Mapped[str]      = mapped_column(String(512), nullable=False, index=True)
    ip:         Mapped[str|None] = mapped_column(String(64),  nullable=True)
    user_agent: Mapped[str|None] = mapped_column(Text,        nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


class Payment(Base):
    """Stripe payment history — populated by webhook handler."""
    __tablename__ = "payments"

    id:                Mapped[str]      = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id:           Mapped[str]      = mapped_column(String, nullable=False, index=True)
    amount_cents:      Mapped[int]      = mapped_column(Integer, default=0, nullable=False)
    currency:          Mapped[str]      = mapped_column(String(8), default="usd", nullable=False)
    plan:              Mapped[str]      = mapped_column(String(32), nullable=False)
    stripe_payment_id: Mapped[str|None] = mapped_column(String(255), nullable=True, unique=True)
    created_at:        Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
