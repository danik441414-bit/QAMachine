from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from schemas import IssueHypothesis, VerifiedIssue, PageContext, SessionMode

_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.0, max_tokens=512)


class _EvidenceReport(BaseModel):
    evidence_found: bool = Field(
        description="True if the screenshot/DOM/aria clearly shows this defect right now"
    )
    evidence_quote: str = Field(
        description="Exact quote from aria, DOM text, or console/network error supporting the finding. Empty if not found."
    )
    suggested_severity: str = Field(
        description="critical / high / medium / low"
    )


class _FinalVerdict(BaseModel):
    confirmed: bool = Field(description="True if this is a genuine defect worth filing")
    severity: str = Field(description="critical / high / medium / low")
    final_description: str = Field(description="Polished one-sentence defect description")


_evidence_chain = _llm.with_structured_output(_EvidenceReport)
_verdict_chain  = _llm.with_structured_output(_FinalVerdict)


def _evidence_system(mode: SessionMode) -> str:
    base = (
        "You are a senior QA engineer verifying a suspected bug.\n"
        "You receive: hypothesis, screenshot, DOM elements, aria snapshot, console errors, network errors.\n"
        "Find CONCRETE evidence that this bug EXISTS on this page RIGHT NOW.\n"
        "Only confirm if you can quote something specific from the data.\n\n"
    )
    rules = {
        SessionMode.UI_UX: (
            "SCOPE: UI/UX audit mode.\n"
            "✅ CONFIRM: overflow text, broken layout, misaligned elements, broken images,\n"
            "   invisible CTAs, poor contrast, overlapping elements, typography issues.\n"
            "❌ REJECT: functional issues, text-on-image overlays (intentional design), animations."
        ),
        SessionMode.FUNCTIONAL: (
            "SCOPE: Functional testing mode.\n"
            "✅ CONFIRM: feature doesn't work, wrong output, broken nav, form won't submit,\n"
            "   unexpected error, page crash, data not saved, wrong redirect.\n"
            "❌ REJECT: cosmetic/visual issues that don't affect behavior."
        ),
        SessionMode.REGRESSION: (
            "SCOPE: Regression testing. Focus on areas that may have broken due to recent changes.\n"
            "✅ CONFIRM: features that worked before and now fail, unexpected behavior in\n"
            "   changed zones or their neighbors, broken integrations.\n"
            "❌ REJECT: pre-existing cosmetic issues unrelated to the change."
        ),
        SessionMode.NETWORK: (
            "SCOPE: Network audit mode.\n"
            "✅ CONFIRM: 4xx/5xx responses visible in network_errors, requests that break UI\n"
            "   (blank sections, stuck spinners, failed asset loads), repeated network failures.\n"
            "❌ REJECT: slow but successful requests, minor cosmetic issues."
        ),
        SessionMode.API: (
            "SCOPE: API collection + testing mode.\n"
            "✅ CONFIRM: visible API failures (error shown in UI), unexpected empty responses,\n"
            "   UI broken because an API call failed (blank data, crash).\n"
            "❌ REJECT: cosmetic issues."
        ),
        SessionMode.LOAD_PERFORMANCE: (
            "SCOPE: Performance audit mode.\n"
            "✅ CONFIRM: page_load_ms > 3000 (slow page), console errors for failed resources\n"
            "   (CSS/JS/images), page visibly broken due to slow/failed resources.\n"
            "❌ REJECT: functional issues, cosmetic issues."
        ),
        SessionMode.SPECIFIC_FLOW: (
            "SCOPE: Specific flow test.\n"
            "✅ CONFIRM: flow interrupted, step produces wrong result, required element missing,\n"
            "   form validation broken, success state not reached, unexpected redirect.\n"
            "❌ REJECT: cosmetic issues that don't block the flow."
        ),
        SessionMode.ALL_FLOWS: (
            "SCOPE: All user flows test.\n"
            "✅ CONFIRM: flow interruptions, missing error messages on negative paths,\n"
            "   happy path failures, validation silently passing invalid data.\n"
            "❌ REJECT: cosmetic-only issues."
        ),
        SessionMode.MOBILE: (
            "SCOPE: Mobile device testing. Viewport is narrow (mobile size).\n"
            "✅ CONFIRM: horizontal overflow/scroll visible, touch targets clearly too small,\n"
            "   text visibly cut off or overflowing its container, burger menu not working,\n"
            "   elements visibly overlapping, sticky bar covering content, modal not fitting screen,\n"
            "   images overflowing, forms unusably narrow.\n"
            "❌ REJECT: desktop-only design patterns, minor pixel differences, intentional\n"
            "   responsive design choices that work correctly, color/font preferences."
        ),
    }
    return base + rules.get(mode, "Be strict. Only confirm clear, reproducible issues.")


