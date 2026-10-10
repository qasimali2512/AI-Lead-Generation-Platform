import json
import logging
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.ai_analysis import AIAnalysis
from app.models.lead import Lead
from app.models.website_issue import WebsiteIssue
from app.models.website_scan import WebsiteScan
from app.schemas.ai_analysis import AIAnalysisData


logger = logging.getLogger(__name__)

PROMPT_VERSION = "1.0"


def get_cloudflare_url() -> str:
    return (
        "https://api.cloudflare.com/client/v4/"
        f"accounts/{settings.cloudflare_account_id}"
        "/ai/run/"
        f"{settings.cloudflare_ai_model}"
    )


def build_analysis_context(
    lead: Lead,
    scan: WebsiteScan,
    issues: list[WebsiteIssue],
) -> dict:

    return {
        "lead": {
            "name": lead.name,
            "industry": lead.industry,
            "address": lead.address,
            "city": lead.city,
            "state": lead.state,
            "country": lead.country,
            "phone": lead.phone,
            "email": lead.email,
            "website": lead.website,
            "website_status": lead.website_status,
        },

        "website_scan": {
            "url": scan.url,
            "final_url": scan.final_url,
            "http_status": scan.http_status,
            "response_time_ms": scan.response_time_ms,
            "page_size_bytes": scan.page_size_bytes,
            "content_type": scan.content_type,
            "title": scan.title,
            "meta_description": scan.meta_description,
            "h1_count": scan.h1_count,
            "h2_count": scan.h2_count,
            "image_count": scan.image_count,
            "images_without_alt": scan.images_without_alt,
            "internal_link_count": scan.internal_link_count,
            "external_link_count": scan.external_link_count,
            "has_viewport": scan.has_viewport,
            "has_canonical": scan.has_canonical,
            "is_https": scan.is_https,
            "robots_txt_found": scan.robots_txt_found,
            "sitemap_found": scan.sitemap_found,
            "html_language": scan.html_language,
        },

        "website_issues": [
            {
                "issue_code": issue.issue_code,
                "category": issue.category,
                "title": issue.title,
                "severity": issue.severity,
                "evidence": issue.evidence,
                "recommendation": issue.recommendation,
                "current_value": issue.current_value,
                "expected_value": issue.expected_value,
            }
            for issue in issues
        ],
    }


def build_system_prompt() -> str:
    return """
You are a professional B2B website analysis assistant.

Your writing must sound like a knowledgeable human
consultant who actually reviewed the supplied website
audit data.

WRITING STYLE:

- Professional
- Natural
- Human-like
- Clear
- Concise
- Specific
- Conversational but business appropriate
- No robotic wording
- No unnecessary marketing buzzwords
- No exaggerated claims
- No generic filler
- No emojis

Do not write like an automated SEO report.

For example, avoid:

"Your website has several technical issues that
negatively impact your online presence."

Prefer natural wording such as:

"I noticed a few technical areas that could be cleaned
up, including the missing mobile viewport configuration
and missing page metadata."

FACTUAL RULES:

1. Use ONLY the information supplied in the input.

2. Never invent facts.

3. Never invent revenue, customers, traffic, rankings,
conversion rates, employees, technologies or business
services.

4. Never claim that an issue definitely caused lost sales
unless the supplied data proves it.

5. You may explain potential business impact, but clearly
treat it as potential impact.

6. Every priority issue MUST use an issue_code from the
supplied website_issues list.

7. Evidence must come from supplied scanner data.

8. Never invent a person's name.

9. Never invent competitors.

10. Never invent testimonials or customer information.

11. If information is unavailable, say so naturally.

12. Personalization points must be based on actual
business information or scanner findings.

13. The sales angle should explain how a professional
service could help based on the actual findings.

14. Do not promise specific results.

15. Do not use phrases such as:
    "guaranteed results"
    "10x your sales"
    "double your revenue"
    "get thousands of customers"

16. Return ONLY valid JSON.

Required JSON structure:

{
  "business_summary": "Natural professional summary",
  "website_assessment": "Natural assessment",
  "opportunity_summary": "Natural opportunity explanation",
  "sales_angle": "Natural sales angle",
  "personalization_points": [
    "specific point"
  ],
  "priority_issues": [
    {
      "issue_code": "existing issue code",
      "title": "existing issue title",
      "severity": "existing severity",
      "evidence": "actual evidence",
      "business_impact": "potential business impact",
      "recommended_action": "practical recommendation"
    }
  ]
}
""".strip()


