import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analytics import AnalyticsSummary
from app.services.analytics import analytics_service
from app.utils.auth import get_current_user, get_jwks_client
from app.config import settings

import jwt

logger = logging.getLogger("ai-lead-api")

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
)
def get_analytics_summary(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return analytics_service.get_summary(
        db=db,
        user_id=current_user["sub"],
        days=days,
    )


def _verify_token_param(token: str) -> dict:
    """
    Query-param se aaya token verify karo (SSE ke liye — browser
    EventSource custom header nahi bhej sakta).
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
        )
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        algorithm = signing_key.algorithm_name
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience="authenticated",
            issuer=f"{settings.supabase_url}/auth/v1",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc

    if not claims.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has no user ID.",
        )
    return claims


@router.get(
    "/stream",
    summary="Real-time analytics via Server-Sent Events",
    response_class=StreamingResponse,
)
async def stream_analytics(
    token: str = Query(..., description="Supabase JWT (Bearer token)"),
    days: int = Query(default=30, ge=1, le=365),
    interval: int = Query(
        default=15,
        ge=5,
        le=120,
        description="Push interval in seconds",
    ),
    db: Session = Depends(get_db),
):
    """
    SSE stream: har `interval` second mein latest analytics push karta
    hai.  Browser `EventSource` se connect karo — token query-param mein
    bhejein kyunki EventSource custom headers support nahi karta.

    Events:
      - `connected`  — pehla handshake event
      - `analytics`  — full AnalyticsSummary JSON
      - `heartbeat`  — har 30s ka keep-alive (data: ping)
      - `error`      — kuch gadbad hui
    """
    current_user = _verify_token_param(token)
    user_id = current_user["sub"]

    async def event_generator():
        # Pehla handshake
        yield (
            "event: connected\n"
            f"data: {{\"status\": \"ok\", \"interval\": {interval}}}\n\n"
        )

        heartbeat_counter = 0

        while True:
            try:
                # Analytics fetch (sync DB call — thread pool mein)
                summary = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: analytics_service.get_summary(
                        db=db,
                        user_id=user_id,
                        days=days,
                    ),
                )

                payload = summary.model_dump(mode="json")
                # datetime objects ko string mein convert karo
                payload["generated_at"] = summary.generated_at.isoformat()

                yield (
                    "event: analytics\n"
                    f"data: {json.dumps(payload)}\n\n"
                )

                heartbeat_counter += 1

                # Interval tak wait karo, beech mein heartbeat bhejte raho
                for _ in range(interval):
                    await asyncio.sleep(1)

                # Har 30s (2 cycles) par ek heartbeat bhi bhejo
                if heartbeat_counter % max(1, 30 // interval) == 0:
                    yield "event: heartbeat\ndata: ping\n\n"

            except asyncio.CancelledError:
                # Client ne connection band kiya
                logger.info(
                    "SSE client disconnected: user=%s", user_id
                )
                break
            except Exception as exc:
                logger.exception(
                    "SSE analytics error for user=%s: %s", user_id, exc
                )
                yield (
                    "event: error\n"
                    f"data: {{\"detail\": \"Server error, reconnecting...\"}}\n\n"
                )
                # Thodi der ruko phir retry
                await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Nginx buffering band karo
            "Connection": "keep-alive",
        },
    )