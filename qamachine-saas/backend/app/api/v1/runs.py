from __future__ import annotations

import asyncio
import json
import os
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user_id, decode_token
from app.models.run import Run
from app.schemas.run import RunOut

router = APIRouter()


# ── Static routes MUST come before /{run_id} to avoid being shadowed ──────────

@router.get("/artifact")
async def download_artifact(
    artifact_id: str = Query(...),
    token:       str = Query(...),
):
    """Download an artifact file by its ID. Auth via query token (like SSE stream)."""
    try:
        payload = decode_token(token)
        user_id: str = payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Search all user runs for the artifact
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Run).where(Run.user_id == user_id)
        )
        runs = result.scalars().all()

    for run in runs:
        artifacts = run.artifacts or []
        for artifact in artifacts:
            if isinstance(artifact, dict) and artifact.get("id") == artifact_id:
                path = artifact.get("path", "")
                if not path or not os.path.exists(path):
                    raise HTTPException(status_code=404, detail="File not found on disk")
                return FileResponse(
                    path=path,
                    filename=artifact.get("name", os.path.basename(path)),
                    media_type="application/octet-stream",
                )

    raise HTTPException(status_code=404, detail="Artifact not found")


# ── Dynamic routes ─────────────────────────────────────────────────────────────

@router.get("/{run_id}", response_model=RunOut)
async def get_run(
    run_id:  str,
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    run = await _get_run_or_404(db, run_id, user_id)
    return run


@router.get("/{run_id}/stream")
async def stream_run_status(
    run_id: str,
    token:  str = Query(...),
):
    """Server-Sent Events — polls DB every 2s and pushes updated Run JSON."""
    try:
        payload = decode_token(token)
        user_id: str = payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Run).where(Run.id == run_id)
                )
                run = result.scalar_one_or_none()

            if not run:
                yield f"data: {json.dumps({'error': 'Run not found'})}\n\n"
                break

            run_out = RunOut.model_validate(run)
            yield f"data: {run_out.model_dump_json()}\n\n"

            if run.status in ("completed", "failed"):
                break

            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _get_run_or_404(db: AsyncSession, run_id: str, user_id: str) -> Run:
    result = await db.execute(
        select(Run).where(Run.id == run_id, Run.user_id == user_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
