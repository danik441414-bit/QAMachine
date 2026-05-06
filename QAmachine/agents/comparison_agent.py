"""
Comparison Agent — visits the same pages on two URLs (e.g. staging vs production)
and uses LLM vision to identify visual and structural differences.

Usage:
    results = asyncio.run(run(url1="https://prod.site.com", url2="https://staging.site.com"))
"""
from __future__ import annotations
import asyncio
import base64
import json
import logging
import os
import re
from urllib.parse import urljoin, urlparse

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

log = logging.getLogger(__name__)

_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.0, max_tokens=1500)

_COMPARE_SYSTEM = """You are a senior QA engineer comparing two versions of the same web page.
LEFT screenshot = URL A (first/primary). RIGHT screenshot = URL B (second/comparison).

Find ALL differences. Be specific — name the element, the change, and where on page.

Respond ONLY with a valid JSON array. No prose, no explanation, just the array:
[
  {"type": "visual|content|functional|missing", "description": "...", "severity": "minor|significant|critical"}
]

Types:
  visual     — color, font, spacing, layout shift, broken styles, image differences
  content    — different text, wrong labels, missing copy, price differences
  functional — UI state difference, missing buttons, broken component
  missing    — element present in one URL but absent in the other

Severity:
  critical    — missing core content/feature, broken page structure
  significant — noticeable UX-impacting difference
  minor       — subtle spacing, color, or style difference

Return [] if the pages look identical or the differences are negligible browser artifacts."""


class ComparisonDiff:
    __slots__ = ("type", "description", "severity")

    def __init__(self, type_: str, description: str, severity: str):
        self.type = type_
        self.description = description
        self.severity = severity


class ComparisonResult:
    __slots__ = ("path", "url1", "url2", "differences", "screenshot_path1", "screenshot_path2")

    def __init__(
        self,
        path: str,
        url1: str,
        url2: str,
        differences: list[ComparisonDiff],
        screenshot_path1: str = "",
        screenshot_path2: str = "",
    ):
        self.path = path
        self.url1 = url1
        self.url2 = url2
        self.differences = differences
        self.screenshot_path1 = screenshot_path1
        self.screenshot_path2 = screenshot_path2


async def _screenshot_b64(page) -> str:
    raw = await page.screenshot(type="jpeg", quality=75, full_page=False)
    return base64.b64encode(raw).decode()


async def _page_title(page) -> str:
    try:
        return await page.evaluate("document.title || ''")
    except Exception:
        return ""


async def _discover_paths(page, base_url: str, max_paths: int = 10) -> list[str]:
    """Crawl the homepage of base_url and collect internal paths from nav/header links."""
    try:
        await page.goto(base_url, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(2000)
        paths: list[str] = await page.evaluate("""() => {
            const seen = new Set(['/']);
            const result = ['/'];
            const base = window.location.hostname;
            document.querySelectorAll('a[href]').forEach(a => {
                try {
                    const u = new URL(a.href, window.location.href);
                    if (u.hostname === base) {
                        const p = u.pathname + u.search;
                        if (!seen.has(p) && !p.includes('#') && p.length < 120) {
                            seen.add(p);
                            result.push(p);
                        }
                    }
                } catch {}
            });
            return result;
        }""")
        return paths[:max_paths]
    except Exception as e:
        log.warning("[compare] discovery failed: %s", e)
        return ["/"]


def _llm_compare(ss1_b64: str, ss2_b64: str, url1: str, url2: str, path: str) -> list[ComparisonDiff]:
    """Send two screenshots to LLM and parse differences."""
    try:
        resp = _llm.invoke([
            SystemMessage(content=_COMPARE_SYSTEM),
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": (
                        f"Path: {path}\n"
                        f"LEFT  (A): {url1}\n"
                        f"RIGHT (B): {url2}\n\n"
                        "Return JSON array of differences only."
                    ),
                },
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": ss1_b64}},
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": ss2_b64}},
            ]),
        ])
        text = str(resp.content).strip()
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return []
        raw = json.loads(match.group())
        return [
            ComparisonDiff(
                type_=d.get("type", "visual"),
                description=d.get("description", ""),
                severity=d.get("severity", "minor"),
            )
            for d in raw
            if isinstance(d, dict) and d.get("description")
        ]
    except Exception as e:
        log.warning("[compare] LLM compare failed on %s: %s", path, e)
        return []


