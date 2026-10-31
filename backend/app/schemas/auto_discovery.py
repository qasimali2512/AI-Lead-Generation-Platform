from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID
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

    # Auto-Campaign Automation fields
    auto_campaign_enabled: bool = False
    auto_campaign_opportunity_threshold: float = Field(default=30.0, ge=0.0, le=100.0)
    auto_campaign_daily_limit: int = Field(default=50, ge=1, le=10000)
    auto_campaign_email_account_ids: list[str] = Field(default_factory=list)
    auto_campaign_start_time: str = Field(default="09:00", min_length=5, max_length=5)
    auto_campaign_end_time: str = Field(default="17:00", min_length=5, max_length=5)

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

    # Auto-Campaign Automation
    auto_campaign_enabled: bool = False
    auto_campaign_paused: bool = False
    auto_campaign_opportunity_threshold: float = 30.0
    auto_campaign_daily_limit: int = 50
    auto_campaign_email_account_ids: list[str] = Field(default_factory=list)
    auto_campaign_start_time: str = "09:00"
    auto_campaign_end_time: str = "17:00"
    auto_campaign_last_created_at: datetime | None = None
    auto_campaigns_created: int = 0
    auto_campaign_id: UUID | None = None
    auto_campaign_status: str | None = None
    auto_campaign_leads_total: int = 0
    auto_campaign_leads_sent: int = 0
    auto_campaign_leads_left: int = 0
    auto_campaign_preview_count: int = 0
    auto_campaign_preview_remaining: int = 0
    auto_campaign_preview_leads: list["AutoCampaignLeadPreview"] = Field(
        default_factory=list
    )


class AutoCampaignLeadPreview(BaseModel):
    id: UUID
    name: str
    email: str
    score: int
    status: str = "queued"


class CountryOption(BaseModel):
    code: str
    name: str


class AutoDiscoveryCountriesResponse(BaseModel):
    countries: list[CountryOption]