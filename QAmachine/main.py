"""
QAmachine — Senior QA Agent
Entry point with intent-based routing.

Intents:
  BROWSER_TEST       → planner → Orchestrator (full QA session)
  MOBILE_TEST        → planner → Orchestrator (mobile emulation context)
  GENERATE_DOCS      → page_scanner → doc_generator → artifact_writer
  GENERATE_AUTOMATION → page_scanner → playwright_generator → artifact_writer
"""
import asyncio
from agents import intent_parser, planner
from agents import doc_generator, playwright_generator
from agents.mobile_engine import get_device_config
from schemas import Intent, DocType, AutomationTestType
from orchestrator import Orchestrator
import artifact_writer

# ── Display helpers ────────────────────────────────────────────────────────────

_INTENT_LABEL = {
    Intent.BROWSER_TEST:        "Browser QA Test",
    Intent.MOBILE_TEST:         "Mobile QA Test",
    Intent.GENERATE_DOCS:       "QA Document Generation",
    Intent.GENERATE_AUTOMATION: "Playwright Test Generation",
}

_DOC_LABEL = {
    DocType.TEST_CASES: "Test Cases",
    DocType.CHECKLIST:  "Checklist",
    DocType.TEST_PLAN:  "Test Plan",
}

_AUTO_LABEL = {
    AutomationTestType.SMOKE:       "Smoke",
    AutomationTestType.FUNCTIONAL:  "Functional",
    AutomationTestType.REGRESSION:  "Regression",
    AutomationTestType.MOBILE:      "Mobile",
}

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

_MODE_DESC = {
    "ui_ux":            "Visual defects, layout, contrast, overlapping elements",
    "functional":       "Forms, buttons, filters, search, tabs, modals, CRUD, auth",
    "specific_flow":    "One exact user journey, step by step",
    "all_flows":        "All user flows: positive happy paths + negative edge cases",
    "regression":       "Changed areas first, then neighbors, then smoke related flows",
    "network":          "Network errors, 4xx/5xx, slow requests, broken assets",
    "api":              "Collect and test API endpoints from network traffic",
    "load_performance": "Page load times, slow resources, API response timing",
    "mobile":           "Mobile-device emulation + mobile-specific UX/functional checks",
}


def _banner() -> None:
    print("\n" + "=" * 54)
    print("   QAmachine  -  Senior QA Agent")
    print("=" * 54 + "\n")


def _print_intent_preview(intent_result) -> None:
    intent       = intent_result.intent
    intent_label = _INTENT_LABEL.get(intent, intent.value)
    scope        = intent_result.test_scope or "Full site"

    print("\n" + "=" * 54)
    print("  INTENT DETECTED")
    print("=" * 54)
    print(f"  Intent   : {intent_label}")
    print(f"  Scope    : {scope}")

    if intent == Intent.MOBILE_TEST:
        print(f"  Device   : {intent_result.device_name}")
        print(f"  Check    : {intent_result.mobile_check_type}")

    elif intent == Intent.GENERATE_DOCS:
        doc_type = intent_result.doc_type or DocType.TEST_CASES
        print(f"  Document : {_DOC_LABEL.get(doc_type, doc_type.value)}")

    elif intent == Intent.GENERATE_AUTOMATION:
        atype = intent_result.automation_test_type or AutomationTestType.FUNCTIONAL
        print(f"  Test type: {_AUTO_LABEL.get(atype, atype.value)}")

    if intent_result.scope_url_keywords:
        kw = ", ".join(intent_result.scope_url_keywords[:4])
        print(f"  URL kw   : {kw}")
    if intent_result.credentials_text:
        print(f"  Creds    : {intent_result.credentials_text}")
    if intent_result.changed_areas:
        print(f"  Changed  : {', '.join(intent_result.changed_areas)}")

    print("=" * 54 + "\n")


