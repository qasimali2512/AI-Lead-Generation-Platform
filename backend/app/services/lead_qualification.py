from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_analysis import AIAnalysis
from app.models.lead import Lead
from app.models.lead_qualification import LeadQualification
from app.models.website_issue import WebsiteIssue
from app.models.website_opportunity import WebsiteOpportunity
from app.models.website_scan import WebsiteScan


def get_lead_for_user(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
) -> Lead:

    lead = db.scalar(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.user_id == user_id,
        )
    )

    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found.",
        )

    return lead


def get_latest_scan(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
) -> WebsiteScan | None:

    return db.scalar(
        select(WebsiteScan)
        .where(
            WebsiteScan.lead_id == lead_id,
            WebsiteScan.user_id == user_id,
            WebsiteScan.scan_status == "completed",
        )
        .order_by(
            WebsiteScan.scanned_at.desc()
        )
    )


def get_latest_ai_analysis(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
) -> AIAnalysis | None:

    return db.scalar(
        select(AIAnalysis)
        .where(
            AIAnalysis.lead_id == lead_id,
            AIAnalysis.user_id == user_id,
        )
        .order_by(
            AIAnalysis.created_at.desc()
        )
    )


def get_website_issues(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
) -> list[WebsiteIssue]:

    return list(
        db.scalars(
            select(WebsiteIssue)
            .where(
                WebsiteIssue.lead_id == lead_id,
                WebsiteIssue.user_id == user_id,
            )
            .order_by(
                WebsiteIssue.created_at.asc()
            )
        ).all()
    )


def get_website_opportunity(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
) -> WebsiteOpportunity | None:

    return db.scalar(
        select(WebsiteOpportunity)
        .where(
            WebsiteOpportunity.lead_id == lead_id,
            WebsiteOpportunity.user_id == user_id,
        )
        .order_by(
            WebsiteOpportunity.created_at.desc()
        )
    )


def add_factor(
    factors: list[dict],
    name: str,
    points: int,
    reason: str,
) -> None:

    if points == 0:
        return

    factors.append(
        {
            "name": name,
            "points": points,
            "reason": reason,
        }
    )


def calculate_qualification(
    lead: Lead,
    scan: WebsiteScan | None,
    issues: list[WebsiteIssue],
    opportunity: WebsiteOpportunity | None,
) -> dict:

    factors: list[dict] = []

    website_score = 0
    business_score = 0
    opportunity_score = 0
    contact_score = 0

    # Business identity and phone are not scoring factors. The score is
    # focused on website opportunity and whether outreach is possible.

    if lead.email:
        contact_score += 25

        add_factor(
            factors,
            "Email available",
            25,
            "A business email is available.",
        )

    # ---------------------------------------------------------
    # No website
    # ---------------------------------------------------------

    if lead.website_status == "no_website":

        opportunity_score += 75

        add_factor(
            factors,
            "No website detected",
            75,
            "The business does not currently have a detected website.",
        )

    # ---------------------------------------------------------
    # Existing website
    # ---------------------------------------------------------

    elif lead.website_status == "has_website":

        website_score += 10

        add_factor(
            factors,
            "Website detected",
            10,
            "The business has a detected website.",
        )

        if scan is not None:

            website_score += 10

            add_factor(
                factors,
                "Website successfully scanned",
                10,
                "A completed website scan is available.",
            )

        issue_count = len(issues)

        if issue_count >= 3:

            website_score += 15

            add_factor(
                factors,
                "Multiple website issues",
                15,
                (
                    f"The latest available issue data contains "
                    f"{issue_count} detected issues."
                ),
            )

        elif issue_count >= 1:

            website_score += 8

            add_factor(
                factors,
                "Website issue detected",
                8,
                (
                    f"The latest available issue data contains "
                    f"{issue_count} detected issue."
                ),
            )

    # ---------------------------------------------------------
    # Website unreachable
    # ---------------------------------------------------------

    elif lead.website_status == "unreachable":

        website_score += 20

        add_factor(
            factors,
            "Website unreachable",
            20,
            (
                "A website was discovered but could not "
                "currently be reached."
            ),
        )

    # ---------------------------------------------------------
    # Unknown website
    # ---------------------------------------------------------

    elif lead.website_status == "unknown":

        website_score += 5

        add_factor(
            factors,
            "Website status unknown",
            5,
            "The website status has not been fully determined.",
        )

    # ---------------------------------------------------------
    # Total
    # ---------------------------------------------------------

    total_score = (
        website_score
        + business_score
        + opportunity_score
        + contact_score
    )

    # ---------------------------------------------------------
    # Qualification level
    # ---------------------------------------------------------

    if total_score >= 80:
        qualification_level = "high"

    elif total_score >= 55:
        qualification_level = "medium"

    elif total_score >= 30:
        qualification_level = "low"

    else:
        qualification_level = "unqualified"

    # ---------------------------------------------------------
    # Outreach readiness
    # ---------------------------------------------------------

    if not lead.email:

        outreach_readiness = "missing_contact"

    elif total_score >= 80:

        outreach_readiness = "ready"

    elif total_score >= 55:

        outreach_readiness = "review"

    else:

        outreach_readiness = "not_ready"

    # ---------------------------------------------------------
    # Recommended approach
    # ---------------------------------------------------------

    if lead.website_status == "no_website":

        recommended_approach = (
            "Introduce a professional website-development "
            "solution based on the business industry and "
            "location. Keep the message focused on practical "
            "online presence improvements rather than "
            "unsupported claims."
        )

    elif lead.website_status == "has_website":

        recommended_approach = (
            "Reference specific website findings from the "
            "latest scan and explain practical improvements "
            "that could make the website more polished, "
            "accessible, or technically sound."
        )

    elif lead.website_status == "unreachable":

        recommended_approach = (
            "Mention that the website could not be reached "
            "during the latest automated check and offer "
            "technical assistance without assuming the "
            "reason for the outage."
        )

    else:

        recommended_approach = (
            "Collect additional website and contact "
            "information before starting personalized "
            "outreach."
        )

    # ---------------------------------------------------------
    # Qualification reason
    # ---------------------------------------------------------

    reason_parts = []

    if lead.industry:
        reason_parts.append(
            f"Industry: {lead.industry}."
        )

    if lead.city:
        reason_parts.append(
            f"Location: {lead.city}."
        )

    if lead.website_status:
        reason_parts.append(
            f"Website status: {lead.website_status}."
        )

    if lead.email:
        reason_parts.append(
            "A contact email is available."
        )
    else:
        reason_parts.append(
            "No contact email is currently available."
        )

    qualification_reason = " ".join(
        reason_parts
    )

    qualification_json = {
        "scores": {
            "website_score": website_score,
            "business_score": business_score,
            "opportunity_score": opportunity_score,
            "contact_score": contact_score,
            "total_score": total_score,
        },
        "qualification_level": qualification_level,
        "outreach_readiness": outreach_readiness,
        "website_status": lead.website_status,
        "factors": factors,
    }

    return {
        "website_score": website_score,
        "business_score": business_score,
        "opportunity_score": opportunity_score,
        "contact_score": contact_score,
        "total_score": total_score,
        "qualification_level": qualification_level,
        "outreach_readiness": outreach_readiness,
        "qualification_reason": qualification_reason,
        "recommended_approach": recommended_approach,
        "qualification_factors": factors,
        "qualification_json": qualification_json,
    }


