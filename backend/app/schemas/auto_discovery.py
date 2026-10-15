from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.auto_discovery_locations import available_countries


class AutoDiscoveryUpdateRequest(BaseModel):
    enabled: bool = False
    industry: str | None = Field(default=None, max_length=100)
    batch_size: int = Field(default=50, ge=10, le=500)
    require_email: bool = False
    require_website: bool = False
    run_every_minutes: int = Field(default=30, ge=5, le=1440)
    countries: list[str] = Field(default_factory=list)

    @field_validator("industry")
    @classmethod
    def _clean_industry(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        return value or None

    @field_validator("countries")
    @classmethod
    def _check_countries(cls, value: list[str]) -> list[str]:
        allowed = set(available_countries())
        unknown = [c for c in value if c not in allowed]
        if unknown:
            raise ValueError(f"Unknown countries: {', '.join(unknown)}")
        return list(dict.fromkeys(value))


class AutoDiscoverySettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    industry: str | None
    batch_size: int
    require_email: bool
    require_website: bool
    run_every_minutes: int
    countries: list[str]

    location_index: int
    last_run_at: datetime | None
    last_location: str | None
    last_run_found: int
    total_found: int
    last_error: str | None

    next_location: str | None = None
    total_locations: int = 0


class AutoDiscoveryCountriesResponse(BaseModel):
    countries: list[str]