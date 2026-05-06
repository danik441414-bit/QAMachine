from __future__ import annotations
import base64
import datetime
import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from schemas import VerifiedIssue, StepLog, TestMission, SessionMode

_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.3, max_tokens=3000)

_UX_SYSTEM = """You are a Lead UX/UI Product Designer conducting a usability audit.
You are given a storyboard of screenshots from an automated QA session.
Analyze and provide recommendations on:
1. Visual hierarchy and contrast
2. Navigation clarity and consistency
3. Form usability and feedback
Format in Markdown. Be specific and critical."""

_SEVERITY_ORDER = ["critical", "high", "medium", "low"]
_SEVERITY_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
_MODE_LABEL = {
    "ui_ux":            "UI/UX Audit",
    "functional":       "Functional Testing",
    "specific_flow":    "Specific Flow Test",
    "all_flows":        "All User Flows",
    "regression":       "Regression Test",
    "network":          "Network Audit",
    "api":              "API Testing",
    "load_performance": "Performance Audit",
    "mobile":           "Mobile Testing",
}


def _sample(paths: list[str], n: int = 8) -> list[str]:
    if len(paths) <= n:
        return paths
    step = max(1, len(paths) // (n - 2))
    return [paths[0]] + paths[1:-1:step] + [paths[-1]]


def _ux_section(journey_screenshots: list[str], target_url: str) -> str:
    if not journey_screenshots:
        return "_No screenshots available._"
    sampled = _sample(journey_screenshots)
    content: list = [{"type": "text", "text": "Session storyboard:"}]
    for path in sampled:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "rb") as f:
                raw = f.read()
            b64 = base64.b64encode(raw).decode("utf-8")
            media = "image/jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "image/png"
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media, "data": b64},
            })
        except Exception:
            continue
    if len(content) == 1:
        return "_Could not load screenshots._"
    try:
        system = f"{_UX_SYSTEM}\n\nSite: {target_url}"
        resp = _llm.invoke([SystemMessage(content=system), HumanMessage(content=content)])
        return str(resp.content)
    except Exception as e:
        return f"_UX audit failed: {e}_"


def _network_section(network_events: list[dict]) -> str:
    if not network_events:
        return "_No network events recorded._"
    errors = [e for e in network_events if e.get("status", 0) >= 400]
    if not errors:
        return f"✅ No HTTP errors observed across {len(network_events)} captured requests."

    lines = [f"**{len(errors)} failed request(s) out of {len(network_events)} total:**", ""]
    by_status: dict[int, list] = {}
    for e in errors:
        by_status.setdefault(e["status"], []).append(e)

    for status in sorted(by_status):
        emoji = "🔴" if status >= 500 else "🟠"
        lines.append(f"### {emoji} HTTP {status} ({len(by_status[status])} requests)")
        for e in by_status[status][:10]:
            lines.append(f"- `{e.get('method','?')}` `{e.get('url','?')[:100]}`")
        if len(by_status[status]) > 10:
            lines.append(f"  _...and {len(by_status[status])-10} more_")
        lines.append("")
    return "\n".join(lines)


def _api_section(api_results: list[dict], api_summary: str) -> str:
    if not api_results:
        return (
            "_No XHR/fetch API endpoints were captured during this session._\n\n"
            "**Possible reasons:**\n"
            "- The page is a server-side rendered app (no XHR calls)\n"
            "- The session ended before the app fully loaded (SPA timing)\n"
            "- Authentication failed — try providing credentials in the task description\n"
            "- The app requires user interaction before making API calls\n\n"
            "_Tip: For best results, ensure the machine can log in and navigate to "
            "data-heavy pages (dashboard, lists, reports) which trigger the most API calls._"
        )

    # Captured-only mode (non-API sessions): just list what was seen
    if all(r.get("captured_only") for r in api_results):
        lines = [
            f"**Captured:** {len(api_results)} XHR/fetch endpoints observed during session.",
            "_Run in **API** mode to test these endpoints for errors and performance._",
            "",
            "#### Observed Endpoints",
        ]
        for r in api_results[:30]:
            status = r.get("status", "—")
            flag = " ⚠️" if isinstance(status, int) and status >= 400 else ""
            lines.append(f"- `{r.get('method','GET')}` `{r.get('url','?')[:100]}` → {status}{flag}")
        return "\n".join(lines)

    # Full API test mode
    errors = [r for r in api_results if r.get("status", 0) >= 400 or r.get("error")]
    slow   = [r for r in api_results if r.get("duration_ms", 0) > 2000]
    ok     = len(api_results) - len({r["url"] for r in errors})

    lines = [
        f"**Tested:** {len(api_results)} endpoints | "
        f"**OK:** {ok} | **Errors:** {len(errors)} | **Slow (>2s):** {len(slow)}",
        "",
    ]

    if errors:
        lines.append("#### Failed Endpoints")
        for r in errors[:15]:
            status_str = str(r.get("status") or r.get("error", "?"))
            lines.append(
                f"- `{r.get('method','?')}` `{r.get('url','?')[:90]}` → "
                f"**{status_str}** ({r.get('duration_ms',0)}ms)"
            )
        lines.append("")

    if slow:
        lines.append("#### Slow Endpoints (>2s)")
        for r in slow[:10]:
            lines.append(
                f"- `{r.get('method','?')}` `{r.get('url','?')[:90]}` → "
                f"{r.get('duration_ms',0)}ms"
            )
        lines.append("")

    if api_summary:
        lines += ["#### Summary", api_summary, ""]

    return "\n".join(lines)


def _mobile_section(mission, verified_issues: list[VerifiedIssue]) -> str:
    """Summary section specific to MOBILE mode reports."""
    mc = mission.mobile_config if mission else None
    device_line = (
        f"**Device:** {mc.device_name} | "
        f"**Viewport:** {mc.viewport_width} x {mc.viewport_height} | "
        f"**Scale:** {mc.device_scale_factor}x"
        if mc else "_Mobile config not recorded._"
    )

    mobile_issues = [
        vi for vi in verified_issues
        if any(kw in vi.description.lower() for kw in (
            "scroll", "touch", "burger", "menu", "overflow", "truncat",
            "mobile", "tap", "sticky", "overlap", "modal", "bottom bar",
            "font", "image", "responsive",
        ))
    ]
    non_mobile = len(verified_issues) - len(mobile_issues)

    lines = [
        device_line, "",
        f"**Total confirmed issues:** {len(verified_issues)} | "
        f"**Mobile-specific:** {len(mobile_issues)} | "
        f"**General:** {non_mobile}",
        "",
    ]

    checks = [
        ("Horizontal scroll",     "scroll"),
        ("Touch targets",         "touch"),
        ("Burger / nav menu",     "burger"),
        ("Text overflow",         "overflow"),
        ("Overlapping elements",  "overlap"),
        ("Sticky header/footer",  "sticky"),
        ("Mobile forms",          "form"),
        ("Modals / overlays",     "modal"),
        ("Images responsive",     "image"),
        ("CTA visibility",        "cta"),
    ]
    lines.append("### Mobile Check Coverage")
    lines.append("")
    for label, kw in checks:
        hit = any(kw in vi.description.lower() for vi in verified_issues)
        mark = "FAIL" if hit else "pass"
        lines.append(f"- [{mark}] {label}")

    return "\n".join(lines)


