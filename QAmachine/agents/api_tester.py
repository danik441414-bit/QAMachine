"""
API endpoint testing module.
Uses only stdlib (urllib) — no extra dependencies required.
Called after the main browser session to test collected API endpoints.
"""
from __future__ import annotations
import json
import time
import urllib.request
import urllib.error
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.0, max_tokens=1000)

_SLOW_MS = 2000    # threshold for "slow" API response
_MAX_TEST = 25     # max endpoints to test per session


def _test_one(url: str, method: str = "GET") -> dict:
    """Test a single endpoint with urllib. Returns result dict."""
    start = time.monotonic()
    result: dict = {"url": url, "method": method, "status": 0,
                    "duration_ms": 0, "is_json": False, "error": None}
    try:
        req = urllib.request.Request(url, method=method)
        req.add_header("User-Agent", "QAmachine/1.0 API-Tester")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result["duration_ms"] = int((time.monotonic() - start) * 1000)
            result["status"] = resp.status
            body = resp.read(4096)           # read first 4KB only
            ct = resp.headers.get("Content-Type", "")
            result["is_json"] = "json" in ct.lower()
            if result["is_json"]:
                try:
                    json.loads(body)
                    result["valid_json"] = True
                except Exception:
                    result["valid_json"] = False
    except urllib.error.HTTPError as e:
        result["duration_ms"] = int((time.monotonic() - start) * 1000)
        result["status"] = e.code
        result["error"] = str(e.reason)
    except Exception as e:
        result["duration_ms"] = int((time.monotonic() - start) * 1000)
        result["error"] = str(e)[:120]
    return result


def run(api_endpoints: dict) -> list[dict]:
    """
    Test collected API endpoints.
    api_endpoints: {url: {method, status (from browser), resource_type, ...}}
    Returns list of test results.
    """
    if not api_endpoints:
        return []

    # Prioritize: errors first, then unique paths, skip duplicates
    urls = list(api_endpoints.keys())

    # Prefer endpoints that showed errors in the browser session
    def priority(url: str) -> int:
        e = api_endpoints[url]
        s = e.get("status", 200)
        if s >= 500: return 0
        if s >= 400: return 1
        return 2

    urls.sort(key=priority)
    urls = urls[:_MAX_TEST]

    results = []
    for url in urls:
        method = api_endpoints[url].get("method", "GET")
        result = _test_one(url, method)
        result["browser_status"] = api_endpoints[url].get("status", "unknown")
        results.append(result)

    return results


def load_test(urls: list[str], passes: int = 3) -> list[dict]:
    """
    Repeat GET requests to a list of URLs N times and collect timing stats.
    Used by LOAD_PERFORMANCE mode to get avg/min/max response time per endpoint.

    Returns a list of dicts:
      {url, passes, avg_ms, min_ms, max_ms, errors, status_sample}
    """
    results = []
    for url in urls:
        timings: list[int] = []
        errors = 0
        status_sample = 0
        for _ in range(passes):
            r = _test_one(url)
            if r.get("error") or r.get("status", 0) == 0:
                errors += 1
            else:
                timings.append(r["duration_ms"])
                if not status_sample:
                    status_sample = r["status"]
        if timings:
            results.append({
                "url":           url,
                "passes":        passes,
                "avg_ms":        int(sum(timings) / len(timings)),
                "min_ms":        min(timings),
                "max_ms":        max(timings),
                "errors":        errors,
                "status_sample": status_sample,
            })
        else:
            results.append({
                "url":           url,
                "passes":        passes,
                "avg_ms":        0,
                "min_ms":        0,
                "max_ms":        0,
                "errors":        errors,
                "status_sample": 0,
            })
    return results


def summarize(results: list[dict], target_url: str) -> str:
    """LLM summary of API test results. Called only if there are interesting findings."""
    if not results:
        return "_No API endpoints were collected during the session._"

    errors   = [r for r in results if r.get("status", 0) >= 400 or r.get("error")]
    slow     = [r for r in results if r.get("duration_ms", 0) > _SLOW_MS]
    ok_count = len(results) - len(errors)

    if not errors and not slow:
        return (
            f"All {len(results)} tested API endpoints responded successfully "
            f"(status 2xx/3xx, under {_SLOW_MS}ms)."
        )

    # Build compact summary for LLM
    findings_lines = []
    for r in (errors + slow)[:15]:
        line = f"- {r['method']} {r['url'][:80]} → status={r['status']} ({r['duration_ms']}ms)"
        if r.get("error"):
            line += f" ERROR: {r['error']}"
        if r in slow and r not in errors:
            line += " [SLOW]"
        findings_lines.append(line)

    prompt = (
        f"API test results for {target_url}:\n"
        f"Total tested: {len(results)} | OK: {ok_count} | Errors: {len(errors)} | Slow: {len(slow)}\n\n"
        f"Issues found:\n" + "\n".join(findings_lines) + "\n\n"
        "Write a concise QA summary (3-5 sentences) describing the API health issues found."
    )

    try:
        resp = _llm.invoke([
            SystemMessage(content="You are a QA engineer summarizing API test results. Be concise and factual."),
            HumanMessage(content=prompt),
        ])
        return resp.content
    except Exception as e:
        return f"_API summary unavailable: {e}_"
