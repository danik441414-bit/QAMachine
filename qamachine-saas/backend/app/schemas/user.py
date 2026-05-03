from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id:             str
    email:          EmailStr
    name:           str | None
    avatar_url:     str | None
    plan:           str
    usage_credits:  int
    usage_cap:      int
    created_at:     datetime

    model_config = {"from_attributes": True}


class UserRegister(BaseModel):
    email:    EmailStr
    name:     str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    name:  str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password:     str = Field(min_length=8)


class Token(BaseModel):
    access_token: str
    token_type:   str = "bearer"
