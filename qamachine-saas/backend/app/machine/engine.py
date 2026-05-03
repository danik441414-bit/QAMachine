"""
QAmachine Engine — runs QAmachine as a subprocess using the Python
that has all QAmachine dependencies (langchain, playwright, etc.).

Uses run_in_executor + subprocess.run (blocking) so it works on Windows
regardless of the asyncio event loop type (SelectorEventLoop vs Proactor).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess

log = logging.getLogger(__name__)


def _run_subprocess(run_id: str, target_url: str, task: str, allowed_modes: list[str] | None = None) -> tuple[str, str, int]:
    """Blocking call — runs in a thread via run_in_executor."""
    from app.core.config import settings

    env = {**os.environ, "ANTHROPIC_API_KEY": settings.ANTHROPIC_API_KEY}
    if allowed_modes is not None:
        env["QAMACHINE_ALLOWED_MODES"] = ",".join(allowed_modes)

    result = subprocess.run(
        [settings.QAMACHINE_PYTHON, settings.QAMACHINE_RUNNER, run_id, target_url, task],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=settings.QAMACHINE_DIR,
        env=env,
        timeout=600,  # 10 min max
    )
    return result.stdout, result.stderr, result.returncode


async def run_machine(run_id: str, target_url: str, task: str, allowed_modes: list[str] | None = None) -> dict:
    """
    Run the QAmachine engine in a subprocess and return structured results.
    """
    log.info(f"[engine] run_id={run_id} url={target_url}")
    log.info(f"[engine] task: {task[:100]}")

    loop = asyncio.get_event_loop()
    stdout, stderr, returncode = await loop.run_in_executor(
        None, _run_subprocess, run_id, target_url, task, allowed_modes
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
