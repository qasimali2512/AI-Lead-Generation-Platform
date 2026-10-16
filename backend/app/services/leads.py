from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.schemas.discovery import BusinessDiscoveryResult
from app.schemas.leads import LeadStatusUpdateRequest


# ---------------------------------------------------------
# Save discovered business
# ---------------------------------------------------------

def save_discovered_business(
    db: Session,
    user_id: UUID,
    business: BusinessDiscoveryResult,
) -> tuple[Lead, bool]:

    existing = db.scalar(
        select(Lead).where(
            Lead.user_id == user_id,
            Lead.source == business.source,
            Lead.source_id == business.source_id,
        )
    )

    if existing:
        return existing, False

    lead = Lead(
        user_id=user_id,

        source=business.source,
        source_id=business.source_id,

        name=business.name,
        industry=business.industry,

        address=business.address,
        city=business.city,
        state=business.state,
        country=business.country,

        latitude=business.latitude,
        longitude=business.longitude,

        phone=business.phone,
        email=business.email,
        website=business.website,

        website_status=business.website_status,

        osm_type=business.osm_type,
        osm_id=business.osm_id,

        lead_status="new",
        qualification_status="pending",
    )

    db.add(lead)
    db.flush()

    return lead, True


# ---------------------------------------------------------
# Save discovery batch
# ---------------------------------------------------------

def save_discovery_results(
    db: Session,
    user_id: UUID,
    businesses: list[BusinessDiscoveryResult],
) -> dict:

    created = 0
    existing = 0

    saved_leads: list[Lead] = []

    try:
        for business in businesses:

            lead, was_created = save_discovered_business(
                db=db,
                user_id=user_id,
                business=business,
            )

            saved_leads.append(lead)

            if was_created:
                created += 1
            else:
                existing += 1

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "created": created,
        "existing": existing,
        "total": len(saved_leads),
        "leads": saved_leads,
    }


# ---------------------------------------------------------
# Get leads  — server-side search + filter + pagination
# ---------------------------------------------------------

def get_user_leads(
    db: Session,
    user_id: UUID,
    page: int = 1,
    page_size: int = 25,
    # --- date range ---
    days: int | None = 1,
    # --- text search (name / city / industry) ---
    search: str | None = None,
    # --- column filters ---
    has_website: str | None = None,   # "yes" | "no"
    has_email: str | None = None,     # "yes" | "no"
    qualification: str | None = None, # "qualified" | "unqualified" | "ready"
    industry: str | None = None,
    city: str | None = None,
    website_status: str | None = None,
    lead_status: str | None = None,
    # --- sort ---
    sort_by: str = "date",            # "date" | "name" | "industry"
) -> tuple[list[Lead], int]:

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    filters = [Lead.user_id == user_id]

    # Date range filter — DB level
    if days is not None and days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        filters.append(Lead.created_at >= since)

    # Full-text search across name / city / industry (ILIKE)
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Lead.name.ilike(term),
                Lead.city.ilike(term),
                Lead.industry.ilike(term),
                Lead.email.ilike(term),
                Lead.address.ilike(term),
            )
        )

    # Website presence filter
    if has_website == "yes":
        filters.append(Lead.website.is_not(None))
        filters.append(Lead.website != "")
    elif has_website == "no":
        filters.append(
            or_(Lead.website.is_(None), Lead.website == "")
        )

    # Email presence filter
    if has_email == "yes":
        filters.append(Lead.email.is_not(None))
        filters.append(Lead.email != "")
    elif has_email == "no":
        filters.append(
            or_(Lead.email.is_(None), Lead.email == "")
        )

    # Qualification filter
    if qualification == "qualified":
        filters.append(Lead.qualification_status.ilike("%qualified%"))
        filters.append(Lead.qualification_status.not_ilike("%unqualified%"))
    elif qualification == "unqualified":
        filters.append(
            or_(
                Lead.qualification_status.ilike("%unqualified%"),
                Lead.qualification_status.ilike("%not qualified%"),
            )
        )
    elif qualification == "ready":
        filters.append(
            or_(
                Lead.qualification_status.ilike("%ready%"),
                Lead.qualification_status.ilike("%high%"),
            )
        )

    # Legacy filters
    if industry:
        filters.append(Lead.industry == industry.strip().lower())

    if city:
        filters.append(func.lower(Lead.city) == city.strip().lower())

    if website_status:
        filters.append(Lead.website_status == website_status)

    if lead_status:
        filters.append(Lead.lead_status == lead_status)

    # Count
    total = db.scalar(
        select(func.count())
        .select_from(Lead)
        .where(*filters)
    ) or 0

    # Sort
    if sort_by == "name":
        order = Lead.name.asc()
    elif sort_by == "industry":
        order = Lead.industry.asc()
    else:
        order = Lead.created_at.desc()

    query = (
        select(Lead)
        .where(*filters)
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    leads = list(db.scalars(query).all())

    return leads, total


# ---------------------------------------------------------
# Get one lead
# ---------------------------------------------------------

def get_user_lead(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
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


# ---------------------------------------------------------
# Update lead
# ---------------------------------------------------------

def update_user_lead(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
    payload: LeadStatusUpdateRequest,
) -> Lead:

    lead = get_user_lead(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    lead.lead_status = payload.lead_status.strip()

    if payload.notes is not None:
        lead.notes = payload.notes

    try:
        db.commit()
        db.refresh(lead)

    except Exception:
        db.rollback()
        raise

    return lead


# ---------------------------------------------------------
# Delete lead
# ---------------------------------------------------------

def delete_user_lead(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
) -> None:

    lead = get_user_lead(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    try:
        db.delete(lead)
        db.commit()

    except Exception:
        db.rollback()
        raise