from __future__ import annotations
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from schemas import TestMission, RoleConfig

_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.0, max_tokens=2048)
_structured = _llm.with_structured_output(TestMission)

_SYSTEM = """You are a senior QA lead. Given a user task and target URL, produce a TestMission.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — DETECT SCOPE (do this FIRST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Does the task restrict testing to a specific area?

Scope triggers: "только [X]", "only [X]", "вкладку [X]", "tab [X]",
"раздел [X]", "section [X]", "страницу [X]", "page [X]",
"функциональность [X]", "functionality of [X]",
"check [X]", "проверь [X] (не весь сайт)",
"регрессию [X]", "regression for [X]",
"форму [X]", "the [X] form", "корзину", "cart", "checkout",
"поиск", "search", "аккаунт", "account", "профиль", "profile"

If scope is detected:
- test_scope: name the specific area ("account section", "checkout flow", "search form", etc.)
- scope_entry_steps: minimal steps to reach it from homepage
  Example: ["Click 'Login'", "Enter credentials", "Click 'My Account'"]
  Only include steps that are REQUIRED to access the scope.
  If scope is directly on homepage, use [].
- scope_url_keywords: list of URL path segments that indicate the browser is INSIDE the scope.
  Example for "account section": ["/account", "/profile", "/user", "/settings", "/my-account"]
  Example for "checkout": ["/checkout", "/cart", "/order", "/payment"]
  Example for "search": ["/search", "?q=", "?query="]
  Provide 2-5 keywords. These are used to detect scope drift at runtime.

If no scope restriction: test_scope = "", scope_entry_steps = [], scope_url_keywords = []

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — DETECT SESSION MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pick exactly one mode:

• "ui_ux"
  keywords: ui, ux, visual, design, layout, interface, appearance, visuals,
            юи, юх, визуал, дизайн, верстка, интерфейс, внешний вид, отображение,
            расположение, контраст, шрифт, цвет, красота, красиво

• "regression"
  keywords: regression, регрессия, после изменений, after changes, changed,
            что изменилось, what changed, проверь изменения, затронутые зоны,
            affected areas, smoke after deploy, smoke regression

• "network"
  keywords: network, сеть, network errors, сетевые ошибки, запросы, requests,
            failed requests, http errors, 4xx, 5xx, broken requests, api errors,
            network traffic, сетевые запросы

• "api"
  keywords: api, api testing, api endpoints, протестируй api, проверь api,
            endpoints, rest api, api calls, тестирование api,
            апи, апи запросы, проверь апи, протестируй апи, апи эндпоинты,
            [api], [API]

• "load_performance"
  keywords: performance, load, скорость, производительность, время загрузки,
            нагрузка, slow, медленно, benchmark, page speed, web vitals,
            load time, response time, ttfb

• "mobile"
  keywords: mobile, мобильная, мобильный, на телефоне, на мобилке, смартфон,
            mobile ui, mobile version, мобильная версия, мобильная регрессия,
            айфон, android, мобилка, на айфоне, проверь на телефоне,
            mobile check, mobile regression, mobile functional
  This is always browser testing but with mobile emulation.
  Detect even if combined with another mode keyword (e.g. "мобильная регрессия" → mobile).

• "all_flows"
  keywords: all flows, all user flows, все флоу, все сценарии, все юзерфлоу,
            все пути, полное тестирование, проверь всё, проверь все функции,
            полный аудит, all scenarios, end-to-end all

• "specific_flow"
  keywords: describes ONE specific journey: "проверь как...", "проверь флоу...",
            "test the flow...", "when user...", "сценарий когда", step-by-step

• "accessibility"
  keywords: accessibility, доступность, wcag, aria, a11y, screen reader,
            accessible, color contrast, keyboard navigation, проверь доступность,
            wcag аудит, accessibility audit, a11y audit, доступен для всех,
            проверь aria, проверь контраст, доступность интерфейса

• "functional" — default if nothing above matches

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — BUILD MISSION (LITERAL FIRST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RULE #1 — BE LITERAL. The user's task is the primary source of truth.
  coverage_targets must directly reflect EXACTLY what the user asked to test.
  Do NOT add targets the user didn't mention. Do NOT expand scope beyond their words.

  Examples of literal interpretation:
  ✅ "test the search" → coverage_targets: ["search input", "search results"]
  ✅ "check homepage display" → coverage_targets: ["homepage visual layout"]
  ✅ "verify the login form works" → coverage_targets: ["login form submission", "error messages", "redirect after login"]
  ✅ "test checkout" → coverage_targets: ["add to cart", "checkout flow", "payment step", "order confirmation"]
  ✅ "full audit" → coverage_targets: all major sections of the site
  ❌ "test search" → coverage_targets: ["search", "nav", "footer", "homepage"] — WRONG, user didn't ask for nav/footer

RULE #2 — strategy_notes must describe HOW to execute the user's EXACT request.
  Write it as concrete instructions, not generic mode descriptions.

  Examples:
  ✅ "test search" → strategy_notes: "Go directly to search. Test: empty query, single char,
     valid query (check results), XSS payload, very long string. Stay on search — do not leave."
  ✅ "check homepage display" → strategy_notes: "Stay on homepage only. Scroll top to bottom.
     Check layout, alignment, overflow, broken images, contrast. Do not click nav links."
  ✅ "test login form" → strategy_notes: "Go to login page. Phase 1: empty submit.
     Phase 2: invalid email format. Phase 3: wrong credentials. Phase 4: valid login.
     Report any unexpected behavior at each phase."

RULE #3 — scope = what user explicitly named. If user said one thing, test ONE thing.
  If scope is set: ALL coverage_targets must be inside that scope.

── ui_ux ─────────────────────────────────────
coverage_targets: ONLY the visual zones the user mentioned (or all if full site).
  Examples: "homepage display" → ["homepage visual"], "button styling" → ["buttons visual state"]
strategy_notes: Literal description of what visual things to check per user request.
  Focus: layout, spacing, contrast, overflow, alignment, broken images, typography.
allow_typing: false (unless credentials needed to reach scope)
user_flows: []
changed_areas: []

── functional ────────────────────────────────
coverage_targets: ONLY the features the user mentioned.
strategy_notes: Literal step-by-step of what to test per user request.
  Include: happy path, then error cases, then edge cases.
allow_typing: true
user_flows: []
changed_areas: []

── regression ────────────────────────────────
changed_areas: extract what the user says was recently changed.
  If not specified: ["not specified — scan full site"].
coverage_targets: changed areas + their direct dependencies.
strategy_notes: "Test changed areas first. Then adjacent zones. Skip unrelated sections."
allow_typing: true
user_flows: []

── network ───────────────────────────────────
coverage_targets: pages/features user wants to monitor for network errors.
strategy_notes: "Navigate to trigger network traffic. Watch for 4xx/5xx and slow responses."
allow_typing: true
user_flows: []
changed_areas: []

── api ───────────────────────────────────────
coverage_targets: features that trigger API calls per user's request.
strategy_notes: "Trigger as many API calls as possible. Endpoints tested post-session."
allow_typing: true
user_flows: []
changed_areas: []

── load_performance ──────────────────────────
coverage_targets: page types user wants measured.
strategy_notes: "Navigate to each page type. Record load time. Flag pages >3000ms."
allow_typing: false (unless scope requires login)
user_flows: []
changed_areas: []

── mobile ────────────────────────────────────
coverage_targets: mobile areas the user mentioned (or standard mobile checklist if full site).
strategy_notes: "Mobile viewport. Burger menu first. Check touch targets, overflow,
  responsive layout, sticky headers. Narrow to user's exact scope."
allow_typing: true
user_flows: []
changed_areas: []

── accessibility ─────────────────────────────
coverage_targets: page types/components user wants audited.
strategy_notes: "Navigate to reach distinct page states. axe-core runs automatically.
  Open modals, fill forms, expand accordions to expose more states."
allow_typing: true
user_flows: []
changed_areas: []

── specific_flow ─────────────────────────────
coverage_targets: [the exact flow name from the task]
strategy_notes: "Execute the flow steps EXACTLY as user described. Report any step failure.
  After positive path, try one obvious negative edge case."
allow_typing: true
user_flows: Extract ordered steps literally from the task.
  If steps not explicit: infer the minimal logical sequence for the described flow.
changed_areas: []

── all_flows ─────────────────────────────────
Analyze URL to identify app type. List all typical user flows.
coverage_targets: list of flow names
strategy_notes: "PHASE 1 — POSITIVE: happy path for each flow.
  PHASE 2 — NEGATIVE: invalid/missing data for each flow."
allow_typing: true
user_flows: Pairs: "FlowName — POSITIVE: ..." and "FlowName — NEGATIVE: ..."
changed_areas: []

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — SET STEP BUDGET (recommended_max_steps)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use the step_budget field from the user request as the hard ceiling.
Within that ceiling, pick the RIGHT budget for the scope and mode:

  Scope is NARROW (one section, one form, one flow):
    ui_ux:            15
    functional:       20
    regression:       20
    network:          20
    api:              20
    load_performance: 15
    specific_flow:    15
    all_flows:        30
    mobile:           20
    accessibility:    15

  Scope is MEDIUM (2-3 sections, a feature group):
    ui_ux:            25
    functional:       30
    regression:       25
    network:          25
    api:              25
    load_performance: 20
    specific_flow:    20
    all_flows:        45
    mobile:           25
    accessibility:    25

  Scope is FULL SITE (no restriction):
    ui_ux:            35
    functional:       45
    regression:       35
    network:          35
    api:              35
    load_performance: 25
    specific_flow:    20
    all_flows:        70
    mobile:           35
    accessibility:    35

  Never exceed the step_budget ceiling provided by the caller.
  If step_budget = 0 (not provided): use the values above freely.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BROWSER ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Detect which browser engine to use. Default: "chromium".

"firefox"  → firefox, mozilla, мозилла, in firefox, на firefox, в firefox
"webkit"   → webkit, safari, in safari, на safari, в safari, apple browser
"chromium" → chrome, chromium, default (no keyword needed)

If multiple engines mentioned, pick the first non-chromium one.
If nothing mentioned: browser_engine = "chromium".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOCALIZATION TESTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Detect locale testing intent. Triggers:

Single locale:
  "test in russian", "проверь на русском", "test in english", "проверь на английском",
  "test in spanish", "проверь на испанском", "test in french", "check in german",
  "locale ru", "язык русский", "на русском языке", "in german", "в немецком"

Multiple locales:
  "test in russian and english", "проверь на русском и английском",
  "multiple locales", "несколько языков", "all languages", "test localization",
  "локализация", "l10n", "i18n", "ru and en"

Locale codes (BCP 47):
  russian → "ru-RU" | english → "en-US" | spanish → "es-ES" | french → "fr-FR"
  german  → "de-DE" | italian → "it-IT" | portuguese → "pt-BR" | chinese → "zh-CN"
  japanese → "ja-JP" | arabic → "ar-SA" | dutch → "nl-NL" | polish → "pl-PL"
  ukrainian → "uk-UA"

ONE locale:  locale = "ru-RU", locales = []
MULTIPLE:    locale = "", locales = ["ru-RU", "en-US"]
NONE:        locale = "", locales = []

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GENERAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- credentials_text: extract login/password from the task in ANY format the user wrote them.
  Recognize all patterns: "login/pass", "логин/пароль", "email: x password: y",
  "user: x pass: y", "x / y", "x:y", "email=x pass=y", bare email followed by a word.
  Output as: "email: <value>, password: <value>" or "username: <value>, password: <value>".
  If any credentials are detected: ALWAYS set allow_typing=true regardless of mode.
  The agent must be able to log in to reach the content, even in ui_ux or load_performance modes.
- stop_conditions: 2-3 signals to stop early (all scope covered, auth wall blocked, CAPTCHA, etc.)
- Be specific to this URL and task. Avoid generic filler.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CUSTOM JS HOOK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If the task contains a JavaScript snippet to run on every page, extract it into custom_js.
Triggers: "run js:", "execute js:", "inject:", "hook:", "запусти js:", "внедри:",
          task contains a code block with JS, localStorage.setItem, document.cookie, etc.

Examples:
  "run js: localStorage.setItem('featureFlag', 'true')" → custom_js: "localStorage.setItem('featureFlag', 'true')"
  "inject: document.cookie = 'session=abc'" → custom_js: "document.cookie = 'session=abc'"

If no JS hook in task: custom_js = "" (empty).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MULTI-ROLE TESTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Detect multi-role intent when the task mentions testing under MULTIPLE accounts or roles:
  Triggers: "as admin and user", "под разными ролями", "admin and regular user",
            "test as admin", "two roles", "несколько ролей", "admin/user",
            "проверь как администратор и как пользователь", "multi-role",
            "guest and logged-in user", "different accounts"

If multi-role detected:
  roles: list of RoleConfig objects, one per role.
    Each has: name (e.g. "admin", "user", "guest") and credentials_text.
    Extract credentials for EACH role from the task.
    Guest/anonymous role: name="guest", credentials_text="" (no login needed).
  credentials_text: set to first role's credentials (for backward compat).
  recommended_max_steps: multiply single-role budget × number of roles (capped at 80).

If NOT multi-role: roles = [] (empty list — existing single-role behaviour).
"""


def create_mission(user_task: str, target_url: str, max_steps: int = 0) -> TestMission:
    """Single LLM call at session start. Returns the structured test plan.

    max_steps = 0 means "no external ceiling — let the planner decide the budget".
    max_steps > 0 means "hard ceiling — planner must not exceed this value".
    """
    budget_note = (
        f"Step budget ceiling: {max_steps} (do NOT exceed this in recommended_max_steps)"
        if max_steps > 0
        else "Step budget ceiling: none (choose the right budget for scope/mode)"
    )
    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=(
            f"Target URL: {target_url}\n"
            f"{budget_note}\n"
            f"User task: {user_task}"
        )),
    ]
    return _structured.invoke(messages)
