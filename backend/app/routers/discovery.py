from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.discovery import (
    BusinessDiscoveryRequest,
    BusinessDiscoveryResponse,
)
from app.services.discovery import discover_businesses
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/discovery",
    tags=["Business Discovery"],
)


@router.post(
    "/businesses",
    response_model=BusinessDiscoveryResponse,
)
async def discover(
    payload: BusinessDiscoveryRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    return await discover_businesses(
        payload=payload,
        db=db,
        user_id=user_id,
    )