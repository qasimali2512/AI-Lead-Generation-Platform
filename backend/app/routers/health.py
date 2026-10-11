
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.database import SessionLocal


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.api_route(
    "",
    methods=["GET", "HEAD"],
    summary="Health Check",
)
def health_check():
    """Check API and database health."""

    database_status = "healthy"

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))

    except Exception:
        database_status = "unhealthy"

    overall_status = (
        "healthy"
        if database_status == "healthy"
        else "degraded"
    )

    return {
        "success": True,
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "api": "healthy",
            "database": database_status,
        },
    }
