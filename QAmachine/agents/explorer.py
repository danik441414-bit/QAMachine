from __future__ import annotations
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from schemas import PageContext, NavigationDecision, NavAction, SessionMode
from agents.mobile_engine import mobile_mode_rules

_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.1, max_tokens=1024)
_structured = _llm.with_structured_output(NavigationDecision)

_BASE_SYSTEM = """You are an autonomous senior QA engineer controlling a real browser.
Your job: explore websites systematically and find real bugs. You must handle ANY website.

Each step: screenshot + filtered DOM (qa-id numbers) + aria snapshot + history + mission.

══════════════════════════════════════════════════════════════
DECISION PROTOCOL (follow strictly, in this order)
══════════════════════════════════════════════════════════════

STEP 0 — CLEAR BLOCKERS FIRST (before any testing)
  Cookie/GDPR consent banner visible? → click Accept/OK/Agree FIRST
  Newsletter popup or modal overlay? → click X or Close FIRST
  Chat widget covering content? → click to minimize FIRST
  Age verification gate? → confirm/proceed FIRST
  Only after clearing blockers: proceed with actual testing

STEP 1 — LOGIN WALL DETECTION (if credentials provided)
  If you see a login/sign-in form AND credentials are in "Typing rule":
    → type email/username into the email field
    → type password into the password field
    → click the Login/Sign In/Submit button (do NOT press Enter — click the button)
  If login fails (error message appears): report it as a bug, then try go_to_main
  If site requires OAuth (Google/Facebook login): note it in suspected_issues, use go_to_main
  If CAPTCHA appears: note it in suspected_issues, use go_to_main
  NEVER loop go_to_main when a login form is visible — ALWAYS try to fill it

STEP 2 — PAGE ASSESSMENT
  Classify page_type. Read action_history — avoid repeating explored areas.
  Check: did the previous action have any effect? (URL changed? Content updated?)
  If a click had no visible effect: try a different element, not the same one again

STEP 3 — SMART NAVIGATION
  New tab opened? → it will be handled — treat current page as unchanged
  URL didn't change after click? → content may have updated in place (SPA) — that's ok
  Hover menus you can't open? → note if menu items are invisible, click alternatives
  Lazy content? → use scroll_down to reveal more elements before declaring page exhausted
  Bottom of page reached with no new content? → go_to_main or use 'done'

STEP 4 — CHOOSE BEST ACTION
  Priority: unexplored meaningful content > scroll to reveal more > go_to_main > done
  Never repeat the same action on the same element twice
  Never choose go_to_main more than 2 times consecutively

══════════════════════════════════════════════════════════════
DROPDOWN STRATEGY
══════════════════════════════════════════════════════════════
  [+▼] = has hidden submenu → click to reveal, then explore each sub-item
  [▼ OPEN] = submenu open → click sub-items directly
  [▶HIDDEN] = needs parent [+▼] opened first
  After a dropdown: explore ALL sub-items before moving on

══════════════════════════════════════════════════════════════
OUTPUT CONTRACT — strictly enforced
══════════════════════════════════════════════════════════════
  action:         click | type | go_to_main | press_key | scroll_down | done
  target_id:      NUMBER from available elements (NEVER empty for click/type)
  value_to_type:  non-empty string when action=type
  done:           only when ALL coverage_targets satisfied OR site is fully exhausted
  go_to_main:     reset to homepage — NEVER use 3+ times in a row (it is a loop)
  If action_history shows 3+ consecutive go_to_main → choose 'done' immediately"""


# ── Scope enforcement ─────────────────────────────────────────────────────────

def _scope_block(mission) -> str:
    if not mission.test_scope:
        return ""

    entry = "\n".join(f"  {s}" for s in mission.scope_entry_steps) if mission.scope_entry_steps else "  (navigate logically from current page)"

    return f"""
━━ SCOPE RESTRICTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOU ARE ONLY TESTING: {mission.test_scope}

⛔ DO NOT visit: homepage content, unrelated sections, other nav tabs,
   or ANY page outside this scope.
   EXCEPTION: you may pass through required pages to REACH the scope.

Steps to reach the scope (if not already there):
{entry}

Once inside the scope: test it thoroughly and stay there.
If you accidentally leave the scope: use go_to_main then re-navigate to scope.
Use 'done' when the scope has been fully tested — not when the whole site is done.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""


# ── Mode-specific strategy blocks ─────────────────────────────────────────────

def _mode_rules(mission) -> str:
    mode = mission.session_mode
    flows = mission.user_flows
    changed = mission.changed_areas

    if mode == SessionMode.UI_UX:
        return """
━━ MODE: UI/UX AUDIT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Find VISUAL and LAYOUT defects only. Your job is to LOOK, not to test features.

✅ Look for: overflow text, overlapping elements, broken/missing images,
   misaligned items, poor contrast, invisible CTAs, layout breaking at scroll,
   unreadable typography, inconsistent spacing, broken menus, cut-off content,
   elements behind other elements, wrong z-index, horizontal scrollbar appearing.

