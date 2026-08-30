"""Health check and system telemetry endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models.issue import Issue

router = APIRouter(tags=["Health"])


@router.get("/health", summary="System Health & Telemetry")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Returns system status, active database connectivity, and total indexed open issues count.
    """
    db_connected = False
    issues_count = 0

    try:
        # Check DB connectivity
        await db.execute(text("SELECT 1"))
        db_connected = True

        # Query issues count
        count_stmt = select(func.count(Issue.id))
        res = await db.execute(count_stmt)
        issues_count = res.scalar() or 0

    except Exception:
        db_connected = False

    return {
        "status": "healthy" if db_connected else "degraded",
        "issues_count": issues_count,
        "db_connected": db_connected,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }
