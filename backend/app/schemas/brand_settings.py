from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BrandSettingsBase(BaseModel):
    agency_name: str = Field(
        default="SoftPeak Technologies",
        min_length=1,
        max_length=200,
    )

    website: str | None = Field(
        default=None,
        max_length=500,
    )

    logo_url: str | None = Field(
        default=None,
        max_length=1000,
    )

    primary_color: str = Field(
        default="#1f6b4f",
        min_length=4,
        max_length=20,
    )

    secondary_color: str = Field(
        default="#c49a4a",
        min_length=4,
        max_length=20,
    )

    sender_name: str | None = Field(
        default=None,
        max_length=200,
    )

    sender_role: str | None = Field(
        default=None,
        max_length=200,
    )

    phone: str | None = Field(
        default=None,
        max_length=100,
    )

    address: str | None = None

    booking_url: str | None = Field(
        default=None,
        max_length=1000,
    )

    unsubscribe_url: str | None = Field(
        default=None,
        max_length=1000,
    )


class BrandSettingsCreate(BrandSettingsBase):
    pass


class BrandSettingsUpdate(BrandSettingsBase):
    pass


class BrandSettingsResponse(BrandSettingsBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    user_id: UUID