def _verdict_system(mode: SessionMode) -> str:
    base = (
        "You are a QA team lead making the final call on a defect report.\n"
        "Decide: is this worth filing? Testing mode: "
        + mode.value + "\n\n"
    )
    verdicts = {
        SessionMode.UI_UX: (
            "Confirm ONLY visual/layout defects with visible evidence.\n"
            "Reject: functional issues, design choices, animations, text-on-image, pixel quirks."
        ),
        SessionMode.FUNCTIONAL: (
            "Confirm ONLY functional failures with clear behavioral evidence.\n"
            "Reject: cosmetic/visual issues. The test: does the feature do what it should?"
        ),
        SessionMode.REGRESSION: (
            "Confirm issues that are likely REGRESSIONS (broken by recent changes).\n"
            "Confirm pre-existing issues in changed areas that now need attention.\n"
            "Reject: issues clearly unrelated to the changed areas."
        ),
        SessionMode.NETWORK: (
            "Confirm network failures that impact user experience: 4xx/5xx breaking UI,\n"
            "failed assets, repeated errors. Reject: slow but working requests, cosmetics."
        ),
        SessionMode.API: (
            "Confirm visible API-related failures. Reject cosmetics."
        ),
        SessionMode.LOAD_PERFORMANCE: (
            "Confirm slow page loads (>3000ms) and resource failures.\n"
            "Reject: functional issues, cosmetics."
        ),
        SessionMode.SPECIFIC_FLOW: (
            "Confirm issues that BLOCK or CORRUPT the user flow.\n"
            "Reject: cosmetic issues that don't affect flow completion."
        ),
        SessionMode.ALL_FLOWS: (
            "Confirm issues that break flow completion or produce wrong results.\n"
            "Reject: cosmetic-only issues."
        ),
        SessionMode.MOBILE: (
            "Confirm mobile-specific UX/functional issues with clear visual evidence:\n"
            "horizontal scroll, overlapping elements, unreadable text, broken navigation,\n"
            "oversized/undersized touch targets, modals off-screen, sticky bars blocking content.\n"
            "Reject: desktop-only design decisions, minor spacing, color issues."
        ),
    }
    return base + verdicts.get(mode, "Only confirm clear, reproducible issues with real user impact.")


def verify(
    hypothesis: IssueHypothesis,
    ctx: PageContext,
    screenshot_path: str = "",
) -> Optional[VerifiedIssue]:
    """
    Two-phase mode-aware verification.
    Phase 1 (visual): screenshot + DOM + aria → evidence.
    Phase 2 (text-only): evidence → final verdict.
    Returns None if not confirmed or confidence < 0.4.
    """
    if hypothesis.confidence < 0.4:
        return None

    mode = ctx.mission.session_mode if ctx.mission else SessionMode.FUNCTIONAL
    dom_str     = "\n".join(f"[{el.id}] {el.tag} | '{el.text}'" for el in ctx.dom_elements)
    console_str = "\n".join(ctx.console_errors) or "None."
    network_str = "\n".join(ctx.network_errors) or "None."

    # Phase 1
    p1_content = [
        {
            "type": "text",
            "text": (
                f"Hypothesis: {hypothesis.description}\n"
                f"Element qa-id: {hypothesis.element_id or 'N/A'}\n\n"
                f"DOM:\n{dom_str}\n\n"
                f"Console errors:\n{console_str}\n"
                f"Network errors:\n{network_str}\n\n"
                f"Aria snapshot:\n{ctx.aria_snapshot}\n\n"
                "Look at the screenshot and find evidence:"
            ),
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{ctx.screenshot_b64}"},
        },
    ]
    evidence: _EvidenceReport = _evidence_chain.invoke([
        SystemMessage(content=[{
            "type": "text",
            "text": _evidence_system(mode),
            "cache_control": {"type": "ephemeral"},
        }]),
        HumanMessage(content=p1_content),
    ])

    if not evidence.evidence_found:
        return None

    # Phase 2
    p2_text = (
        f"Hypothesis: {hypothesis.description}\n"
        f"Confidence: {hypothesis.confidence}\n"
        f"Evidence: {evidence.evidence_quote}\n"
        f"Severity estimate: {evidence.suggested_severity}\n"
        f"URL: {ctx.current_url} | Page type: {ctx.page_type}\n"
    )
    verdict: _FinalVerdict = _verdict_chain.invoke([
        SystemMessage(content=[{
            "type": "text",
            "text": _verdict_system(mode),
            "cache_control": {"type": "ephemeral"},
        }]),
        HumanMessage(content=p2_text),
    ])

    if not verdict.confirmed:
        return None

    return VerifiedIssue(
        description=verdict.final_description,
        severity=verdict.severity,
        url=ctx.current_url,
        step=ctx.step,
        element_id=hypothesis.element_id,
        evidence=evidence.evidence_quote,
        screenshot_path=screenshot_path,
    )
