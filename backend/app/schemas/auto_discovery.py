from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")


class AutoDiscoveryUpdateRequest(BaseModel):
    enabled: bool = False
    industry: str | None = Field(default=None, max_length=100)
    batch_size: int = Field(default=50, ge=10, le=500)
    require_email: bool = False
    require_website: bool = False
    run_every_minutes: int = Field(default=30, ge=5, le=1440)
    city_size: Literal["big", "medium", "small", "mix"] = "mix"
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
        cleaned = [str(c).strip().upper() for c in value]
        bad = [c for c in cleaned if not _COUNTRY_CODE.match(c)]
        if bad:
            raise ValueError(f"Invalid country codes: {', '.join(bad)}")
        return list(dict.fromkeys(cleaned))


class AutoDiscoverySettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    industry: str | None
    batch_size: int
    require_email: bool
    require_website: bool
    run_every_minutes: int
    city_size: str
    countries: list[str]

    last_run_at: datetime | None
    last_location: str | None
    last_run_found: int
    total_found: int
    last_error: str | None

    cities_visited: int = 0
    next_location: str | None = None
    next_location_count: int = 0


class CountryOption(BaseModel):
    code: str
    name: str


class AutoDiscoveryCountriesResponse(BaseModel):
    countries: list[CountryOption]