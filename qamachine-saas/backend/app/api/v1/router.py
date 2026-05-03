from fastapi import APIRouter
from app.api.v1 import auth, users, chats, runs, billing, dashboard, locale, tutor, admin

router = APIRouter()

router.include_router(auth.router,       prefix="/auth",      tags=["auth"])
router.include_router(users.router,      prefix="/users",     tags=["users"])
router.include_router(chats.router,      prefix="/chats",     tags=["chats"])
router.include_router(runs.router,       prefix="/runs",      tags=["runs"])
router.include_router(billing.router,    prefix="/billing",   tags=["billing"])
router.include_router(dashboard.router,  prefix="/dashboard", tags=["dashboard"])
router.include_router(locale.router,     prefix="/locale",    tags=["locale"])
router.include_router(tutor.router,      prefix="/tutor",     tags=["tutor"])
router.include_router(admin.router,      prefix="/admin",     tags=["admin"])
