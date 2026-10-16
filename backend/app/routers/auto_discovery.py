from __future__ import annotations

import asyncio
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
from app.services.auto_discovery import (
    clear_visited,
    count_visited,
    industry_key,
    run_now_background,
    _load_visited,
)
import random
from app.services.geonames import GeoDataUnavailable, get_geo_data, pick_city
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


def _to_response(db: Session, cfg: AutoDiscoverySettings) -> AutoDiscoverySettingsResponse:
    response = AutoDiscoverySettingsResponse.model_validate(cfg)

    # JSONB mein kabhi kabhi purane {code, name} objects hote hain -- strings mein convert karo
    raw_countries = cfg.countries or []
    normalized: list[str] = []
    for item in raw_countries:
        if isinstance(item, str):
            normalized.append(item)
        elif isinstance(item, dict):
            code = item.get("code") or item.get("name") or ""
            if code:
                normalized.append(str(code))
    response.countries = list(dict.fromkeys(normalized))  # deduplicate, preserve order

    if cfg.industry:
        key = industry_key(cfg.industry)
        response.cities_visited = count_visited(db, cfg.user_id, key)

        # Next location preview (non-blocking, best-effort)
        try:
            geo = get_geo_data()
            visited = _load_visited(db, cfg.user_id, key)
            countries = {str(c).upper() for c in (cfg.countries or [])}
            city, _ = pick_city(
                geo,
                city_size=cfg.city_size or "mix",
                position=cfg.mix_position,
                countries=countries,
                excluded_ids=visited,
                rng=random.Random(),
            )
            if city is not None:
                state = geo.state_name(city)
                country = geo.country_name(city.country_code)
                parts = [p for p in (city.name, state, country) if p]
                response.next_location = ", ".join(parts)
                # Remaining cities = total eligible minus visited
                if countries:
                    total_eligible = sum(
                        1 for c in geo.cities if c.country_code in countries
                    )
                else:
                    total_eligible = len(geo.cities)
                response.next_location_count = max(0, total_eligible - len(visited))
        except Exception:  # noqa: BLE001
            pass  # Preview fail hone par silently skip

    return response


@router.get("", response_model=AutoDiscoverySettingsResponse)
def get_settings(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cfg = _get_or_create(db, UUID(current_user["sub"]))
    return _to_response(db, cfg)


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

    if industry_key(cfg.industry) != industry_key(payload.industry):
        cfg.mix_position = 0   # nayi industry -- mix pattern shuru se

    cfg.enabled = payload.enabled
    cfg.industry = payload.industry
    cfg.batch_size = payload.batch_size
    cfg.require_email = payload.require_email
    cfg.require_website = payload.require_website
    cfg.run_every_minutes = payload.run_every_minutes
    cfg.city_size = payload.city_size
    cfg.countries = payload.countries

    db.commit()
    db.refresh(cfg)
    return _to_response(db, cfg)


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
    return {"success": True, "message": "Discovery started."}


@router.post("/reset-location", response_model=AutoDiscoverySettingsResponse)
def reset_progress(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Is industry ke visited shehr saaf karo -- shuru se dobara."""
    cfg = _get_or_create(db, UUID(current_user["sub"]))
    if cfg.industry:
        clear_visited(db, cfg.user_id, industry_key(cfg.industry))
    cfg.mix_position = 0
    db.commit()
    db.refresh(cfg)
    return _to_response(db, cfg)


@router.get("/countries", response_model=AutoDiscoveryCountriesResponse)
async def list_countries(current_user: dict = Depends(get_current_user)):
    try:
        data = await asyncio.to_thread(get_geo_data)
    except GeoDataUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return AutoDiscoveryCountriesResponse(countries=data.countries())