from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_email_draft import AIEmailDraft
from app.models.email_delivery import EmailDelivery
from app.models.email_queue import EmailQueue
from app.models.email_message import EmailMessage
from app.models.lead import Lead
from app.models.lead_qualification import LeadQualification
from app.models.website_issue import WebsiteIssue
from app.models.website_scan import WebsiteScan
from app.schemas.analytics import (
    AnalyticsSummary,
    DailyAnalytics,
    EmailAnalytics,
    EmailRateAnalytics,
    IndustryAnalytics,
    LeadAnalytics,
    QualificationAnalytics,
    WebsiteAnalytics,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def percentage(
    numerator: int,
    denominator: int,
) -> float:
    if denominator <= 0:
        return 0.0

    return round(
        (numerator / denominator) * 100,
        2,
    )


class AnalyticsService:

    def __init__(self) -> None:
        # Simple in-memory cache: {(user_id_str, days): (monotonic_time, result)}
        self._cache: dict = {}

    def get_lead_analytics(
        self,
        db: Session,
        user_id: UUID,
    ) -> LeadAnalytics:

        total = db.scalar(
            select(func.count(Lead.id))
            .where(
                Lead.user_id == user_id
            )
        ) or 0

        status_rows = db.execute(
            select(
                Lead.lead_status,
                func.count(Lead.id),
            )
            .where(
                Lead.user_id == user_id
            )
            .group_by(
                Lead.lead_status
            )
        ).all()

        statuses = {
            str(status or "").lower(): count
            for status, count in status_rows
        }

        website_rows = db.execute(
            select(
                Lead.website_status,
                func.count(Lead.id),
            )
            .where(
                Lead.user_id == user_id
            )
            .group_by(
                Lead.website_status
            )
        ).all()

        website_statuses = {
            str(status or "").lower(): count
            for status, count in website_rows
        }

        return LeadAnalytics(
            total=total,
            new=statuses.get("new", 0),
            contacted=statuses.get(
                "contacted",
                0,
            ),
            qualified=statuses.get(
                "qualified",
                0,
            ),
            converted=statuses.get(
                "converted",
                0,
            ),
            closed=statuses.get(
                "closed",
                0,
            ),
            with_website=website_statuses.get(
                "has_website",
                0,
            ),
            without_website=website_statuses.get(
                "no_website",
                0,
            ),
            unreachable_website=website_statuses.get(
                "unreachable",
                0,
            ),
        )

    def get_qualification_analytics(
        self,
        db: Session,
        user_id: UUID,
    ) -> QualificationAnalytics:

        rows = db.execute(
            select(
                LeadQualification.qualification_level,
                LeadQualification.outreach_readiness,
                func.count(
                    LeadQualification.id
                ),
            )
            .where(
                LeadQualification.user_id == user_id
            )
            .group_by(
                LeadQualification.qualification_level,
                LeadQualification.outreach_readiness,
            )
        ).all()

        result = QualificationAnalytics()

        for level, readiness, count in rows:
            level_value = (
                str(level or "").lower()
            )

            readiness_value = (
                str(readiness or "").lower()
            )

            result.total += count

            if level_value == "high":
                result.high += count
            elif level_value == "medium":
                result.medium += count
            elif level_value == "low":
                result.low += count
            else:
                result.unqualified += count

            if readiness_value == "ready":
                result.ready += count
            elif readiness_value == "review":
                result.review += count
            elif readiness_value == "missing_contact":
                result.missing_contact += count
            else:
                result.not_ready += count

        return result

    def get_website_analytics(
        self,
        db: Session,
        user_id: UUID,
    ) -> WebsiteAnalytics:

        scan_rows = db.execute(
            select(
                WebsiteScan.scan_status,
                func.count(WebsiteScan.id),
            )
            .where(
                WebsiteScan.user_id == user_id
            )
            .group_by(
                WebsiteScan.scan_status
            )
        ).all()

        scans = {
            str(status or "").lower(): count
            for status, count in scan_rows
        }

        issue_rows = db.execute(
            select(
                WebsiteIssue.severity,
                func.count(WebsiteIssue.id),
            )
            .where(
                WebsiteIssue.user_id == user_id
            )
            .group_by(
                WebsiteIssue.severity
            )
        ).all()

        issues = {
            str(severity or "").lower(): count
            for severity, count in issue_rows
        }

        total_scans = sum(
            scans.values()
        )

        total_issues = sum(
            issues.values()
        )

        return WebsiteAnalytics(
            total_scans=total_scans,
            completed_scans=scans.get(
                "completed",
                0,
            ),
            failed_scans=scans.get(
                "failed",
                0,
            ),
            total_issues=total_issues,
            critical_issues=issues.get(
                "critical",
                0,
            ),
            high_issues=issues.get(
                "high",
                0,
            ),
            medium_issues=issues.get(
                "medium",
                0,
            ),
            low_issues=issues.get(
                "low",
                0,
            ),
        )

    def get_email_analytics(
        self,
        db: Session,
        user_id: UUID,
    ) -> EmailAnalytics:

        queue_rows = db.execute(
            select(
                EmailQueue.status,
                func.count(EmailQueue.id),
            )
            .where(
                EmailQueue.user_id == user_id
            )
            .group_by(
                EmailQueue.status
            )
        ).all()

        queue = {
            str(status or "").lower(): count
            for status, count in queue_rows
        }

        delivery_rows = db.execute(
            select(
                EmailDelivery.status,
                func.count(EmailDelivery.id),
            )
            .where(
                EmailDelivery.user_id == user_id
            )
            .group_by(
                EmailDelivery.status
            )
        ).all()

        deliveries = {
            str(status or "").lower(): count
            for status, count in delivery_rows
        }

        replies = db.scalar(
            select(
                func.count(EmailMessage.id)
            )
            .where(
                EmailMessage.user_id == user_id,
                EmailMessage.direction == "inbound",
            )
        ) or 0

        return EmailAnalytics(
            total_queued=sum(
                queue.values()
            ),
            pending=queue.get(
                "pending",
                0,
            ),
            scheduled=queue.get(
                "scheduled",
                0,
            ),
            processing=queue.get(
                "processing",
                0,
            ),
            sent=queue.get(
                "sent",
                0,
            ),
            failed=queue.get(
                "failed",
                0,
            ),
            cancelled=queue.get(
                "cancelled",
                0,
            ),
            total_deliveries=sum(
                deliveries.values()
            ),
            delivered=deliveries.get(
                "delivered",
                0,
            ),
            opened=deliveries.get(
                "opened",
                0,
            ),
            clicked=deliveries.get(
                "clicked",
                0,
            ),
            bounced=deliveries.get(
                "bounced",
                0,
            ),
            complained=deliveries.get(
                "complained",
                0,
            ),
            unsubscribed=deliveries.get(
                "unsubscribed",
                0,
            ),
            replies=replies,
        )

    def get_email_rates(
        self,
        email: EmailAnalytics,
    ) -> EmailRateAnalytics:

        total_deliveries = email.total_deliveries

        return EmailRateAnalytics(
            delivery_rate=percentage(
                email.delivered,
                total_deliveries,
            ),
            open_rate=percentage(
                email.opened,
                total_deliveries,
            ),
            click_rate=percentage(
                email.clicked,
                total_deliveries,
            ),
            bounce_rate=percentage(
                email.bounced,
                total_deliveries,
            ),
            complaint_rate=percentage(
                email.complained,
                total_deliveries,
            ),
            unsubscribe_rate=percentage(
                email.unsubscribed,
                total_deliveries,
            ),
            reply_rate=percentage(
                email.replies,
                total_deliveries,
            ),
        )

    def get_industry_analytics(
        self,
        db: Session,
        user_id: UUID,
    ) -> list[IndustryAnalytics]:

        lead_rows = db.execute(
            select(
                Lead.industry,
                func.count(Lead.id),
            )
            .where(
                Lead.user_id == user_id
            )
            .group_by(
                Lead.industry
            )
            .order_by(
                func.count(Lead.id).desc()
            )
        ).all()

        result = []

        for industry, leads in lead_rows:
            industry_value = (
                industry or "Unknown"
            )

            qualified = db.scalar(
                select(
                    func.count(
                        LeadQualification.id
                    )
                )
                .join(
                    Lead,
                    Lead.id
                    == LeadQualification.lead_id,
                )
                .where(
                    LeadQualification.user_id
                    == user_id,
                    Lead.industry
                    == industry,
                    LeadQualification.qualification_level
                    .in_(
                        [
                            "high",
                            "medium",
                        ]
                    ),
                )
            ) or 0

            with_website = db.scalar(
                select(
                    func.count(Lead.id)
                )
                .where(
                    Lead.user_id == user_id,
                    Lead.industry == industry,
                    Lead.website_status
                    == "has_website",
                )
            ) or 0

            without_website = db.scalar(
                select(
                    func.count(Lead.id)
                )
                .where(
                    Lead.user_id == user_id,
                    Lead.industry == industry,
                    Lead.website_status
                    == "no_website",
                )
            ) or 0

            result.append(
                IndustryAnalytics(
                    industry=industry_value,
                    leads=leads,
                    qualified=qualified,
                    with_website=with_website,
                    without_website=without_website,
                )
            )

        return result

    def get_daily_analytics(
        self,
        db: Session,
        user_id: UUID,
        days: int = 30,
    ) -> list[DailyAnalytics]:

        now = utc_now()

        start_date = (
            now - timedelta(days=days - 1)
        ).date()

        lead_rows = db.execute(
            select(
                func.date(Lead.created_at),
                func.count(Lead.id),
            )
            .where(
                Lead.user_id == user_id,
                Lead.created_at >= datetime.combine(
                    start_date,
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                ),
            )
            .group_by(
                func.date(Lead.created_at)
            )
        ).all()

        email_rows = db.execute(
            select(
                func.date(EmailDelivery.sent_at),
                func.count(EmailDelivery.id),
            )
            .where(
                EmailDelivery.user_id == user_id,
                EmailDelivery.sent_at.is_not(None),
                EmailDelivery.sent_at >= datetime.combine(
                    start_date,
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                ),
            )
            .group_by(
                func.date(EmailDelivery.sent_at)
            )
        ).all()

        reply_rows = db.execute(
            select(
                func.date(EmailMessage.received_at),
                func.count(EmailMessage.id),
            )
            .where(
                EmailMessage.user_id == user_id,
                EmailMessage.direction == "inbound",
                EmailMessage.received_at.is_not(None),
                EmailMessage.received_at >= datetime.combine(
                    start_date,
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                ),
            )
            .group_by(
                func.date(EmailMessage.received_at)
            )
        ).all()

        leads_by_day = {
            str(date): count
            for date, count in lead_rows
        }

        emails_by_day = {
            str(date): count
            for date, count in email_rows
        }

        replies_by_day = {
            str(date): count
            for date, count in reply_rows
        }

        result = []

        for index in range(days):
            current_date = (
                start_date
                + timedelta(days=index)
            )

            key = str(current_date)

            result.append(
                DailyAnalytics(
                    date=key,
                    leads=leads_by_day.get(
                        key,
                        0,
                    ),
                    emails_sent=emails_by_day.get(
                        key,
                        0,
                    ),
                    replies=replies_by_day.get(
                        key,
                        0,
                    ),
                )
            )

        return result

    def get_summary(
        self,
        db: Session,
        user_id: UUID,
        days: int = 30,
    ) -> AnalyticsSummary:
        # ── In-memory cache (10 seconds per user+days combo) ──
        import time as _time
        cache_key = (str(user_id), days)
        cached_at, cached_result = self._cache.get(cache_key, (0, None))
        if cached_result is not None and (_time.monotonic() - cached_at) < 10:
            return cached_result

        leads = self.get_lead_analytics(
            db=db,
            user_id=user_id,
        )

        qualification = (
            self.get_qualification_analytics(
                db=db,
                user_id=user_id,
            )
        )

        website = self.get_website_analytics(
            db=db,
            user_id=user_id,
        )

        email = self.get_email_analytics(
            db=db,
            user_id=user_id,
        )

        rates = self.get_email_rates(
            email=email,
        )

        industries = self.get_industry_analytics(
            db=db,
            user_id=user_id,
        )

        daily = self.get_daily_analytics(
            db=db,
            user_id=user_id,
            days=days,
        )

        result = AnalyticsSummary(
            generated_at=utc_now(),
            leads=leads,
            qualification=qualification,
            website=website,
            email=email,
            rates=rates,
            industries=industries,
            daily=daily,
            metadata={
                "period_days": days,
            },
        )

        self._cache[cache_key] = (_time.monotonic(), result)
        return result


analytics_service = AnalyticsService()