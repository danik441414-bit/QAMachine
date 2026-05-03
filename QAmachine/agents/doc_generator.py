"""
QA Document Generator.

Generates test cases, checklists, and test plans for a given site/scope.
Flow:
  1. page_scanner.quick_scan() — capture page context (screenshot + DOM + aria)
  2. LLM call with page context → structured QA document in Markdown

Respects scope: if test_scope is set, generates ONLY for that area.
"""
from __future__ import annotations
import asyncio
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from schemas import DocType, IntentResult
from agents.page_scanner import quick_scan, PageSnapshot

_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.2, max_tokens=4000)

# ── System prompts per document type ──────────────────────────────────────────

_SYSTEM_TEST_CASES = """You are a senior QA engineer writing test cases.

Generate STRUCTURED test cases in Markdown for the REQUESTED SCOPE ONLY.
Do NOT generate test cases for sections outside the requested scope.

Format for each test case:
---
### TC-{NNN}: {Descriptive Title}

| Field | Value |
|---|---|
| **Priority** | Critical / High / Medium / Low |
| **Type** | Positive / Negative / Edge Case |
| **Preconditions** | What must be true before running this test |

**Steps:**
1. Action one
2. Action two
3. ...

**Test Data:**
- Field name: value (omit this section if no specific data needed)

**Expected Result:**
What should happen when all steps execute correctly.

---

RULES:
- Start IDs at TC-001, increment sequentially
- Group test cases by feature or sub-section with ## headings
- Order: Positive (happy path) → Negative (invalid data) → Edge Cases
- Use REAL element names and workflows from the page structure provided
- Be specific — not "fill the form" but "fill the Email field with a valid email"
- Negative cases must have concrete bad inputs and specific expected error messages
- 10-20 test cases for narrow scope, 20-40 for full section
"""

_SYSTEM_CHECKLIST = """You are a senior QA engineer writing a test checklist.

Generate a CONCISE checklist in Markdown for the REQUESTED SCOPE ONLY.
Do NOT add items for sections outside the requested scope.

FORMAT:
## [Section Name]
- [ ] Specific check item
- [ ] Another check item

## [Next Section]
- [ ] ...

RULES:
- Use checkbox format: - [ ] item
- Each item = ONE specific thing to verify (not a broad category)
- Group items under ## section headings
- Order: critical checks first, then standard, then edge cases
- Be actionable — a human QA can run each item in under 2 minutes
- No explanations, no "check if..." — just the check statement
- 15-30 items for narrow scope, 30-60 for a full section
- Include: happy path checks, error state checks, edge cases, UI checks
"""

_SYSTEM_TEST_PLAN = """You are a senior QA lead writing a test plan document.

Generate a PROFESSIONAL test plan in Markdown for the REQUESTED SCOPE ONLY.

REQUIRED SECTIONS (use these exact ## headings):

## 1. Objective
What we are testing and why.

## 2. Scope
What IS included in this test plan. Be specific to the requested area.

## 3. Out of Scope
What is explicitly NOT being tested.

## 4. Test Types
Which types of testing will be performed (functional, UI/UX, regression, API, etc.)
For each type: brief description of what will be checked.

## 5. Entry Criteria
Conditions that must be met before testing begins.

## 6. Exit Criteria
Conditions that define when testing is complete.

## 7. Test Environment
Browser(s), OS, device types, test data needs, accounts required.

## 8. Risks and Assumptions
What could go wrong. What we assume is true.

## 9. Test Strategy
Brief description of the testing approach and order.

## 10. Deliverables
What artifacts will be produced (test cases, reports, bug reports, etc.)

RULES:
- Be specific to the ACTUAL site/section based on the page structure provided
- Risks should be realistic for the scope (not generic templates)
- Environment section should mention the real URL and any auth requirements
- Keep it professional but concise — no padding, no generic filler
"""

_SYSTEM_MAP: dict[DocType, str] = {
    DocType.TEST_CASES: _SYSTEM_TEST_CASES,
    DocType.CHECKLIST:  _SYSTEM_CHECKLIST,
    DocType.TEST_PLAN:  _SYSTEM_TEST_PLAN,
}

_DOC_LABEL: dict[DocType, str] = {
    DocType.TEST_CASES: "Test Cases",
    DocType.CHECKLIST:  "Checklist",
    DocType.TEST_PLAN:  "Test Plan",
}


# ── Main entry point ───────────────────────────────────────────────────────────

def generate(target_url: str, intent: IntentResult) -> str:
    """
    Scan the target page, then generate the requested QA document.
    Returns Markdown string.
    """
    doc_type  = intent.doc_type or DocType.TEST_CASES
    doc_label = _DOC_LABEL[doc_type]
    scope     = intent.test_scope or "full site"

    print(f"  Scanning page for {doc_label} generation (scope: {scope})...")

    try:
        snapshots = asyncio.run(quick_scan(
            target_url=target_url,
            scope=intent.test_scope,
            scope_entry_steps=intent.scope_entry_steps,
            credentials_text=intent.credentials_text,
        ))
    except Exception as e:
        print(f"  Browser scan failed ({e}). Generating from URL only.")
        snapshots = [PageSnapshot(url=target_url)]

    user_content = _build_prompt(target_url, intent, snapshots, doc_label)
    system       = _SYSTEM_MAP[doc_type]

    print(f"  Generating {doc_label}...")
    response = _llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=user_content),
    ])
    return response.content


# ── Prompt builder ─────────────────────────────────────────────────────────────

def _build_prompt(
    target_url: str,
    intent: IntentResult,
    snapshots: list[PageSnapshot],
    doc_label: str,
) -> list:
    scope_note = f"for: **{intent.test_scope}**" if intent.test_scope else "for the **full site**"
    last = snapshots[-1] if snapshots else PageSnapshot()

    text_block = (
        f"Site URL: {target_url}\n"
        f"Scope: {scope_note}\n"
        f"Page title: {last.title or 'unknown'}\n"
        f"Captured URL: {last.url or target_url}\n\n"
        f"DOM elements on the page (interactive elements):\n"
        f"{last.dom_text or '(DOM not available)'}\n\n"
        f"Aria snapshot (accessibility tree):\n"
        f"{last.aria_snapshot[:2500] if last.aria_snapshot else '(not available)'}\n\n"
        f"Task: Generate the {doc_label} {scope_note}.\n"
        f"Focus ONLY on the requested scope. Do not generate content for other areas."
    )

    parts: list = [{"type": "text", "text": text_block}]

    # Attach up to 2 screenshots at low detail to save tokens
    for snap in snapshots[:2]:
        if snap.screenshot_b64:
            parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{snap.screenshot_b64}",
                },
            })

    return parts
