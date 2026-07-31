from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration


def run_async(coro):
    return asyncio.run(coro)


async def scalar(session_factory: async_sessionmaker[AsyncSession], statement: str):
    async with session_factory() as session:
        return await session.scalar(text(statement))


async def rows(session_factory: async_sessionmaker[AsyncSession], statement: str):
    async with session_factory() as session:
        result = await session.execute(text(statement))
        return result.all()


def run_alembic(database_url: str, *args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr


def test_chat_message_role_enum_exists(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    exists = run_async(
        scalar(
            async_session_factory_for_tests,
            "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chat_message_role')",
        )
    )

    assert exists is True


def test_chat_sessions_table_exists(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    exists = run_async(
        scalar(
            async_session_factory_for_tests,
            "SELECT to_regclass('public.chat_sessions') IS NOT NULL",
        )
    )

    assert exists is True


def test_chat_messages_table_exists(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    exists = run_async(
        scalar(
            async_session_factory_for_tests,
            "SELECT to_regclass('public.chat_messages') IS NOT NULL",
        )
    )

    assert exists is True


def test_chat_session_user_foreign_key_exists(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    delete_behavior = run_async(
        scalar(
            async_session_factory_for_tests,
            """
            SELECT confdeltype
            FROM pg_constraint
            WHERE conrelid = 'chat_sessions'::regclass
              AND contype = 'f'
              AND pg_get_constraintdef(oid) LIKE '%REFERENCES users%'
            """,
        )
    )

    assert delete_behavior in ("r", b"r")


def test_chat_message_session_foreign_key_cascades(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    delete_behavior = run_async(
        scalar(
            async_session_factory_for_tests,
            """
            SELECT confdeltype
            FROM pg_constraint
            WHERE conrelid = 'chat_messages'::regclass
              AND contype = 'f'
              AND pg_get_constraintdef(oid) LIKE '%REFERENCES chat_sessions%'
            """,
        )
    )

    assert delete_behavior in ("c", b"c")


def test_chat_session_indexes_exist(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    index_names = {
        row[0]
        for row in run_async(
            rows(
                async_session_factory_for_tests,
                "SELECT indexname FROM pg_indexes WHERE tablename = 'chat_sessions'",
            )
        )
    }

    assert "ix_chat_sessions_user_updated" in index_names


def test_chat_message_history_index_exists(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    index_names = {
        row[0]
        for row in run_async(
            rows(
                async_session_factory_for_tests,
                "SELECT indexname FROM pg_indexes WHERE tablename = 'chat_messages'",
            )
        )
    }

    assert "ix_chat_messages_session_created" in index_names


def test_chat_message_content_constraint_exists(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    exists = run_async(
        scalar(
            async_session_factory_for_tests,
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ck_chat_messages_content_not_blank'
            )
            """,
        )
    )

    assert exists is True


def test_chat_message_metric_constraints_exist(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    constraint_names = {
        row[0]
        for row in run_async(
            rows(
                async_session_factory_for_tests,
                """
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'chat_messages'::regclass
                """,
            )
        )
    }

    assert "ck_chat_messages_response_time_non_negative" in constraint_names
    assert "ck_chat_messages_prompt_tokens_non_negative" in constraint_names
    assert "ck_chat_messages_completion_tokens_non_negative" in constraint_names


def test_chat_migration_downgrade_removes_and_reupgrade_restores_chat_only(
    integration_database_url: str,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    run_alembic(integration_database_url, "downgrade", "20260718_0006")
    try:
        assert run_async(
            scalar(
                async_session_factory_for_tests,
                "SELECT to_regclass('public.chat_messages') IS NULL",
            )
        )
        assert run_async(
            scalar(
                async_session_factory_for_tests,
                "SELECT to_regclass('public.chat_sessions') IS NULL",
            )
        )
        assert run_async(
            scalar(
                async_session_factory_for_tests,
                "SELECT NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chat_message_role')",
            )
        )
        assert run_async(
            scalar(
                async_session_factory_for_tests,
                "SELECT to_regclass('public.documents') IS NOT NULL",
            )
        )
        assert run_async(
            scalar(
                async_session_factory_for_tests,
                "SELECT to_regclass('public.document_chunks') IS NOT NULL",
            )
        )
        index_names = {
            row[0]
            for row in run_async(
                rows(
                    async_session_factory_for_tests,
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'document_chunks'
                    """,
                )
            )
        }
        assert "ix_document_chunks_embedding_hnsw_cosine" in index_names
        assert "ix_document_chunks_text_fts_simple" in index_names
    finally:
        run_alembic(integration_database_url, "upgrade", "head")

    assert run_async(
        scalar(
            async_session_factory_for_tests,
            "SELECT to_regclass('public.chat_sessions') IS NOT NULL",
        )
    )
    assert run_async(
        scalar(
            async_session_factory_for_tests,
            "SELECT to_regclass('public.chat_messages') IS NOT NULL",
        )
    )
