from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.campaign import (
    CampaignCreate,
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignResponse,
)
from app.services.campaign import (
    cancel_campaign,
    create_campaign,
    delete_campaign,
    get_campaign,
    get_campaign_detail,
    get_campaign_detail_enriched,
    list_campaigns,
    pause_campaign,
    resume_campaign,
    start_campaign,
)
from app.services.campaign_automation import process_campaign
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/campaigns",
    tags=["Campaigns"],
)


def _user_id(current_user: dict) -> UUID:
    return UUID(
        current_user["sub"]
    )


@router.get(
    "",
    response_model=CampaignListResponse,
)
def get_campaigns(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = _user_id(current_user)

    campaigns = list_campaigns(
        db=db,
        user_id=user_id,
    )

    return CampaignListResponse(
        items=campaigns,
        total=len(campaigns),
    )


@router.get(
    "/{campaign_id}",
)
def get_one_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from datetime import datetime

    user_id = _user_id(current_user)

    try:
        campaign, enriched_leads = get_campaign_detail_enriched(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    def _safe(v):
        """Convert any value to a JSON-safe primitive."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        # UUID, and any other non-primitive — stringify
        try:
            import uuid as _uuid
            if isinstance(v, _uuid.UUID):
                return str(v)
        except Exception:
            pass
        if isinstance(v, (str, int, float, bool)):
            return v
        if isinstance(v, list):
            return [_safe(i) for i in v]
        if isinstance(v, dict):
            return {str(k): _safe(vv) for k, vv in v.items()}
        return str(v)

    # Serialize campaign columns to safe primitives
    campaign_dict = {
        col.name: _safe(getattr(campaign, col.name))
        for col in campaign.__table__.columns
    }

    # Serialize each enriched lead dict to safe primitives
    safe_leads = [
        {k: _safe(v) for k, v in lead.items()}
        for lead in enriched_leads
    ]

    return {**campaign_dict, "leads": safe_leads}


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_existing_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = _user_id(current_user)

    try:
        delete_campaign(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return None


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = _user_id(current_user)

    try:
        return create_campaign(
            db=db,
            user_id=user_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{campaign_id}/start",
    response_model=CampaignResponse,
)
def start_existing_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = _user_id(current_user)

    try:
        return start_campaign(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{campaign_id}/pause",
    response_model=CampaignResponse,
)
def pause_existing_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = _user_id(current_user)

    try:
        return pause_campaign(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{campaign_id}/resume",
    response_model=CampaignResponse,
)
def resume_existing_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = _user_id(current_user)

    try:
        return resume_campaign(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{campaign_id}/cancel",
    response_model=CampaignResponse,
)
def cancel_existing_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = _user_id(current_user)

    try:
        return cancel_campaign(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{campaign_id}/process",
)
async def process_existing_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Trigger AI email generation + queue for all pending
    leads in a campaign. Call this immediately after
    POST /{id}/start.
    """
    user_id = _user_id(current_user)

    try:
        result = await process_campaign(
            db=db,
            user_id=user_id,
            campaign_id=campaign_id,
        )
        return result
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Campaign processing failed: {exc}",
        ) from exc
