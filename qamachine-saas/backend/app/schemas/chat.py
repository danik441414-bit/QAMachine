from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator


class ChatOut(BaseModel):
    id:           str
    user_id:      str
    title:        str
    status:       str
    run_count:    int
    last_message: str | None
    created_at:   datetime
    updated_at:   datetime

    model_config = {"from_attributes": True}


class ChatCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=255)


class ChatUpdate(BaseModel):
    title: str = Field(max_length=255)


class MessageOut(BaseModel):
    id:         str
    chat_id:    str
    role:       str
    content:    str
    run_id:     str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    target_url: str = Field(default="", max_length=2048)
    task:       str = Field(min_length=1, max_length=4000)

    @field_validator("target_url")
    @classmethod
    def validate_target_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return v
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        return v


class PaginatedChats(BaseModel):
    items:     list[ChatOut]
    total:     int
    page:      int
    page_size: int
    has_more:  bool
