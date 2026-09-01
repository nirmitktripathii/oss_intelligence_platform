"""Asynchronous SQLAlchemy Database engine, session management and base model."""

import logging
from typing import AsyncGenerator, List
from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

logger = logging.getLogger("gitscout.database")


class Base(DeclarativeBase):
    pass


# Configure async database engine
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif "postgresql" in settings.DATABASE_URL or "neon.tech" in settings.DATABASE_URL:
    connect_args = {"ssl": "require"}

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------- #
# Lightweight additive migrations
#
# create_all() creates brand-new tables but never ALTERs existing ones, so columns
# added to a model after a table already exists (e.g. the AI-triage fields on the
# live Neon Postgres) would silently be missing. This applies only additive,
# nullable columns + their indexes — idempotent, dialect-agnostic, zero-infra. The
# type tokens below are identical to what create_all emits for these column types on
# both SQLite and PostgreSQL, so a migrated table matches a freshly-created one.
# ---------------------------------------------------------------------------- #
_ADDITIVE_COLUMNS = {
    "triage_reports": {
        "llm_enhanced": "BOOLEAN",
        "llm_analysis": "JSON",
        "triage_confidence": "FLOAT",
    },
}
# index name -> (table, column). Names match SQLAlchemy's ix_<table>_<column> default.
_ADDITIVE_INDEXES = {
    "ix_triage_reports_triage_confidence": ("triage_reports", "triage_confidence"),
}


def _plan_migrations(sync_conn) -> List[str]:
    """Reflect the live schema and return the DDL needed to reach the current models."""
    inspector = sa_inspect(sync_conn)
    tables = set(inspector.get_table_names())
    statements: List[str] = []
    for table, columns in _ADDITIVE_COLUMNS.items():
        if table not in tables:
            continue  # create_all() already built it with every column
        present = {c["name"] for c in inspector.get_columns(table)}
        for name, col_type in columns.items():
            if name not in present:
                statements.append(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}")
    for index_name, (table, column) in _ADDITIVE_INDEXES.items():
        if table in tables:
            statements.append(
                f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column})"
            )
    return statements


async def ensure_schema() -> None:
    """Apply additive migrations, each in its own transaction so one can't block the rest."""
    async with engine.connect() as conn:
        plan = await conn.run_sync(_plan_migrations)
    for statement in plan:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(statement))
            logger.info("[schema] applied: %s", statement)
        except Exception as exc:
            logger.warning("[schema] skipped '%s': %s", statement, exc)


async def init_db() -> None:
    """Initialize database tables, then apply additive migrations for existing ones."""
    # Import all models to ensure metadata registration
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await ensure_schema()


async def close_db() -> None:
    """Close the database connection pool."""
    await engine.dispose()
