import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.email_account import EmailAccount
from app.schemas.email_account import (
    EmailAccountCreate,
    EmailAccountUpdate,
)
from app.services.credential_encryption import encrypt_credential


ALLOWED_PROVIDERS = {
    "google",
    "microsoft",
    "smtp",
}

ALLOWED_STATUSES = {
    "active",
    "paused",
    "reauth_required",
    "disabled",
}


GOOGLE_AUTH_URL = (
    "https://accounts.google.com/o/oauth2/v2/auth"
)

GOOGLE_TOKEN_URL = (
    "https://oauth2.googleapis.com/token"
)

GOOGLE_GMAIL_PROFILE_URL = (
    "https://gmail.googleapis.com/gmail/v1/users/me/profile"
)


GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.modify",
]


GOOGLE_STATE_MAX_AGE_SECONDS = 600


# ---------------------------------------------------------
# Existing account CRUD
# ---------------------------------------------------------


def get_account(
    db: Session,
    user_id: UUID,
    account_id: UUID,
) -> EmailAccount | None:
    statement = select(EmailAccount).where(
        EmailAccount.id == account_id,
        EmailAccount.user_id == user_id,
    )

    return db.scalar(statement)


def list_accounts(
    db: Session,
    user_id: UUID,
) -> list[EmailAccount]:
    statement = (
        select(EmailAccount)
        .where(
            EmailAccount.user_id == user_id
        )
        .order_by(
            EmailAccount.created_at.desc()
        )
    )

    return list(
        db.scalars(statement).all()
    )


def create_account(
    db: Session,
    user_id: UUID,
    payload: EmailAccountCreate,
) -> EmailAccount:

    provider = payload.provider.strip().lower()

    if provider not in ALLOWED_PROVIDERS:
        raise ValueError(
            "Unsupported email provider. "
            "Allowed providers: google, microsoft, smtp."
        )

    email = payload.email.strip().lower()

    existing = db.scalar(
        select(EmailAccount).where(
            EmailAccount.user_id == user_id,
            EmailAccount.email == email,
        )
    )

    if existing:
        raise ValueError(
            "This email account is already connected."
        )

    account = EmailAccount(
        user_id=user_id,
        provider=provider,
        email=email,
        display_name=payload.display_name,
        provider_account_id=(
            payload.provider_account_id
        ),
        access_token_encrypted=encrypt_credential(
            payload.access_token
        ),
        refresh_token_encrypted=encrypt_credential(
            payload.refresh_token
        ),
        token_expires_at=payload.token_expires_at,
        scopes=payload.scopes,
        provider_metadata=(
            payload.provider_metadata
        ),
        daily_send_limit=(
            payload.daily_send_limit
        ),
        sent_today=0,
        status="active",
    )

    db.add(account)
    db.commit()
    db.refresh(account)

    return account


def update_account(
    db: Session,
    account: EmailAccount,
    payload: EmailAccountUpdate,
) -> EmailAccount:

    if payload.display_name is not None:
        account.display_name = (
            payload.display_name
        )

    if payload.daily_send_limit is not None:
        account.daily_send_limit = (
            payload.daily_send_limit
        )

    account.updated_at = datetime.now(
        timezone.utc
    )

    db.commit()
    db.refresh(account)

    return account


def update_status(
    db: Session,
    account: EmailAccount,
    status: str,
) -> EmailAccount:

    normalized_status = (
        status.strip().lower()
    )

    if normalized_status not in ALLOWED_STATUSES:
        raise ValueError(
            "Invalid email account status."
        )

    account.status = normalized_status
    account.updated_at = datetime.now(
        timezone.utc
    )

    db.commit()
    db.refresh(account)

    return account


def delete_account(
    db: Session,
    account: EmailAccount,
) -> None:

    db.delete(account)
    db.commit()


def reset_daily_counter(
    db: Session,
    account: EmailAccount,
) -> EmailAccount:

    account.sent_today = 0
    account.updated_at = datetime.now(
        timezone.utc
    )

    db.commit()
    db.refresh(account)

    return account


# ---------------------------------------------------------
# Google OAuth state
# ---------------------------------------------------------


def _state_secret() -> bytes:
    return (
        settings.email_credential_encryption_key
        .encode("utf-8")
    )


