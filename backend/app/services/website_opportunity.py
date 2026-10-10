import json
import logging
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.lead import Lead
from app.models.website_opportunity import WebsiteOpportunity
from app.schemas.website_opportunity import (
    WebsiteOpportunityStatusUpdateRequest,
)


logger = logging.getLogger(__name__)

PROMPT_VERSION = "1.0"


def build_system_prompt() -> str:
    return """
You are a professional B2B website-development opportunity
analyst.

Your job is to analyze a business that currently has no
detected website and identify a realistic website-development
opportunity.

The writing must sound:

- Professional
- Human
- Natural
- Specific
- Helpful
- Business-focused
- Conversational
- Not robotic

IMPORTANT:

The business does NOT currently have a detected website.

Do not pretend that you inspected a website.

Do not invent:

- Revenue
- Customers
- Employees
- Services
- Reviews
- Competitors
- Website traffic
- Search rankings
- Business owner names
- Existing digital systems

Use only the supplied business information.

You may recommend reasonable website features based on the
industry, but clearly present them as recommendations rather
than existing business facts.

Do not make guaranteed sales or revenue claims.

Do not say things such as:

"this website will double your revenue"

"you will get thousands of customers"

"guaranteed leads"

Instead explain the practical opportunity.

The output must be valid JSON only.

Required structure:

{
  "business_summary": "Natural business summary",
  "opportunity_summary": "Natural explanation of the website opportunity",
  "recommended_solution": "Recommended website solution",
  "sales_angle": "Natural personalized sales angle",
  "personalization_points": [
    "specific point"
  ],
  "suggested_features": [
    "feature"
  ]
}
""".strip()


def build_user_prompt(
    lead: Lead,
) -> str:

    location_parts = [
        lead.city,
        lead.state,
        lead.country,
    ]

    location = ", ".join(
        part
        for part in location_parts
        if part
    )

    context = {
        "business": {
            "name": lead.name,
            "industry": lead.industry,
            "city": lead.city,
            "state": lead.state,
            "country": lead.country,
            "location": location,
            "phone": lead.phone,
            "email": lead.email,
            "website": lead.website,
            "website_status": lead.website_status,
            "address": lead.address,
        }
    }

    return (
        "Analyze this business as a potential website "
        "development opportunity.\n\n"
        "The business currently has no detected website.\n\n"
        "Use only the supplied information.\n\n"
        f"{json.dumps(context, indent=2, default=str)}"
    )


async def call_cloudflare_ai(
    system_prompt: str,
    user_prompt: str,
) -> dict:

    url = (
        "https://api.cloudflare.com/client/v4/"
        f"accounts/{settings.cloudflare_account_id}"
        "/ai/run/"
        f"{settings.cloudflare_ai_model}"
    )

    headers = {
        "Authorization": (
            f"Bearer {settings.cloudflare_api_token}"
        ),
        "Content-Type": "application/json",
    }

    payload = {
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        "temperature": 0.3,
        "max_tokens": 2500,
    }

    timeout = httpx.Timeout(
        60.0,
        connect=15.0,
    )

    try:
        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )

    except httpx.TimeoutException as exc:

        logger.exception(
            "Cloudflare AI opportunity request timed out."
        )

        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Cloudflare AI request timed out.",
        ) from exc

    except httpx.RequestError as exc:

        logger.exception(
            "Cloudflare AI opportunity request failed."
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloudflare AI network request failed.",
        ) from exc

    if response.status_code >= 400:

        logger.error(
            "Cloudflare AI returned %s: %s",
            response.status_code,
            response.text[:1000],
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Cloudflare AI returned an error. "
                f"HTTP {response.status_code}."
            ),
        )

    try:
        data = response.json()

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloudflare AI returned invalid JSON.",
        ) from exc

    if not data.get("success", False):

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloudflare AI request was unsuccessful.",
        )

    result = data.get("result")

    if not result:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloudflare AI returned no result.",
        )

    content = None

    if isinstance(result, dict):

        content = result.get("response")

        if content is None:

            choices = result.get("choices")

            if choices:

                content = (
                    choices[0]
                    .get("message", {})
                    .get("content")
                )

    elif isinstance(result, str):

        content = result

    if not content:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloudflare AI returned empty content.",
        )

    content = content.strip()

    if content.startswith("```json"):
        content = content[7:]

    elif content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    content = content.strip()

    try:
        return json.loads(content)

    except json.JSONDecodeError as exc:

        logger.exception(
            "Cloudflare AI returned invalid opportunity JSON."
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Cloudflare AI returned invalid "
                "opportunity data."
            ),
        ) from exc


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


def validate_no_website(
    lead: Lead,
) -> None:

    if lead.website_status != "no_website":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This lead does not have a "
                "no_website status."
            ),
        )


