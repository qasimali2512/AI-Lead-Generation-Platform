import json
import logging
import re
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.ai_analysis import AIAnalysis
from app.models.brand_settings import BrandSettings
from app.models.ai_email_draft import AIEmailDraft
from app.models.lead import Lead
from app.models.lead_qualification import LeadQualification
from app.models.website_issue import WebsiteIssue
from app.models.website_opportunity import WebsiteOpportunity
from app.models.website_scan import WebsiteScan
from app.schemas.ai_email import (
    AIEmailGenerateData,
    AIEmailGenerateRequest,
)


logger = logging.getLogger(__name__)

PROMPT_VERSION = "3.0"


ALLOWED_EMAIL_TYPES = {
    "initial_outreach",
    "follow_up",
    "website_offer",
    "seo_offer",
    "general_business_outreach",
}


def _is_french_lead(lead: Lead) -> bool:
    """Use French for French prospects when no explicit language exists."""
    location = " ".join(
        str(value or "") for value in (
            lead.country, lead.state, lead.city, lead.address,
        )
    ).casefold()
    return "france" in location or "français" in location or "france" in location


def _default_call_to_action(is_french: bool) -> str:
    if is_french:
        return "Seriez-vous disponible pour un échange de 10 minutes ?"
    return "Would you be open to a 10-minute call?"


def _has_verified_website_issue(issues: list[WebsiteIssue]) -> bool:
    return any(
        issue.title and (issue.evidence or issue.recommendation)
        for issue in issues
    )


def _draft_quality_problems(body_text: str) -> list[str]:
    """Reject broken AI output before it can become a queued email."""
    normalized = re.sub(r"\s+", " ", body_text).strip()
    lower = normalized.casefold()
    problems: list[str] = []

    if any(token in body_text for token in ("[", "]", "{{", "}}")):
        problems.append("contains a template placeholder")
    if "business name" in lower:
        problems.append("contains the business-name placeholder")

    word_count = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", body_text))
    if word_count > 120:
        problems.append("exceeds 120 words")

    sentences = [
        re.sub(r"^(issue|solution|automation)\s*:\s*", "", sentence.strip(), flags=re.I)
        .casefold()
        for sentence in re.split(r"[.!?\n]+", body_text)
        if len(sentence.strip()) >= 20
    ]
    if len(sentences) != len(set(sentences)):
        problems.append("repeats a sentence")

    # Exact matching misses the common failure mode where a model repeats the
    # same sentence with only a few filler words changed.  Keep this
    # deliberately conservative so distinct observations are not rejected.
    stop_words = {
        "a", "an", "and", "are", "be", "for", "i", "in", "is", "it",
        "of", "on", "or", "that", "the", "this", "to", "we", "with",
    }
    token_sets = [
        {
            token for token in re.findall(r"[\wÀ-ÿ'-]+", sentence)
            if token not in stop_words
        }
        for sentence in sentences
    ]
    for index, first in enumerate(token_sets):
        for second in token_sets[index + 1:]:
            if len(first) < 5 or len(second) < 5:
                continue
            similarity = len(first & second) / len(first | second)
            if similarity >= 0.8:
                problems.append("repeats the same idea")
                return problems

    return problems


def validate_draft_content(subject: str, body_text: str) -> list[str]:
    """Return send-blocking quality problems for a complete email draft."""
    problems = _draft_quality_problems(body_text)
    normalized_subject = re.sub(r"\s+", " ", subject).strip()
    lower_subject = normalized_subject.casefold()

    if not normalized_subject:
        problems.append("has an empty subject")
    elif any(token in subject for token in ("[", "]", "{{", "}}")):
        problems.append("subject contains a template placeholder")
    elif "business name" in lower_subject:
        problems.append("subject contains the business-name placeholder")

    return problems