def create_google_oauth_state(
    user_id: UUID,
) -> str:

    payload = {
        "user_id": str(user_id),
        "issued_at": int(
            datetime.now(timezone.utc).timestamp()
        ),
        "nonce": secrets.token_urlsafe(24),
    }

    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8")
    ).decode("ascii").rstrip("=")

    signature = hmac.new(
        _state_secret(),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()

    encoded_signature = (
        base64.urlsafe_b64encode(
            signature
        )
        .decode("ascii")
        .rstrip("=")
    )

    return (
        f"{encoded_payload}.{encoded_signature}"
    )


def verify_google_oauth_state(
    state: str,
) -> UUID:

    try:
        encoded_payload, encoded_signature = (
            state.split(".", 1)
        )

        expected_signature = hmac.new(
            _state_secret(),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()

        received_signature = (
            base64.urlsafe_b64decode(
                encoded_signature + "=="
            )
        )

        if not hmac.compare_digest(
            expected_signature,
            received_signature,
        ):
            raise ValueError(
                "Invalid OAuth state."
            )

        payload = json.loads(
            base64.urlsafe_b64decode(
                encoded_payload + "=="
            ).decode("utf-8")
        )

        issued_at = int(
            payload["issued_at"]
        )

        current_timestamp = int(
            datetime.now(timezone.utc).timestamp()
        )

        if (
            current_timestamp - issued_at
            > GOOGLE_STATE_MAX_AGE_SECONDS
        ):
            raise ValueError(
                "OAuth session expired. "
                "Please start again."
            )

        user_id = UUID(
            str(payload["user_id"])
        )

        return user_id

    except ValueError:
        raise

    except Exception as exc:
        raise ValueError(
            "Invalid OAuth state."
        ) from exc


# ---------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------


def get_google_authorization_url(
    user_id: UUID,
) -> str:

    state = create_google_oauth_state(
        user_id=user_id
    )

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }

    return (
        f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    )


async def exchange_google_code(
    code: str,
) -> dict:

    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(
        timeout=30.0
    ) as client:

        response = await client.post(
            GOOGLE_TOKEN_URL,
            data=data,
        )

    if response.is_error:
        try:
            error_data = response.json()
        except Exception:
            error_data = {}

        error_description = (
            error_data.get("error_description")
            or error_data.get("error")
            or "Google token exchange failed."
        )

        raise ValueError(
            error_description
        )

    token_data = response.json()

    if not token_data.get("access_token"):
        raise ValueError(
            "Google did not return an access token."
        )

    return token_data


async def get_google_profile(
    access_token: str,
) -> dict:

    headers = {
        "Authorization": (
            f"Bearer {access_token}"
        )
    }

    async with httpx.AsyncClient(
        timeout=30.0
    ) as client:

        response = await client.get(
            GOOGLE_GMAIL_PROFILE_URL,
            headers=headers,
        )

    if response.is_error:
        try:
            error_data = response.json()
        except Exception:
            error_data = {}

        message = (
            error_data.get("error", {})
            .get("message")
            or "Unable to read Gmail profile."
        )

        raise ValueError(message)

    profile = response.json()

    if not profile.get("emailAddress"):
        raise ValueError(
            "Google did not return the Gmail address."
        )

    return profile


async def connect_google_account(
    db: Session,
    user_id: UUID,
    code: str,
) -> EmailAccount:

    token_data = await exchange_google_code(
        code=code
    )

    access_token = token_data.get(
        "access_token"
    )

    refresh_token = token_data.get(
        "refresh_token"
    )

    if not refresh_token:
        raise ValueError(
            "Google did not return a refresh token. "
            "Please remove this app from your Google "
            "account permissions and connect again."
        )

    profile = await get_google_profile(
        access_token=access_token
    )

    email = (
        str(profile["emailAddress"])
        .strip()
        .lower()
    )

    provider_account_id = email

    existing = db.scalar(
        select(EmailAccount).where(
            EmailAccount.user_id == user_id,
            EmailAccount.email == email,
        )
    )

    expires_in = int(
        token_data.get(
            "expires_in",
            3600,
        )
    )

    token_expires_at = (
        datetime.now(timezone.utc)
        + timedelta(seconds=expires_in)
    )

    granted_scope_string = (
        token_data.get("scope")
        or " ".join(GOOGLE_SCOPES)
    )

    granted_scopes = [
        scope.strip()
        for scope in granted_scope_string.split()
        if scope.strip()
    ]

    provider_metadata = {
        "provider": "google",
        "gmail_profile": {
            "history_id": profile.get(
                "historyId"
            ),
            "messages_total": profile.get(
                "messagesTotal"
            ),
            "threads_total": profile.get(
                "threadsTotal"
            ),
        },
        "token_type": token_data.get(
            "token_type"
        ),
    }

    if existing:
        existing.provider = "google"
        existing.email = email
        existing.provider_account_id = (
            provider_account_id
        )
        existing.access_token_encrypted = (
            encrypt_credential(
                access_token
            )
        )
        existing.refresh_token_encrypted = (
            encrypt_credential(
                refresh_token
            )
        )
        existing.token_expires_at = (
            token_expires_at
        )
        existing.scopes = granted_scopes
        existing.provider_metadata = (
            provider_metadata
        )
        existing.status = "active"
        existing.last_error = None
        existing.last_error_at = None
        existing.updated_at = datetime.now(
            timezone.utc
        )

        db.commit()
        db.refresh(existing)

        return existing

    account = EmailAccount(
        user_id=user_id,
        provider="google",
        email=email,
        display_name=email.split("@")[0],
        provider_account_id=provider_account_id,
        access_token_encrypted=encrypt_credential(
            access_token
        ),
        refresh_token_encrypted=encrypt_credential(
            refresh_token
        ),
        token_expires_at=token_expires_at,
        scopes=granted_scopes,
        provider_metadata=provider_metadata,
        daily_send_limit=50,
        sent_today=0,
        status="active",
    )

    db.add(account)
    db.commit()
    db.refresh(account)

    return account