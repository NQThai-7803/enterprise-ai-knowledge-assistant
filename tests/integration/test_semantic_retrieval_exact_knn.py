"""Exact KNN over permitted chunks (``exact_permitted_knn``): recall and plan guards.

docs/design/hnsw-permission-recall.md, acceptance criteria 1 and 6. A mixed-permission corpus
with random vectors (and dead tuples) is searched with the flag on; the result must equal a
brute-force cosine ranking over exactly the chunks the user may read, and the statement must
never be planned through the HNSW index, whatever planner settings are forced.
"""

from __future__ import annotations

import math
import random
import uuid

import pytest
from sqlalchemy import event, insert, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models import (
    Document,
    DocumentAccessScope,
    DocumentChunk,
    DocumentStatus,
    UserRole,
)
from app.retrieval.semantic_repository import search_permitted_chunks
from tests.conftest import _clear_database_data
from tests.integration.retrieval_helpers import (
    checksum,
    create_department,
    create_document,
    create_permission,
    create_user,
    disable_postgres_jit,
    run_async,
)
from tests.integration.semantic_query_diagnostics import is_distance_query

pytestmark = pytest.mark.integration

HNSW_INDEX = "ix_document_chunks_embedding_hnsw_cosine"
DIMENSIONS = 384
CHUNKS_PER_DOCUMENT = 25
TOP_K = 10
PLANNER_SETTINGS = {
    "default": (),
    "seqscan_off": ("SET LOCAL enable_seqscan = off",),
    "sort_off": ("SET LOCAL enable_sort = off",),
    "seqscan_and_sort_off": ("SET LOCAL enable_seqscan = off", "SET LOCAL enable_sort = off"),
}


def _unit_vector(rng: random.Random) -> list[float]:
    values = [rng.gauss(0.0, 1.0) for _ in range(DIMENSIONS)]
    norm = math.sqrt(sum(value * value for value in values))
    return [value / norm for value in values]


def _cosine_distance(left: list[float], right: list[float]) -> float:
    return 1.0 - sum(a * b for a, b in zip(left, right, strict=True))


def _chunk_rows(document: Document, vectors: list[list[float]]) -> list[dict[str, object]]:
    rows = []
    for index, vector in enumerate(vectors):
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
                "embedding": vector,
                "embedding_provider": "sentence_transformers",
                "embedding_model": "fake-model",
                "embedding_dimensions": DIMENSIONS,
            }
        )
    return rows


async def _maintenance(engine: AsyncEngine, *statements: str) -> None:
    async with engine.connect() as conn:
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        for statement in statements:
            await conn.execute(text(statement))


async def _build_mixed_corpus(session: AsyncSession, rng: random.Random) -> tuple[object, dict]:
    """Return (staff user, {chunk_id: vector} for every chunk the staff user may read)."""
    department_a = await create_department(session, "exact-knn-a")
    department_b = await create_department(session, "exact-knn-b")
    admin = await create_user(session, "exact-knn-admin", role=UserRole.ADMIN)
    staff = await create_user(session, "exact-knn-staff", department_id=department_a.id)

    layout = [
        # (key, scope, department, uploader, status, deleted, permitted for staff)
        ("org-1", DocumentAccessScope.ORGANIZATION, None, admin, DocumentStatus.READY, False, True),
        ("org-2", DocumentAccessScope.ORGANIZATION, None, admin, DocumentStatus.READY, False, True),
        (
            "dept-a",
            DocumentAccessScope.DEPARTMENT,
            department_a,
            admin,
            DocumentStatus.READY,
            False,
            True,
        ),
        (
            "dept-b-1",
            DocumentAccessScope.DEPARTMENT,
            department_b,
            admin,
            DocumentStatus.READY,
            False,
            False,
        ),
        (
            "dept-b-2",
            DocumentAccessScope.DEPARTMENT,
            department_b,
            admin,
            DocumentStatus.READY,
            False,
            False,
        ),
        (
            "private-admin",
            DocumentAccessScope.PRIVATE,
            None,
            admin,
            DocumentStatus.READY,
            False,
            False,
        ),
        (
            "private-staff",
            DocumentAccessScope.PRIVATE,
            None,
            staff,
            DocumentStatus.READY,
            False,
            True,
        ),
        (
            "org-uploaded",
            DocumentAccessScope.ORGANIZATION,
            None,
            admin,
            DocumentStatus.UPLOADED,
            False,
            False,
        ),
        (
            "org-deleted",
            DocumentAccessScope.ORGANIZATION,
            None,
            admin,
            DocumentStatus.READY,
            True,
            False,
        ),
        (
            "dept-b-granted",
            DocumentAccessScope.DEPARTMENT,
            department_b,
            admin,
            DocumentStatus.READY,
            False,
            True,
        ),
    ]
    permitted: dict[uuid.UUID, list[float]] = {}
    for key, scope, department, uploader, status, deleted, allowed in layout:
        document = await create_document(
            session,
            f"exact-knn-{key}",
            uploader=uploader,
            access_scope=scope,
            department_id=department.id if department else None,
            status=status,
            is_deleted=deleted,
        )
        vectors = [_unit_vector(rng) for _ in range(CHUNKS_PER_DOCUMENT)]
        rows = _chunk_rows(document, vectors)
        await session.execute(insert(DocumentChunk), rows)
        await session.commit()
        if key == "dept-b-granted":
            await create_permission(
                session, "exact-knn-grant", document=document, creator=admin, user_id=staff.id
            )
        if allowed:
            permitted.update({row["id"]: row["embedding"] for row in rows})
    return staff, permitted