def _follow_up_uniqueness_problems(
    subject: str,
    body_text: str,
    prior_messages: list[dict],
) -> list[str]:
    """Guard against a follow-up being a subject/body re-send."""
    def normalized(value: str) -> str:
        return re.sub(r"\W+", " ", value.casefold()).strip()

    current_subject = normalized(subject)
    current_body_tokens = set(normalized(body_text).split())
    for message in prior_messages:
        previous_subject = normalized(str(message.get("subject") or ""))
        if current_subject and current_subject == previous_subject:
            return ["reuses a previous subject"]
        previous_tokens = set(normalized(str(message.get("body_text") or "")).split())
        if len(current_body_tokens) >= 8 and len(previous_tokens) >= 8:
            overlap = len(current_body_tokens & previous_tokens) / len(current_body_tokens | previous_tokens)
            if overlap >= 0.72:
                return ["is too similar to a previous message"]
    return []


def _safe_fallback_body(
    *, lead: Lead, issues: list[WebsiteIssue], is_french: bool,
    call_to_action: str,
) -> str:
    """A send-safe email when two model attempts fail quality validation."""
    business_name = " ".join((lead.name or "").split()) or "votre entreprise"
    issue = next(
        (item for item in issues if item.title and (item.evidence or item.recommendation)),
        None,
    )
    if is_french:
        greeting = f"Bonjour l’équipe de {business_name},"
        if issue:
            observation = f"J’ai relevé un point sur votre site : {issue.title}."
            solution = issue.recommendation or "Une correction ciblée peut améliorer le parcours client."
            value = "Nous pouvons aussi automatiser les demandes, réservations et relances selon vos besoins."
            return f"{greeting}\n\n{observation} {solution} {value}\n\n{call_to_action}"
        location = f" à {lead.city}" if lead.city else ""
        return (
            f"{greeting}\n\nJ’ai découvert {business_name}{location}. Nous créons des sites et parcours de réservation plus simples, puis automatisons les demandes et relances. "
            f"Je peux vous proposer quelques pistes adaptées à votre activité.\n\n{call_to_action}"
        )

    greeting = f"Hello {business_name} team,"
    intro = (
        "We are a software agency that helps businesses build a stronger "
        "online presence and automate customer workflows."
    )
    if issue:
        observation = f"I noticed one website issue: {issue.title}."
        solution = issue.recommendation or "A focused fix could make the customer journey smoother."
        value = "We can also automate enquiries, bookings, and follow-ups around the workflow."
        return f"{greeting}\n\n{intro}\n\n{observation} {solution} {value}\n\n{call_to_action}"
    location = f" in {lead.city}" if lead.city else ""
    return (
        f"{greeting}\n\n{intro}\n\nI came across {business_name}{location}. We build clearer websites and booking journeys, then automate enquiries and follow-ups around them. "
        f"I can share a few practical ideas for your business.\n\n{call_to_action}"
    )


def _safe_follow_up_fallback(
    *, lead: Lead, follow_up_number: int, is_french: bool,
) -> tuple[str, str]:
    """Distinct, send-safe fallback when the provider cannot make a follow-up."""
    name = " ".join((lead.name or "your business").split())
    if is_french:
        if follow_up_number == 1:
            return (
                f"Une piste concrète pour {name}",
                "Je voulais vous laisser une idée simple : un parcours de demande ou de réservation plus clair peut réduire les frictions pour vos clients. Je peux vous envoyer un bref aperçu adapté à votre activité par e-mail.",
            )
        return (
            f"Deux idées pour {name} ({follow_up_number})",
            "Plutôt qu’un appel, je peux vous envoyer deux ou trois suggestions concrètes pour votre présence en ligne et vos parcours clients. Souhaitez-vous que je vous les partage par e-mail ?",
        )
    if follow_up_number == 1:
        return (
            f"A practical idea for {name}",
            "One simple area worth reviewing is how easily a visitor can move from interest to an enquiry or booking. I can send a short, tailored review of that journey by email if useful.",
        )
    return (
        f"Two ideas for {name} ({follow_up_number})",
        "Rather than asking for a call, I can send two or three practical ideas for improving the online customer journey and handling enquiries. Would it be useful if I sent them by email?",
    )


