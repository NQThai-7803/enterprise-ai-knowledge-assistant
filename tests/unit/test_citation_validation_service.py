from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any
from uuid import UUID

import pytest

from app.chat.models import SelectedContextItem
from app.citations.errors import (
    CitationFailureCode,
    CitationPermissionRevalidationError,
    CitationValidationError,
)
from app.citations.registry import build_prompt_source_registry
from app.core.config import Settings
from app.models import CitationSourceType, User, UserRole
from app.repositories.citation_source_repository import PermittedCitationSourceRow
from app.services.citation_validation_service import CitationValidationService


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def user() -> User:
    return User(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="citation@example.com",
        full_name="Citation User",
        hashed_password="not-used",
        role=UserRole.STAFF,
        is_active=True,
    )


def source_registry():
    return build_prompt_source_registry(
        context_items=(
            SelectedContextItem(
                ordinal=1,
                text="Context text",
                token_count=4,
                chunk_id=UUID("00000000-0000-0000-0000-000000000101"),
                document_id=UUID("00000000-0000-0000-0000-000000000201"),
                document_title="Document",
                page_numbers=(1,),
                start_page=1,
                end_page=1,
                semantic_score=0.9,
                keyword_score=None,
                hybrid_score=1.0,
            ),
        ),
        max_sources=8,
    )


class FakeSessionProvider:
    def __call__(self):  # noqa: ANN204
        class Context:
            async def __aenter__(self):  # noqa: ANN201
                return object()

            async def __aexit__(self, exc_type, exc, traceback) -> None:  # noqa: ANN001
                return None

        return Context()


class FakeSourceRepository:
    def __init__(self, rows: tuple[PermittedCitationSourceRow, ...]) -> None:
        self.rows = rows
        self.chunk_ids = ()

    async def get_permitted_ready_chunks_by_ids(self, session, *, chunk_ids, current_user):  # noqa: ANN001
        self.chunk_ids = tuple(chunk_ids)
        return self.rows


def service(rows: tuple[PermittedCitationSourceRow, ...]) -> CitationValidationService:
    return CitationValidationService(
        settings=Settings(_env_file=None),
        session_provider=FakeSessionProvider(),
        source_repository=FakeSourceRepository(rows),
    )


def row() -> PermittedCitationSourceRow:
    source = source_registry().sources[0]
    return PermittedCitationSourceRow(
        chunk_id=source.chunk_id,
        document_id=source.document_id,
        document_title="Current Document",
    )


def test_answered_response_requires_marker() -> None:
    async def scenario() -> None:
        with pytest.raises(CitationValidationError) as exc_info:
            await service((row(),)).validate_and_map(
                answer="Answer without marker.",
                source_registry=source_registry(),
                current_user=user(),
            )
        assert exc_info.value.code == CitationFailureCode.CITATION_MARKER_MISSING

    run_async(scenario())


def test_known_marker_is_accepted_and_rewritten() -> None:
    async def scenario() -> None:
        validated = await service((row(),)).validate_and_map(
            answer="Answer [SOURCE_1].",
            source_registry=source_registry(),
            current_user=user(),
        )

        assert validated.answer == "Answer [1]."
        assert len(validated.citations) == 1

    run_async(scenario())


def test_unknown_marker_is_rejected() -> None:
    async def scenario() -> None:
        with pytest.raises(CitationValidationError) as exc_info:
            await service((row(),)).validate_and_map(
                answer="Answer [SOURCE_999].",
                source_registry=source_registry(),
                current_user=user(),
            )
        assert exc_info.value.code == CitationFailureCode.CITATION_MARKER_UNKNOWN

    run_async(scenario())


def test_malformed_marker_is_rejected() -> None:
    async def scenario() -> None:
        with pytest.raises(CitationValidationError) as exc_info:
            await service((row(),)).validate_and_map(
                answer="Answer [SOURCE_X].",
                source_registry=source_registry(),
                current_user=user(),
            )
        assert exc_info.value.code == CitationFailureCode.CITATION_MARKER_INVALID

    run_async(scenario())


def test_duplicate_marker_creates_one_citation() -> None:
    async def scenario() -> None:
        validated = await service((row(),)).validate_and_map(
            answer="A [SOURCE_1]. Again [SOURCE_1].",
            source_registry=source_registry(),
            current_user=user(),
        )

        assert len(validated.citations) == 1
        assert validated.answer == "A [1]. Again [1]."

    run_async(scenario())


def test_permission_revalidation_failure_is_distinct() -> None:
    async def scenario() -> None:
        with pytest.raises(CitationPermissionRevalidationError):
            await service(()).validate_and_map(
                answer="Answer [SOURCE_1].",
                source_registry=source_registry(),
                current_user=user(),
            )

    run_async(scenario())


def web_source_registry():
    return build_prompt_source_registry(
        context_items=(
            SelectedContextItem(
                ordinal=1,
                text="Microsoft Learn describes Azure AI services.",
                token_count=6,
                document_title="Microsoft Learn",
                source_type=CitationSourceType.WEB,
                source_url="https://learn.microsoft.com/en-us/azure/ai-services/",
                page_numbers=(1,),
                start_page=1,
                end_page=1,
                hybrid_score=1.0,
            ),
        ),
        max_sources=8,
    )


def test_web_citation_does_not_revalidate_internal_document_permissions() -> None:
    async def scenario() -> None:
        repository = FakeSourceRepository(())
        validator = CitationValidationService(
            settings=Settings(_env_file=None),
            session_provider=FakeSessionProvider(),
            source_repository=repository,
        )

        validated = await validator.validate_and_map(
            answer="Azure AI is documented [SOURCE_1].",
            source_registry=web_source_registry(),
            current_user=user(),
        )

        assert repository.chunk_ids == ()
        assert validated.answer == "Azure AI is documented [1]."
        assert validated.citations[0].source_type == CitationSourceType.WEB
        assert (
            validated.citations[0].source_url
            == "https://learn.microsoft.com/en-us/azure/ai-services/"
        )

    run_async(scenario())
