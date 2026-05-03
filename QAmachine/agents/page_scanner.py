"""
Page Scanner — lightweight async browser scan utility.

Used by doc_generator and playwright_generator to capture page context
(screenshot + DOM + aria snapshot) WITHOUT running the full QA session.
Navigates to the target URL and optionally into the requested scope.
"""
from __future__ import annotations
import base64
import re
from dataclasses import dataclass, field
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from context_builder import _DOM_JS, _get_aria_snapshot
from schemas import MobileConfig

# Max DOM elements to include in the text snapshot sent to LLM
_MAX_DOM_ELEMENTS = 120


@dataclass
class PageSnapshot:
    url:            str = ""
    title:          str = ""
    screenshot_b64: str = ""
    dom_text:       str = ""   # formatted DOM elements as text, capped at _MAX_DOM_ELEMENTS
    aria_snapshot:  str = ""
    console_errors: list[str] = field(default_factory=list)


async def quick_scan(
    target_url: str,
    scope: str = "",
    scope_entry_steps: list[str] | None = None,
    credentials_text: str = "",
    mobile_config: MobileConfig | None = None,
    headless: bool = False,
    max_snapshots: int = 2,
) -> list[PageSnapshot]:
    """
    Open a browser, navigate to target_url, optionally navigate into scope,
    capture 1-2 PageSnapshots (initial state + post-navigation state).

    Returns a list of PageSnapshot objects (usually 1-2).
    On any failure returns a single empty PageSnapshot so callers can continue.
    """
    snapshots: list[PageSnapshot] = []
    entry_steps = scope_entry_steps or []

    try:
        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=headless)
            context: BrowserContext = await _make_context(browser, mobile_config)
            page: Page = await context.new_page()

            console_errs: list[str] = []
            page.on("console", lambda m: console_errs.append(m.text) if m.type == "error" else None)

            await page.goto(target_url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(2000)
            try:
                await page.wait_for_load_state("networkidle", timeout=4000)
            except Exception:
                pass

            # Capture state 1 — homepage / landing
            snapshots.append(await _capture_snapshot(page, list(console_errs)))
            console_errs.clear()

            # Navigate into scope if entry steps were given
            if entry_steps and len(snapshots) < max_snapshots:
                await _navigate_to_scope(page, entry_steps, credentials_text)
                await page.wait_for_timeout(1500)
                snapshots.append(await _capture_snapshot(page, list(console_errs)))

            await browser.close()

    except Exception as e:
        print(f"  [page_scanner] Browser scan error: {e}")
        if not snapshots:
            snapshots.append(PageSnapshot(url=target_url))

    return snapshots


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _make_context(browser: Browser, mc: MobileConfig | None) -> BrowserContext:
    if mc:
        ctx = await browser.new_context(
            viewport={"width": mc.viewport_width, "height": mc.viewport_height},
            user_agent=mc.user_agent or None,
            is_mobile=mc.is_mobile,
            has_touch=mc.has_touch,
            device_scale_factor=mc.device_scale_factor,
        )
    else:
        ctx = await browser.new_context(viewport={"width": 1280, "height": 720})
    return ctx


async def _capture_snapshot(page: Page, console_errs: list[str]) -> PageSnapshot:
    """Take screenshot, DOM, aria for the current page state."""
    try:
        png   = await page.screenshot(type="png")
        b64   = base64.b64encode(png).decode()
    except Exception:
        b64 = ""

    try:
        raw_dom  = await page.evaluate(_DOM_JS)
        dom_text = "\n".join(
            f"[{el['id']}] {el['tag']} | '{el['text']}'"
            for el in raw_dom[:_MAX_DOM_ELEMENTS]
        )
    except Exception:
        dom_text = "(DOM unavailable)"

    try:
        title = await page.title()
    except Exception:
        title = ""

    aria = await _get_aria_snapshot(page)

    return PageSnapshot(
        url=page.url,
        title=title,
        screenshot_b64=b64,
        dom_text=dom_text,
        aria_snapshot=aria,
        console_errors=list(console_errs),
    )


async def _navigate_to_scope(
    page: Page,
    entry_steps: list[str],
    credentials_text: str,
) -> None:
    """
    Best-effort navigation following scope_entry_steps hints.
    Each step is a natural-language hint like 'Click Login' or 'Enter credentials'.
    We try text-based clicking; failures are silently skipped.
    """
    cred_user = _extract_cred(credentials_text, r"(?:username|email|user):\s*(\S+)")
    cred_pass = _extract_cred(credentials_text, r"password:\s*(\S+)")

    for hint in entry_steps[:4]:   # cap to 4 steps to stay fast
        hint_lower = hint.lower()

        # Fill credentials
        if any(k in hint_lower for k in ("credential", "login", "sign in", "enter user", "email")):
            if cred_user:
                await _try_fill(page, "input[type='email'], input[name='email']", cred_user)
                await _try_fill(page, "input[type='text']", cred_user)
            if cred_pass:
                await _try_fill(page, "input[type='password']", cred_pass)
                # Submit after filling password
                try:
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(2000)
                except Exception:
                    pass
            continue

        # Click element by quoted text
        match = re.search(r"['\"]([^'\"]{2,40})['\"]", hint)
        if match:
            text = match.group(1)
            clicked = await _try_click_text(page, text)
            if clicked:
                await page.wait_for_timeout(1500)
                continue

        # Keyword-based fallback clicks
        if "login" in hint_lower or "sign in" in hint_lower or "войти" in hint_lower:
            await _try_click_text(page, "Login") or await _try_click_text(page, "Sign In") or \
                await _try_click_text(page, "Войти")
        elif "register" in hint_lower or "sign up" in hint_lower:
            await _try_click_text(page, "Register") or await _try_click_text(page, "Sign Up")
        elif "account" in hint_lower or "profile" in hint_lower or "аккаунт" in hint_lower:
            await _try_click_text(page, "My Account") or await _try_click_text(page, "Account") or \
                await _try_click_text(page, "Profile")
        elif "cart" in hint_lower or "корзина" in hint_lower:
            await _try_click_text(page, "Cart") or await _try_click_text(page, "Basket")
        elif "checkout" in hint_lower:
            await _try_click_text(page, "Checkout")

        await page.wait_for_timeout(800)


def _extract_cred(text: str, pattern: str) -> str:
    if not text:
        return ""
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1) if m else ""


async def _try_fill(page: Page, selector: str, value: str) -> bool:
    try:
        await page.fill(selector, value, timeout=2000)
        return True
    except Exception:
        return False


async def _try_click_text(page: Page, text: str) -> bool:
    try:
        await page.click(f"text={text}", timeout=2500)
        return True
    except Exception:
        return False