def _perf_section(
    perf_metrics: list[dict],
    load_test_results: list[dict] | None = None,
) -> str:
    lines = []

    if perf_metrics:
        slow = [p for p in perf_metrics if p.get("load_ms", 0) > 3000]
        lines += [
            f"**Pages measured:** {len(perf_metrics)} | "
            f"**Slow (>3s):** {len(slow)}",
            "",
            "| Step | URL | Load (ms) | Rating |",
            "|---|---|---|---|",
        ]
        for p in sorted(perf_metrics, key=lambda x: x.get("load_ms", 0), reverse=True):
            load = p.get("load_ms", 0)
            rating = "🔴 SLOW" if load > 3000 else "🟡 OK" if load > 1500 else "🟢 Fast"
            url_short = p.get("url", "")[-70:]
            lines.append(f"| {p.get('step','?')} | `{url_short}` | {load} | {rating} |")
        lines.append("")
    else:
        lines.append("_No page load metrics recorded._\n")

    if load_test_results:
        lines += [
            "### Repeated-Request Load Test",
            f"_(Each endpoint tested {load_test_results[0].get('passes', 3)}x)_",
            "",
            "| URL | Avg (ms) | Min (ms) | Max (ms) | Errors | Rating |",
            "|---|---|---|---|---|---|",
        ]
        for r in sorted(load_test_results, key=lambda x: -x.get("avg_ms", 0)):
            avg = r.get("avg_ms", 0)
            rating = "🔴 SLOW" if avg > 2000 else "🟡 OK" if avg > 800 else "🟢 Fast"
            url_short = r.get("url", "")[-60:]
            lines.append(
                f"| `{url_short}` | {avg} | {r.get('min_ms',0)} "
                f"| {r.get('max_ms',0)} | {r.get('errors',0)} | {rating} |"
            )

    return "\n".join(lines) if lines else "_No performance metrics recorded._"