def _clean_json_response(text: str) -> str:
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

        text = text.strip()

    # If the text doesn't look like JSON (e.g. it's reasoning text
    # that contains a JSON block), extract the first {...} block.
    if not text.startswith("{"):
        match = re.search(r"\{[\s\S]+\}", text)
        if match:
            text = match.group(0)

    return text.strip()


def _extract_response_text(data: dict) -> str:
    result = data.get("result")

    if isinstance(result, dict):
        response = result.get("response")

        if isinstance(response, str):
            return response

        choices = result.get("choices")

        if isinstance(choices, list) and choices:
            first_choice = choices[0]

            if isinstance(first_choice, dict):
                message = first_choice.get("message")

                if isinstance(message, dict):
                    # Primary: content field
                    content = message.get("content")

                    if isinstance(content, str) and content.strip():
                        return content

                    # Fallback: GLM-style models sometimes return
                    # the actual response in reasoning_content when
                    # content is null (thinking models).
                    for fallback_key in (
                        "reasoning_content",
                        "reasoning",
                    ):
                        fallback = message.get(fallback_key)

                        if isinstance(fallback, str) and fallback.strip():
                            return fallback

                text = first_choice.get("text")

                if isinstance(text, str):
                    return text

    response = data.get("response")

    if isinstance(response, str):
        return response

    raise ValueError(
        "Cloudflare AI returned an unexpected response format."
    )


def _build_context(
    lead: Lead,
    scan: WebsiteScan | None,
    issues: list[WebsiteIssue],
    analysis: AIAnalysis | None,
    opportunity: WebsiteOpportunity | None,
    qualification: LeadQualification | None,
    request: AIEmailGenerateRequest,
) -> dict:

    issue_context = []

    for issue in issues:
        issue_context.append(
            {
                "issue_code": issue.issue_code,
                "title": issue.title,
                "category": issue.category,
                "severity": issue.severity,
                "evidence": issue.evidence,
                "recommendation": issue.recommendation,
                "current_value": issue.current_value,
                "expected_value": issue.expected_value,
            }
        )

    scan_context = None

    if scan:
        scan_context = {
            "url": scan.url,
            "final_url": scan.final_url,
            "http_status": scan.http_status,
            "response_time_ms": scan.response_time_ms,
            "page_size_bytes": scan.page_size_bytes,
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
        }

    analysis_context = None

    if analysis:
        analysis_context = {
            "business_summary": analysis.business_summary,
            "website_assessment": analysis.website_assessment,
            "opportunity_summary": analysis.opportunity_summary,
            "sales_angle": analysis.sales_angle,
            "personalization_points": analysis.personalization_points,
            "priority_issues": analysis.priority_issues,
        }

    opportunity_context = None

    if opportunity:
        opportunity_context = {
            "industry": opportunity.industry,
            "business_summary": opportunity.business_summary,
            "opportunity_summary": opportunity.opportunity_summary,
            "recommended_solution": opportunity.recommended_solution,
            "sales_angle": opportunity.sales_angle,
            "personalization_points": opportunity.personalization_points,
            "suggested_features": opportunity.suggested_features,
        }

    qualification_context = None

    if qualification:
        qualification_context = {
            "website_score": qualification.website_score,
            "business_score": qualification.business_score,
            "opportunity_score": qualification.opportunity_score,
            "contact_score": qualification.contact_score,
            "total_score": qualification.total_score,
            "qualification_level": qualification.qualification_level,
            "outreach_readiness": qualification.outreach_readiness,
            "qualification_reason": qualification.qualification_reason,
            "recommended_approach": qualification.recommended_approach,
            "qualification_factors": qualification.qualification_factors,
        }

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
            "website_final_url": lead.website_final_url,
            "website_http_status": lead.website_http_status,
            "website_response_time_ms": lead.website_response_time_ms,
        },
        "scan": scan_context,
        "issues": issue_context,
        "ai_analysis": analysis_context,
        "website_opportunity": opportunity_context,
        "qualification": qualification_context,
        "sender": {
            "name": request.sender_name,
            "company": request.sender_company,
            "service": request.sender_service,
        },
        "email_type": request.email_type,
        "tone": request.tone,
        "length": request.length,
        "requested_call_to_action": request.call_to_action,
        "prior_messages": request.prior_messages,
        "follow_up_number": request.follow_up_number,
    }


