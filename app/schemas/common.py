from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class PaginationMeta(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=MAX_PAGE_SIZE)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class DataResponse(BaseModel, Generic[T]):  # noqa: UP046
    data: T
    meta: None = None


class ListResponse(BaseModel, Generic[T]):  # noqa: UP046
    data: list[T]
    meta: PaginationMeta


def calculate_offset(page: int, page_size: int) -> int:
    return (page - 1) * page_size


def calculate_total_pages(total: int, page_size: int) -> int:
    if total <= 0:
        return 0
    return ceil(total / page_size)


def build_pagination_meta(*, page: int, page_size: int, total: int) -> PaginationMeta:
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=calculate_total_pages(total, page_size),
    )
