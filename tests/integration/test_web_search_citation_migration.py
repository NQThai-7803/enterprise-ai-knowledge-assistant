from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration


def run_async(coro):  # noqa: ANN001, ANN201
    return asyncio.run(coro)


async def rows(session_factory: async_sessionmaker[AsyncSession], statement: str):  # noqa: ANN201
    async with session_factory() as session:
        result = await session.execute(text(statement))
        return result.all()


def test_message_citations_support_internal_and_web_source_columns(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    columns = {
        row.column_name: row.is_nullable
        for row in run_async(
            rows(
                async_session_factory_for_tests,
                """
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'message_citations'
                  AND column_name IN ('source_type', 'source_url', 'source_title', 'document_id')
                """,
            )
        )
    }

    assert columns["source_type"] == "NO"
    assert columns["source_url"] == "YES"
    assert columns["source_title"] == "YES"
    assert columns["document_id"] == "YES"


def test_message_citations_web_source_constraints_exist(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    constraints = {
        row[0]
        for row in run_async(
            rows(
                async_session_factory_for_tests,
                """
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'message_citations'::regclass
                """,
            )
        )
    }
    indexes = {
        row[0]
        for row in run_async(
            rows(
                async_session_factory_for_tests,
                "SELECT indexname FROM pg_indexes WHERE tablename = 'message_citations'",
            )
        )
    }

    assert "ck_message_citations_source_type_valid" in constraints
    assert "ck_message_citations_internal_document_required" in constraints
    assert "ck_message_citations_web_source_required" in constraints
    assert "ix_message_citations_source_type" in indexes
