from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Chat(Base):
    __tablename__ = "chats"

    id:           Mapped[str]        = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id:      Mapped[str]        = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title:        Mapped[str]        = mapped_column(String(255), default="New Chat", nullable=False)
    status:       Mapped[str]        = mapped_column(String(32), default="idle", nullable=False)
    run_count:    Mapped[int]        = mapped_column(Integer, default=0, nullable=False)
    created_at:   Mapped[datetime]   = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at:   Mapped[datetime]   = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    user:     Mapped["User"]          = relationship("User", back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="chat",
        order_by="Message.created_at",
        cascade="all, delete-orphan",
    )

    @property
    def last_message(self) -> str | None:
        if self.messages:
            return self.messages[-1].content[:120]
        return None


class Message(Base):
    __tablename__ = "messages"

    id:         Mapped[str]       = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id:    Mapped[str]       = mapped_column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    role:       Mapped[str]       = mapped_column(String(16), nullable=False)   # "user" | "machine"
    content:    Mapped[str]       = mapped_column(Text, nullable=False)
    run_id:     Mapped[str | None]= mapped_column(String, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime]  = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
    run:  Mapped["Run | None"] = relationship("Run", back_populates="message", foreign_keys=[run_id])
