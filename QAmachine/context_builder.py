from __future__ import annotations
import base64
import io
from playwright.async_api import Page
from PIL import Image

from schemas import PageContext, DOMElement, TestMission

_DOM_JS = """() => {
    const res = [];
    let c = 1;

    // ── Pass 1: all visible interactive elements ──────────────────────────────
    const els = Array.from(document.querySelectorAll(
        'button, a, input, select, textarea, [role="button"], ' +
        '[class*="nav-tab"], [class*="dropdown"], [class*="menu-item"]'
    ));
    for (const el of els) {
        const r = el.getBoundingClientRect();
        if (r.width <= 2 || r.height <= 2) continue;
        if (window.getComputedStyle(el).visibility === 'hidden') continue;

        const t = (el.innerText || el.placeholder || el.title || el.value || '')
                    .substring(0, 50).replace(/\\n/g, ' ').trim();
        const tl = t.toLowerCase();

        if (el.tagName === 'A') {
            if (/cookie|privacy|policy|terms|accept/i.test(tl)) continue;
            const href = el.getAttribute('href');
            if (href && href.startsWith('http')) {
                try {
                    if (new URL(href).hostname !== window.location.hostname) continue;
                } catch (_) {}
            }
        }

        // Detect dropdown trigger: has aria-haspopup, aria-expanded, or a direct
        // child/sibling <ul> or element with submenu-like class
        const hasPopup = el.getAttribute('aria-haspopup') === 'true'
            || el.getAttribute('data-toggle') === 'dropdown'
            || el.querySelector('ul, [class*="submenu"], [class*="dropdown-menu"]') !== null
            || (el.nextElementSibling && el.nextElementSibling.matches('ul, [class*="submenu"], [class*="dropdown"]'));
        const isExpanded = el.getAttribute('aria-expanded') === 'true';

        let prefix = '';
        if (hasPopup && !isExpanded) prefix = '[+▼] ';   // has dropdown, currently closed
        else if (hasPopup && isExpanded) prefix = '[▼ OPEN] '; // dropdown currently open

        el.setAttribute('qa-id', String(c));
        res.push({ id: String(c), tag: el.tagName.toLowerCase(), text: prefix + t });
        c++;
    }

    // ── Pass 2: items inside hidden dropdown/submenu containers ───────────────
    // These are not interactable yet but the LLM should know they exist.
    const menuContainers = Array.from(document.querySelectorAll(
        'ul[class*="dropdown"], ul[class*="submenu"], [role="menu"], ' +
        '[class*="dropdown-menu"], [class*="nav-dropdown"]'
    ));
    const seenQaIds = new Set(res.map(r => r.id));
    for (const container of menuContainers) {
        const cs = window.getComputedStyle(container);
        const isHidden = cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0';
        if (!isHidden) continue; // already captured in pass 1

        for (const item of container.querySelectorAll('a, button, li[role="menuitem"]')) {
            const t = (item.innerText || '').substring(0, 50).replace(/\\n/g, ' ').trim();
            if (!t) continue;
            const existingId = item.getAttribute('qa-id');
            if (existingId && seenQaIds.has(existingId)) continue;
            item.setAttribute('qa-id', String(c));
            res.push({ id: String(c), tag: item.tagName.toLowerCase(), text: '[▶HIDDEN] ' + t });
            c++;
        }
    }

    return res;
}"""


async def _get_aria_snapshot(page: Page) -> str:
    """
    Try aria_snapshot() (Playwright >= 1.44).
    Falls back to empty string if unavailable or if the page is mid-navigation.
    Truncates to 3000 chars to stay within LLM context budget.
    """
    try:
        snapshot = await page.locator("body").aria_snapshot()
        return snapshot[:3000]
    except Exception:
        return ""


async def _get_page_load_ms(page: Page) -> int:
    """Return total page load duration in ms using Navigation Timing API."""
    try:
        ms = await page.evaluate("""() => {
            const nav = performance.getEntriesByType('navigation')[0];
            return nav ? Math.round(nav.duration) : 0;
        }""")
        return int(ms or 0)
    except Exception:
        return 0


async def build_page_context(
    page: Page,
    step: int,
    mission: TestMission,
    tracker_snapshot: dict,
    action_history: list[str],
    console_error_buffer: list[str],
    network_event_buffer: list[dict] | None = None,
) -> tuple[PageContext, list[DOMElement]]:
    """
    Collect multi-layer page state. Returns (PageContext, full_dom).

    The caller is responsible for:
    - Replacing ctx.dom_elements with the filtered subset before passing to Explorer.
    - Saving ctx.screenshot_b64 to disk if a trace file is needed.

    full_dom is the unfiltered element list, used by CoverageTracker.available_elements().
    network_event_buffer: raw network events from Playwright response listener (optional).
    """
    # Screenshot → base64 JPEG compressed (50% scale, quality 55)
    # Reduces token cost ~80% vs full-size PNG while keeping defects clearly visible.
    png_bytes = await page.screenshot(type="png")
    img = Image.open(io.BytesIO(png_bytes))
    w, h = img.size
    img = img.resize((w // 2, h // 2), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=55, optimize=True)
    screenshot_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # DOM elements
    raw_dom = await page.evaluate(_DOM_JS)
    full_dom = [DOMElement(id=el["id"], tag=el["tag"], text=el["text"]) for el in raw_dom]

    # Aria snapshot
    aria = await _get_aria_snapshot(page)

    # Network errors (4xx/5xx from buffer)
    network_errors: list[str] = []
    if network_event_buffer:
        for e in network_event_buffer:
            if e.get("status", 0) >= 400:
                network_errors.append(
                    f"{e.get('method','?')} {e.get('url','?')[:100]} → {e.get('status','?')}"
                )

    # Page load timing (useful for LOAD_PERFORMANCE mode)
    page_load_ms = await _get_page_load_ms(page)

    ctx = PageContext(
        step=step,
        current_url=page.url,
        dom_elements=full_dom,          # replaced by caller with filtered subset
        aria_snapshot=aria,
        console_errors=list(console_error_buffer),
        network_errors=network_errors,
        page_load_ms=page_load_ms,
        screenshot_b64=screenshot_b64,
        url_stay_count=tracker_snapshot["url_stay_count"],
        visited_urls=list(tracker_snapshot["visited_urls"]),
        clicked_element_ids=list(tracker_snapshot["clicked_element_ids"]),
        nav_items_clicked=list(tracker_snapshot["nav_items_clicked"]),
        action_history=action_history,
        mission=mission,
    )
    return ctx, full_dom
