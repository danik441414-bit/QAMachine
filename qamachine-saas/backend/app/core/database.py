from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    **({} if _is_sqlite else {
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    }),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create all tables on startup (dev only — use Alembic in prod)."""
    from app.models import analytics  # noqa: F401 — registers PageView + Payment with Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safe migrations: add new columns if they don't exist yet
        if _is_sqlite:
            await _sqlite_add_column_if_missing(conn, "runs", "max_steps", "INTEGER NOT NULL DEFAULT 0")
            await _sqlite_add_column_if_missing(conn, "users", "tutor_credits", "INTEGER NOT NULL DEFAULT 0")
            await _sqlite_add_column_if_missing(conn, "users", "email_verified", "BOOLEAN NOT NULL DEFAULT 1")
            await _sqlite_add_column_if_missing(conn, "users", "email_verify_token", "VARCHAR(64)")
            await _sqlite_add_column_if_missing(conn, "users", "email_verify_expires", "DATETIME")
            await _sqlite_add_column_if_missing(conn, "users", "reset_password_token", "VARCHAR(64)")
            await _sqlite_add_column_if_missing(conn, "users", "reset_password_expires", "DATETIME")
            await _sqlite_add_column_if_missing(conn, "users", "google_id", "VARCHAR(255)")
            await _sqlite_add_column_if_missing(conn, "users", "magic_token", "VARCHAR(64)")
            await _sqlite_add_column_if_missing(conn, "users", "magic_token_expires", "DATETIME")
        else:
            # PostgreSQL — existing rows get email_verified=TRUE so they stay active
            await _pg_add_column_if_missing(conn, "runs", "max_steps", "INTEGER NOT NULL DEFAULT 0")
            await _pg_add_column_if_missing(conn, "users", "email_verified", "BOOLEAN NOT NULL DEFAULT TRUE")
            await _pg_add_column_if_missing(conn, "users", "email_verify_token", "VARCHAR(64)")
            await _pg_add_column_if_missing(conn, "users", "email_verify_expires", "TIMESTAMPTZ")
            await _pg_add_column_if_missing(conn, "users", "reset_password_token", "VARCHAR(64)")
            await _pg_add_column_if_missing(conn, "users", "reset_password_expires", "TIMESTAMPTZ")
            await _pg_add_column_if_missing(conn, "users", "google_id", "VARCHAR(255)")
            await _pg_add_column_if_missing(conn, "users", "magic_token", "VARCHAR(64)")
            await _pg_add_column_if_missing(conn, "users", "magic_token_expires", "TIMESTAMPTZ")


async def _sqlite_add_column_if_missing(conn, table: str, column: str, col_def: str) -> None:
    from sqlalchemy import text
    result = await conn.execute(text(f"PRAGMA table_info({table})"))
    cols = [row[1] for row in result.fetchall()]
    if column not in cols:
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"))


async def _pg_add_column_if_missing(conn, table: str, column: str, col_def: str) -> None:
    from sqlalchemy import text
    result = await conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    if not result.fetchone():
        await conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_def}'))


async def get_db():
    """FastAPI dependency — yields an async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