❌ STRICTLY FORBIDDEN:
   - Do NOT submit any form to check if it works
   - Do NOT test if buttons produce correct results
   - Do NOT fill in search fields to test search functionality
   - Do NOT test any feature behavior
   EXCEPTION: You MAY type login credentials if site is behind a login wall —
   but ONLY to get past the wall. After login: switch back to visual-only testing.

NAVIGATION STRATEGY for UI/UX:
   - Visit each DISTINCT PAGE TYPE (homepage, list/category, detail/product, forms, modals)
   - On each page: scroll to bottom to see full layout
   - Click nav links to reach different page types — do NOT click functional buttons
   - Report ONLY what you can visually see as wrong, never invent functional failures
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    if mode == SessionMode.FUNCTIONAL:
        return """
━━ MODE: FUNCTIONAL TESTING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Verify features work correctly.

✅ Test: buttons produce expected results, forms submit, navigation works,
   search/filters return results, CRUD completes, modals open/close,
   tabs switch, error messages appear on invalid input.
❌ Do NOT report cosmetic issues (colors, minor spacing).

suspected_issues = functional failures: wrong behavior, broken feature, errors.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    if mode == SessionMode.REGRESSION:
        changed_str = ", ".join(changed) if changed else "unknown (scan broadly)"
        return f"""
━━ MODE: REGRESSION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Changed areas: {changed_str}

PRIORITY ORDER:
1. Test the changed areas FIRST — check they work correctly after changes.
2. Test neighboring/dependent zones — areas that interact with what changed.
3. Run a quick smoke check on related user flows.
4. DO NOT spend time on unrelated sections of the site.

suspected_issues = regressions (things that broke due to the change) + pre-existing
issues in changed zones. Note which area the issue is in.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    if mode == SessionMode.NETWORK:
        return """
━━ MODE: NETWORK AUDIT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Monitor network requests during UI interactions.

STRATEGY: Navigate to key pages and interact with features to generate traffic.
After each action, check the NETWORK ERRORS section in your context.

✅ Flag as suspected_issue if you see:
   - 4xx or 5xx responses in network_errors
   - Console errors mentioning failed requests
   - Page behavior broken after a network failure (blank section, spinner stuck)
   - Patterns of repeated errors on the same endpoint

Navigate breadth-first: visit each main section to trigger its data loads.
suspected_issues = network failures that visibly impact user experience.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    if mode == SessionMode.API:
        return """
━━ MODE: API COLLECTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Navigate and interact to trigger as many unique API calls as possible.

STRATEGY: Use features that load data (search, filters, CRUD, user management,
forms submission) — these trigger the most API calls.
Don't repeat the same action; explore breadth-first to maximize API coverage.

Note in suspected_issues any visible API failures (errors, empty data, crashes).
The actual API endpoint testing will happen automatically after this session.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    if mode == SessionMode.LOAD_PERFORMANCE:
        return """
━━ MODE: PERFORMANCE AUDIT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Measure page load times across key page types.

STRATEGY: Navigate to each key page type (homepage, listing, detail, dashboard,
search, forms). Minimal interaction needed — just load the page and move on.
Check page_load_ms in your context after each navigation.

✅ Flag as suspected_issue if:
   - page_load_ms > 3000 (slow page load)
   - Console shows resource errors (CSS/JS/images failed to load)
   - Page visibly renders broken due to slow/failed resources

Focus on BREADTH: visit as many distinct page types as possible.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    if mode == SessionMode.SPECIFIC_FLOW:
        steps_str = "\n".join(f"  {s}" for s in flows) if flows else "  (infer steps from mission)"
        return f"""
━━ MODE: SPECIFIC FLOW TEST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Execute EXACTLY this flow, in strict order. Do NOT deviate.

FLOW STEPS:
{steps_str}

