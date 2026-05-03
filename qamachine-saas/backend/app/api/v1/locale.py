"""
Locale detection endpoint.

Priority:
  1. Detect country from client IP via ip-api.com (free, no key needed)
  2. Fall back to Accept-Language header
  3. Default to "en"

Russian-speaking countries mapped to "ru":
  Russia, Ukraine, Belarus, Kazakhstan, Azerbaijan, Armenia, Georgia,
  Kyrgyzstan, Moldova, Tajikistan, Turkmenistan, Uzbekistan.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Request

router = APIRouter()

_RU_COUNTRIES = {
    "RU", "UA", "BY", "KZ", "AZ", "AM", "GE",
    "KG", "MD", "TJ", "TM", "UZ",
}


def _lang_from_accept(accept: str) -> str:
    for part in accept.split(","):
        tag = part.split(";")[0].strip().lower()
        if tag.startswith("ru"):
            return "ru"
    return "en"


@router.get("/detect")
async def detect_locale(request: Request):
    """Return the detected interface language based on client IP + headers."""

    # Extract real IP (works behind proxies / Nginx)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else None

    # Skip loopback / private IPs — fall back to Accept-Language
    if client_ip and not _is_private(client_ip):
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    f"http://ip-api.com/json/{client_ip}",
                    params={"fields": "countryCode,status"},
                )
                data = resp.json()
                if data.get("status") == "success":
                    if data.get("countryCode", "").upper() in _RU_COUNTRIES:
                        return {"language": "ru", "source": "ip"}
                    return {"language": "en", "source": "ip"}
        except Exception:
            pass  # Network error — fall through to header-based detection

    # Accept-Language fallback
    accept = request.headers.get("Accept-Language", "")
    lang = _lang_from_accept(accept)
    return {"language": lang, "source": "accept-language"}


def _is_private(ip: str) -> bool:
    """Return True for localhost and RFC-1918 / RFC-4193 private addresses."""
    private_prefixes = ("127.", "10.", "192.168.", "::1", "localhost")
    if any(ip.startswith(p) for p in private_prefixes):
        return True
    if ip.startswith("172."):
        parts = ip.split(".")
        if len(parts) >= 2 and 16 <= int(parts[1]) <= 31:
            return True
    return False
