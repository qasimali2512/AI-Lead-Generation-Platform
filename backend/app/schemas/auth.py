from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Registration request."""

    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )


class LoginRequest(BaseModel):
    """Login request."""

    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )


class RefreshRequest(BaseModel):
    """Refresh-token request."""

    refresh_token: str = Field(
        min_length=1,
    )


class UserResponse(BaseModel):
    """Authenticated user."""

    id: str
    email: str | None = None
    role: str | None = None
    email_confirmed: bool = False


class AuthResponse(BaseModel):
    """Authentication response."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    user: UserResponse