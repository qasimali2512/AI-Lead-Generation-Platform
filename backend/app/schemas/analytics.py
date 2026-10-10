from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LeadAnalytics(BaseModel):
    total: int = 0
    new: int = 0
    contacted: int = 0
    qualified: int = 0
    converted: int = 0
    closed: int = 0

    with_website: int = 0
    without_website: int = 0
    unreachable_website: int = 0


class QualificationAnalytics(BaseModel):
    total: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    unqualified: int = 0
    ready: int = 0
    review: int = 0
    not_ready: int = 0
    missing_contact: int = 0


class WebsiteAnalytics(BaseModel):
    total_scans: int = 0
    completed_scans: int = 0
    failed_scans: int = 0

    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0


class EmailAnalytics(BaseModel):
    total_queued: int = 0
    pending: int = 0
    scheduled: int = 0
    processing: int = 0
    sent: int = 0
    failed: int = 0
    cancelled: int = 0

    total_deliveries: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0
    complained: int = 0
    unsubscribed: int = 0

    replies: int = 0


class EmailRateAnalytics(BaseModel):
    delivery_rate: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    bounce_rate: float = 0.0
    complaint_rate: float = 0.0
    unsubscribe_rate: float = 0.0
    reply_rate: float = 0.0


class IndustryAnalytics(BaseModel):
    industry: str
    leads: int = 0
    qualified: int = 0
    with_website: int = 0
    without_website: int = 0


class DailyAnalytics(BaseModel):
    date: str
    leads: int = 0
    emails_sent: int = 0
    replies: int = 0


class AnalyticsSummary(BaseModel):
    generated_at: datetime

    leads: LeadAnalytics
    qualification: QualificationAnalytics
    website: WebsiteAnalytics
    email: EmailAnalytics
    rates: EmailRateAnalytics

    industries: list[IndustryAnalytics] = Field(
        default_factory=list
    )

    daily: list[DailyAnalytics] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )