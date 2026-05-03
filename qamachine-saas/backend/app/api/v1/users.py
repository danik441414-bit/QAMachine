from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id, hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate, PasswordChange

router = APIRouter()


@router.patch("/me", response_model=UserOut)
async def update_profile(
    body:    UserUpdate,
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    user = await _get_user(db, user_id)

    if body.name is not None:
        user.name = body.name.strip()

    if body.email is not None and body.email.lower() != user.email:
        # Check uniqueness
        existing = await db.execute(select(User).where(User.email == body.email.lower()))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already taken")
        user.email = body.email.lower()

    await db.flush()
    await db.refresh(user)
    return user


@router.post("/me/password")
async def change_password(
    body:    PasswordChange,
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    user = await _get_user(db, user_id)
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.hashed_password = hash_password(body.new_password)
    await db.flush()
    return {"ok": True}


async def _get_user(db: AsyncSession, user_id: str) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
