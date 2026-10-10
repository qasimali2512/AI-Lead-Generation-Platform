import base64
import json
import logging
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.email_account import EmailAccount
from app.models.ai_email_draft import AIEmailDraft
from app.models.email_queue import EmailQueue


logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"


class GmailSendError(RuntimeError):
    pass


def _encode_message(message: EmailMessage) -> str:
    raw = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("utf-8")

    return raw.rstrip("=")


async def refresh_access_token(
    refresh_token: str,
) -> dict[str, Any]:

    payload = {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient(
        timeout=30
    ) as client:

        response = await client.post(
            GOOGLE_TOKEN_URL,
            data=payload,
        )

    if response.status_code >= 400:
        logger.error(
            "Google token refresh failed: %s",
            response.text[:500],
        )

        raise GmailSendError(
            "Unable to refresh Google access token."
        )

    return response.json()


async def send_gmail_message(
    *,
    access_token: str,
    recipient_email: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    sender_email: str | None = None,
    inline_logo_path: Path | None = None,
) -> dict[str, Any]:

    message = EmailMessage()

    if sender_email:
        message["From"] = sender_email

    message["To"] = recipient_email
    message["Subject"] = subject

    message.set_content(body_text)

    if body_html:
        message.add_alternative(
            body_html,
            subtype="html",
        )

        if inline_logo_path and inline_logo_path.is_file():
            html_part = message.get_payload()[-1]
            html_part.add_related(
                inline_logo_path.read_bytes(),
                maintype="image",
                subtype="png",
                cid="<softpeak-brand-logo>",
                filename=inline_logo_path.name,
                disposition="inline",
            )

    raw_message = _encode_message(message)

    url = (
        f"{GMAIL_API_BASE}/users/me/messages/send"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "raw": raw_message,
    }

    async with httpx.AsyncClient(
        timeout=45
    ) as client:

        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    if response.status_code >= 400:
        logger.error(
            "Gmail send failed: %s",
            response.text[:1000],
        )

        raise GmailSendError(
            f"Gmail API returned HTTP "
            f"{response.status_code}: "
            f"{response.text[:500]}"
        )

    return response.json()


def get_email_account(
    db: Session,
    user_id: UUID,
    email_account_id: UUID,
) -> EmailAccount | None:

    return db.scalar(
        select(EmailAccount).where(
            EmailAccount.id == email_account_id,
            EmailAccount.user_id == user_id,
        )
    )


async def send_queue_email(
    db: Session,
    *,
    user_id: UUID,
    queue_item: EmailQueue,
) -> dict[str, Any]:

    if not queue_item.email_account_id:
        raise GmailSendError(
            "No email account is assigned to this queue item."
        )

    account = get_email_account(
        db=db,
        user_id=user_id,
        email_account_id=queue_item.email_account_id,
    )

    if not account:
        raise GmailSendError(
            "Email account was not found."
        )

    if account.status != "active":
        raise GmailSendError(
            "The selected email account is inactive."
        )

    if account.provider not in ("gmail", "google"):
        raise GmailSendError(
            "This sender currently supports Gmail only."
        )

    # ------------------------------------------------------------------
    # Decrypt tokens
    # ------------------------------------------------------------------
    from app.services.credential_encryption import (
        decrypt_credential,
        CredentialEncryptionError,
    )
    from datetime import datetime, timezone

    try:
        access_token  = decrypt_credential(account.access_token_encrypted)
        refresh_token = decrypt_credential(account.refresh_token_encrypted)
    except CredentialEncryptionError as exc:
        raise GmailSendError(
            f"Unable to decrypt email account credentials: {exc}"
        ) from exc

    if not access_token and not refresh_token:
        raise GmailSendError(
            "Gmail access token is missing. Please reconnect the email account."
        )

    # ------------------------------------------------------------------
    # Token expiry check — refresh if needed
    # ------------------------------------------------------------------
    now_utc = datetime.now(timezone.utc)
    token_expired = (
        account.token_expires_at is not None
        and account.token_expires_at <= now_utc
    )

    if (not access_token or token_expired) and refresh_token:
        try:
            token_data = await refresh_access_token(refresh_token)
            access_token = token_data.get("access_token", "")

            # Save refreshed token back to DB
            from app.services.credential_encryption import encrypt_credential
            from datetime import timedelta

            account.access_token_encrypted = encrypt_credential(access_token)
            expires_in = int(token_data.get("expires_in", 3600))
            account.token_expires_at = now_utc + timedelta(seconds=expires_in)
            account.updated_at = now_utc
            db.commit()

        except GmailSendError:
            raise
        except Exception as exc:
            raise GmailSendError(
                f"Token refresh failed: {exc}"
            ) from exc

    if not access_token:
        raise GmailSendError(
            "Gmail access token is missing after refresh attempt."
        )

    sender_email = account.email

    # ------------------------------------------------------------------
    # HTML email rendering — brand settings se professional template
    # ------------------------------------------------------------------
    body_html: str | None = None

    try:
        from app.services.brand_settings import get_brand_settings
        from app.services.email_templates import (
            render_initial_email,
            render_follow_up_email,
        )

        brand = get_brand_settings(db=db, user_id=user_id)

        # Default logo — frontend public folder
        _default_logo = "cid:softpeak-brand-logo"
        _inline_logo_path = (
            Path(__file__).resolve().parents[3]
            / "frontend" / "public" / "softpeak-logo.png"
        )

        # Brand settings nahi hain to sensible defaults use karo
        agency_name     = (brand.agency_name    if brand else "SoftPeak Technologies")
        logo_url        = (brand.logo_url        if brand and brand.logo_url else _default_logo)
        if logo_url.startswith(("http://localhost", "http://127.0.0.1")):
            logo_url = _default_logo
        primary_color   = (brand.primary_color   if brand else "#1f6b4f")
        secondary_color = (brand.secondary_color if brand else "#c49a4a")
        sender_name     = (brand.sender_name     if brand else None)
        sender_role     = (brand.sender_role     if brand else None)
        phone           = (brand.phone           if brand else None)
        website         = (brand.website         if brand else None)
        address         = (brand.address         if brand else None)
        booking_url     = (brand.booking_url     if brand else None)
        unsubscribe_url = (brand.unsubscribe_url if brand else None)

        draft = db.scalar(
            select(AIEmailDraft).where(
                AIEmailDraft.id == queue_item.draft_id,
                AIEmailDraft.user_id == user_id,
            )
        )
        issues = (
            draft.generation_context.get("issues", [])
            if draft and isinstance(draft.generation_context, dict)
            else []
        )

        # queue_type ke basis pe template choose karo
        is_follow_up = (queue_item.queue_type or "").lower() == "follow_up"

        if is_follow_up:
            body_html = render_follow_up_email(
                body_text=queue_item.body_text,
                sender_name=sender_name,
                sender_role=sender_role,
                agency_name=agency_name,
                logo_url=logo_url,
                primary_color=primary_color,
                secondary_color=secondary_color,
                booking_url=booking_url,
                phone=phone,
                website=website,
                address=address,
                unsubscribe_url=unsubscribe_url,
                issues=issues,
            )
        else:
            body_html = render_initial_email(
                body_text=queue_item.body_text,
                sender_name=sender_name,
                sender_role=sender_role,
                agency_name=agency_name,
                logo_url=logo_url,
                primary_color=primary_color,
                secondary_color=secondary_color,
                phone=phone,
                website=website,
                address=address,
                unsubscribe_url=unsubscribe_url,
                issues=issues,
            )

    except Exception as tmpl_err:
        # Template rendering fail hone par plain-text fallback
        logger.warning(
            "HTML template rendering failed for queue=%s, "
            "falling back to plain text: %s",
            queue_item.id,
            tmpl_err,
        )
        body_html = None

    # ------------------------------------------------------------------

    result = await send_gmail_message(
        access_token=access_token,
        recipient_email=queue_item.recipient_email,
        subject=queue_item.subject,
        body_text=queue_item.body_text,
        body_html=body_html,
        sender_email=sender_email,
        inline_logo_path=(
            _inline_logo_path if logo_url == _default_logo else None
        ),
    )

    # ── Update daily send counter ──────────────────────────────────────
    try:
        from datetime import datetime, timezone as _tz, date as _date
        _now = datetime.now(_tz.utc)

        # Auto-reset if last_sent_at was a previous day
        if account.last_sent_at:
            _last_date = account.last_sent_at.astimezone(_tz.utc).date()
            if _last_date < _now.date():
                account.sent_today = 0

        account.sent_today = (account.sent_today or 0) + 1
        account.last_sent_at = _now
        account.updated_at = _now
        db.commit()
    except Exception as _counter_err:
        logger.warning(
            "Failed to increment sent_today for account=%s: %s",
            queue_item.email_account_id,
            _counter_err,
        )
        db.rollback()

    return result


def mark_queue_sent(
    db: Session,
    queue_item: EmailQueue,
    provider_message_id: str | None,
) -> EmailQueue:

    from datetime import datetime, timezone

    queue_item.status = "sent"
    queue_item.sent_at = datetime.now(timezone.utc)
    queue_item.provider_message_id = (
        provider_message_id
    )
    queue_item.last_error = None
    queue_item.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(queue_item)

    return queue_item


def mark_queue_failed(
    db: Session,
    queue_item: EmailQueue,
    error_message: str,
) -> EmailQueue:

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    queue_item.status = "failed"
    queue_item.last_error = error_message
    queue_item.last_error_at = now
    queue_item.updated_at = now

    db.commit()
    db.refresh(queue_item)

    return queue_item


async def process_due_queue(
    db: Session,
    batch_size: int = 10,
) -> dict:
    """
    Pending/scheduled emails ko batch mein process karo.
    Har queue item ke liye:
      1. Status 'processing' karo
      2. Gmail se send karo
      3. Success pe 'sent', failure pe 'failed' mark karo

    Returns dict: { processed, sent, failed, results }
    """
    from datetime import datetime, timezone
    from app.services.email_queue import (
        get_ready_queue_items,
        mark_processing,
        mark_sent,
        mark_failed,
    )

    items = get_ready_queue_items(db=db, limit=batch_size)

    processed = 0
    sent = 0
    failed = 0
    results = []

    for item in items:
        processed += 1

        # Skip items without an email account assigned
        if not item.email_account_id:
            results.append({
                "id": str(item.id),
                "recipient": item.recipient_email,
                "success": False,
                "error": "No email account assigned.",
            })
            mark_failed(
                db=db,
                queue_item=item,
                error_message="No email account assigned.",
            )
            failed += 1
            continue

        mark_processing(db=db, queue_item=item)

        try:
            send_result = await send_queue_email(
                db=db,
                user_id=item.user_id,
                queue_item=item,
            )

            provider_message_id = send_result.get("id")

            mark_sent(
                db=db,
                queue_item=item,
                provider_message_id=provider_message_id,
            )

            # Sent deliveries are the source of truth for reply matching and
            # for creating a campaign's delayed dynamic follow-up sequence.
            from app.services.email_delivery import record_sent_queue_delivery
            delivery = record_sent_queue_delivery(db=db, queue_item=item)
            if (item.queue_type or "").lower() == "initial":
                from app.services.follow_up import create_campaign_follow_up_sequence
                create_campaign_follow_up_sequence(
                    db=db,
                    initial_delivery=delivery,
                )

            sent += 1
            results.append({
                "id": str(item.id),
                "recipient": item.recipient_email,
                "success": True,
                "provider_message_id": provider_message_id,
            })

        except Exception as exc:
            error_msg = str(exc)

            logger.error(
                "Failed to send email to %s: %s",
                item.recipient_email,
                error_msg,
            )

            mark_failed(
                db=db,
                queue_item=item,
                error_message=error_msg,
            )

            failed += 1
            results.append({
                "id": str(item.id),
                "recipient": item.recipient_email,
                "success": False,
                "error": error_msg,
            })

    return {
        "processed": processed,
        "sent": sent,
        "failed": failed,
        "results": results,
    }
