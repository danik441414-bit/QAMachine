"""
Playwright Test Generator.

Generates a complete, runnable pytest-playwright Python test file
for a given site scope and test type.

Flow:
  1. page_scanner.quick_scan() — capture page state (screenshot + DOM + aria)
  2. LLM call → complete Python test file
  3. Strip markdown fences if LLM wrapped output
  4. Caller saves the result via artifact_writer

Generated tests use:
  - pytest class structure
  - Playwright sync API
  - Role/text/label selectors (accessible, stable)
  - expect() assertions
  - No hard sleeps — only Playwright built-in waiting
"""
from __future__ import annotations
import asyncio
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from schemas import IntentResult, AutomationTestType
from agents.page_scanner import quick_scan, PageSnapshot

_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.1, max_tokens=5000)

_SYSTEM = """You are a senior QA automation engineer.
Generate a COMPLETE, RUNNABLE pytest-playwright test file in Python.

OUTPUT: Return ONLY the Python source code — no markdown, no explanations, no code fences.

FILE STRUCTURE:
```
import re
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://example.com"


class Test{ScopePascalCase}:

    def test_{scenario_name}(self, page: Page) -> None:
        \"\"\"One-line description of what this test verifies.\"\"\"
        page.goto(BASE_URL)
        # ... steps ...
        expect(page.locator(...)). ...

    def test_{another_scenario}(self, page: Page) -> None:
        ...
```

SELECTOR PRIORITY (use in this order — stop at the first that works):
1. page.get_by_role("button", name="Submit")          — semantic + stable
2. page.get_by_text("Sign In")                        — visible text
3. page.get_by_label("Email address")                 — form label
4. page.get_by_placeholder("Enter your email")        — placeholder
5. page.locator("#specific-id")                       — stable id
6. page.locator("[data-testid='submit']")              — test attribute
7. page.locator(".stable-class-name")                 — only if truly stable
8. NEVER use: xpath, nth-child, positional CSS

ASSERTIONS — always use expect():
  expect(element).to_be_visible()
  expect(element).to_be_enabled()
  expect(element).to_have_text("Expected Text")
  expect(element).to_have_value("input value")
  expect(page).to_have_url(re.compile(r"/dashboard"))
  expect(page).to_have_title(re.compile(r"Success"))
  expect(element).to_contain_text("partial text")
  expect(element).not_to_be_visible()

NAVIGATION & WAITS:
  page.goto(url)                                          — navigate
  page.wait_for_load_state("networkidle")                 — after clicks that trigger navigation
  page.wait_for_url(re.compile(r"/target"))              — wait for URL change
  expect(element).to_be_visible(timeout=5000)            — element wait

NEVER use: time.sleep(), page.wait_for_timeout()

LOGIN HELPER (if tests need authentication):
  def _login(page: Page, username: str, password: str) -> None:
      page.goto(BASE_URL + "/login")
      page.get_by_label("Email").fill(username)
      page.get_by_label("Password").fill(password)
      page.get_by_role("button", name="Sign In").click()
      page.wait_for_load_state("networkidle")

RULES:
1. Generate ONLY tests for the requested scope — nothing else
2. Include 3-6 test methods: start with happy path, add 1-2 negative cases
3. Every test must be INDEPENDENT (starts from a clean state)
4. Use REAL selectors derived from the DOM/aria snapshot provided
5. If credentials are provided, use them in auth-related tests
6. Each test method must have a clear docstring
7. Add inline comments for non-obvious multi-step interactions
8. Tests must be complete — no "# TODO" or placeholder selectors
9. If a selector cannot be derived from the data: use a commented-out stub
   with a note explaining what to replace it with
"""

