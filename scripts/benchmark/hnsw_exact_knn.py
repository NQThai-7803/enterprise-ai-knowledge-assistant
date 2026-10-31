"""Benchmark the default semantic statement against exact KNN over permitted chunks.

docs/design/hnsw-permission-recall.md, section 3. Throwaway database only: the script truncates
the retrieval tables. It refuses to run unless BENCHMARK_ALLOW_TRUNCATE=yes and the database URL
host is not localhost-published production-looking.

Grid: total chunks x permitted fraction x top_k. Vectors are clustered (50 centroids), queries are
drawn near the same centroids, so with a small permitted fraction most nearest neighbours are
unauthorized (the HNSW post-filter worst case). For every cell: p50/p95/max wall time of each
statement, recall@k of each statement against a NumPy brute force over the permitted chunks, and
one EXPLAIN (ANALYZE) per statement.

usage (inside the backend test image, DATABASE_URL pointing at a throwaway pgvector database):
  BENCHMARK_ALLOW_TRUNCATE=yes python scripts/benchmark/hnsw_exact_knn.py /out/benchmark.json
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
import uuid

import numpy as np
from sqlalchemy import event, insert, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.base import Base
from app.models import (
    Department,
    Document,
    DocumentAccessScope,
    DocumentChunk,
    DocumentStatus,
    User,
    UserRole,
)
from app.retrieval.semantic_repository import search_permitted_chunks

SIZES = tuple(
    int(s) for s in os.environ.get("BENCHMARK_SIZES", "1000,10000,50000,100000").split(",")
)
FRACTIONS = (0.05, 0.5, 1.0)
TOP_KS = (40, 10)
QUERIES = int(os.environ.get("BENCHMARK_QUERIES", "50"))
DOCUMENTS = 100
DIMENSIONS = 384
CENTROIDS = 50
HNSW_INDEX = "ix_document_chunks_embedding_hnsw_cosine"
CREATE_HNSW = (
    f"CREATE INDEX {HNSW_INDEX} ON document_chunks USING hnsw (embedding vector_cosine_ops)"
)


def _normalize(matrix: np.ndarray) -> np.ndarray:
    return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def _vector_literal(row: np.ndarray) -> list[float]:
    return [float(x) for x in row]


async def _execute(engine, *statements: str, autocommit: bool = False) -> None:
    async with engine.connect() as conn:
        if autocommit:
            conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        for statement in statements:
            await conn.execute(text(statement))
        if not autocommit:
            await conn.commit()


async def _load(factory, engine, *, size: int, rng: np.random.Generator):
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    await _execute(engine, f"TRUNCATE {tables} RESTART IDENTITY CASCADE")
    await _execute(engine, f"DROP INDEX IF EXISTS {HNSW_INDEX}")
    centroids = _normalize(rng.normal(size=(CENTROIDS, DIMENSIONS)))
    assignment = rng.integers(0, CENTROIDS, size=size)
    vectors = _normalize(centroids[assignment] + 0.35 * rng.normal(size=(size, DIMENSIONS))).astype(
        np.float32
    )
    async with factory() as session:
        dept_a = Department(id=uuid.uuid4(), name="Bench A", code="BENCH-A")
        dept_b = Department(id=uuid.uuid4(), name="Bench B", code="BENCH-B")
        session.add_all([dept_a, dept_b])
        await session.flush()
        admin = User(
            id=uuid.uuid4(),
            email="bench-admin@bench.example.com",
            full_name="Bench Admin",
            hashed_password="x",
            role=UserRole.ADMIN,
            is_active=True,
        )
        staff = User(
            id=uuid.uuid4(),
            email="bench-staff@bench.example.com",
            full_name="Bench Staff",
            hashed_password="x",
            role=UserRole.STAFF,
            department_id=dept_a.id,
            is_active=True,
        )
        session.add_all([admin, staff])
        await session.flush()
        documents = []
        for index in range(DOCUMENTS):
            documents.append(
                Document(
                    id=uuid.uuid4(),
                    title=f"Bench {index}",
                    description="bench",
                    original_filename=f"bench-{index}.pdf",
                    storage_key=f"bench/{index}.pdf",
                    mime_type="application/pdf",
                    file_size=1,
                    checksum_sha256=f"{index:064d}",
                    status=DocumentStatus.READY,
                    access_scope=DocumentAccessScope.DEPARTMENT,
                    department_id=dept_b.id,
                    uploaded_by=admin.id,
                    is_deleted=False,
                )
            )
        session.add_all(documents)
        await session.commit()
        document_ids = [d.id for d in documents]
        staff_id, dept_b_id = staff.id, dept_b.id
    chunk_document = np.arange(size) % DOCUMENTS
    ids = [uuid.uuid4() for _ in range(size)]
    started = time.perf_counter()
    async with factory() as session:
        # Build rows per batch so Python float lists never exist for the whole corpus at once.
        for start in range(0, size, 5000):
            batch = [
                {
                    "id": ids[index],
                    "document_id": document_ids[chunk_document[index]],
                    "chunk_index": index // DOCUMENTS,
                    "text": f"bench chunk {index}",
                    "token_count": 3,
                    "character_count": 18,
                    "page_numbers": [1],
                    "start_page": 1,
                    "end_page": 1,
                    "overlap_token_count": 0,
                    "content_sha256": f"{index:064x}"[-64:],
                    "embedding": _vector_literal(vectors[index]),
                    "embedding_provider": "sentence_transformers",
                    "embedding_model": "bench",
                    "embedding_dimensions": DIMENSIONS,
                }
                for index in range(start, min(start + 5000, size))
            ]
            await session.execute(insert(DocumentChunk), batch)
        await session.commit()
    load_s = time.perf_counter() - started
    started = time.perf_counter()
    # No parallel build: parallel workers need dynamic shared memory, and container /dev/shm is
    # small (64 MB by default).
    await _execute(
        engine,
        "SET maintenance_work_mem = '128MB'",
        "SET max_parallel_maintenance_workers = 0",
        CREATE_HNSW,
    )
    index_s = time.perf_counter() - started
    await _execute(
        engine, "VACUUM ANALYZE document_chunks", "VACUUM ANALYZE documents", autocommit=True
    )
    queries = _normalize(
        centroids[rng.integers(0, CENTROIDS, size=QUERIES)]
        + 0.35 * rng.normal(size=(QUERIES, DIMENSIONS))
    )
    return {
        "vectors": vectors,
        "chunk_document": chunk_document,
        "ids": ids,
        "document_ids": document_ids,
        "staff_id": staff_id,
        "dept_b_id": dept_b_id,
        "queries": queries,
        "load_s": round(load_s, 1),
        "index_s": round(index_s, 1),
    }


async def _set_permitted(engine, data, fraction: float) -> np.ndarray:
    permitted_documents = int(round(DOCUMENTS * fraction))
    org = [str(d) for d in data["document_ids"][:permitted_documents]]
    await _execute(
        engine,
        f"UPDATE documents SET access_scope = 'DEPARTMENT', department_id = '{data['dept_b_id']}'",
    )
    if org:
        # ORGANIZATION documents carry no department (ck_documents_access_scope_department).
        await _execute(
            engine,
            "UPDATE documents SET access_scope = 'ORGANIZATION', department_id = NULL "
            "WHERE id IN (" + ",".join(f"'{d}'" for d in org) + ")",
        )
    await _execute(engine, "ANALYZE documents", autocommit=True)
    return data["chunk_document"] < permitted_documents


def _brute_force(data, permitted_mask: np.ndarray, query: np.ndarray, top_k: int) -> list:
    indexes = np.nonzero(permitted_mask)[0]
    distances = 1.0 - data["vectors"][indexes] @ query
    keep = distances <= 1.0
    indexes, distances = indexes[keep], distances[keep]
    order = np.argsort(distances, kind="stable")[:top_k]
    return [data["ids"][i] for i in indexes[order]]


async def _run_cell(factory, engine, data, staff, permitted_mask, top_k: int, exact: bool):
    latencies, recalls = [], []
    captured: list = []

    def capture(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        if "<=>" in statement and not captured:
            captured.append((statement, parameters))

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        for query in data["queries"]:
            async with factory() as session:
                started = time.perf_counter()
                rows = await search_permitted_chunks(
                    session,
                    query_vector=_vector_literal(query),
                    current_user=staff,
                    top_k=top_k,
                    min_relevance_score=0.0,
                    exact_permitted_knn=exact,
                )
                latencies.append((time.perf_counter() - started) * 1000)
            expected = _brute_force(data, permitted_mask, query, top_k)
            got = [row.chunk_id for row in rows]
            recalls.append(len(set(got) & set(expected)) / len(expected) if expected else 1.0)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
    statement, parameters = captured[0]
    async with engine.connect() as conn:
        plan = await conn.exec_driver_sql("EXPLAIN (ANALYZE) " + statement, parameters)
        plan_lines = [row[0] for row in plan.all()]
    ordered = sorted(latencies)
    return {
        "p50_ms": round(statistics.median(ordered), 2),
        "p95_ms": round(ordered[max(0, int(len(ordered) * 0.95) - 1)], 2),
        "max_ms": round(ordered[-1], 2),
        "recall_mean": round(statistics.mean(recalls), 4),
        "recall_min": round(min(recalls), 4),
        "plan_uses_hnsw": any(HNSW_INDEX in line for line in plan_lines),
        "explain_execution": next(
            (line for line in plan_lines if line.startswith("Execution Time")), None
        ),
    }


async def main() -> None:
    if os.environ.get("BENCHMARK_ALLOW_TRUNCATE") != "yes":
        raise SystemExit("Set BENCHMARK_ALLOW_TRUNCATE=yes; this truncates the retrieval tables.")
    url = os.environ["DATABASE_URL"]
    if "production" in url.lower():
        raise SystemExit("Refusing a production-looking DATABASE_URL.")
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    rng = np.random.default_rng(20261031)
    async with engine.connect() as conn:
        pgvector = (
            await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'"))
        ).scalar_one()
        server = (await conn.execute(text("SHOW server_version"))).scalar_one()
    results = {
        "pgvector": pgvector,
        "server_version": server,
        "queries_per_cell": QUERIES,
        "cells": [],
    }
    for size in SIZES:
        data = await _load(factory, engine, size=size, rng=rng)
        async with factory() as session:
            staff = await session.get(User, data["staff_id"])
        for fraction in FRACTIONS:
            mask = await _set_permitted(engine, data, fraction)
            for top_k in TOP_KS:
                cell = {
                    "chunks": size,
                    "permitted_fraction": fraction,
                    "top_k": top_k,
                    "load_s": data["load_s"],
                    "index_s": data["index_s"],
                }
                for name, exact in (("default", False), ("exact", True)):
                    cell[name] = await _run_cell(factory, engine, data, staff, mask, top_k, exact)
                results["cells"].append(cell)
                print(
                    json.dumps(
                        {k: cell[k] for k in ("chunks", "permitted_fraction", "top_k")}
                        | {
                            n: {
                                k: cell[n][k]
                                for k in ("p50_ms", "p95_ms", "recall_min", "plan_uses_hnsw")
                            }
                            for n in ("default", "exact")
                        }
                    ),
                    flush=True,
                )
    await engine.dispose()
    with open(sys.argv[1], "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=1)


if __name__ == "__main__":
    asyncio.run(main())
