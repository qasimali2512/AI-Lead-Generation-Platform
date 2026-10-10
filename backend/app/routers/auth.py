from fastapi import APIRouter, Depends

from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.auth import (
    login_user,
    refresh_session,
    register_user,
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=AuthResponse,
)
def register(
    payload: RegisterRequest,
):
    """Register a new user."""

    return register_user(
        email=payload.email,
        password=payload.password,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
)
def login(
    payload: LoginRequest,
):
    """Login an existing user."""

    return login_user(
        email=payload.email,
        password=payload.password,
    )


@router.post(
    "/refresh",
    response_model=AuthResponse,
)
def refresh(
    payload: RefreshRequest,
):
    """Refresh an authentication session."""

    return refresh_session(
        refresh_token=payload.refresh_token,
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: dict = Depends(get_current_user),
):
    """Return the currently authenticated user."""

    return {
        "id": current_user["sub"],
        "email": current_user.get("email"),
        "role": current_user.get("role"),
        "email_confirmed": True,
    }


@router.post("/logout")
def logout():
    """
    Logout endpoint.

    The frontend removes the stored access and refresh tokens.
    Supabase access tokens remain valid until their expiry.
    """

    return {
        "success": True,
        "message": "Logout successful. Clear the local session.",
    }