def _brute_force_top_k(
    query: list[float], permitted: dict, *, top_k: int, min_relevance_score: float
) -> list[uuid.UUID]:
    max_distance = 1.0 - min_relevance_score
    scored = [
        (_cosine_distance(query, vector), chunk_id)
        for chunk_id, vector in permitted.items()
        if _cosine_distance(query, vector) <= max_distance
    ]
    return [chunk_id for _, chunk_id in sorted(scored)[:top_k]]


async def _exact_search_and_plan(
    session: AsyncSession, engine: AsyncEngine, *, user, query, settings, top_k
):
    captured: list[tuple[str, object]] = []

    def capture(conn, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        if is_distance_query(statement):
            captured.append((statement, parameters))

    for setting in settings:
        await session.execute(text(setting))
    await disable_postgres_jit(session)
    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        rows = await search_permitted_chunks(
            session,
            query_vector=query,
            current_user=user,
            top_k=top_k,
            min_relevance_score=0.0,
            exact_permitted_knn=True,
        )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
    assert len(captured) == 1
    statement, parameters = captured[0]
    connection = await session.connection()
    plan = await connection.exec_driver_sql("EXPLAIN " + statement, parameters)
    return rows, "\n".join(row[0] for row in plan.all())


def test_exact_knn_matches_brute_force_and_never_plans_hnsw(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    engine: AsyncEngine = async_session_factory_for_tests.kw["bind"]
    rng = random.Random(20261031)

    async def scenario() -> None:
        await _maintenance(engine, "ALTER TABLE document_chunks SET (autovacuum_enabled = false)")
        try:
            async with async_session_factory_for_tests() as session:
                staff, permitted = await _build_mixed_corpus(session, rng)
            # Dead index entries next to the queries must not change exact results.
            queries = [_unit_vector(rng) for _ in range(5)]
            async with async_session_factory_for_tests() as session:
                dead = await create_document(
                    session,
                    "exact-knn-dead",
                    uploader=staff,
                    access_scope=DocumentAccessScope.ORGANIZATION,
                )
                near = [
                    [0.98 * q + 0.2 * r for q, r in zip(query, _unit_vector(rng), strict=True)]
                    for query in queries
                    for _ in range(12)
                ]
                await session.execute(insert(DocumentChunk), _chunk_rows(dead, near))
                await session.commit()
                await session.execute(
                    text("DELETE FROM document_chunks WHERE document_id = :id"), {"id": dead.id}
                )
                await session.commit()
            await _maintenance(engine, "ANALYZE document_chunks", "ANALYZE documents")

            for query in queries:
                expected = _brute_force_top_k(
                    query, permitted, top_k=TOP_K, min_relevance_score=0.0
                )
                for name, settings in PLANNER_SETTINGS.items():
                    async with async_session_factory_for_tests() as session:
                        rows, plan_text = await _exact_search_and_plan(
                            session,
                            engine,
                            user=staff,
                            query=query,
                            settings=settings,
                            top_k=TOP_K,
                        )
                    got = [row.chunk_id for row in rows]
                    assert HNSW_INDEX not in plan_text, name
                    assert set(got) <= set(permitted), name
                    # recall@k = 100 % against brute force, in brute-force order.
                    assert got == expected, name
        finally:
            await _clear_database_data(async_session_factory_for_tests)
            await _maintenance(
                engine,
                "ALTER TABLE document_chunks RESET (autovacuum_enabled)",
                "VACUUM ANALYZE document_chunks",
            )

    run_async(scenario())