def generate(
    mission: TestMission,
    target_url: str,
    user_task: str,
    steps: list[StepLog],
    verified_issues: list[VerifiedIssue],
    journey_screenshots: list[str],
    # Optional mode-specific data
    network_events: list[dict] | None = None,
    api_results: list[dict] | None = None,
    api_summary: str = "",
    perf_metrics: list[dict] | None = None,
    load_test_results: list[dict] | None = None,
) -> tuple[str, str]:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode_label = _MODE_LABEL.get(mission.session_mode.value, mission.session_mode.value)
    scope_note = f" | **Scope:** {mission.test_scope}" if mission.test_scope else ""

    grouped: dict[str, list[VerifiedIssue]] = {s: [] for s in _SEVERITY_ORDER}
    for issue in verified_issues:
        grouped.setdefault(issue.severity.lower(), []).append(issue)

    mc = mission.mobile_config

    lines = [
        "# QAmachine Report",
        "",
        f"| | |",
        f"|---|---|",
        f"| **Target** | `{target_url}` |",
        f"| **Task** | {user_task} |",
        f"| **Mode** | {mode_label}{scope_note} |",
        f"| **Generated** | {ts} |",
        f"| **Steps** | {len(steps)} / {mission.recommended_max_steps} budget |",
        f"| **Unique URLs** | {len({s.url for s in steps})} |",
        f"| **Confirmed issues** | {len(verified_issues)} |",
        *([f"| **Device** | {mc.device_name} ({mc.viewport_width}x{mc.viewport_height}) |"] if mc else []),
        *([ f"| **Changed areas** | {', '.join(mission.changed_areas)} |"] if mission.changed_areas else []),
        *([ f"| **Scope keywords** | `{', '.join(mission.scope_url_keywords)}` |"] if mission.scope_url_keywords else []),
        *([ f"| **Roles tested** | {', '.join(r.name for r in mission.roles)} |"] if getattr(mission, 'roles', []) else []),
        *([ f"| **JS hook** | `{mission.custom_js[:80]}` |"] if getattr(mission, 'custom_js', '') else []),
        "",
        "---",
        "",
    ]

    # ── Confirmed Issues ───────────────────────────────────────────────────────
    lines += ["## Confirmed Issues", ""]
    if not verified_issues:
        lines.append("No defects confirmed during this session.\n")
    else:
        for sev in _SEVERITY_ORDER:
            issues = grouped.get(sev, [])
            if not issues:
                continue
            emoji = _SEVERITY_EMOJI[sev]
            lines += [f"### {emoji} {sev.upper()} ({len(issues)})", ""]
            for i, issue in enumerate(issues, 1):
                role_badge = f" `[{issue.role.upper()}]`" if getattr(issue, "role", "") else ""
                lines += [
                    f"**{i}.{role_badge} {issue.description}**",
                    f"- **URL:** `{issue.url}`",
                    f"- **Step:** {issue.step}",
                    f"- **Element:** `{issue.element_id or 'N/A'}`",
                    f"- **Evidence:** _{issue.evidence}_",
                ]
                if issue.screenshot_path and os.path.exists(issue.screenshot_path):
                    lines.append(f"- **Screenshot:** `{issue.screenshot_path}`")
                lines.append("")

    # ── Multi-role summary (only when roles present) ───────────────────────────
    roles_present = list(dict.fromkeys(
        i.role for i in verified_issues if getattr(i, "role", "")
    ))
    if roles_present:
        lines += ["## Issues by Role", ""]
        lines.append("| Role | Critical | High | Medium | Low | Total |")
        lines.append("|---|---|---|---|---|---|")
        for role in roles_present:
            ri = [i for i in verified_issues if getattr(i, "role", "") == role]
            c = sum(1 for i in ri if i.severity == "critical")
            h = sum(1 for i in ri if i.severity == "high")
            m = sum(1 for i in ri if i.severity == "medium")
            l = sum(1 for i in ri if i.severity == "low")
            lines.append(f"| **{role}** | {c} | {h} | {m} | {l} | {len(ri)} |")
        lines += [""]

    lines += ["---", ""]

    # ── Mode-specific sections ─────────────────────────────────────────────────
    mode = mission.session_mode

    if mode == SessionMode.ACCESSIBILITY:
        wcag_issues = [v for v in verified_issues if "[WCAG]" in v.description]
        other_issues = [v for v in verified_issues if "[WCAG]" not in v.description]
        impact_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for v in wcag_issues:
            impact_counts[v.severity] = impact_counts.get(v.severity, 0) + 1
        a11y_lines = [
            "### Accessibility Summary",
            "",
            f"- **Total WCAG violations:** {len(wcag_issues)}",
            f"- Critical: {impact_counts['critical']} | High: {impact_counts['high']} | "
            f"Medium: {impact_counts['medium']} | Low: {impact_counts['low']}",
            f"- **Pages audited:** {len(set(v.url for v in wcag_issues))}",
            f"- **Standard:** WCAG 2.1 AA (axe-core automated scan)",
            "",
            "All violations were automatically detected by axe-core and are confirmed defects,",
            "not hypotheses. Fix critical and high issues first — they block assistive technology users.",
            "",
        ]
        if other_issues:
            a11y_lines += [
                "### Additional Manual Findings",
                "",
                *(f"- **[{v.severity.upper()}]** {v.description}" for v in other_issues),
                "",
            ]
        lines += ["## Accessibility Audit (WCAG 2.1 AA)", ""] + a11y_lines + ["---", ""]

    if mode == SessionMode.MOBILE:
        lines += ["## Mobile Test Summary", "", _mobile_section(mission, verified_issues), "", "---", ""]

    if mode == SessionMode.NETWORK and network_events is not None:
        lines += ["## Network Audit", "", _network_section(network_events), "", "---", ""]

    if mode == SessionMode.API:
        lines += ["## API Test Results", "", _api_section(api_results or [], api_summary), "", "---", ""]

    if mode == SessionMode.LOAD_PERFORMANCE and (perf_metrics is not None or load_test_results):
        lines += [
            "## Performance Metrics", "",
            _perf_section(perf_metrics or [], load_test_results),
            "", "---", "",
        ]

    # ── UX section (skip for modes where it doesn't add value) ────────────────
    ux_analysis_text = ""
    if mode in (SessionMode.UI_UX, SessionMode.FUNCTIONAL, SessionMode.ALL_FLOWS,
                SessionMode.SPECIFIC_FLOW, SessionMode.REGRESSION, SessionMode.MOBILE,
                SessionMode.ACCESSIBILITY):
        ux_analysis_text = _ux_section(journey_screenshots, target_url)
        lines += ["## UX Analysis", "", ux_analysis_text, "", "---", ""]

    # ── Action Log ────────────────────────────────────────────────────────────
    lines += ["## Action Log", ""]
    for s in steps:
        bug_note = ""
        if s.verified_issues:
            bug_note = " — **BUG:** " + "; ".join(vi.description[:60] for vi in s.verified_issues)
        lines.append(
            f"**Step {s.step}** `{s.url}`  \n"
            f"_{s.action}_ → `{s.target_text}` | {s.reasoning[:90]}"
            f"{bug_note}\n"
        )

    return "\n".join(lines), ux_analysis_text
