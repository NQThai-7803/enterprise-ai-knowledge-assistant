from __future__ import annotations

import os
import subprocess
import sys

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration


def test_feedback_rating_enum_exists(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            labels = tuple(
                await session.scalars(
                    text(
                        "select enumlabel from pg_enum "
                        "join pg_type on pg_enum.enumtypid = pg_type.oid "
                        "where pg_type.typname = 'feedback_rating' "
                        "order by enumsortorder"
                    )
                )
            )
            assert labels == ("HELPFUL", "NOT_HELPFUL")

    import asyncio

    asyncio.run(scenario())


def test_feedback_table_exists(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            exists = await session.scalar(text("select to_regclass('public.feedback') is not null"))
            assert exists is True

    import asyncio

    asyncio.run(scenario())


def test_feedback_constraints_and_indexes_exist(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            constraints = set(
                await session.scalars(
                    text(
                        "select conname from pg_constraint "
                        "where conrelid = 'public.feedback'::regclass"
                    )
                )
            )
            indexes = set(
                await session.scalars(
                    text(
                        "select indexname from pg_indexes "
                        "where schemaname = 'public' and tablename = 'feedback'"
                    )
                )
            )
            assert "uq_feedback_message_user" in constraints
            assert "ck_feedback_reason_not_blank" in constraints
            assert "ck_feedback_reason_max_length" in constraints
            assert "ix_feedback_user_updated" in indexes
            assert "ix_feedback_rating_updated" in indexes
            assert "ix_feedback_message" in indexes

    import asyncio

    asyncio.run(scenario())


def test_feedback_foreign_keys_exist(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            rows = {
                row.column_name: (row.foreign_table_name, row.delete_rule)
                for row in (
                    await session.execute(
                        text(
                            "select kcu.column_name, ccu.table_name as foreign_table_name, "
                            "rc.delete_rule "
                            "from information_schema.table_constraints tc "
                            "join information_schema.key_column_usage kcu "
                            "on tc.constraint_name = kcu.constraint_name "
                            "and tc.table_schema = kcu.table_schema "
                            "join information_schema.constraint_column_usage ccu "
                            "on ccu.constraint_name = tc.constraint_name "
                            "and ccu.table_schema = tc.table_schema "
                            "join information_schema.referential_constraints rc "
                            "on rc.constraint_name = tc.constraint_name "
                            "and rc.constraint_schema = tc.table_schema "
                            "where tc.constraint_type = 'FOREIGN KEY' "
                            "and tc.table_schema = 'public' and tc.table_name = 'feedback'"
                        )
                    )
                ).all()
            }
            assert rows["message_id"] == ("chat_messages", "CASCADE")
            assert rows["user_id"] == ("users", "RESTRICT")

    import asyncio

    asyncio.run(scenario())


def test_feedback_migration_downgrade_and_reupgrade_preserves_existing_tables(
    integration_database_url: str,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = integration_database_url
    try:
        downgrade = subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", "20260720_0007"],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        assert downgrade.returncode == 0, downgrade.stderr

        async def scenario() -> None:
            async with async_session_factory_for_tests() as session:
                row = (
                    await session.execute(
                        text(
                            "select to_regclass('public.feedback') is null as feedback_missing, "
                            "to_regtype('public.feedback_rating') is null as enum_missing, "
                            "to_regclass('public.chat_messages') is not null as chat_present, "
                            "to_regclass('public.message_citations') is not null "
                            "as citations_present"
                        )
                    )
                ).one()
                assert tuple(row) == (True, True, True, True)

        import asyncio

        asyncio.run(scenario())
    finally:
        upgrade = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        assert upgrade.returncode == 0, upgrade.stderr