async def run(
    url1: str,
    url2: str,
    traces_dir: str = "ux_traces",
    max_pages: int = 10,
) -> list[ComparisonResult]:
    """
    Compare url1 vs url2 by visiting the same pages on both and comparing screenshots.
    Returns list of ComparisonResult sorted by page path.
    """
    from playwright.async_api import async_playwright

    os.makedirs(traces_dir, exist_ok=True)
    results: list[ComparisonResult] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page_a = await context.new_page()
        page_b = await context.new_page()

        try:
            print(f"  [COMPARE] Discovering pages on {url1} ...")
            paths = await _discover_paths(page_a, url1, max_paths=max_pages)
            print(f"  [COMPARE] {len(paths)} page(s) to compare: {', '.join(paths)}")

            for i, path in enumerate(paths):
                full_url1 = urljoin(url1, path)
                full_url2 = urljoin(url2, path)

                print(f"  [COMPARE] [{i+1}/{len(paths)}] {path}")

                try:
                    await asyncio.gather(
                        page_a.goto(full_url1, wait_until="domcontentloaded", timeout=25_000),
                        page_b.goto(full_url2, wait_until="domcontentloaded", timeout=25_000),
                    )
                    await asyncio.gather(page_a.wait_for_timeout(2000), page_b.wait_for_timeout(2000))
                except Exception as e:
                    print(f"  [COMPARE] Load failed on {path}: {e}")
                    continue

                ss1 = await _screenshot_b64(page_a)
                ss2 = await _screenshot_b64(page_b)

                path_safe = re.sub(r"[^a-zA-Z0-9_-]", "_", path)[:40].strip("_") or "home"
                sp1 = os.path.join(traces_dir, f"cmp_{i:02d}_{path_safe}_A.jpg")
                sp2 = os.path.join(traces_dir, f"cmp_{i:02d}_{path_safe}_B.jpg")

                with open(sp1, "wb") as f:
                    f.write(base64.b64decode(ss1))
                with open(sp2, "wb") as f:
                    f.write(base64.b64decode(ss2))

                diffs = _llm_compare(ss1, ss2, url1, url2, path)
                results.append(ComparisonResult(
                    path=path,
                    url1=full_url1,
                    url2=full_url2,
                    differences=diffs,
                    screenshot_path1=sp1,
                    screenshot_path2=sp2,
                ))

                if diffs:
                    sev = {}
                    for d in diffs:
                        sev[d.severity] = sev.get(d.severity, 0) + 1
                    print(f"  [COMPARE] {len(diffs)} diff(s): {sev}")
                else:
                    print(f"  [COMPARE] No differences.")

        finally:
            await browser.close()

    return results


def generate_report(
    url1: str,
    url2: str,
    results: list[ComparisonResult],
    label1: str = "URL A",
    label2: str = "URL B",
) -> str:
    """Generate a Markdown comparison report from ComparisonResult list."""
    import datetime

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_diffs = sum(len(r.differences) for r in results)
    critical = sum(1 for r in results for d in r.differences if d.severity == "critical")
    significant = sum(1 for r in results for d in r.differences if d.severity == "significant")
    minor = sum(1 for r in results for d in r.differences if d.severity == "minor")

    _SEV_EMOJI = {"critical": "🔴", "significant": "🟠", "minor": "🟡"}
    _TYPE_ICON = {"visual": "🎨", "content": "📝", "functional": "⚙️", "missing": "❌"}

    lines = [
        "# QAmachine — Environment Comparison Report",
        "",
        f"| | |",
        f"|---|---|",
        f"| **{label1}** | `{url1}` |",
        f"| **{label2}** | `{url2}` |",
        f"| **Generated** | {ts} |",
        f"| **Pages compared** | {len(results)} |",
        f"| **Total differences** | {total_diffs} |",
        f"| **Critical** | {critical} |",
        f"| **Significant** | {significant} |",
        f"| **Minor** | {minor} |",
        "",
        "---",
        "",
    ]

    if total_diffs == 0:
        lines += [
            "## Result",
            "",
            "✅ **No differences detected.** Both environments appear visually and structurally identical.",
            "",
        ]
    else:
        lines += ["## Differences by Page", ""]

        for r in results:
            if not r.differences:
                lines.append(f"### ✅ `{r.path}` — identical")
                lines.append("")
                continue

            lines.append(f"### `{r.path}` — {len(r.differences)} difference(s)")
            lines.append("")
            lines.append(f"- **A:** `{r.url1}`")
            lines.append(f"- **B:** `{r.url2}`")
            if r.screenshot_path1 and os.path.exists(r.screenshot_path1):
                lines.append(f"- **Screenshots:** `{r.screenshot_path1}` | `{r.screenshot_path2}`")
            lines.append("")

            for d in sorted(r.differences, key=lambda x: ["critical", "significant", "minor"].index(x.severity) if x.severity in ["critical", "significant", "minor"] else 3):
                sev_emoji = _SEV_EMOJI.get(d.severity, "⚪")
                type_icon = _TYPE_ICON.get(d.type, "•")
                lines.append(f"- {sev_emoji} **[{d.severity.upper()}]** {type_icon} {d.description}")
            lines.append("")

    lines += ["---", "", "## Pages Comparison Summary", ""]
    lines.append("| Page | Diffs | Critical | Significant | Minor |")
    lines.append("|---|---|---|---|---|")
    for r in results:
        c = sum(1 for d in r.differences if d.severity == "critical")
        s = sum(1 for d in r.differences if d.severity == "significant")
        m = sum(1 for d in r.differences if d.severity == "minor")
        status = "✅" if not r.differences else ("🔴" if c else ("🟠" if s else "🟡"))
        lines.append(f"| {status} `{r.path}` | {len(r.differences)} | {c} | {s} | {m} |")

    return "\n".join(lines)