async def _call_cloudflare(
    system_prompt: str,
    user_prompt: str,
) -> str:

    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{settings.cloudflare_account_id}/ai/run/"
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
        "temperature": 0.35,
        "max_tokens": 1500,
        # glm-4.7-flash is a "thinking" model. Without these two
        # options it spends most of its time (and tokens) reasoning
        # before writing the email, which made requests take 30s+.
        "chat_template_kwargs": {"enable_thinking": False},
        "reasoning_effort": "low",
    }

    timeout = httpx.Timeout(
        90.0,
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
        raise RuntimeError(
            "Cloudflare AI timed out. Please try again."
        ) from exc

    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"Could not reach Cloudflare AI: {exc}"
        ) from exc

    if response.status_code >= 400:
        logger.error(
            "Cloudflare AI error %s: %s",
            response.status_code,
            response.text[:500],
        )
        raise RuntimeError(
            f"Cloudflare AI returned HTTP {response.status_code}. "
            "Check CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN and "
            "CLOUDFLARE_AI_MODEL in .env."
        )

    data = response.json()

    result = data.get("result") or {}
    choices = result.get("choices") or [{}]
    first = choices[0] if isinstance(choices[0], dict) else {}

    logger.info(
        "Cloudflare AI email response: finish_reason=%s content_null=%s",
        first.get("finish_reason"),
        (first.get("message") or {}).get("content") is None,
    )

    return _extract_response_text(data)


def _get_lead(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
) -> Lead | None:

    return db.scalar(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.user_id == user_id,
        )
    )


def _get_latest_scan(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
) -> WebsiteScan | None:

    statement = (
        select(WebsiteScan)
        .where(
            WebsiteScan.user_id == user_id,
            WebsiteScan.lead_id == lead_id,
            WebsiteScan.scan_status == "completed",
        )
        .order_by(
            WebsiteScan.scanned_at.desc()
        )
        .limit(1)
    )

    return db.scalar(statement)


def _get_issues(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
    scan_id: UUID | None,
) -> list[WebsiteIssue]:

    if scan_id is None:
        return []

    statement = (
        select(WebsiteIssue)
        .where(
            WebsiteIssue.user_id == user_id,
            WebsiteIssue.lead_id == lead_id,
            WebsiteIssue.scan_id == scan_id,
            WebsiteIssue.status == "open",
        )
        .order_by(
            WebsiteIssue.severity.asc()
        )
    )

    return list(db.scalars(statement).all())


def _get_latest_analysis(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
    scan_id: UUID | None,
) -> AIAnalysis | None:

    if scan_id is None:
        return None

    statement = (
        select(AIAnalysis)
        .where(
            AIAnalysis.user_id == user_id,
            AIAnalysis.lead_id == lead_id,
            AIAnalysis.scan_id == scan_id,
        )
        .order_by(
            AIAnalysis.created_at.desc()
        )
        .limit(1)
    )

    return db.scalar(statement)


def _get_opportunity(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
) -> WebsiteOpportunity | None:

    statement = select(WebsiteOpportunity).where(
        WebsiteOpportunity.user_id == user_id,
        WebsiteOpportunity.lead_id == lead_id,
    )

    return db.scalar(statement)


def _get_qualification(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
) -> LeadQualification | None:

    statement = select(LeadQualification).where(
        LeadQualification.user_id == user_id,
        LeadQualification.lead_id == lead_id,
    )

    return db.scalar(statement)


