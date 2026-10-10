from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None
    role: str | None = None
    email_confirmed: bool = False


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=100,
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(
        min_length=8,
        max_length=128,
    )
    new_password: str = Field(
        min_length=8,
        max_length=128,
    )
    confirm_password: str = Field(
        min_length=8,
        max_length=128,
    )