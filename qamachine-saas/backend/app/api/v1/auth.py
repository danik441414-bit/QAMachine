from __future__ import annotations

import asyncio
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user_id
from app.models.user import User
from app.schemas.user import Token, UserOut, UserRegister

router = APIRouter()


# ── Login ──────────────────────────────────────────────────────────────────────

@router.post("/token", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form.username.lower()))
    user = result.scalar_one_or_none()

    if not user or user.hashed_password.startswith("oauth:") or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    if settings.EMAIL_VERIFICATION_REQUIRED and not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="EMAIL_NOT_VERIFIED",
        )

    return Token(access_token=create_access_token(subject=user.id))


# ── Register ───────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body:       UserRegister,
    background: BackgroundTasks,
    db:         AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    token   = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)

    user = User(
        email=body.email.lower(),
        name=body.name.strip(),
        hashed_password=hash_password(body.password),
        email_verified=not settings.EMAIL_VERIFICATION_REQUIRED,
        email_verify_token=token if settings.EMAIL_VERIFICATION_REQUIRED else None,
        email_verify_expires=expires if settings.EMAIL_VERIFICATION_REQUIRED else None,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    if settings.EMAIL_VERIFICATION_REQUIRED:
        from app.services.email import send_verification_email
        background.add_task(send_verification_email, user.email, token)

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "email_verified": user.email_verified,
        "verification_required": settings.EMAIL_VERIFICATION_REQUIRED,
    }


# ── Verify email ───────────────────────────────────────────────────────────────

@router.get("/verify-email")
async def verify_email(
    token: str,
    db:    AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email_verify_token == token))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    if user.email_verify_expires and user.email_verify_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification link expired. Request a new one.")

    user.email_verified       = True
    user.email_verify_token   = None
    user.email_verify_expires = None
    await db.flush()

    return {"ok": True, "message": "Email verified. You can now log in."}


# ── Resend verification email ─────────────────────────────────────────────────

@router.post("/resend-verification")
async def resend_verification(
    body:       dict,
    background: BackgroundTasks,
    db:         AsyncSession = Depends(get_db),
):
    email = (body.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Always return 200 to avoid email enumeration
    if user and not user.email_verified:
        token   = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=24)
        user.email_verify_token   = token
        user.email_verify_expires = expires
        await db.flush()

        from app.services.email import send_verification_email
        background.add_task(send_verification_email, user.email, token)

    return {"ok": True, "message": "If this email exists and is unverified, a new link was sent."}


# ── Me ─────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
async def me(
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── Forgot password ────────────────────────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(
    body:       dict,
    background: BackgroundTasks,
    db:         AsyncSession = Depends(get_db),
):
    email = (body.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        token   = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        user.reset_password_token   = token
        user.reset_password_expires = expires
        await db.flush()

        from app.services.email import send_reset_password_email
        background.add_task(send_reset_password_email, user.email, token)

    # Always 200 to avoid email enumeration
    return {"ok": True, "message": "If this email exists, a reset link was sent."}


# ── Reset password ─────────────────────────────────────────────────────────────

@router.post("/reset-password")
async def reset_password(body: dict, db: AsyncSession = Depends(get_db)):
    token    = (body.get("token") or "").strip()
    password = (body.get("password") or "").strip()

    if not token or not password:
        raise HTTPException(status_code=400, detail="Token and password are required")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    result = await db.execute(select(User).where(User.reset_password_token == token))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    if user.reset_password_expires and user.reset_password_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset link expired. Request a new one.")

    user.hashed_password        = hash_password(password)
    user.reset_password_token   = None
    user.reset_password_expires = None
    await db.flush()

    return {"ok": True, "message": "Password updated. You can now log in."}


# ── Google OAuth ───────────────────────────────────────────────────────────────

@router.post("/google", response_model=Token)
async def google_login(
    body: dict,
    db:   AsyncSession = Depends(get_db),
):
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests

    credential = (body.get("credential") or "").strip()
    if not credential:
        raise HTTPException(400, "Google credential is required")

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(501, "Google login is not configured on this server")

    try:
        # verify_oauth2_token makes a synchronous HTTP call to fetch Google's public keys
        loop = asyncio.get_event_loop()
        idinfo = await loop.run_in_executor(
            None,
            lambda: google_id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            ),
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_id = idinfo.get("sub", "")
    email     = idinfo.get("email", "").lower().strip()
    name      = idinfo.get("name") or email.split("@")[0]
    picture   = idinfo.get("picture") or None

    if not email or not google_id:
        raise HTTPException(400, "Google account is missing email or ID")

    # Find existing user by google_id OR email (link accounts)
    result = await db.execute(
        select(User).where(or_(User.google_id == google_id, User.email == email))
    )
    user = result.scalar_one_or_none()

    if user:
        changed = False
        if not user.google_id:
            user.google_id = google_id
            changed = True
        if picture and not user.avatar_url:
            user.avatar_url = picture
            changed = True
        if changed:
            await db.flush()
    else:
        user = User(
            email=email,
            name=name,
            google_id=google_id,
            hashed_password="oauth:google",  # placeholder — not a valid bcrypt hash
            avatar_url=picture,
            email_verified=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    return Token(access_token=create_access_token(subject=user.id))


# ── Magic link (passwordless email login) ─────────────────────────────────────

@router.post("/magic-link")
async def request_magic_link(
    body:       dict,
    background: BackgroundTasks,
    db:         AsyncSession = Depends(get_db),
):
    email = (body.get("email") or "").lower().strip()
    if not email or "@" not in email:
        raise HTTPException(400, "Valid email is required")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    token   = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)

    if user:
        user.magic_token         = token
        user.magic_token_expires = expires
        await db.flush()
    else:
        # Auto-create account — no password, email auto-verified via magic link
        user = User(
            email=email,
            name=email.split("@")[0],
            hashed_password="oauth:magic",
            email_verified=True,
            magic_token=token,
            magic_token_expires=expires,
        )
        db.add(user)
        await db.flush()

    from app.services.email import send_magic_link_email
    background.add_task(send_magic_link_email, email, token)

    return {"ok": True, "message": "Login link sent. Check your email."}


@router.get("/magic-link/verify", response_model=Token)
async def verify_magic_link(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.magic_token == token))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(400, "Invalid or expired link")

    if user.magic_token_expires and user.magic_token_expires < datetime.now(timezone.utc):
        raise HTTPException(400, "Link expired (15 min). Request a new one.")

    user.magic_token         = None
    user.magic_token_expires = None
    user.email_verified      = True
    await db.flush()

    if not user.is_active:
        raise HTTPException(403, "Account disabled")

    return Token(access_token=create_access_token(subject=user.id))
