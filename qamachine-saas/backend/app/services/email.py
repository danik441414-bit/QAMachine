"""Email sending service — uses Resend HTTP API."""
from __future__ import annotations

import asyncio
import logging

import httpx

log = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_email(to: str, subject: str, html: str, text: str) -> None:
    from app.core.config import settings

    if not settings.RESEND_API_KEY:
        log.warning("[email] RESEND_API_KEY not set — skipping send to %s", to)
        log.info("[email] Subject: %s | Preview: %s", subject, text[:120])
        return

    payload = {
        "from": f"QAmachine <{settings.SMTP_FROM}>",
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(
                RESEND_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            )
            res.raise_for_status()
        log.info("[email] Sent '%s' to %s via Resend", subject, to)
    except Exception as exc:
        log.error("[email] Resend failed for %s: %s", to, exc)


# ── Templates ─────────────────────────────────────────────────────────────────

async def send_verification_email(to_email: str, token: str) -> None:
    from app.core.config import settings
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    html = f"""
<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;background:#0f0f0f;color:#e2e8f0;padding:40px 20px;margin:0">
  <div style="max-width:480px;margin:0 auto;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:16px;padding:40px">
    <div style="text-align:center;margin-bottom:32px">
      <div style="display:inline-flex;align-items:center;justify-content:center;
                  width:48px;height:48px;background:#7c3aed;border-radius:12px;margin-bottom:16px">
        <span style="color:white;font-size:24px">⚡</span>
      </div>
      <h1 style="margin:0;font-size:22px;font-weight:700;color:#f1f5f9">QAmachine</h1>
    </div>

    <h2 style="font-size:18px;font-weight:600;color:#f1f5f9;margin:0 0 8px">Confirm your email</h2>
    <p style="color:#94a3b8;font-size:14px;line-height:1.6;margin:0 0 28px">
      Thanks for signing up! Click the button below to verify your email address
      and start using QAmachine.
    </p>

    <a href="{link}"
       style="display:block;text-align:center;background:#7c3aed;color:white;
              text-decoration:none;font-weight:600;font-size:15px;
              padding:14px 24px;border-radius:10px;margin-bottom:24px">
      Verify email address
    </a>

    <p style="color:#64748b;font-size:12px;line-height:1.5;margin:0">
      This link expires in <strong style="color:#94a3b8">24 hours</strong>.
      If you didn't create an account, you can safely ignore this email.
    </p>

    <div style="border-top:1px solid #2a2a2a;margin-top:28px;padding-top:20px">
      <p style="color:#475569;font-size:11px;margin:0">
        Or copy this link:<br/>
        <a href="{link}" style="color:#7c3aed;word-break:break-all;font-size:11px">{link}</a>
      </p>
    </div>
  </div>
</body>
</html>
"""
    plain = (
        f"Welcome to QAmachine!\n\n"
        f"Verify your email by opening this link:\n{link}\n\n"
        f"Link expires in 24 hours."
    )
    await send_email(to_email, "Verify your QAmachine email", html, plain)


async def send_magic_link_email(to_email: str, token: str) -> None:
    from app.core.config import settings
    link = f"{settings.FRONTEND_URL}/magic-link?token={token}"

    html = f"""
<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;background:#0f0f0f;color:#e2e8f0;padding:40px 20px;margin:0">
  <div style="max-width:480px;margin:0 auto;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:16px;padding:40px">
    <div style="text-align:center;margin-bottom:32px">
      <div style="display:inline-flex;align-items:center;justify-content:center;
                  width:48px;height:48px;background:#7c3aed;border-radius:12px;margin-bottom:16px">
        <span style="color:white;font-size:24px">⚡</span>
      </div>
      <h1 style="margin:0;font-size:22px;font-weight:700;color:#f1f5f9">QAmachine</h1>
    </div>

    <h2 style="font-size:18px;font-weight:600;color:#f1f5f9;margin:0 0 8px">Your login link</h2>
    <p style="color:#94a3b8;font-size:14px;line-height:1.6;margin:0 0 28px">
      Click the button below to sign in instantly — no password needed.
      This link expires in <strong style="color:#f1f5f9">15 minutes</strong>.
    </p>

    <a href="{link}"
       style="display:block;text-align:center;background:#7c3aed;color:white;
              text-decoration:none;font-weight:600;font-size:15px;
              padding:14px 24px;border-radius:10px;margin-bottom:24px">
      Sign in to QAmachine
    </a>

    <p style="color:#64748b;font-size:12px;line-height:1.5;margin:0">
      If you didn't request this link, you can safely ignore this email.
    </p>

    <div style="border-top:1px solid #2a2a2a;margin-top:28px;padding-top:20px">
      <p style="color:#475569;font-size:11px;margin:0">
        Or copy this link:<br/>
        <a href="{link}" style="color:#7c3aed;word-break:break-all;font-size:11px">{link}</a>
      </p>
    </div>
  </div>
</body>
</html>
"""
    plain = f"Sign in to QAmachine:\n\n{link}\n\nThis link expires in 15 minutes."
    await send_email(to_email, "Your QAmachine login link", html, plain)


async def send_reset_password_email(to_email: str, token: str) -> None:
    from app.core.config import settings
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    html = f"""
<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;background:#0f0f0f;color:#e2e8f0;padding:40px 20px;margin:0">
  <div style="max-width:480px;margin:0 auto;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:16px;padding:40px">
    <div style="text-align:center;margin-bottom:32px">
      <div style="display:inline-flex;align-items:center;justify-content:center;
                  width:48px;height:48px;background:#7c3aed;border-radius:12px;margin-bottom:16px">
        <span style="color:white;font-size:24px">⚡</span>
      </div>
      <h1 style="margin:0;font-size:22px;font-weight:700;color:#f1f5f9">QAmachine</h1>
    </div>

    <h2 style="font-size:18px;font-weight:600;color:#f1f5f9;margin:0 0 8px">Reset your password</h2>
    <p style="color:#94a3b8;font-size:14px;line-height:1.6;margin:0 0 28px">
      Click the button below to set a new password. This link expires in <strong style="color:#f1f5f9">1 hour</strong>.
    </p>

    <a href="{link}"
       style="display:block;text-align:center;background:#7c3aed;color:white;
              text-decoration:none;font-weight:600;font-size:15px;
              padding:14px 24px;border-radius:10px;margin-bottom:24px">
      Reset password
    </a>

    <p style="color:#64748b;font-size:12px;line-height:1.5;margin:0">
      If you didn't request a password reset, you can safely ignore this email.
    </p>

    <div style="border-top:1px solid #2a2a2a;margin-top:28px;padding-top:20px">
      <p style="color:#475569;font-size:11px;margin:0">
        Or copy this link:<br/>
        <a href="{link}" style="color:#7c3aed;word-break:break-all;font-size:11px">{link}</a>
      </p>
    </div>
  </div>
</body>
</html>
"""
    plain = (
        f"Reset your QAmachine password:\n\n{link}\n\n"
        f"Link expires in 1 hour. If you didn't request this, ignore this email."
    )
    await send_email(to_email, "Reset your QAmachine password", html, plain)
