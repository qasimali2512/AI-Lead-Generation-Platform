from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.supabase import supabase


security = HTTPBearer(
    auto_error=False,
)


def serialize_user(user) -> dict:
    """Convert Supabase user object into API response."""

    email_confirmed = bool(
        getattr(
            user,
            "email_confirmed_at",
            None,
        )
    )

    return {
        "id": str(user.id),
        "email": user.email,
        "role": getattr(
            user,
            "role",
            None,
        ),
        "email_confirmed": email_confirmed,
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None,
) -> dict:
    """
    Validate the Bearer access token through Supabase Auth
    and return the authenticated user.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    access_token = credentials.credentials.strip()

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    try:
        response = supabase.auth.get_user(
            access_token,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from exc

    if response.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return serialize_user(
        response.user,
    )


def register_user(
    email: str,
    password: str,
) -> dict:
    """Register a user through Supabase Auth."""

    try:
        response = supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
            }
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to create the account: {str(exc)}",
        ) from exc

    if response.user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create the account.",
        )

    user = serialize_user(
        response.user,
    )

    session = response.session

    if session is None:
        return {
            "access_token": "",
            "refresh_token": None,
            "token_type": "bearer",
            "expires_in": None,
            "user": user,
        }

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "expires_in": session.expires_in,
        "user": user,
    }


def login_user(
    email: str,
    password: str,
) -> dict:
    """Authenticate a user through Supabase Auth."""

    try:
        response = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )

    except Exception as exc:
        print(
            f"[AUTH LOGIN ERROR] "
            f"type={type(exc).__name__} "
            f"message={str(exc)}"
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(exc)}",
        ) from exc

    if (
        response.user is None
        or response.session is None
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Supabase returned no session.",
        )

    session = response.session

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "expires_in": session.expires_in,
        "user": serialize_user(
            response.user,
        ),
    }


def refresh_session(
    refresh_token: str,
) -> dict:
    """Create a new session from a refresh token."""

    try:
        response = supabase.auth.refresh_session(
            refresh_token,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired refresh token: {str(exc)}",
        ) from exc

    if (
        response.user is None
        or response.session is None
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to refresh session.",
        )

    session = response.session

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "expires_in": session.expires_in,
        "user": serialize_user(
            response.user,
        ),
    }