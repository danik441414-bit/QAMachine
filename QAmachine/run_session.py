"""
QAmachine session runner — called as a subprocess by the SaaS backend.

Usage:
    python run_session.py <run_id> <target_url> <task>

Outputs a JSON result to stdout on the last line.
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
import uuid

# Ensure QAmachine directory is in path
QAMACHINE_DIR = os.path.dirname(os.path.abspath(__file__))
if QAMACHINE_DIR not in sys.path:
    sys.path.insert(0, QAMACHINE_DIR)

os.chdir(QAMACHINE_DIR)


async def main(run_id: str, target_url: str, task: str) -> dict:
    from agents import intent_parser, planner
    from agents import doc_generator, playwright_generator
    from agents.mobile_engine import get_device_config
    from orchestrator import Orchestrator
    import artifact_writer
    from schemas import Intent, DocType, AutomationTestType

    intent_result = intent_parser.parse(task, target_url)
    intent = intent_result.intent

    if intent in (Intent.BROWSER_TEST, Intent.MOBILE_TEST):
        mission = planner.create_mission(task, target_url)
        if intent == Intent.MOBILE_TEST:
            mission.mobile_config = get_device_config(intent_result.device_name)

        # Safety net: enforce plan-level mode restrictions
        allowed_modes_env = os.environ.get("QAMACHINE_ALLOWED_MODES", "")
        if allowed_modes_env:
            allowed = [m.strip() for m in allowed_modes_env.split(",") if m.strip()]
            actual_mode = mission.session_mode.value
            if actual_mode not in allowed:
                return {
                    "step_count":  0,
                    "issue_count": 0,
                    "summary":     f"Mode '{actual_mode}' is not available on your plan. Allowed modes: {', '.join(allowed)}. Upgrade to Pro to unlock all testing modes.",
                    "report_path": "",
                    "mode":        actual_mode,
                    "artifacts":   [],
                    "blocked_by_plan": True,
                }

        orch = Orchestrator(
            target_url=target_url,
            user_task=task,
            mission=mission,
            headless=True,
        )
        report_path = await orch.run()

        step_count  = len(orch.log.steps)
        issue_count = len(orch.log.verified_issues)

        if orch.failure_reason:
            summary = f"Session stopped early: {orch.failure_reason}"
            if orch.log.verified_issues:
                summary += f"\n\nIssues found before stopping ({issue_count}):\n"
                for vi in orch.log.verified_issues[:5]:
                    summary += f"- [{vi.severity.upper()}] {vi.description}\n"
        elif orch.log.verified_issues:
            lines = [f"Found {issue_count} issue(s) across {step_count} steps.\n"]
            for vi in orch.log.verified_issues[:10]:
                lines.append(f"- [{vi.severity.upper()}] {vi.description}")
            summary = "\n".join(lines)
        else:
            summary = f"No issues found across {step_count} steps."

        abs_report = os.path.abspath(report_path) if report_path else ""
        artifacts = []
        if abs_report and os.path.exists(abs_report):
            artifacts.append({
                "id":   str(uuid.uuid4()),
                "type": "report",
                "name": os.path.basename(abs_report),
                "path": abs_report,
                "size": os.path.getsize(abs_report),
            })
        docx_path = abs_report.replace(".md", ".docx")
        if docx_path != abs_report and os.path.exists(docx_path):
            artifacts.append({
                "id":   str(uuid.uuid4()),
                "type": "report",
                "name": os.path.basename(docx_path),
                "path": docx_path,
                "size": os.path.getsize(docx_path),
            })

        return {
            "step_count":  step_count,
            "issue_count": issue_count,
            "summary":     summary,
            "report_path": abs_report,
            "mode":        mission.session_mode.value,
            "artifacts":   artifacts,
        }

    elif intent == Intent.GENERATE_DOCS:
        doc_type = intent_result.doc_type or DocType.TEST_CASES
        content  = doc_generator.generate(target_url, intent_result)
        path     = artifact_writer.save_doc(
            content=content, doc_type=doc_type.value,
            scope=intent_result.test_scope, target_url=target_url,
        )
        abs_path = os.path.abspath(path)
        return {
            "step_count": 0, "issue_count": 0,
            "summary":    f"Generated {doc_type.value.replace('_', ' ')} document.",
            "report_path": abs_path, "mode": "generate_docs",
            "artifacts": [{"id": str(uuid.uuid4()), "type": "qa_doc",
                           "name": os.path.basename(abs_path), "path": abs_path,
                           "size": os.path.getsize(abs_path) if os.path.exists(abs_path) else 0}],
        }

    elif intent == Intent.GENERATE_AUTOMATION:
        atype = intent_result.automation_test_type or AutomationTestType.FUNCTIONAL
        code  = playwright_generator.generate(target_url, intent_result)
        path  = artifact_writer.save_playwright_test(
            content=code, scope=intent_result.test_scope,
            test_type=atype.value, target_url=target_url,
        )
        abs_path = os.path.abspath(path)
        return {
            "step_count": 0, "issue_count": 0,
            "summary":    f"Generated Playwright {atype.value} test.",
            "report_path": abs_path, "mode": "generate_automation",
            "artifacts": [{"id": str(uuid.uuid4()), "type": "playwright_test",
                           "name": os.path.basename(abs_path), "path": abs_path,
                           "size": os.path.getsize(abs_path) if os.path.exists(abs_path) else 0}],
        }

    else:
        mission = planner.create_mission(task, target_url)
        orch    = Orchestrator(target_url=target_url, user_task=task,
                               mission=mission, headless=True)
        report_path = await orch.run()
        abs_report  = os.path.abspath(report_path) if report_path else ""
        return {
            "step_count":  len(orch.log.steps),
            "issue_count": len(orch.log.verified_issues),
            "summary":     f"Session completed ({len(orch.log.verified_issues)} issues).",
            "report_path": abs_report,
            "mode":        mission.session_mode.value,
            "artifacts":   [],
        }


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(json.dumps({"error": "Usage: run_session.py <run_id> <target_url> <task>"}))
        sys.exit(1)

    run_id     = sys.argv[1]
    target_url = sys.argv[2]
    task       = sys.argv[3]

    try:
        result = asyncio.run(main(run_id, target_url, task))
        # Print result as last line so backend can parse it
        print("QAMACHINE_RESULT:" + json.dumps(result))
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print("QAMACHINE_ERROR:" + json.dumps({"error": str(exc)}))
        sys.exit(1)