_TEST_TYPE_GUIDANCE: dict[str, str] = {
    "smoke": (
        "Generate SMOKE tests: 2-3 critical happy-path scenarios only.\n"
        "Cover: page loads, primary CTA works, core navigation works.\n"
        "No negative cases in smoke tests."
    ),
    "functional": (
        "Generate FUNCTIONAL tests: happy paths + 1-2 key negative scenarios.\n"
        "Cover: main feature works correctly, error messages appear on invalid input,\n"
        "form validation fires, key user actions complete successfully."
    ),
    "regression": (
        "Generate REGRESSION-ORIENTED tests: cover change-prone flows and edge cases.\n"
        "Include: boundary inputs, state transitions, integration points,\n"
        "scenarios most likely to break during refactoring."
    ),
    "mobile": (
        "Generate MOBILE tests: set viewport to 390x844 (iPhone 12).\n"
        "Use a browser fixture with mobile viewport.\n"
        "Cover: mobile navigation (burger menu), touch-friendly forms,\n"
        "responsive layout checks, mobile-specific interactions.\n"
        "Add a mobile_page fixture:\n"
        "  @pytest.fixture\n"
        "  def mobile_page(browser):\n"
        "      context = browser.new_context(viewport={'width':390,'height':844},\n"
        "          is_mobile=True, has_touch=True)\n"
        "      page = context.new_page()\n"
        "      yield page\n"
        "      context.close()\n"
        "Use mobile_page instead of page in test methods."
    ),
}


def generate(target_url: str, intent: IntentResult) -> str:
    """
    Scan the target page, generate a complete Playwright test file.
    Returns Python source code as a string (no markdown fences).
    """
    test_type = (intent.automation_test_type or AutomationTestType.FUNCTIONAL).value
    scope     = intent.test_scope or "main functionality"

    # Use mobile config for mobile test type
    mobile_config = None
    if test_type == "mobile":
        from agents.mobile_engine import get_device_config
        mobile_config = get_device_config("iPhone 12")

    print(f"  Scanning page for Playwright test generation ({test_type}, scope: {scope})...")

    try:
        snapshots = asyncio.run(quick_scan(
            target_url=target_url,
            scope=intent.test_scope,
            scope_entry_steps=intent.scope_entry_steps,
            credentials_text=intent.credentials_text,
            mobile_config=mobile_config,
        ))
    except Exception as e:
        print(f"  Browser scan failed ({e}). Generating from URL only.")
        snapshots = [PageSnapshot(url=target_url)]

    user_content = _build_prompt(target_url, intent, snapshots, test_type)

    print(f"  Generating Playwright test ({test_type})...")
    response = _llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=user_content),
    ])

    return _strip_fences(response.content)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_prompt(
    target_url: str,
    intent: IntentResult,
    snapshots: list[PageSnapshot],
    test_type: str,
) -> list:
    scope_note = f"for scope: **{intent.test_scope}**" if intent.test_scope else "for the main functionality"
    type_note  = _TEST_TYPE_GUIDANCE.get(test_type, _TEST_TYPE_GUIDANCE["functional"])
    last       = snapshots[-1] if snapshots else PageSnapshot()
    creds_note = f"Credentials available: {intent.credentials_text}" if intent.credentials_text else ""

    text_block = (
        f"Site URL: {target_url}\n"
        f"Scope: {scope_note}\n"
        f"Test type: {test_type.upper()}\n"
        f"{type_note}\n"
        f"{creds_note}\n"
        f"Page title: {last.title or 'unknown'}\n"
        f"Captured URL: {last.url or target_url}\n\n"
        f"DOM elements (interactive elements with their qa-ids, tags, and text):\n"
        f"{last.dom_text or '(DOM not available)'}\n\n"
        f"Aria snapshot (accessibility tree):\n"
        f"{last.aria_snapshot[:2500] if last.aria_snapshot else '(not available)'}\n\n"
        f"Generate the complete pytest-playwright Python file {scope_note}.\n"
        f"Return ONLY Python code — no markdown, no explanations."
    )

    parts: list = [{"type": "text", "text": text_block}]

    for snap in snapshots[:2]:
        if snap.screenshot_b64:
            parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{snap.screenshot_b64}",
                },
            })

    return parts


def _strip_fences(content: str) -> str:
    """Remove ```python ... ``` or ``` ... ``` wrapping if the LLM added it."""
    content = content.strip()
    if content.startswith("```python"):
        content = content[len("```python"):].lstrip("\n")
    elif content.startswith("```"):
        content = content[3:].lstrip("\n")
    if content.endswith("```"):
        content = content[:-3].rstrip()
    return content
