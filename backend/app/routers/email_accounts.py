from urllib.parse import quote
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.email_account import (
    EmailAccountCreate,
    EmailAccountListResponse,
    EmailAccountResponse,
    EmailAccountStatusUpdate,
    EmailAccountUpdate,
)
from app.services.email_account import (
    connect_google_account,
    create_account,
    delete_account,
    get_account,
    get_google_authorization_url,
    list_accounts,
    update_account,
    update_status,
    verify_google_oauth_state,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/email-accounts",
    tags=["Email Accounts"],
)


# ---------------------------------------------------------
# Existing account endpoints
# ---------------------------------------------------------


@router.get(
    "",
    response_model=EmailAccountListResponse,
)
def get_email_accounts(
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        get_current_user
    ),
):
    user_id = UUID(
        current_user["sub"]
    )

    accounts = list_accounts(
        db=db,
        user_id=user_id,
    )

    return EmailAccountListResponse(
        items=accounts,
        total=len(accounts),
    )


@router.get(
    "/{account_id}",
    response_model=EmailAccountResponse,
)
def get_email_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        get_current_user
    ),
):
    user_id = UUID(
        current_user["sub"]
    )

    account = get_account(
        db=db,
        user_id=user_id,
        account_id=account_id,
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found.",
        )

    return account


@router.post(
    "",
    response_model=EmailAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def connect_email_account(
    payload: EmailAccountCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        get_current_user
    ),
):
    user_id = UUID(
        current_user["sub"]
    )

    try:
        return create_account(
            db=db,
            user_id=user_id,
            payload=payload,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{account_id}",
    response_model=EmailAccountResponse,
)
def edit_email_account(
    account_id: UUID,
    payload: EmailAccountUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        get_current_user
    ),
):
    user_id = UUID(
        current_user["sub"]
    )

    account = get_account(
        db=db,
        user_id=user_id,
        account_id=account_id,
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found.",
        )

    return update_account(
        db=db,
        account=account,
        payload=payload,
    )


@router.patch(
    "/{account_id}/status",
    response_model=EmailAccountResponse,
)
def change_email_account_status(
    account_id: UUID,
    payload: EmailAccountStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        get_current_user
    ),
):
    user_id = UUID(
        current_user["sub"]
    )

    account = get_account(
        db=db,
        user_id=user_id,
        account_id=account_id,
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found.",
        )

    try:
        return update_status(
            db=db,
            account=account,
            status=payload.status,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_email_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        get_current_user
    ),
):
    user_id = UUID(
        current_user["sub"]
    )

    account = get_account(
        db=db,
        user_id=user_id,
        account_id=account_id,
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email account not found.",
        )

    delete_account(
        db=db,
        account=account,
    )

    return None


# ---------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------


@router.get(
    "/google/connect",
)
def google_connect(
    current_user: dict = Depends(
        get_current_user
    ),
):
    user_id = UUID(
        current_user["sub"]
    )

    authorization_url = (
        get_google_authorization_url(
            user_id=user_id
        )
    )

    return {
        "authorization_url": authorization_url
    }


@router.get(
    "/google/callback",
)
async def google_callback(
    code: str | None = Query(
        default=None
    ),
    state: str | None = Query(
        default=None
    ),
    error: str | None = Query(
        default=None
    ),
    db: Session = Depends(get_db),
):
    frontend_url = (
        settings.frontend_url.rstrip("/")
    )

    if error:
        return RedirectResponse(
            url=(
                f"{frontend_url}/email/accounts"
                f"?google=error"
                f"&message={quote(error)}"
            )
        )

    if not code or not state:
        return RedirectResponse(
            url=(
                f"{frontend_url}/email/accounts"
                "?google=error"
                "&message=missing_oauth_response"
            )
        )

    try:
        user_id = verify_google_oauth_state(
            state=state
        )

        account = await connect_google_account(
            db=db,
            user_id=user_id,
            code=code,
        )

        return RedirectResponse(
            url=(
                f"{frontend_url}/email/accounts"
                "?google=connected"
                f"&email={quote(account.email)}"
            )
        )

    except ValueError as exc:
        message = str(exc)

        return RedirectResponse(
            url=(
                f"{frontend_url}/email/accounts"
                "?google=error"
                f"&message={quote(message)}"
            )
        )

    except Exception:
        return RedirectResponse(
            url=(
                f"{frontend_url}/email/accounts"
                "?google=error"
                "&message=google_connection_failed"
            )
        )