def save_qualification(
    db: Session,
    lead: Lead,
    data: dict,
) -> LeadQualification:

    existing = db.scalar(
        select(LeadQualification).where(
            LeadQualification.user_id == lead.user_id,
            LeadQualification.lead_id == lead.id,
        )
    )

    if existing is None:

        record = LeadQualification(
            user_id=lead.user_id,
            lead_id=lead.id,
        )

        db.add(record)

    else:

        record = existing

    record.website_score = data["website_score"]
    record.business_score = data["business_score"]
    record.opportunity_score = data["opportunity_score"]
    record.contact_score = data["contact_score"]
    record.total_score = data["total_score"]
    record.qualification_level = data[
        "qualification_level"
    ]
    record.outreach_readiness = data[
        "outreach_readiness"
    ]
    record.qualification_reason = data[
        "qualification_reason"
    ]
    record.recommended_approach = data[
        "recommended_approach"
    ]
    record.qualification_factors = data[
        "qualification_factors"
    ]
    record.qualification_json = data[
        "qualification_json"
    ]

    lead.qualification_status = data[
        "qualification_level"
    ]

    # NOTE: Caller is responsible for committing the transaction.
    # This allows save_qualification to be called inside an outer
    # transaction (e.g. save_discovery_results) without double-commits.

    return record


def qualify_lead(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
    commit: bool = True,
) -> LeadQualification:
    """Score + persist a single lead's qualification.

    Args:
        commit: If True (default), commit after saving so the score is
                persisted immediately.  Pass False when called inside an
                outer transaction that will commit itself (e.g.
                save_discovery_results).
    """

    lead = get_lead_for_user(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    scan = get_latest_scan(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    issues = get_website_issues(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    opportunity = get_website_opportunity(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    data = calculate_qualification(
        lead=lead,
        scan=scan,
        issues=issues,
        opportunity=opportunity,
    )

    record = save_qualification(
        db=db,
        lead=lead,
        data=data,
    )

    if commit:
        db.commit()
        db.refresh(record)

    return record


def qualify_pending_leads(
    db: Session,
    user_id: UUID,
    batch_size: int = 5,
) -> int:
    """Qualify all pending leads for a user.

    Uses a single commit per batch to avoid N x commit overhead and
    session conflicts when called inside another transaction.
    """
    pending_leads = list(
        db.scalars(
            select(Lead).where(
                Lead.user_id == user_id,
                Lead.qualification_status == "pending",
            ).limit(batch_size)
        ).all()
    )

    if not pending_leads:
        return 0

    for lead in pending_leads:
        qualify_lead(
            db=db,
            lead_id=lead.id,
            user_id=user_id,
            commit=False,
        )

    db.commit()

    return len(pending_leads)


def get_latest_qualification(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
) -> LeadQualification:

    get_lead_for_user(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    record = db.scalar(
        select(LeadQualification).where(
            LeadQualification.lead_id == lead_id,
            LeadQualification.user_id == user_id,
        )
    )

    if record is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No qualification found for this lead."
            ),
        )

    return record


def list_qualifications(
    db: Session,
    user_id: UUID,
    page: int = 1,
    page_size: int = 25,
) -> tuple[int, list[LeadQualification]]:

    total = db.scalar(
        select(
            func.count(
                LeadQualification.id
            )
        ).where(
            LeadQualification.user_id == user_id
        )
    ) or 0

    records = list(
        db.scalars(
            select(LeadQualification)
            .where(
                LeadQualification.user_id == user_id
            )
            .order_by(
                LeadQualification.total_score.desc()
            )
            .offset(
                (page - 1) * page_size
            )
            .limit(page_size)
        ).all()
    )

    return int(total), records