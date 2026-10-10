from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WebsiteScanResponse(BaseModel):
    model_config = {"from_attributes": True}

    success: bool

    id: UUID
    lead_id: UUID

    url: str
    final_url: str | None = None

    http_status: int | None = None
    response_time_ms: int | None = None

    page_size_bytes: int | None = None

    content_type: str | None = None

    title: str | None = None
    meta_description: str | None = None

    h1_count: int
    h2_count: int

    image_count: int
    images_without_alt: int

    internal_link_count: int
    external_link_count: int

    has_viewport: bool
    has_canonical: bool

    is_https: bool

    robots_txt_found: bool
    sitemap_found: bool

    html_language: str | None = None

    scan_status: str
    error: str | None = None

    scanned_at: datetime


class WebsiteScanListResponse(BaseModel):
    success: bool
    total: int
    scans: list[WebsiteScanResponse]


class WebsiteScanRequest(BaseModel):
    force_rescan: bool = Field(
        default=False
    )