Track which step you are on via action_history.
Report unexpected results as suspected_issues and continue.
After completing all steps, try one negative edge case.
Use 'done' when the full flow (+ edge case) is complete.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    if mode == SessionMode.MOBILE:
        device_name  = mission.mobile_config.device_name if mission.mobile_config else "iPhone 12"
        check_type   = "functional"
        # Infer check type from strategy_notes if regression/ui_ux hint present
        notes_lower  = mission.strategy_notes.lower()
        if "regression" in notes_lower:
            check_type = "regression"
        elif "visual" in notes_lower or "layout" in notes_lower or "ui" in notes_lower:
            check_type = "ui_ux"
        return mobile_mode_rules(device_name, check_type)

    if mode == SessionMode.ALL_FLOWS:
        flows_str = "\n".join(f"  {f}" for f in flows) if flows else "  (discover from site structure)"
        return f"""
━━ MODE: ALL USER FLOWS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1 — POSITIVE: happy path for every flow (valid data, verify success).
PHASE 2 — NEGATIVE: failure cases (invalid/missing data, verify proper errors).

FLOWS (in order):
{flows_str}

Track in reasoning: which flow + which phase (POSITIVE/NEGATIVE) you're executing.
Complete ALL positive flows first, then ALL negative flows.
Between flows: use go_to_main to reset. Use 'done' only when all phases complete.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    return ""


# ── Main decision function ─────────────────────────────────────────────────────

def decide(ctx: PageContext) -> NavigationDecision:
    """One LLM call per step. ctx.dom_elements must already be filtered by CoverageTracker.

    Cost optimisation: the static system prompt (BASE_SYSTEM + mode rules + mission config)
    is sent with cache_control=ephemeral so Anthropic caches it across all steps of a session.
    Only the dynamic context (history, DOM, errors, screenshot) is re-sent uncached each step.
    """
    # Cap at 60 elements — more causes LLM confusion and wastes tokens
    capped_elements = ctx.dom_elements[:60]
    dom_lines = "\n".join(
        f"[{el.id}] {el.tag} | '{el.text}'" for el in capped_elements
    ) or "(no interactive elements visible)"

    history   = "\n".join(ctx.action_history) or "First step — log is empty."
    console   = "\n".join(ctx.console_errors) or "None."
    network   = "\n".join(ctx.network_errors) or "None."
    visited   = "\n".join(list(ctx.visited_urls)[-20:]) or "None."
    load_info = f"{ctx.page_load_ms} ms" if ctx.page_load_ms else "not measured"

    has_creds = bool(ctx.mission.credentials_text)
    if ctx.mission.allow_typing:
        typing_rule = f"Typing IS allowed. Credentials if needed: {ctx.mission.credentials_text}"
    elif has_creds:
        # Mode restricts typing, but credentials exist → allow typing on login pages only
        typing_rule = (
            f"Typing is restricted to LOGIN FORMS ONLY. "
            f"On login/signin pages: type credentials: {ctx.mission.credentials_text}. "
            f"On all other pages: do NOT type."
        )
    else:
        typing_rule = "Typing is FORBIDDEN. Never use action='type'."

    # ── Static part (constant for entire session) → cached by Anthropic ──────
    static_text = "\n".join([
        _BASE_SYSTEM,
        "",
        _scope_block(ctx.mission),
        _mode_rules(ctx.mission),
        "",
        f"MISSION STRATEGY: {ctx.mission.strategy_notes}",
        f"Coverage targets: {', '.join(ctx.mission.coverage_targets)}",
        f"Stop conditions: {', '.join(ctx.mission.stop_conditions)}",
        f"Typing rule: {typing_rule}",
    ])

    # ── Dynamic part (changes every step) → never cached ─────────────────────
    # Count consecutive go_to_main in recent history to warn LLM
    recent_actions = [s.split(":")[1].strip().split(" ")[0] if ":" in s else "" for s in ctx.action_history[-5:]]
    go_to_main_streak = sum(1 for a in reversed(recent_actions) if a == "go_to_main")
    stuck_note = ""
    if ctx.url_stay_count >= 5:
        stuck_note = f"\n⚠️  STUCK: {ctx.url_stay_count} steps on same URL. Choose a different page or action.\n"
    if go_to_main_streak >= 3:
        stuck_note += f"\n🔴 LOOP DETECTED: {go_to_main_streak} consecutive go_to_main. Choose 'done' NOW — session is complete.\n"

    # Show credentials reminder whenever agent has them — not just when looping
    creds_hint = ""
    if ctx.mission.credentials_text:
        creds_hint = f"\n🔑 LOGIN CREDENTIALS AVAILABLE: {ctx.mission.credentials_text}\n   If a login/signin form is visible → TYPE these credentials and click Submit.\n"
    dynamic_text = "\n".join([
        f"ACTION HISTORY (last 10):\n{history}",
        "",
        f"CONSOLE ERRORS:\n{console}",
        f"NETWORK ERRORS (this step):\n{network}",
        f"PAGE LOAD TIME: {load_info}",
        "",
        f"VISITED URLS (recent 20):\n{visited}",
        "",
        f"CURRENT URL: {ctx.current_url}",
        f"URL STAY COUNT: {ctx.url_stay_count}",
        stuck_note,
        creds_hint,
        "",
        f"AVAILABLE ELEMENTS:\n{dom_lines}",
        "",
        f"ARIA SNAPSHOT:\n{ctx.aria_snapshot[:1500]}",
        "",
        "Analyze the screenshot and decide your next action.",
    ])

    messages = [
        SystemMessage(content=[{
            "type": "text",
            "text": static_text,
            "cache_control": {"type": "ephemeral"},
        }]),
        HumanMessage(content=[
            {"type": "text", "text": dynamic_text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{ctx.screenshot_b64}"},
            },
        ]),
    ]
    return _structured.invoke(messages)
