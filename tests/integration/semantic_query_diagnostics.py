"""Diagnostics for intermittent semantic retrieval failures on CI.

The fixture records every pgvector distance query a test runs. After the test, it replays each
query with EXPLAIN (ANALYZE, BUFFERS), counts the rows the same query returns under a few planner
and HNSW settings, and reads the chunk table statistics. Each record is appended to a JSON Lines
file. When the test failed, the record is also printed to the terminal so it lands in the CI log.

This only observes. It never changes the settings of the query the test itself runs.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

DIAGNOSTICS_PATH_ENV = "EAKA_SEMANTIC_DIAGNOSTICS_PATH"
DEFAULT_DIAGNOSTICS_PATH = Path("logs") / "semantic-retrieval-diagnostics.jsonl"
MAX_QUERIES_PER_TEST = 3

# Each variant replays the recorded query in its own rolled-back transaction.
ROW_COUNT_VARIANTS: dict[str, tuple[str, ...]] = {
    "as_run": (),
    "no_index_scan": ("SET LOCAL enable_indexscan = off", "SET LOCAL enable_bitmapscan = off"),
    "ef_search_1000": ("SET LOCAL hnsw.ef_search = 1000",),
    "iterative_relaxed": ("SET LOCAL hnsw.iterative_scan = relaxed_order",),
}

TABLE_STATS_SQL = (
    "SELECT relname, n_live_tup, n_dead_tup, n_mod_since_analyze, n_ins_since_vacuum, "
    "last_autovacuum, last_autoanalyze, autovacuum_count, autoanalyze_count "
    "FROM pg_stat_user_tables WHERE relname IN ('document_chunks', 'documents') ORDER BY relname"
)
SETTINGS_SQL = (
    "SELECT current_setting('hnsw.ef_search', true), "
    "current_setting('hnsw.iterative_scan', true), "
    "(SELECT extversion FROM pg_extension WHERE extname = 'vector'), "
    "current_setting('server_version'), "
    "current_setting('autovacuum'), "
    "current_setting('autovacuum_naptime'), "
    "pg_relation_size('ix_document_chunks_embedding_hnsw_cosine'), "
    "(SELECT count(*) FROM document_chunks)"
)
SETTINGS_KEYS = (
    "hnsw.ef_search",
    "hnsw.iterative_scan",
    "vector_extversion",
    "server_version",
    "autovacuum",
    "autovacuum_naptime",
    "hnsw_index_bytes",
    "visible_chunk_rows",
)


def is_distance_query(statement: str) -> bool:
    return "document_chunks" in statement and "<=>" in statement


_FAILED_PHASES = pytest.StashKey[set[str]]()


def record_failed_phases(item: pytest.Item, report: pytest.TestReport) -> None:
    if report.failed:
        item.stash.setdefault(_FAILED_PHASES, set()).add(report.when)


@pytest.fixture
def semantic_query_diagnostics(
    request: pytest.FixtureRequest,
    clean_database_data: None,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> Iterator[None]:
    # Depending on clean_database_data makes this teardown run before the data is deleted.
    engine: AsyncEngine = async_session_factory_for_tests.kw["bind"]
    captured: list[tuple[str, Any]] = []

    def capture(conn, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        if is_distance_query(statement) and len(captured) < MAX_QUERIES_PER_TEST:
            captured.append((statement, parameters))

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        yield
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)

    if not captured:
        return
    failed = bool(request.node.stash.get(_FAILED_PHASES, set()))
    try:
        record = asyncio.run(_collect(engine, captured))
    except Exception as exc:  # noqa: BLE001 - diagnostics must never change the test outcome
        record = {"collection_error": f"{type(exc).__name__}: {exc}"}
    record = {
        "test": request.node.nodeid,
        "outcome": "failed" if failed else "passed",
        "collected_at": datetime.now(UTC).isoformat(),
        **record,
    }
    _write(record)
    if failed:
        _print_to_terminal(request.config, record)


async def _collect(engine: AsyncEngine, captured: list[tuple[str, Any]]) -> dict[str, Any]:
    queries = []
    for statement, parameters in captured:
        query: dict[str, Any] = {"row_counts": {}}
        async with engine.connect() as conn:
            for name, settings in ROW_COUNT_VARIANTS.items():
                query["row_counts"][name] = await _row_count(conn, statement, parameters, settings)
            plan = await _in_rolled_back_transaction(
                conn,
                ("SET LOCAL jit = off",),
                "EXPLAIN (ANALYZE, BUFFERS) " + statement,
                parameters,
            )
            query["explain_analyze"] = [row[0] for row in plan]
        queries.append(query)

    async with engine.connect() as conn:
        stats = await _in_rolled_back_transaction(conn, (), TABLE_STATS_SQL, ())
        settings = await _in_rolled_back_transaction(conn, (), SETTINGS_SQL, ())
    return {
        "queries": queries,
        "table_stats": [_stats_row(row) for row in stats],
        "settings": dict(zip(SETTINGS_KEYS, (_plain(value) for value in settings[0]), strict=True)),
    }


async def _row_count(
    conn,  # noqa: ANN001
    statement: str,
    parameters: Any,
    settings: tuple[str, ...],
) -> int | str:
    try:
        rows = await _in_rolled_back_transaction(
            conn, ("SET LOCAL jit = off", *settings), statement, parameters
        )
    except Exception as exc:  # noqa: BLE001 - an unknown GUC on an older pgvector is a result
        return f"{type(exc).__name__}: {exc}"
    return len(rows)


async def _in_rolled_back_transaction(
    conn,  # noqa: ANN001
    settings: tuple[str, ...],
    statement: str,
    parameters: Any,
) -> list[Any]:
    transaction = await conn.begin()
    try:
        for setting in settings:
            await conn.exec_driver_sql(setting)
        result = await conn.exec_driver_sql(statement, parameters)
        return list(result.all())
    finally:
        await transaction.rollback()


def _stats_row(row: Any) -> dict[str, Any]:
    return {key: _plain(value) for key, value in row._mapping.items()}


def _plain(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _write(record: dict[str, Any]) -> None:
    configured = os.environ.get(DIAGNOSTICS_PATH_ENV)
    path = Path(configured) if configured else DEFAULT_DIAGNOSTICS_PATH
    if not configured and not path.parent.is_dir():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _print_to_terminal(config: pytest.Config, record: dict[str, Any]) -> None:
    lines = [f"\n=== semantic retrieval diagnostics: {record['test']} ==="]
    lines.append(json.dumps({k: v for k, v in record.items() if k != "queries"}, indent=2))
    for index, query in enumerate(record.get("queries", ())):
        lines.append(f"--- query {index}: row counts {json.dumps(query['row_counts'])}")
        lines.extend(query["explain_analyze"])
    capture = config.pluginmanager.getplugin("capturemanager")
    if capture is None:
        sys.stderr.write("\n".join(lines) + "\n")
        return
    with capture.global_and_fixture_disabled():
        sys.stderr.write("\n".join(lines) + "\n")
