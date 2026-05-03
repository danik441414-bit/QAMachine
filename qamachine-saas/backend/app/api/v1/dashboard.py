from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.chat import Chat
from app.models.run import Run
from app.schemas.run import RunOut

router = APIRouter()


class RecentRun(BaseModel):
    id: str
    chat_id: str
    chat_title: str
    target_url: str
    status: str
    issue_count: int
    step_count: int
    mode: str | None
    created_at: str


class DashboardStats(BaseModel):
    total_runs: int
    total_issues: int
    total_chats: int
    recent_runs: list[RecentRun]


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Aggregate counts
    chats_count = await db.scalar(
        select(func.count(Chat.id)).where(Chat.user_id == user_id)
    )
    runs_agg = await db.execute(
        select(func.count(Run.id), func.coalesce(func.sum(Run.issue_count), 0))
        .where(Run.user_id == user_id)
    )
    total_runs, total_issues = runs_agg.one()

    # Recent 5 runs with their chat title
    recent_result = await db.execute(
        select(Run, Chat.title)
        .join(Chat, Run.chat_id == Chat.id)
        .where(Run.user_id == user_id)
        .order_by(Run.created_at.desc())
        .limit(5)
    )
    recent_rows = recent_result.all()

    recent_runs = [
        RecentRun(
            id=run.id,
            chat_id=run.chat_id,
            chat_title=title or "Untitled",
            target_url=run.target_url,
            status=run.status,
            issue_count=run.issue_count,
            step_count=run.step_count,
            mode=run.mode,
            created_at=run.created_at.isoformat(),
        )
        for run, title in recent_rows
    ]

    return DashboardStats(
        total_runs=total_runs or 0,
        total_issues=total_issues or 0,
        total_chats=chats_count or 0,
        recent_runs=recent_runs,
    )
