from fastapi import APIRouter

from app.config import settings


router = APIRouter(
    prefix="/api",
    tags=["API"],
)


@router.get("/info")
def api_info():
    return {
        "success": True,
        "message": "AI Lead Generation API",
        "data": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "api_prefix": settings.api_prefix,
        },
    }