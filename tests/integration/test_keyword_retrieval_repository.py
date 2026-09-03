from __future__ import annotations

import asyncio
import inspect
from collections.abc import Coroutine
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import DocumentAccessScope, UserRole
from app.retrieval.keyword_repository import (
    KeywordRetrievalRow,
    search_permitted_chunks_by_keyword,
)
from tests.integration.retrieval_helpers import (
    assert_marker_absent,
    create_chunk,
    create_document,
    create_user,
    disable_postgres_jit,
    row_document_ids,
)

pytestmark = pytest.mark.integration
HIDDEN_MARKER = "UNAUTHORIZED_KEYWORD_MARKER"


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


async def keyword_rows(
    session: AsyncSession,
    *,
    user,
    query: str,
    top_k: int = 20,
    min_rank: float = 0.0,
) -> tuple[KeywordRetrievalRow, ...]:
    await disable_postgres_jit(session)
    return await search_permitted_chunks_by_keyword(
        session,
        query=query,
        current_user=user,
        top_k=top_k,
        min_keyword_rank=min_rank,
    )


def test_keyword_search_finds_exact_term(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-exact-admin", role=UserRole.ADMIN)
            document = await create_document(session, "keyword-exact-doc", uploader=admin)
            await create_chunk(
                session,
                "keyword-exact-doc",
                document=document,
                text="The retention policy defines retention periods.",
            )

            rows = await keyword_rows(session, user=admin, query="retention")

            assert row_document_ids(rows) == [document.id]
            assert rows[0].keyword_rank > 0.0

    run_async(scenario())


def test_keyword_search_finds_vietnamese_phrase(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-vietnamese-admin", role=UserRole.ADMIN)
            document = await create_document(session, "keyword-vietnamese-doc", uploader=admin)
            await create_chunk(
                session,
                "keyword-vietnamese-doc",
                document=document,
                text="Chính sách bảo mật quy định thời hạn thanh toán và nghỉ phép.",
            )

            rows = await keyword_rows(session, user=admin, query="thời hạn thanh toán")

            assert row_document_ids(rows) == [document.id]

    run_async(scenario())


def test_keyword_search_finds_accented_policy_from_ascii_vietnamese_query(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(
                session,
                "keyword-ascii-vietnamese-admin",
                role=UserRole.ADMIN,
            )
            document = await create_document(
                session,
                "keyword-ascii-vietnamese-doc",
                uploader=admin,
                title="Ch\u00ednh s\u00e1ch ti\u1ec1n l\u01b0\u01a1ng v\u00e0 ph\u1ee5 c\u1ea5p",
            )
            lunch_chunk = await create_chunk(
                session,
                "keyword-ascii-vietnamese-chunk",
                document=document,
                text="Ph\u1ee5 c\u1ea5p \u0103n tr\u01b0a l\u00e0 900.000 \u0111/th\u00e1ng.",
            )

            rows = await keyword_rows(
                session,
                user=admin,
                query="moi thang phu cap an trua bao nhieu",
                top_k=8,
            )

            assert rows
            assert rows[0].chunk_id == lunch_chunk.id

    run_async(scenario())


def test_keyword_fallback_finds_vietnamese_leave_policy_question(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        query = (
            "Trong công việc điều kiện bình thường, mức nghỉ hằng năm hưởng nguyên lương "
            "là bao nhiêu ngày?"
        )
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-vn-leave-admin", role=UserRole.ADMIN)
            leave_document = await create_document(
                session,
                "keyword-vn-leave-doc",
                uploader=admin,
                title="Chính sách nghỉ của người lao động",
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            unrelated_document = await create_document(
                session,
                "keyword-vn-leave-unrelated",
                uploader=admin,
                title="Giới thiệu về công ty",
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            leave_chunk = await create_chunk(
                session,
                "keyword-vn-leave-chunk",
                document=leave_document,
                text=(
                    "Mức nghỉ hằng năm hưởng nguyên lương là 12 ngày. "
                    "Áp dụng cho công việc trong điều kiện bình thường."
                ),
            )
            await create_chunk(
                session,
                "keyword-vn-leave-company",
                document=unrelated_document,
                text="Giới thiệu về công ty, cơ cấu tổ chức và các phòng ban nội bộ.",
            )

            rows = await keyword_rows(session, user=admin, query=query, top_k=8)

            assert rows
            assert rows[0].chunk_id == leave_chunk.id
            assert rows[0].document_id == leave_document.id
            assert rows[0].keyword_rank > 0.0

    run_async(scenario())


def test_keyword_search_finds_contract_code(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_code_search_case(async_session_factory_for_tests, "HD-2026-001")


def test_keyword_search_finds_policy_code(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_code_search_case(async_session_factory_for_tests, "POLICY-IT-09")


def test_keyword_search_finds_invoice_code(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_code_search_case(async_session_factory_for_tests, "INV/2026/00045")


def test_keyword_search_finds_employee_code(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_code_search_case(async_session_factory_for_tests, "NV-00125")


def _run_code_search_case(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession], code: str
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            key = code.lower().replace("/", "-")
            admin = await create_user(session, f"keyword-code-admin-{key}", role=UserRole.ADMIN)
            document = await create_document(session, f"keyword-code-doc-{key}", uploader=admin)
            await create_chunk(
                session,
                f"keyword-code-doc-{key}",
                document=document,
                text=f"Mã tài liệu {code} quy định thời hạn thanh toán.",
            )

            rows = await keyword_rows(session, user=admin, query=code)

            assert row_document_ids(rows) == [document.id]

    run_async(scenario())


def test_keyword_search_finds_code_inside_natural_question(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-code-question-admin", role=UserRole.ADMIN)
            document = await create_document(session, "keyword-code-question-doc", uploader=admin)
            await create_chunk(
                session,
                "keyword-code-question-doc",
                document=document,
                text="Hợp đồng HD-2026-001 quy định thời hạn thanh toán trong 30 ngày.",
            )

            rows = await keyword_rows(
                session,
                user=admin,
                query="HD-2026-001 quy định thời hạn thanh toán thế nào?",
            )

            assert row_document_ids(rows) == [document.id]
            assert rows[0].keyword_rank > 0.0

    run_async(scenario())


def test_keyword_search_orders_higher_rank_first(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-rank-admin", role=UserRole.ADMIN)
            low = await create_document(session, "keyword-rank-low", uploader=admin)
            high = await create_document(session, "keyword-rank-high", uploader=admin)
            await create_chunk(session, "keyword-rank-low", document=low, text="nghỉ phép")
            await create_chunk(
                session,
                "keyword-rank-high",
                document=high,
                text="nghỉ phép nghỉ phép nghỉ phép quy định nghỉ phép",
            )

            rows = await keyword_rows(session, user=admin, query="nghỉ phép")

            assert row_document_ids(rows)[0] == high.id

    run_async(scenario())


def test_keyword_search_returns_stable_order(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-stable-admin", role=UserRole.ADMIN)
            for key in ("b", "a", "c"):
                document = await create_document(session, f"keyword-stable-{key}", uploader=admin)
                await create_chunk(
                    session,
                    f"keyword-stable-{key}",
                    document=document,
                    text="stable keyword",
                )

            first = row_document_ids(await keyword_rows(session, user=admin, query="stable"))
            second = row_document_ids(await keyword_rows(session, user=admin, query="stable"))

            assert first == second
            assert first == sorted(first)

    run_async(scenario())


def test_keyword_search_returns_no_unmatched_chunks(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-unmatched-admin", role=UserRole.ADMIN)
            document = await create_document(session, "keyword-unmatched-doc", uploader=admin)
            await create_chunk(session, "keyword-unmatched-doc", document=document, text="finance")

            rows = await keyword_rows(session, user=admin, query="human resources")

            assert rows == ()

    run_async(scenario())


def test_keyword_search_applies_min_rank(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-min-rank-admin", role=UserRole.ADMIN)
            document = await create_document(session, "keyword-min-rank-doc", uploader=admin)
            await create_chunk(session, "keyword-min-rank-doc", document=document, text="policy")

            matching_rows = await keyword_rows(session, user=admin, query="policy")
            high_threshold_rows = await keyword_rows(
                session,
                user=admin,
                query="policy",
                min_rank=matching_rows[0].keyword_rank + 1.0,
            )
            equal_threshold_rows = await keyword_rows(
                session,
                user=admin,
                query="policy",
                min_rank=matching_rows[0].keyword_rank,
            )

            assert high_threshold_rows == ()
            assert row_document_ids(equal_threshold_rows) == [document.id]

    run_async(scenario())


def test_keyword_search_limits_top_k(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-limit-admin", role=UserRole.ADMIN)
            for index in range(3):
                document = await create_document(session, f"keyword-limit-{index}", uploader=admin)
                await create_chunk(
                    session,
                    f"keyword-limit-{index}",
                    document=document,
                    text="limit keyword",
                )

            rows = await keyword_rows(session, user=admin, query="limit", top_k=2)

            assert len(rows) == 2

    run_async(scenario())


def test_keyword_search_does_not_select_embeddings() -> None:
    source = inspect.getsource(search_permitted_chunks_by_keyword)

    assert "DocumentChunk.embedding" not in source
    assert "numpy" not in source


def test_keyword_query_is_parameterized(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run_query_safety_case(async_session_factory_for_tests, "' OR 1=1 --", "parameterized", caplog)


def test_websearch_syntax_does_not_bypass_permissions(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run_query_safety_case(
        async_session_factory_for_tests,
        "thanh toán OR hóa đơn",
        "websearch-or",
        caplog,
    )


def test_quotes_do_not_break_query(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run_query_safety_case(async_session_factory_for_tests, '"nghỉ phép"', "quotes", caplog)


def test_sql_like_input_does_not_inject_sql(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run_query_safety_case(async_session_factory_for_tests, "' OR 1=1 --", "sql-like", caplog)


def test_unicode_query_is_supported(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run_query_safety_case(async_session_factory_for_tests, " bảo mật", "unicode", caplog)


def test_emoji_query_does_not_crash(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run_query_safety_case(async_session_factory_for_tests, "nghỉ phép 🙂", "emoji", caplog)


def test_query_is_not_logged(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        caplog.set_level("INFO", logger="app.retrieval.keyword_service")
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "keyword-query-log-admin", role=UserRole.ADMIN)
            document = await create_document(session, "keyword-query-log-doc", uploader=admin)
            await create_chunk(
                session, "keyword-query-log-doc", document=document, text="SensitiveKeyword"
            )

            rows = await keyword_rows(session, user=admin, query="SensitiveKeyword")

            assert len(rows) == 1
            assert "SensitiveKeyword" not in caplog.text

    run_async(scenario())


def _run_query_safety_case(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    query: str,
    key: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, f"keyword-query-{key}-admin", role=UserRole.ADMIN)
            staff = await create_user(session, f"keyword-query-{key}-staff")
            allowed = await create_document(
                session,
                f"keyword-query-{key}-allowed",
                uploader=admin,
                access_scope=DocumentAccessScope.ORGANIZATION,
            )
            hidden = await create_document(
                session,
                f"keyword-query-{key}-hidden",
                uploader=admin,
                title=HIDDEN_MARKER,
            )
            await create_chunk(
                session,
                f"keyword-query-{key}-allowed",
                document=allowed,
                text="nghỉ phép bảo mật thanh toán hóa đơn 1 1",
            )
            await create_chunk(
                session,
                f"keyword-query-{key}-hidden",
                document=hidden,
                text=f"{HIDDEN_MARKER} nghỉ phép bảo mật thanh toán hóa đơn 1 1",
            )

            rows = await keyword_rows(session, user=staff, query=query)

            assert all(row.document_id != hidden.id for row in rows)
            assert_marker_absent(rows, HIDDEN_MARKER, caplog.text)

    run_async(scenario())
