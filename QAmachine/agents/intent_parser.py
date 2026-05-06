"""
Intent Parser — fast pre-routing LLM call.

Classifies the user request into one of 4 intents and extracts
all the routing metadata (scope, device, doc_type, test_type, credentials).
This runs BEFORE the planner and determines which execution path to take.
"""
from __future__ import annotations
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from schemas import IntentResult, Intent

_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.0, max_tokens=512)
_structured = _llm.with_structured_output(IntentResult)

_SYSTEM = """You are an intent classifier for a QA automation system called QAmachine.

Your job: read the user's task and classify it into exactly ONE intent, then extract metadata.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTENT DETECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. "browser_test"   — standard QA session (UI/UX, functional, regression, network, API, perf, accessibility)
   Triggers: проверь, протестируй, сделай регрессию, проверь функциональность,
             check, test, verify, audit, regression, ux audit, проверь сеть,
             проверь api, проверь производительность, network check, api test,
             accessibility, доступность, wcag, aria, a11y, screen reader,
             accessible, color contrast, keyboard navigation, проверь доступность,
             wcag аудит, accessibility audit, a11y audit
   NOT mobile-specific. NOT doc generation. NOT automation.

2. "mobile_test"    — testing ON A MOBILE DEVICE / mobile viewport
   Triggers (ANY of these = mobile_test):
     мобильная версия, мобильный, на мобилке, на телефоне, на смартфоне,
     mobile, mobile ui, mobile version, mobile check, mobile regression,
     мобильная регрессия, проверь мобилку, проверь на телефоне,
     на айфоне, на android, мобильная функциональность
   This is a browser test but run with mobile emulation.

3. "generate_docs"  — generate QA documentation (test cases, checklist, test plan)
   Triggers: тест кейсы, test cases, чек лист, checklist, тест план, test plan,
             напиши, составь документ, сгенерируй тест кейсы, сделай чеклист,
             написать тест, чеклист для, кейсы для, план для,
             test documentation, qa docs, test cases for, checklist for

4. "generate_automation" — generate Playwright automated test file (.py)
   Triggers: playwright test, автотест, автоматический тест, e2e test,
             сгенерируй тест, generate test, сделай автотест, playwright тест,
             сгенерируй playwright, create automation, automation test,
             e2e automation, automated scenario

5. "compare_envs"   — compare two environments (staging vs production, two URLs)
   Triggers: compare, сравни, сравнить, сравнение, compare with, vs, versus,
             стейджинг vs прод, staging vs prod, staging vs production,
             найди разницу, find differences, что изменилось между,
             compare environments, two urls, два урла, сравни урлы,
             compare staging, compare production, diff between

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCOPE DETECTION (applies to ALL intents)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Extract the specific area the user is targeting.

Scope keywords and their canonical names:
  аккаунт / account / профиль / profile / кабинет / my account → "account section"
  checkout / оформление заказа / оплата / payment → "checkout flow"
  корзина / cart / basket / bag → "cart"
  login / вход / авторизация / sign in → "login form"
  регистрация / registration / sign up → "registration form"
  поиск / search → "search"
  товар / product / product page / страница товара → "product page"
  главная / homepage / home → "homepage"
  категория / catalog / category / listing → "category page"
  настройки / settings → "settings"
  форма / form + context → "{context} form"

If NO specific scope: test_scope = "" (full site or full app)

scope_url_keywords — URL path segments likely for this scope:
  "account section"     → ["/account", "/profile", "/user", "/my-account", "/cabinet"]
  "checkout flow"       → ["/checkout", "/order", "/payment", "/purchase"]
  "cart"                → ["/cart", "/basket", "/bag"]
  "login form"          → ["/login", "/signin", "/auth", "/sign-in"]
  "registration form"   → ["/register", "/signup", "/registration", "/sign-up"]
  "search"              → ["/search", "?q=", "?query=", "/results", "/find"]
  "product page"        → ["/product", "/item", "/p/", "/goods"]
  "homepage"            → [] (it's the root)
  "category page"       → ["/category", "/catalog", "/c/", "/shop"]
  "settings"            → ["/settings", "/preferences", "/config"]

scope_entry_steps — minimal steps to REACH the scope from homepage:
  "account section":    ["Click Login / Sign In", "Enter credentials", "Click My Account / Profile"]
  "checkout flow":      ["Add item to cart", "Click Checkout"]
  "cart":               ["Click Cart icon"]
  "login form":         ["Click Login"]
  "registration form":  ["Click Register / Sign Up"]
  If scope is reachable directly (search bar, homepage): []

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MOBILE-SPECIFIC FIELDS (mobile_test only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

device_name — extract from task if mentioned, default "iPhone 12":
  iPhone 12 / iphone 12 / айфон 12       → "iPhone 12"
  iPhone SE / iphone se / айфон se       → "iPhone SE"
  iPhone 14 Pro / iphone 14 pro          → "iPhone 14 Pro"
  Pixel 5 / pixel 5 / пиксель 5          → "Pixel 5"
  Galaxy S21 / samsung s21 / galaxy      → "Galaxy S21"
  iPad / айпад / планшет / tablet        → "iPad"
  Any Android / android / андроид        → "Pixel 5"
  No device mentioned                    → "iPhone 12"

mobile_check_type — what kind of check:
  visual / ui / ux / дизайн / layout     → "ui_ux"
  regression / регрессия                 → "regression"
  Default                                → "functional"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GENERATE_DOCS FIELDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

doc_type:
  "test_cases"  if: тест кейс, test case, кейсы, кейс, test cases
  "checklist"   if: чеклист, чек лист, checklist, check list
  "test_plan"   if: тест план, test plan, план тестирования
  Default: "test_cases"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GENERATE_AUTOMATION FIELDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

automation_test_type:
  "smoke"       if: smoke, смоук, базовый, basic, минимальный
  "regression"  if: regression, регрессия, regression test
  "mobile"      if: mobile, мобильный
  Default: "functional"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPARE_ENVS FIELDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

comparison_url — the SECOND URL mentioned in the task (the one to compare against).
  The primary URL is always provided separately. Extract only the second URL from the task text.
  Examples:
    "compare https://staging.site.com with https://site.com" → "https://site.com"
    "сравни https://staging.site.com и https://prod.site.com" → "https://prod.site.com"
    "compare with https://staging.myapp.com" → "https://staging.myapp.com"
  If no second URL found in task: "" (user will be prompted)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREDENTIALS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Extract login/password from the task literally.
Format: "username: X, password: Y" — or "" if none.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHANGED AREAS (regression only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

List what the user says was recently changed. Empty for non-regression tasks.
"""


def parse(user_task: str, target_url: str) -> IntentResult:
    """Single fast LLM call. Returns intent + all routing metadata."""
    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=(
            f"Target URL: {target_url}\n"
            f"User task: {user_task}"
        )),
    ]
    return _structured.invoke(messages)
