from typing import Literal

from pydantic import BaseModel, Field


class BusinessDiscoveryRequest(BaseModel):
    country: str = Field(min_length=2, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str = Field(min_length=2, max_length=100)
    industry: str = Field(min_length=2, max_length=100)
    limit: int = Field(default=100, ge=1, le=10000)
    filters: set[Literal["has_email", "has_website"]] = Field(
        default_factory=set,
        description="Required lead attributes. Select both to require both.",
    )


class BusinessDiscoveryResult(BaseModel):
    source_id: str
    source: str

    name: str

    industry: str | None = None

    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None

    latitude: float | None = None
    longitude: float | None = None

    phone: str | None = None
    email: str | None = None
    website: str | None = None

    website_status: str

    osm_type: str | None = None
    osm_id: int | None = None


class BusinessDiscoveryResponse(BaseModel):
    success: bool
    total_found: int
    location: dict
    industry: str
    businesses: list[BusinessDiscoveryResult]
    candidates_scanned: int = 0
    filters_applied: list[str] = Field(default_factory=list)
