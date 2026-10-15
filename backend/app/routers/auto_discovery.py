from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auto_discovery import AutoDiscoverySettings
from app.schemas.auto_discovery import (
    AutoDiscoveryCountriesResponse,
    AutoDiscoverySettingsResponse,
    AutoDiscoveryUpdateRequest,
)
from app.services.auto_discovery import run_now_background
from app.services.auto_discovery_locations import (
    available_countries,
    build_location_sequence,
)
from app.utils.auth import get_current_user

router = APIRouter(
    prefix="/auto-discovery",
    tags=["Auto Discovery"],
)


def _get_or_create(db: Session, user_id: UUID) -> AutoDiscoverySettings:
    cfg = db.scalar(
        select(AutoDiscoverySettings).where(
            AutoDiscoverySettings.user_id == user_id
        )
    )
    if cfg is None:
        cfg = AutoDiscoverySettings(user_id=user_id, countries=[])
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def _to_response(cfg: AutoDiscoverySettings) -> AutoDiscoverySettingsResponse:
    response = AutoDiscoverySettingsResponse.model_validate(cfg)
    sequence = build_location_sequence(cfg.countries)
    response.total_locations = len(sequence)
    if sequence:
        country, state, city = sequence[cfg.location_index % len(sequence)]
        response.next_location = ", ".join(
            p for p in (city, state, country) if p
        )
    return response


@router.get("", response_model=AutoDiscoverySettingsResponse)
def get_settings(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cfg = _get_or_create(db, UUID(current_user["sub"]))
    return _to_response(cfg)


@router.put("", response_model=AutoDiscoverySettingsResponse)
def update_settings(
    payload: AutoDiscoveryUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.enabled and not payload.industry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select an industry before turning auto-discovery on.",
        )

    cfg = _get_or_create(db, UUID(current_user["sub"]))

    # Industry ya countries badle to list shuru se chalao
    if (
        (cfg.industry or "").lower() != (payload.industry or "").lower()
        or sorted(cfg.countries or []) != sorted(payload.countries)
    ):
        cfg.location_index = 0
        cfg.consecutive_failures = 0

    cfg.enabled = payload.enabled
    cfg.industry = payload.industry
    cfg.batch_size = payload.batch_size
    cfg.require_email = payload.require_email
    cfg.require_website = payload.require_website
    cfg.run_every_minutes = payload.run_every_minutes
    cfg.countries = payload.countries

    db.commit()
    db.refresh(cfg)
    return _to_response(cfg)


@router.post("/run-now")
def run_now(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = UUID(current_user["sub"])
    cfg = _get_or_create(db, user_id)

    if not cfg.industry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select an industry first.",
        )

    # Scheduler isi waqt dobara na uthaye
    cfg.last_run_at = datetime.now(timezone.utc)
    db.commit()

    background_tasks.add_task(run_now_background, user_id)
    return {"success": True, "message": "Discovery started for the next location."}


@router.post("/reset-location", response_model=AutoDiscoverySettingsResponse)
def reset_location(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cfg = _get_or_create(db, UUID(current_user["sub"]))
    cfg.location_index = 0
    cfg.consecutive_failures = 0
    db.commit()
    db.refresh(cfg)
    return _to_response(cfg)


@router.get("/countries", response_model=AutoDiscoveryCountriesResponse)
def list_countries(current_user: dict = Depends(get_current_user)):
    return AutoDiscoveryCountriesResponse(countries=available_countries())