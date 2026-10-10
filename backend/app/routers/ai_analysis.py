from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ai_analysis import (
    AIAnalysisListResponse,
    AIAnalysisResponse,
)
from app.services.ai_analysis import (
    analyze_lead,
    get_analysis_history,
    get_latest_analysis,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/leads",
    tags=["AI Analysis"],
)


def serialize_analysis(
    analysis,
) -> dict:

    return {
        "success": True,
        "analysis_id": analysis.id,
        "lead_id": analysis.lead_id,
        "scan_id": analysis.scan_id,
        "provider": analysis.provider,
        "model": analysis.model,
        "prompt_version": analysis.prompt_version,
        "business_summary": (
            analysis.business_summary
        ),
        "website_assessment": (
            analysis.website_assessment
        ),
        "opportunity_summary": (
            analysis.opportunity_summary
        ),
        "sales_angle": (
            analysis.sales_angle
        ),
        "personalization_points": (
            analysis.personalization_points
        ),
        "priority_issues": (
            analysis.priority_issues
        ),
        "analysis_json": (
            analysis.analysis_json
        ),
        "created_at": analysis.created_at,
    }


@router.post(
    "/{lead_id}/ai-analysis",
    response_model=AIAnalysisResponse,
)
async def create_ai_analysis(
    lead_id: UUID,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    analysis = await analyze_lead(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    return serialize_analysis(
        analysis
    )


@router.get(
    "/{lead_id}/ai-analysis",
    response_model=AIAnalysisResponse,
)
def latest_ai_analysis(
    lead_id: UUID,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    analysis = get_latest_analysis(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    return serialize_analysis(
        analysis
    )


@router.get(
    "/{lead_id}/ai-analysis/history",
    response_model=AIAnalysisListResponse,
)
def ai_analysis_history(
    lead_id: UUID,
    current_user: dict = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    user_id = UUID(
        current_user["sub"]
    )

    analyses = get_analysis_history(
        db=db,
        lead_id=lead_id,
        user_id=user_id,
    )

    return {
        "success": True,
        "total": len(analyses),
        "analyses": [
            serialize_analysis(
                analysis
            )
            for analysis in analyses
        ],
    }