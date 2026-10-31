"""Known defect: HNSW post-filter recall in permission-scoped semantic retrieval.

``search_permitted_chunks`` filters by document status and permission in the same statement that
orders by cosine distance and applies LIMIT. When the planner uses the HNSW index, pgvector hands
back only ``hnsw.ef_search`` (default 40) nearest index elements. The permission join and the heap
visibility check run after that. If more than 40 index elements closer to the query belong to
chunks the user may not see, or to chunks that were deleted but not vacuumed yet, every candidate
is discarded and an authorized user gets no result even though a permitted chunk matches. Nothing
unauthorized is returned.

The searching transaction forces the index-friendly planner settings itself (``enable_seqscan``
and ``enable_sort`` off; with only ``enable_seqscan`` off the planner still avoids HNSW).

- Flag off (default statement): xfail(strict). EXPLAIN in the same transaction must show the
  HNSW index; if it does not, the test raises ``RuntimeError``, which is reported as a real
  failure, never as an expected failure or an XPASS.
- Flag on (``exact_permitted_knn``, docs/design/hnsw-permission-recall.md): the same scenarios
  must return the permitted chunk, and the plan must not use the HNSW index.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import event, insert, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models import Document, DocumentAccessScope, DocumentChunk, User, UserRole
from app.retrieval.semantic_repository import RetrievalRow
from tests.conftest import _clear_database_data
from tests.integration.retrieval_helpers import (
    checksum,
    create_chunk,
    create_department,
    create_document,
    create_user,
    row_document_ids,
    run_async,
    search_rows,
    similarity_vector,
)
from tests.integration.semantic_query_diagnostics import is_distance_query

# The integration CI lane selects every test marked integration without a model/Celery marker.
pytestmark = pytest.mark.integration

HNSW_INDEX = "ix_document_chunks_embedding_hnsw_cosine"
FORCE_HNSW_PLAN = ("SET LOCAL enable_seqscan = off", "SET LOCAL enable_sort = off")
DEFAULT_EF_SEARCH = 40
# Enough distinct vectors to fill every HNSW candidate slot. Identical vectors share one index
# element (up to 10 heap TIDs each), so each chunk below gets its own axis.
NEARER_THAN_PERMITTED = DEFAULT_EF_SEARCH + 20
KNOWN_DEFECT = (
    "HNSW post-filter recall: permission and visibility are applied after pgvector returns "
    "hnsw.ef_search candidates"
)


def _chunk_rows(document: Document, *, count: int, similarity: float) -> list[dict[str, object]]:
    rows = []
    for index in range(count):
        text_value = f"Chunk {document.id} {index}"
        rows.append(
            {
                "id": uuid.uuid4(),
                "document_id": document.id,
                "chunk_index": index,
                "text": text_value,
                "token_count": len(text_value.split()),
                "character_count": len(text_value),
                "page_numbers": [1],
                "start_page": 1,
                "end_page": 1,
                "overlap_token_count": 0,
                "content_sha256": checksum(text_value),
                "embedding": similarity_vector(similarity, axis=1 + index),
                "embedding_provider": "sentence_transformers",
                "embedding_model": "fake-model",
                "embedding_dimensions": 384,
            }
        )
    return rows


async def _maintenance(engine: AsyncEngine, *statements: str) -> None:
    async with engine.connect() as conn:
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        for statement in statements:
            await conn.execute(text(statement))


async def _search_with_forced_index_settings(
    session: AsyncSession, engine: AsyncEngine, user: User, *, exact_permitted_knn: bool
) -> tuple[tuple[RetrievalRow, ...], str]:
    captured: list[tuple[str, object]] = []

    def capture(conn, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        if is_distance_query(statement):
            captured.append((statement, parameters))

    for setting in FORCE_HNSW_PLAN:
        await session.execute(text(setting))
    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        rows = await search_rows(
            session, user=user, top_k=1, exact_permitted_knn=exact_permitted_knn
        )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
    if len(captured) != 1:
        raise RuntimeError(f"expected one distance query, captured {len(captured)}")
    statement, parameters = captured[0]
    # Same transaction, so the same SET LOCAL values shape this plan.
    connection = await session.connection()
    plan = await connection.exec_driver_sql("EXPLAIN " + statement, parameters)
    plan_text = "\n".join(row[0] for row in plan.all())
    if not exact_permitted_knn and HNSW_INDEX not in plan_text:
        raise RuntimeError(
            "precondition failed: the query did not use the HNSW index:\n" + plan_text
        )
    return rows, plan_text


def _run_recall_case(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    key: str,
    *,
    delete_nearer_chunks: bool,
    exact_permitted_knn: bool = False,
) -> None:
    engine: AsyncEngine = async_session_factory_for_tests.kw["bind"]

    async def scenario() -> None:
        await _maintenance(
            engine,
            # Start without dead index entries left by earlier tests.
            "VACUUM document_chunks",
            # Keep autovacuum from removing the dead index entries this case relies on.
            "ALTER TABLE document_chunks SET (autovacuum_enabled = false)",
        )
        try:
            async with async_session_factory_for_tests() as session:
                department_a = await create_department(session, f"{key}-a")
                department_b = await create_department(session, f"{key}-b")
                admin = await create_user(session, f"{key}-admin", role=UserRole.ADMIN)
                staff = await create_user(session, f"{key}-staff", department_id=department_a.id)
                nearer = await create_document(
                    session,
                    f"{key}-nearer",
                    uploader=admin,
                    access_scope=DocumentAccessScope.DEPARTMENT,
                    department_id=department_b.id,
                )
                await session.execute(
                    insert(DocumentChunk),
                    _chunk_rows(nearer, count=NEARER_THAN_PERMITTED, similarity=0.99),
                )
                allowed = await create_document(
                    session,
                    f"{key}-allowed",
                    uploader=admin,
                    access_scope=DocumentAccessScope.ORGANIZATION,
                )
                await create_chunk(session, f"{key}-allowed", document=allowed, similarity=0.2)
                if delete_nearer_chunks:
                    await session.execute(
                        text("DELETE FROM document_chunks WHERE document_id = :id"),
                        {"id": nearer.id},
                    )
                    await session.commit()

                rows, plan_text = await _search_with_forced_index_settings(
                    session, engine, staff, exact_permitted_knn=exact_permitted_knn
                )

                assert row_document_ids(rows) == [allowed.id]
                if exact_permitted_knn:
                    assert HNSW_INDEX not in plan_text
        finally:
            # Leave no dead tuples behind and restore the table's autovacuum setting.
            await _clear_database_data(async_session_factory_for_tests)
            await _maintenance(
                engine,
                "ALTER TABLE document_chunks RESET (autovacuum_enabled)",
                "VACUUM ANALYZE document_chunks",
            )

    run_async(scenario())


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=KNOWN_DEFECT)
def test_unauthorized_nearer_chunks_do_not_hide_permitted_chunk_under_hnsw(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_recall_case(
        async_session_factory_for_tests, "hnsw-recall-unauthorized", delete_nearer_chunks=False
    )


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=KNOWN_DEFECT)
def test_deleted_nearer_chunks_do_not_hide_permitted_chunk_under_hnsw(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_recall_case(
        async_session_factory_for_tests, "hnsw-recall-deleted", delete_nearer_chunks=True
    )


def test_exact_knn_keeps_permitted_chunk_despite_nearer_unauthorized_chunks(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_recall_case(
        async_session_factory_for_tests,
        "exact-knn-unauthorized",
        delete_nearer_chunks=False,
        exact_permitted_knn=True,
    )


def test_exact_knn_keeps_permitted_chunk_despite_nearer_deleted_chunks(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    _run_recall_case(
        async_session_factory_for_tests,
        "exact-knn-deleted",
        delete_nearer_chunks=True,
        exact_permitted_knn=True,
    )
