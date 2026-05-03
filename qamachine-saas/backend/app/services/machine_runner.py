"""
MachineRunner — bridge between the SaaS backend and the QAmachine engine.

This service:
1. Picks up a queued Run from the DB
2. Calls the QAmachine Orchestrator
3. Updates Run status in real time (queued → running → completed/failed)
4. Saves artifacts and summary back to the DB

Integration point:
  The QAmachine engine lives at app/machine/engine.py (stub by default).
  Replace the stub with your real QAmachine Orchestrator import.
"""
from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime, timezone

log = logging.getLogger(__name__)


def _format_error_message(error: str) -> str:
    e = error.lower()
    if "timeout" in e or "timed out" in e:
        reason = "The session timed out — the page took too long to respond."
        tip    = "Try testing a simpler flow, or check if the site is reachable."
    elif "captcha" in e or "cloudflare" in e or "blocked" in e:
        reason = "The session was blocked by CAPTCHA or bot protection."
        tip    = "Test on a staging environment, or disable bot protection temporarily."
    elif "navigation" in e or "net::err" in e or "unreachable" in e:
        reason = "The session couldn't reach the target URL."
        tip    = "Check that the URL is correct and publicly accessible."
    elif "rate limit" in e or "429" in e:
        reason = "Hit an API rate limit while analysing the page."
        tip    = "Wait a minute and try again, or run a shorter/more specific task."
    elif "auth" in e or "401" in e or "403" in e:
        reason = "Access was denied — the page requires authentication."
        tip    = "Include login credentials in your task (e.g. 'login with email X and password Y first')."
    else:
        reason = "An unexpected error stopped the session."
        tip    = "Try rephrasing your task more specifically, or test a smaller part of the site."

    return (
        f"**Session failed.** {reason}\n\n"
        f"**How to fix:** {tip}\n\n"
        f"Write a new message below to try again."
    )


class MachineRunner:
    """
    Wrapper that runs the QAmachine engine for a given Run.
    Operates in its own DB session (not the request session).
    """

    def __init__(self, db=None):
        # db is not used here — we open our own sessions
        pass

    async def run_async(self, run_id: str, target_url: str, task: str, allowed_modes: list[str] | None = None) -> None:
        """Fire-and-forget background task."""
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.models.run import Run
        from app.models.chat import Chat

        log.info(f"[MachineRunner] Starting run {run_id}")

        async with AsyncSessionLocal() as db:
            try:
                # Mark as running
                result = await db.execute(select(Run).where(Run.id == run_id))
                run = result.scalar_one_or_none()
                if not run:
                    log.error(f"[MachineRunner] Run {run_id} not found")
                    return

                run.status     = "running"
                run.started_at = datetime.now(timezone.utc)
                await db.commit()

                # ── Call Machine engine ──────────────────────────────────────
                from app.machine.engine import run_machine
                result_data = await run_machine(
                    run_id=run_id,
                    target_url=target_url,
                    task=task,
                    allowed_modes=allowed_modes,
                )
                # ────────────────────────────────────────────────────────────

                # Mark completed
                async with AsyncSessionLocal() as db2:
                    res2 = await db2.execute(select(Run).where(Run.id == run_id))
                    run2 = res2.scalar_one()
                    run2.status       = "completed"
                    run2.completed_at = datetime.now(timezone.utc)
                    run2.step_count   = result_data.get("step_count",  0)
                    run2.issue_count  = result_data.get("issue_count", 0)
                    run2.summary      = result_data.get("summary",     "")
                    run2.report_path  = result_data.get("report_path", "")
                    run2.mode         = result_data.get("mode",        "")
                    run2.artifacts    = result_data.get("artifacts",   [])

                    # Save machine response message to DB so it persists on reload
                    from app.models.chat import Message as ChatMessage
                    issue_count = run2.issue_count
                    step_count  = run2.step_count
                    issues_word = "issue" if issue_count == 1 else "issues"
                    machine_msg = ChatMessage(
                        chat_id=run2.chat_id,
                        role="machine",
                        content=(
                            f"Session completed. Found **{issue_count}** {issues_word} "
                            f"across **{step_count}** steps."
                        ),
                        run_id=run_id,
                    )
                    db2.add(machine_msg)

                    # Update chat status
                    chat_res = await db2.execute(select(Chat).where(Chat.id == run2.chat_id))
                    chat = chat_res.scalar_one_or_none()
                    if chat:
                        chat.status = "idle"

                    await db2.commit()

                log.info(f"[MachineRunner] Run {run_id} completed — {run2.issue_count} issues")

            except Exception as exc:
                log.error(f"[MachineRunner] Run {run_id} failed: {exc}\n{traceback.format_exc()}")

                async with AsyncSessionLocal() as db3:
                    res3 = await db3.execute(select(Run).where(Run.id == run_id))
                    run3 = res3.scalar_one_or_none()
                    error_str = str(exc) or repr(exc) or "Unknown error"
                    if run3:
                        run3.status        = "failed"
                        run3.completed_at  = datetime.now(timezone.utc)
                        run3.error_message = error_str[:1000]

                    chat_res = await db3.execute(select(Chat).where(Chat.id == (run3.chat_id if run3 else "")))
                    chat = chat_res.scalar_one_or_none()
                    if chat:
                        chat.status = "idle"

                    if run3:
                        from app.models.chat import Message as ChatMessage
                        error_msg = ChatMessage(
                            chat_id=run3.chat_id,
                            role="machine",
                            content=_format_error_message(error_str),
                            run_id=run3.id,
                        )
                        db3.add(error_msg)

                    await db3.commit()
