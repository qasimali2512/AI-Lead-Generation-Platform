from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.brand_settings import (
    BrandSettingsCreate,
    BrandSettingsResponse,
    BrandSettingsUpdate,
)
from app.services.brand_settings import (
    create_brand_settings,
    get_brand_settings,
    update_brand_settings,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
)


def _get_user_id(current_user: dict) -> UUID:
    try:
        return UUID(
            str(current_user["sub"])
        )
    except (
        KeyError,
        ValueError,
        TypeError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticated user.",
        ) from exc


@router.get(
    "/brand",
    response_model=BrandSettingsResponse,
)
def get_brand_settings_route(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.config import settings as app_settings

    user_id = _get_user_id(current_user)

    brand = get_brand_settings(
        db=db,
        user_id=user_id,
    )

    # Default logo — frontend public folder mein serve hota hai
    default_logo = (
        f"{app_settings.frontend_url}/softpeak-logo.png"
    )

    if not brand:
        return BrandSettingsResponse(
            id=UUID(
                "00000000-0000-0000-0000-000000000000"
            ),
            user_id=user_id,
            agency_name="SoftPeak Technologies",
            website=None,
            logo_url=default_logo,
            primary_color="#1f6b4f",
            secondary_color="#c49a4a",
            sender_name=None,
            sender_role=None,
            phone=None,
            address=None,
            booking_url=None,
            unsubscribe_url=None,
        )

    # Agar user ne logo save nahi kiya to default use karo
    if not brand.logo_url:
        brand.logo_url = default_logo

    return brand


@router.post(
    "/brand",
    response_model=BrandSettingsResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_brand_settings_route(
    payload: BrandSettingsCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = _get_user_id(current_user)

    try:
        return create_brand_settings(
            db=db,
            user_id=user_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.put(
    "/brand",
    response_model=BrandSettingsResponse,
)
def update_brand_settings_route(
    payload: BrandSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = _get_user_id(current_user)

    return update_brand_settings(
        db=db,
        user_id=user_id,
        payload=payload,
    )