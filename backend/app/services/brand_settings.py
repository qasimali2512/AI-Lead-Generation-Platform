from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.brand_settings import BrandSettings
from app.schemas.brand_settings import (
    BrandSettingsCreate,
    BrandSettingsUpdate,
)


def get_brand_settings(
    db: Session,
    user_id: UUID,
) -> BrandSettings | None:
    return db.scalar(
        select(BrandSettings).where(
            BrandSettings.user_id == user_id
        )
    )


def create_brand_settings(
    db: Session,
    user_id: UUID,
    payload: BrandSettingsCreate,
) -> BrandSettings:
    existing = get_brand_settings(db, user_id)

    if existing:
        raise ValueError(
            "Brand settings already exist for this user."
        )

    settings = BrandSettings(
        user_id=user_id,
        **payload.model_dump(),
    )

    db.add(settings)
    db.commit()
    db.refresh(settings)

    return settings


def update_brand_settings(
    db: Session,
    user_id: UUID,
    payload: BrandSettingsUpdate,
) -> BrandSettings:
    settings = get_brand_settings(db, user_id)

    if not settings:
        settings = BrandSettings(
            user_id=user_id,
            **payload.model_dump(),
        )

        db.add(settings)
    else:
        values = payload.model_dump()

        for key, value in values.items():
            setattr(settings, key, value)

    db.commit()
    db.refresh(settings)

    return settings