from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Request completed successfully."
    data: T | None = None


class PaginationMeta(BaseModel):
    page: int = Field(
        default=1,
        ge=1,
    )

    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    total: int = Field(
        default=0,
        ge=0,
    )

    total_pages: int = Field(
        default=0,
        ge=0,
    )

    has_next: bool = False
    has_previous: bool = False


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Request completed successfully."
    data: list[T] = Field(
        default_factory=list
    )
    pagination: PaginationMeta


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: list[ErrorDetail] = Field(
        default_factory=list
    )