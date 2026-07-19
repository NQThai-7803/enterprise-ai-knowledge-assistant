from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import Coroutine
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def run_alembic(integration_database_url: str, *args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = integration_database_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr


async def indexdef(session: AsyncSession, index_name: str) -> str | None:
    result = await session.execute(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename = 'document_chunks' AND indexname = :index_name"
        ),
        {"index_name": index_name},
    )
    return result.scalar_one_or_none()


def test_full_text_index_exists(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            assert await indexdef(session, "ix_document_chunks_text_fts_simple") is not None

    run_async(scenario())


def test_full_text_index_uses_gin(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            definition = await indexdef(session, "ix_document_chunks_text_fts_simple")

            assert definition is not None
            assert "USING gin" in definition

    run_async(scenario())


def test_full_text_index_uses_simple_configuration(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            definition = await indexdef(session, "ix_document_chunks_text_fts_simple")

            assert definition is not None
            assert "'simple'::regconfig" in definition

    run_async(scenario())


def test_full_text_index_targets_document_chunk_text(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            definition = await indexdef(session, "ix_document_chunks_text_fts_simple")

            assert definition is not None
            assert "to_tsvector" in definition
            assert "text" in definition

    run_async(scenario())


def test_migration_does_not_remove_hnsw_index(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            definition = await indexdef(session, "ix_document_chunks_embedding_hnsw_cosine")

            assert definition is not None
            assert "USING hnsw" in definition
            assert "vector_cosine_ops" in definition

    run_async(scenario())


def test_migration_does_not_modify_vector_column(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            result = await session.execute(
                text(
                    "SELECT format_type(atttypid, atttypmod) "
                    "FROM pg_attribute "
                    "WHERE attrelid = 'document_chunks'::regclass "
                    "AND attname = 'embedding'"
                )
            )

            assert result.scalar_one() == "vector(384)"

    run_async(scenario())


def test_downgrade_removes_only_full_text_index(
    integration_database_url: str,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        run_alembic(integration_database_url, "downgrade", "-1")
        try:
            async with async_session_factory_for_tests() as session:
                assert await indexdef(session, "ix_document_chunks_text_fts_simple") is None
                assert (
                    await indexdef(session, "ix_document_chunks_embedding_hnsw_cosine") is not None
                )
                table = await session.scalar(text("SELECT to_regclass('public.document_chunks')"))
                extension = await session.scalar(
                    text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
                )

                assert table == "document_chunks"
                assert extension == "vector"
        finally:
            run_alembic(integration_database_url, "upgrade", "head")

    run_async(scenario())


def test_reupgrade_restores_full_text_index(
    integration_database_url: str,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        run_alembic(integration_database_url, "downgrade", "-1")
        try:
            async with async_session_factory_for_tests() as session:
                assert await indexdef(session, "ix_document_chunks_text_fts_simple") is None
            run_alembic(integration_database_url, "upgrade", "head")
            async with async_session_factory_for_tests() as session:
                assert await indexdef(session, "ix_document_chunks_text_fts_simple") is not None
        finally:
            run_alembic(integration_database_url, "upgrade", "head")

    run_async(scenario())
