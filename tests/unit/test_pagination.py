from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.common import PaginationMeta, calculate_total_pages


def test_page_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        PaginationMeta(page=0, page_size=20, total=0, total_pages=0)


def test_page_size_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        PaginationMeta(page=1, page_size=0, total=0, total_pages=0)


def test_page_size_cannot_exceed_100() -> None:
    with pytest.raises(ValidationError):
        PaginationMeta(page=1, page_size=101, total=0, total_pages=0)


def test_total_pages_calculation() -> None:
    assert calculate_total_pages(125, 20) == 7


def test_zero_results_has_zero_total_pages() -> None:
    assert calculate_total_pages(0, 20) == 0
