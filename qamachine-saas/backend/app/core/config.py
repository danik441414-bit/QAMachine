from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "QAmachine"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/qamachine"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Anthropic (for the Machine)
    ANTHROPIC_API_KEY: str = ""

    # Stripe (billing)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_TEAM: str = ""

    # NOWPayments (crypto billing)
    NOWPAYMENTS_API_KEY: str = ""
    NOWPAYMENTS_IPN_SECRET: str = ""

    # Dodo Payments (card billing)
    DODO_API_KEY: str = ""
    DODO_WEBHOOK_SECRET: str = ""
    DODO_PRODUCT_PRO: str = ""
    DODO_PRODUCT_TEAM: str = ""
    DODO_ENV: str = "test"  # "test" or "live"

    # Plan limits — runs
    FREE_RUNS_CAP: int = 3
    PRO_RUNS_CAP: int = 50
    TEAM_RUNS_CAP: int = 200

    # Plan limits — chats
    FREE_CHATS_CAP: int = 1

    # Plan limits — tutor messages
    FREE_TUTOR_CAP: int = 20

    # Allowed testing modes per plan (Free = only these two)
    FREE_ALLOWED_MODES: list[str] = ["functional", "ui_ux"]

    # Frontend URL (used in Stripe redirect URLs)
    FRONTEND_URL: str = "http://localhost:3000"

    # Email — Resend API
    RESEND_API_KEY: str = ""
    SMTP_FROM:      str = "noreply@qamachine.site"
    EMAIL_VERIFICATION_REQUIRED: bool = True

    # Legacy SMTP (unused, kept for reference)
    SMTP_HOST:     str = ""
    SMTP_PORT:     int = 587
    SMTP_USER:     str = ""
    SMTP_PASSWORD: str = ""

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""

    # Admin access
    ADMIN_EMAILS: list[str] = ["danik441414@gmail.com"]

    # QAmachine engine paths (override in .env for other environments)
    QAMACHINE_DIR: str = r"C:\Users\Даниил\Desktop\QAmachine"
    QAMACHINE_PYTHON: str = r"C:\Users\Даниил\Desktop\QAmachine\.venv\Scripts\python.exe"
    QAMACHINE_RUNNER: str = r"C:\Users\Даниил\Desktop\QAmachine\run_session.py"


settings = Settings()