async def generate_opportunity(
    lead: Lead,
) -> dict:

    response = await call_cloudflare_ai(
        system_prompt=build_system_prompt(),
        user_prompt=build_user_prompt(lead),
    )

    required_fields = [
        "business_summary",
        "opportunity_summary",
        "recommended_solution",
        "sales_angle",
    ]

    for field in required_fields:

        if not response.get(field):

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Cloudflare AI returned incomplete "
                    "opportunity data."
                ),
            )

    response.setdefault(
        "personalization_points",
        [],
    )

    response.setdefault(
        "suggested_features",
        [],
    )

    if not isinstance(
        response["personalization_points"],
        list,
    ):

        response["personalization_points"] = []

    if not isinstance(
        response["suggested_features"],
        list,
    ):

        response["suggested_features"] = []

    return response


async def create_opportunity(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
) -> WebsiteOpportunity:

    lead = get_lead_for_user(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    validate_no_website(lead)

    existing = db.scalar(
        select(WebsiteOpportunity).where(
            WebsiteOpportunity.lead_id == lead_id,
            WebsiteOpportunity.user_id == user_id,
        )
    )

    if existing is not None:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A website opportunity already exists "
                "for this lead."
            ),
        )

    analysis = await generate_opportunity(
        lead
    )

    location_parts = [
        lead.city,
        lead.state,
        lead.country,
    ]

    location_summary = ", ".join(
        part
        for part in location_parts
        if part
    )

    record = WebsiteOpportunity(
        user_id=user_id,
        lead_id=lead.id,
        opportunity_type="website_development",
        industry=lead.industry,
        business_name=lead.name,
        location_summary=location_summary,
        business_summary=(
            analysis["business_summary"]
        ),
        opportunity_summary=(
            analysis["opportunity_summary"]
        ),
        recommended_solution=(
            analysis["recommended_solution"]
        ),
        sales_angle=(
            analysis["sales_angle"]
        ),
        personalization_points=(
            analysis["personalization_points"]
        ),
        suggested_features=(
            analysis["suggested_features"]
        ),
        qualification_status="pending",
        opportunity_status="open",
        analysis_json=analysis,
        provider="cloudflare",
        model=settings.cloudflare_ai_model,
        prompt_version=PROMPT_VERSION,
    )

    db.add(record)

    db.commit()

    db.refresh(record)

    return record


def get_latest_opportunity(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
) -> WebsiteOpportunity:

    get_lead_for_user(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    opportunity = db.scalar(
        select(WebsiteOpportunity)
        .where(
            WebsiteOpportunity.lead_id == lead_id,
            WebsiteOpportunity.user_id == user_id,
        )
        .order_by(
            WebsiteOpportunity.created_at.desc()
        )
    )

    if opportunity is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No website opportunity found "
                "for this lead."
            ),
        )

    return opportunity


def list_opportunities(
    db: Session,
    user_id: UUID,
    page: int = 1,
    page_size: int = 25,
) -> tuple[int, list[dict]]:
    """Return a list of opportunity dicts enriched with Lead contact data."""

    from sqlalchemy import func as sa_func
    from app.models.lead import Lead

    page = max(page, 1)

    page_size = min(
        max(page_size, 1),
        100,
    )

    total = db.scalar(
        select(
            sa_func.count(WebsiteOpportunity.id)
        ).where(
            WebsiteOpportunity.user_id == user_id
        )
    ) or 0

    rows = db.execute(
        select(WebsiteOpportunity, Lead)
        .join(
            Lead,
            Lead.id == WebsiteOpportunity.lead_id,
        )
        .where(
            WebsiteOpportunity.user_id == user_id
        )
        .order_by(
            WebsiteOpportunity.created_at.desc()
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    enriched: list[dict] = []

    for opportunity, lead in rows:
        enriched.append({
            "opportunity": opportunity,
            "email": lead.email,
            "phone": lead.phone,
        })

    return int(total), enriched


def update_opportunity_status(
    db: Session,
    opportunity_id: UUID,
    user_id: UUID,
    payload: WebsiteOpportunityStatusUpdateRequest,
) -> WebsiteOpportunity:

    opportunity = db.scalar(
        select(WebsiteOpportunity).where(
            WebsiteOpportunity.id == opportunity_id,
            WebsiteOpportunity.user_id == user_id,
        )
    )

    if opportunity is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website opportunity not found.",
        )

    valid_opportunity_statuses = {
        "open",
        "contacted",
        "converted",
        "closed",
        "ignored",
    }

    valid_qualification_statuses = {
        "pending",
        "qualified",
        "unqualified",
    }

    if (
        payload.opportunity_status
        not in valid_opportunity_statuses
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid opportunity status."
            ),
        )

    if (
        payload.qualification_status is not None
        and payload.qualification_status
        not in valid_qualification_statuses
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid qualification status."
            ),
        )

    opportunity.opportunity_status = (
        payload.opportunity_status
    )

    if payload.qualification_status is not None:

        opportunity.qualification_status = (
            payload.qualification_status
        )

    db.commit()

    db.refresh(opportunity)

    return opportunity