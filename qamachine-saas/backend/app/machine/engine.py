"""
QAmachine Engine — runs QAmachine as a subprocess using the Python
that has all QAmachine dependencies (langchain, playwright, etc.).

Uses run_in_executor + subprocess.Popen (streaming) so it works on Windows
regardless of the asyncio event loop type (SelectorEventLoop vs Proactor).
QAMACHINE_PROGRESS lines are parsed in real-time and pushed to the DB via
an async coroutine scheduled on the event loop from the background thread.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import threading

log = logging.getLogger(__name__)


async def _async_update_progress(run_id: str, step: int, max_steps: int) -> None:
    """Update step_count and max_steps in DB. Called from background thread via run_coroutine_threadsafe."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.run import Run
        from sqlalchemy import update
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(Run).where(Run.id == run_id).values(
                    step_count=step, max_steps=max_steps
                )
            )
            await session.commit()
    except Exception as exc:
        log.debug(f"[engine] progress update failed (non-critical): {exc}")


def _run_subprocess(
    run_id: str,
    target_url: str,
    task: str,
    allowed_modes: list[str] | None,
    event_loop: asyncio.AbstractEventLoop | None,
) -> tuple[str, str, int]:
    """
    Blocking call — runs in a thread via run_in_executor.
    Reads stdout line by line so QAMACHINE_PROGRESS lines trigger live DB updates.
    stderr is read in a daemon thread to prevent pipe buffer deadlock.
    """
    from app.core.config import settings

    env = {
        **os.environ,
        "ANTHROPIC_API_KEY": settings.ANTHROPIC_API_KEY,
        "PYTHONUNBUFFERED": "1",  # disable Python output buffering
    }
    if allowed_modes is not None:
        env["QAMACHINE_ALLOWED_MODES"] = ",".join(allowed_modes)

    proc = subprocess.Popen(
        [settings.QAMACHINE_PYTHON, settings.QAMACHINE_RUNNER, run_id, target_url, task],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=settings.QAMACHINE_DIR,
        env=env,
    )

    # Read stderr in a daemon thread to prevent pipe deadlock
    stderr_chunks: list[str] = []

    def _drain_stderr() -> None:
        try:
            for line in proc.stderr:
                stderr_chunks.append(line)
        except Exception:
            pass

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()

    # Read stdout line by line — parse progress events
    stdout_lines: list[str] = []
    for raw_line in proc.stdout:
        line = raw_line.rstrip("\n\r")
        stdout_lines.append(line)

        if line.startswith("QAMACHINE_PROGRESS:") and event_loop is not None:
            try:
                payload = line[len("QAMACHINE_PROGRESS:"):].strip()
                step_s, max_s = payload.split("/", 1)
                step = int(step_s)
                max_steps = int(max_s)
                # Fire-and-forget on the main event loop — non-blocking for the thread
                asyncio.run_coroutine_threadsafe(
                    _async_update_progress(run_id, step, max_steps),
                    event_loop,
                )
            except Exception:
                pass

    try:
        proc.wait(timeout=600)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    stderr_thread.join(timeout=10)
    stderr = "".join(stderr_chunks)

    return "\n".join(stdout_lines), stderr, proc.returncode


async def run_machine(
    run_id: str,
    target_url: str,
    task: str,
    allowed_modes: list[str] | None = None,
) -> dict:
    """Run the QAmachine engine in a subprocess and return structured results."""
    log.info(f"[engine] run_id={run_id} url={target_url}")
    log.info(f"[engine] task: {task[:100]}")

    loop = asyncio.get_event_loop()
    stdout, stderr, returncode = await loop.run_in_executor(
        None, _run_subprocess, run_id, target_url, task, allowed_modes, loop
    )

    log.info(f"[engine] returncode={returncode}")
    log.info(f"[engine] stdout:\n{stdout[:2000]}")
    if stderr:
        log.error(f"[engine] stderr:\n{stderr[:2000]}")

    result_line = None
    error_line  = None
    for line in stdout.splitlines():
        if line.startswith("QAMACHINE_RESULT:"):
            result_line = line[len("QAMACHINE_RESULT:"):]
        elif line.startswith("QAMACHINE_ERROR:"):
            error_line = line[len("QAMACHINE_ERROR:"):]

    if error_line:
        err = json.loads(error_line).get("error", "Unknown error")
        log.error(f"[engine] QAmachine error: {err}\nstderr: {stderr}")
        raise RuntimeError(err)

    if result_line:
        return json.loads(result_line)

    log.error(f"[engine] No result line! stdout:\n{stdout}\nstderr:\n{stderr}")
    err_msg = stderr.strip() or stdout.strip() or "QAmachine produced no output"
    raise RuntimeError(err_msg[:500])