def build_user_prompt(context: dict) -> str:

    return (
        "Review the following business and website audit "
        "data.\n\n"
        "Write a professional, natural and human-like "
        "analysis.\n\n"
        "Do not add information that is not supplied.\n\n"
        f"{json.dumps(context, indent=2, default=str)}"
    )


async def call_cloudflare_ai(
    system_prompt: str,
    user_prompt: str,
) -> str:

    url = get_cloudflare_url()

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
        "max_tokens": 3000,
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
            "Cloudflare AI request timed out."
        )

        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Cloudflare AI request timed out.",
        ) from exc

    except httpx.RequestError as exc:

        logger.exception(
            "Cloudflare AI request failed."
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

        logger.error(
            "Cloudflare AI unsuccessful response: %s",
            data,
        )

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

    return content


async def generate_ai_analysis(
    lead: Lead,
    scan: WebsiteScan,
    issues: list[WebsiteIssue],
) -> AIAnalysisData:

    context = build_analysis_context(
        lead=lead,
        scan=scan,
        issues=issues,
    )

    system_prompt = build_system_prompt()

    user_prompt = build_user_prompt(
        context
    )

    content = await call_cloudflare_ai(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
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

        parsed = json.loads(content)

        return AIAnalysisData.model_validate(
            parsed
        )

    except Exception as exc:

        logger.exception(
            "Invalid Cloudflare AI analysis."
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Cloudflare AI returned invalid "
                "analysis data."
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


def get_latest_completed_scan(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
) -> WebsiteScan:

    scan = db.scalar(
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

    if scan is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No completed website scan found "
                "for this lead."
            ),
        )

    return scan


def get_scan_issues(
    db: Session,
    lead_id: UUID,
    scan_id: UUID,
    user_id: UUID,
) -> list[WebsiteIssue]:

    return list(
        db.scalars(
            select(WebsiteIssue)
            .where(
                WebsiteIssue.lead_id == lead_id,
                WebsiteIssue.scan_id == scan_id,
                WebsiteIssue.user_id == user_id,
            )
            .order_by(
                WebsiteIssue.created_at.asc()
            )
        ).all()
    )


def save_analysis(
    db: Session,
    lead: Lead,
    scan: WebsiteScan,
    analysis: AIAnalysisData,
) -> AIAnalysis:

    analysis_json = analysis.model_dump()

    record = AIAnalysis(
        user_id=lead.user_id,
        lead_id=lead.id,
        scan_id=scan.id,
        provider="cloudflare",
        model=settings.cloudflare_ai_model,
        prompt_version=PROMPT_VERSION,
        business_summary=analysis.business_summary,
        website_assessment=analysis.website_assessment,
        opportunity_summary=analysis.opportunity_summary,
        sales_angle=analysis.sales_angle,
        personalization_points=(
            analysis.personalization_points
        ),
        priority_issues=[
            issue.model_dump()
            for issue in analysis.priority_issues
        ],
        analysis_json=analysis_json,
    )

    db.add(record)

    db.commit()

    db.refresh(record)

    return record


async def analyze_lead(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
) -> AIAnalysis:

    lead = get_lead_for_user(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    scan = get_latest_completed_scan(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    issues = get_scan_issues(
        db=db,
        lead_id=lead_id,
        scan_id=scan.id,
        user_id=user_id,
    )

    analysis = await generate_ai_analysis(
        lead=lead,
        scan=scan,
        issues=issues,
    )

    return save_analysis(
        db=db,
        lead=lead,
        scan=scan,
        analysis=analysis,
    )


def get_latest_analysis(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
) -> AIAnalysis:

    get_lead_for_user(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    analysis = db.scalar(
        select(AIAnalysis)
        .where(
            AIAnalysis.lead_id == lead_id,
            AIAnalysis.user_id == user_id,
        )
        .order_by(
            AIAnalysis.created_at.desc()
        )
    )

    if analysis is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AI analysis found for this lead.",
        )

    return analysis


def get_analysis_history(
    db: Session,
    lead_id: UUID,
    user_id: UUID,
) -> list[AIAnalysis]:

    get_lead_for_user(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    return list(
        db.scalars(
            select(AIAnalysis)
            .where(
                AIAnalysis.lead_id == lead_id,
                AIAnalysis.user_id == user_id,
            )
            .order_by(
                AIAnalysis.created_at.desc()
            )
        ).all()
    )