async def generate_email_draft(
    db: Session,
    user_id: UUID,
    lead_id: UUID,
    request: AIEmailGenerateRequest,
) -> AIEmailDraft:

    email_type = request.email_type.strip().lower()

    if email_type not in ALLOWED_EMAIL_TYPES:
        raise ValueError(
            "Invalid email_type."
        )

    lead = _get_lead(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    if not lead:
        raise LookupError(
            "Lead not found."
        )

    if not lead.email:
        raise ValueError(
            "This lead does not have an email address."
        )

    is_french = _is_french_lead(lead)

    scan = _get_latest_scan(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    issues = _get_issues(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
        scan_id=scan.id if scan else None,
    )

    analysis = _get_latest_analysis(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
        scan_id=scan.id if scan else None,
    )

    opportunity = _get_opportunity(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    qualification = _get_qualification(
        db=db,
        user_id=user_id,
        lead_id=lead_id,
    )

    brand = db.scalar(
        select(BrandSettings).where(
            BrandSettings.user_id == user_id
        )
    )

    if brand:
        if not request.sender_name:
            request.sender_name = brand.sender_name or None

        if not request.sender_company:
            request.sender_company = brand.agency_name

        if not request.sender_service:
            request.sender_service = (
                "websites, software and automation"
            )

    if not request.call_to_action:
        request.call_to_action = _default_call_to_action(is_french)

    context = _build_context(
        lead=lead,
        scan=scan,
        issues=issues,
        analysis=analysis,
        opportunity=opportunity,
        qualification=qualification,
        request=request,
    )

    context["brand"] = {
        "agency_name": (
            brand.agency_name
            if brand
            else (
                request.sender_company
                or "SoftPeak Technologies"
            )
        ),
        "sender_name": (
            brand.sender_name
            if brand
            else request.sender_name
        ),
        "sender_role": (
            brand.sender_role
            if brand
            else "Software Engineer"
        ),
    }

    context["scan_id"] = (
        str(scan.id)
        if scan
        else None
    )

    # Initial campaign emails must not reuse an earlier subject either.  A
    # follow-up has the stricter per-thread comparison below.
    existing_subjects = {
        re.sub(r"\s+", " ", subject).strip().casefold()
        for subject in db.scalars(
            select(AIEmailDraft.subject).where(
                AIEmailDraft.user_id == user_id
            )
        ).all()
        if subject
    }

    # Release the database connection before the slow AI call, so it
    # is not sitting idle (and get dropped by the pooler) while we wait.
    db.commit()

    system_prompt = """
You are a professional B2B outreach email writer.

Your job is to create a concise, natural and genuinely personalized
business outreach email using ONLY the supplied lead data.

The email must sound like a real professional person wrote it.

Writing requirements:

- Professional.
- Natural.
- Human-like.
- Conversational but business appropriate.
- Concise.
- Specific to the business.
- Useful rather than sales-heavy.
- No emojis.
- No generic filler.
- Do not start with "I hope this message finds you well".
- Do not use exaggerated marketing language.
- Do not make unsupported claims.
- Do not invent facts.
- Do not invent revenue.
- Do not invent traffic.
- Do not invent rankings.
- Do not invent customers.
- Do not invent employees.
- Do not invent reviews.
- Do not invent competitors.
- Do not invent technologies.
- Do not invent services.
- Do not invent owner names.
- Do not claim that something was observed unless it exists
  in the supplied scan or analysis.
- If the business has no website, never pretend that its website
  was inspected.
- Website issues must come from supplied scanner evidence.
- Industry-based recommendations must be presented as suggestions,
  not facts about the business.
- Avoid long lists of technical issues.
- Mention only the strongest relevant 1-3 findings.
- Explain findings in simple business language.
- The email should not sound like an automated audit report.
- Avoid excessive use of words such as "leverage", "optimize",
  "revolutionize", "transform", "unlock", or "synergy".
- Do not guarantee sales, revenue, rankings, traffic or conversions.

For initial_outreach, use one of these two formats:

A. VERIFIED WEBSITE ISSUE: Only when the supplied issues contain a title and
   scanner evidence or a recommendation. Open personally, name ONE specific
   verified issue in plain business language, state its practical fix, then
   briefly explain one relevant workflow we can automate.

B. NO VERIFIED WEBSITE ISSUE: Never claim, imply, or invent a website problem.
   Send clean general outreach based only on the business and its real location
   or industry. You may offer website, booking, enquiry, or follow-up
   automation, but do not use Issue/Solution/Automation labels or bullets.

Strict format and length requirements for initial_outreach:

- Write a concise, natural, business-specific subject (4-10 words). Do NOT
  start every email with "Quick question" and never use a generic repeated
  subject. Include the supplied business name or a concrete, verified angle
  where natural; never output brackets, placeholders, or template variables.
- body_text MUST be 60-90 words, excluding the greeting. Use 120 words only
  as an absolute maximum.
- Start with "Hello [Business name] team," (or the local-language equivalent),
  never just "Hi,". Do not add a sign-off or sender signature.
- After the greeting, add one short sentence introducing the sender as a
  software agency that helps businesses strengthen their online presence and
  automate relevant customer workflows. Then move directly into the
  personalized observation; do not repeat this introduction elsewhere.
- Use short paragraphs only: no bullets, headings, links, or lists.
- Mention one specific observation at most. Do not repeat a sentence or idea.
- Use the requested call to action verbatim as the final sentence. It is the
  only question and the only call to action.
- Match the lead's language: write in French for a lead in France; otherwise
  write in the requested/default language.
- Do not promise that all of a business will be automated. Say we can assess,
  build, or automate the relevant website/business workflow end-to-end.

For follow_up, write a short NEW message using prior_messages as conversation
context. Never reuse a previous subject. The subject must be materially
different from every previous subject, natural, and specific (not "Re:" or
"Following up"). The body must introduce a different angle from earlier
messages, must not repeat their sentences, and must not claim a reply was
received. Do not include a greeting/signature. Keep it to 35-75 words and one
clear low-pressure CTA.

Follow the "tone" and "length" values in the supplied context:

- tone: the writing style of the email (for example professional,
  friendly, direct).
- length: "concise" means about 60-90 words in body_text,
  "detailed" means about 120-180 words.

Return ONLY valid JSON.

Required JSON structure:

{
  "subject": "string",
  "body_text": "string",
  "personalization_points": [
    {
      "point": "string",
      "source": "string"
    }
  ],
  "source_evidence": [
    {
      "item": "string",
      "source": "string"
    }
  ],
  "call_to_action": "string"
}
"""

    user_prompt = (
        "Generate one personalized outreach email using this "
        "structured context:\n\n"
        + json.dumps(
            context,
            indent=2,
            default=str,
        )
    )

    email_data: AIEmailGenerateData | None = None
    quality_errors: list[str] = []
    for attempt in range(2):
        attempt_prompt = user_prompt
        if attempt:
            attempt_prompt += (
                "\n\nThe previous draft failed quality checks: "
                + ", ".join(quality_errors or ["invalid JSON"])
                + ". Generate a completely new draft that follows every rule."
            )
        try:
            raw_response = await _call_cloudflare(
                system_prompt=system_prompt,
                user_prompt=attempt_prompt,
            )
            parsed = json.loads(_clean_json_response(raw_response))
            candidate = AIEmailGenerateData.model_validate(parsed)
            if not candidate.subject.strip() or not candidate.body_text.strip():
                quality_errors = ["an empty subject or body"]
                continue
            quality_errors = validate_draft_content(
                candidate.subject,
                candidate.body_text,
            )
            if (
                email_type == "initial_outreach"
                and re.sub(r"\s+", " ", candidate.subject).strip().casefold()
                in existing_subjects
            ):
                quality_errors.append("reuses a subject from an earlier email")
            if email_type == "follow_up":
                quality_errors += _follow_up_uniqueness_problems(
                    candidate.subject,
                    candidate.body_text,
                    request.prior_messages,
                )
            if not quality_errors:
                email_data = candidate
                break
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning("AI email attempt %s failed validation: %s", attempt + 1, exc)
            quality_errors = ["invalid response format"]

    if email_data is None:
        # A bad AI answer must never enter the queue.  This deterministic
        # fallback is concise, localized, and contains no template variables.
        logger.warning(
            "Using safe email fallback for lead=%s after quality failures: %s",
            lead_id,
            ", ".join(quality_errors),
        )
        fallback_subject = ""
        fallback_body = _safe_fallback_body(
            lead=lead,
            issues=issues,
            is_french=is_french,
            call_to_action=request.call_to_action or _default_call_to_action(is_french),
        )
        if email_type == "follow_up":
            fallback_subject, fallback_body = _safe_follow_up_fallback(
                lead=lead,
                follow_up_number=request.follow_up_number or 1,
                is_french=is_french,
            )
        email_data = AIEmailGenerateData(
            subject=fallback_subject,
            body_text=fallback_body,
            personalization_points=[],
            source_evidence=[],
            call_to_action=request.call_to_action,
        )

    if email_type == "initial_outreach" and not email_data.subject.strip():
        business_name = " ".join((lead.name or "your business").split())
        email_data.subject = f"A practical idea for {business_name}"

    draft = AIEmailDraft(
        user_id=user_id,
        lead_id=lead_id,
        ai_analysis_id=(
            analysis.id
            if analysis
            else None
        ),
        website_opportunity_id=(
            opportunity.id
            if opportunity
            else None
        ),
        qualification_id=(
            qualification.id
            if qualification
            else None
        ),
        provider="cloudflare",
        model=settings.cloudflare_ai_model,
        prompt_version=PROMPT_VERSION,
        email_type=email_type,
        subject=email_data.subject.strip(),
        body_text=email_data.body_text.strip(),
        personalization_points=[
            item.model_dump()
            for item in email_data.personalization_points
        ],
        source_evidence=[
            item.model_dump()
            for item in email_data.source_evidence
        ],
        call_to_action=email_data.call_to_action,
        generation_context=context,
        status="draft",
    )

    db.add(draft)
    db.commit()
    db.refresh(draft)

    return draft


def list_email_drafts(
    db: Session,
    user_id: UUID,
    lead_id: UUID | None = None,
) -> list[AIEmailDraft]:

    statement = select(AIEmailDraft).where(
        AIEmailDraft.user_id == user_id
    )

    if lead_id:
        statement = statement.where(
            AIEmailDraft.lead_id == lead_id
        )

    statement = statement.order_by(
        AIEmailDraft.created_at.desc()
    )

    return list(
        db.scalars(statement).all()
    )


def get_email_draft(
    db: Session,
    user_id: UUID,
    draft_id: UUID,
) -> AIEmailDraft | None:

    return db.scalar(
        select(AIEmailDraft).where(
            AIEmailDraft.id == draft_id,
            AIEmailDraft.user_id == user_id,
        )
    )


def update_email_draft(
    db: Session,
    draft: AIEmailDraft,
    subject: str | None,
    body_text: str | None,
    status: str | None,
) -> AIEmailDraft:

    candidate_subject = (
        subject.strip()
        if subject is not None
        else draft.subject
    )
    candidate_body = (
        body_text.strip()
        if body_text is not None
        else draft.body_text
    )
    quality_errors = validate_draft_content(
        candidate_subject,
        candidate_body,
    )
    if quality_errors:
        raise ValueError(
            "Draft failed email quality checks: "
            + "; ".join(quality_errors)
            + "."
        )

    if subject is not None:
        draft.subject = candidate_subject

    if body_text is not None:
        draft.body_text = candidate_body

    if status is not None:
        normalized_status = status.strip().lower()

        allowed_statuses = {
            "draft",
            "approved",
            "rejected",
            "archived",
        }

        if normalized_status not in allowed_statuses:
            raise ValueError(
                "Invalid draft status."
            )

        draft.status = normalized_status

    draft.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(draft)

    return draft


def delete_email_draft(
    db: Session,
    draft: AIEmailDraft,
) -> None:

    db.delete(draft)
    db.commit()
