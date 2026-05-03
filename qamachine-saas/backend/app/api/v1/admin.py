from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.analytics import PageView, Payment
from app.models.chat import Chat
from app.models.run import Run, Subscription
from app.models.user import User

router = APIRouter(tags=["admin"])


# ── Auth guard ────────────────────────────────────────────────────────────────

async def _require_admin(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user or user.email not in settings.ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── Public: track page view ───────────────────────────────────────────────────

@router.post("/track", include_in_schema=False)
async def track_visit(request: Request, path: str = "/", db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:512]
    db.add(PageView(path=path[:512], ip=ip, user_agent=ua))
    return {"ok": True}


# ── Admin: analytics ──────────────────────────────────────────────────────────

@router.get("/analytics")
async def get_analytics(
    _: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    now      = datetime.now(timezone.utc)
    day_ago  = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    mon_ago  = now - timedelta(days=30)

    # ── Users (only verified — incomplete registrations excluded) ──
    verified = User.email_verified == True  # noqa: E712
    total_users      = (await db.execute(select(func.count(User.id)).where(verified))).scalar_one()
    unverified_users = (await db.execute(select(func.count(User.id)).where(User.email_verified == False))).scalar_one()  # noqa: E712
    new_today = (await db.execute(select(func.count(User.id)).where(verified, User.created_at >= day_ago))).scalar_one()
    new_week  = (await db.execute(select(func.count(User.id)).where(verified, User.created_at >= week_ago))).scalar_one()
    new_month = (await db.execute(select(func.count(User.id)).where(verified, User.created_at >= mon_ago))).scalar_one()

    plan_counts: dict[str, int] = {}
    for plan in ("free", "pro", "team", "enterprise"):
        c = (await db.execute(select(func.count(User.id)).where(verified, User.plan == plan))).scalar_one()
        plan_counts[plan] = c
    paid_users = total_users - plan_counts.get("free", 0)

    # ── Runs ──
    total_runs     = (await db.execute(select(func.count(Run.id)))).scalar_one()
    runs_today     = (await db.execute(select(func.count(Run.id)).where(Run.created_at >= day_ago))).scalar_one()
    runs_week      = (await db.execute(select(func.count(Run.id)).where(Run.created_at >= week_ago))).scalar_one()
    completed_runs = (await db.execute(select(func.count(Run.id)).where(Run.status == "completed"))).scalar_one()
    failed_runs    = (await db.execute(select(func.count(Run.id)).where(Run.status == "failed"))).scalar_one()

    mode_res = await db.execute(
        select(Run.mode, func.count(Run.id))
        .where(Run.created_at >= mon_ago, Run.mode.isnot(None))
        .group_by(Run.mode)
    )
    modes = {row[0]: row[1] for row in mode_res.fetchall()}

    # ── Page views ──
    total_views      = (await db.execute(select(func.count(PageView.id)))).scalar_one()
    views_today      = (await db.execute(select(func.count(PageView.id)).where(PageView.created_at >= day_ago))).scalar_one()
    views_week       = (await db.execute(select(func.count(PageView.id)).where(PageView.created_at >= week_ago))).scalar_one()
    unique_visitors  = (await db.execute(
        select(func.count(func.distinct(PageView.ip))).where(PageView.created_at >= mon_ago)
    )).scalar_one()

    # ── Payments ──
    total_payments = (await db.execute(select(func.count(Payment.id)))).scalar_one()
    repeat_res     = await db.execute(
        select(Payment.user_id)
        .group_by(Payment.user_id)
        .having(func.count(Payment.id) > 1)
    )
    repeat_payers = len(repeat_res.fetchall())
    estimated_revenue = plan_counts.get("pro", 0) * 29 + plan_counts.get("team", 0) * 79

    # ── Daily registrations (last 14 days, verified only) ──
    daily_regs = []
    for i in range(13, -1, -1):
        ds = now - timedelta(days=i + 1)
        de = now - timedelta(days=i)
        c  = (await db.execute(
            select(func.count(User.id)).where(verified, User.created_at >= ds, User.created_at < de)
        )).scalar_one()
        daily_regs.append({"date": ds.strftime("%m/%d"), "count": c})

    # ── Recent users (last 20 verified) ──
    recent_res = await db.execute(
        select(User).where(verified).order_by(User.created_at.desc()).limit(20)
    )
    recent = recent_res.scalars().all()

    return {
        "users": {
            "total":      total_users,
            "unverified": unverified_users,
            "new_today":  new_today,
            "new_week":   new_week,
            "new_month":  new_month,
            "by_plan":    plan_counts,
            "paid":       paid_users,
        },
        "runs": {
            "total":     total_runs,
            "today":     runs_today,
            "week":      runs_week,
            "completed": completed_runs,
            "failed":    failed_runs,
            "modes":     modes,
        },
        "visits": {
            "total":          total_views,
            "today":          views_today,
            "week":           views_week,
            "unique_month":   unique_visitors,
        },
        "payments": {
            "total":                      total_payments,
            "repeat_payers":              repeat_payers,
            "estimated_monthly_revenue":  estimated_revenue,
        },
        "daily_registrations": daily_regs,
        "recent_users": [
            {
                "id":            u.id,
                "email":         u.email,
                "name":          u.name,
                "plan":          u.plan,
                "usage_credits": u.usage_credits,
                "created_at":    u.created_at.isoformat(),
            }
            for u in recent
        ],
    }


# ── Admin: update user plan ───────────────────────────────────────────────────

@router.patch("/users/{user_id}/plan")
async def update_user_plan(
    user_id: str,
    body: dict,
    _: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    plan = body.get("plan")
    if plan not in ("free", "pro", "team", "enterprise"):
        raise HTTPException(status_code=400, detail="Invalid plan")
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.plan = plan
    await db.commit()
    return {"id": user.id, "email": user.email, "plan": user.plan}


# ── Admin: raw table data ─────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 50,
    _: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    total  = (await db.execute(select(func.count(User.id)))).scalar_one()
    res    = await db.execute(select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size))
    users  = res.scalars().all()
    return {
        "total": total,
        "page":  page,
        "items": [
            {
                "id":            u.id,
                "email":         u.email,
                "name":          u.name,
                "plan":          u.plan,
                "usage_credits": u.usage_credits,
                "tutor_credits": u.tutor_credits,
                "is_active":     u.is_active,
                "created_at":    u.created_at.isoformat(),
            }
            for u in users
        ],
    }