def _print_mission_plan(mission) -> None:
    mode_key  = mission.session_mode.value
    scope     = mission.test_scope or "Full site"
    targets   = ", ".join(mission.coverage_targets[:5])
    if len(mission.coverage_targets) > 5:
        targets += f" (+{len(mission.coverage_targets) - 5} more)"

    print("=" * 54)
    print("  QA PLAN")
    print("=" * 54)
    print(f"  Mode     : {_MODE_LABEL.get(mode_key, mode_key)}")
    print(f"  Desc     : {_MODE_DESC.get(mode_key, '')}")
    print(f"  Scope    : {scope}")
    if mission.mobile_config:
        mc = mission.mobile_config
        print(f"  Device   : {mc.device_name} ({mc.viewport_width}x{mc.viewport_height})")
    if mission.scope_url_keywords:
        kw = ", ".join(mission.scope_url_keywords[:4])
        print(f"  URL kw   : {kw}")
    if mission.changed_areas:
        print(f"  Changed  : {', '.join(mission.changed_areas)}")
    print(f"  Targets  : {targets}")
    print(f"  Steps    : {mission.recommended_max_steps}")
    print(f"  Typing   : {'Yes' if mission.allow_typing else 'No'}")
    if mission.credentials_text:
        print(f"  Creds    : {mission.credentials_text}")
    print("-" * 54)
    print(f"  Strategy : {mission.strategy_notes[:120]}")
    print("=" * 54 + "\n")


def _confirm(prompt: str = "Proceed? [Y/n]: ") -> bool:
    ans = input(prompt).strip().lower()
    return ans in ("", "y", "yes", "д", "да")


# ── Execution paths ────────────────────────────────────────────────────────────

def _run_browser_test(target_url: str, task: str, intent_result) -> None:
    """BROWSER_TEST and MOBILE_TEST — full Orchestrator session."""
    print("Planning mission...")
    mission = planner.create_mission(task, target_url)

    # Inject mobile config for MOBILE intent
    if intent_result.intent == Intent.MOBILE_TEST:
        mission.mobile_config = get_device_config(intent_result.device_name)

    _print_mission_plan(mission)

    if not _confirm("Start? [Y/n]: "):
        print("Cancelled.")
        return

    orch = Orchestrator(target_url=target_url, user_task=task, mission=mission)
    report_path = asyncio.run(orch.run())
    print(f"\nDone. Report: {report_path}")


def _run_generate_docs(target_url: str, intent_result) -> None:
    """GENERATE_DOCS — scan page + LLM doc generation."""
    doc_type  = intent_result.doc_type or DocType.TEST_CASES
    doc_label = _DOC_LABEL.get(doc_type, doc_type.value)
    scope     = intent_result.test_scope or "full site"

    print(f"\nGenerating {doc_label} for: {scope}")
    if not _confirm("Proceed? [Y/n]: "):
        print("Cancelled.")
        return

    content = doc_generator.generate(target_url, intent_result)
    path    = artifact_writer.save_doc(
        content=content,
        doc_type=doc_type.value,
        scope=intent_result.test_scope,
        target_url=target_url,
    )
    print(f"\nDocument saved: {path}")
    print(f"Preview (first 300 chars):\n{content[:300]}...")


def _run_generate_automation(target_url: str, intent_result) -> None:
    """GENERATE_AUTOMATION — scan page + LLM Playwright test generation."""
    atype      = intent_result.automation_test_type or AutomationTestType.FUNCTIONAL
    type_label = _AUTO_LABEL.get(atype, atype.value)
    scope      = intent_result.test_scope or "general"

    print(f"\nGenerating Playwright {type_label} test for: {scope}")
    if not _confirm("Proceed? [Y/n]: "):
        print("Cancelled.")
        return

    code = playwright_generator.generate(target_url, intent_result)
    path = artifact_writer.save_playwright_test(
        content=code,
        scope=intent_result.test_scope,
        test_type=atype.value,
        target_url=target_url,
    )
    print(f"\nPlaywright test saved: {path}")
    print(f"Run with: pytest {path} -v")
    print(f"\nPreview (first 400 chars):\n{code[:400]}...")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    _banner()

    target_url = input("URL  : ").strip()[:512]
    if not target_url:
        print("URL cannot be empty.")
        return
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    task = input("Task : ").strip()[:2000]
    if not task:
        print("Task cannot be empty.")
        return

    print("\nDetecting intent...")
    intent_result = intent_parser.parse(task, target_url)
    _print_intent_preview(intent_result)

    intent = intent_result.intent

    if intent in (Intent.BROWSER_TEST, Intent.MOBILE_TEST):
        _run_browser_test(target_url, task, intent_result)

    elif intent == Intent.GENERATE_DOCS:
        _run_generate_docs(target_url, intent_result)

    elif intent == Intent.GENERATE_AUTOMATION:
        _run_generate_automation(target_url, intent_result)

    else:
        print(f"Unknown intent: {intent}. Falling back to browser test.")
        _run_browser_test(target_url, task, intent_result)


if __name__ == "__main__":
    main()
