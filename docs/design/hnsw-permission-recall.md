# Design: exact KNN over permitted chunks (HNSW post-filter recall)

Status: **PROPOSED, design only.** No code yet. Any implementation follows
`.claude/skills/eaka-rag-change-guard` (flag-gated, old behaviour by default).
Date: 2026-10-31. Evidence: `artifacts/prompt3d/hnsw-report.md` (local, git-ignored),
`tests/integration/test_semantic_retrieval_hnsw_recall.py`.

## 1. Problem

`search_permitted_chunks` (`app/retrieval/semantic_repository.py:48-104`) runs one statement:
the status filter, `build_accessible_document_filter`, the threshold `cosine_distance <= 1 - min`,
`ORDER BY cosine_distance, authority, ...` and `LIMIT top_k`. When the planner picks
`Index Scan using ix_document_chunks_embedding_hnsw_cosine`, pgvector hands back about
`hnsw.ef_search` (40) nearest index elements, and the permission join and heap visibility check
run afterwards. If more than 40 nearer elements belong to chunks the user cannot see, or to
deleted chunks that are not vacuumed yet, every permitted chunk is lost. This loses recall; it
does not leak, because nothing unauthorized is returned.

Measured locally (pgvector 0.8.6):
- `iterative_scan` (relaxed or strict) did not recover the permitted chunk on synthetic data.
- `ef_search >= 100` recovered it only because the planner stopped using HNSW.

## 2. Proposal

Do an exact nearest-neighbour search over the chunks the user may read: apply the permission and
status filter first (documents table, btree indexes), then compute the distance for every
permitted chunk and keep the top `k`.

### 2.1 Query

```sql
SELECT s.*
FROM (
    SELECT dc.id AS chunk_id, dc.document_id, d.title AS document_title, dc.chunk_index,
           dc.text, dc.page_numbers, dc.start_page, dc.end_page, dc.token_count,
           dc.embedding <=> :query_vector AS cosine_distance,
           <authority expression> AS authority_rank
    FROM document_chunks AS dc
    JOIN documents AS d ON d.id = dc.document_id
    WHERE d.status = 'READY'
      AND <build_accessible_document_filter(current_user)>
    OFFSET 0                      -- optimization fence, see 2.2
) AS s
WHERE s.cosine_distance <= :max_cosine_distance
ORDER BY s.cosine_distance, s.authority_rank DESC, s.document_id, s.chunk_index, s.chunk_id
LIMIT :top_k
```

- The permission predicate is the same `build_accessible_document_filter` and still sits inside
  the statement, so it applies before any ranking, prompt or citation step. It is not a new
  filter. The future classification filter (PROMPT 7) goes into that same function.
- The result columns, threshold semantics and tie-break order match the current query, so
  `RetrievalRow` and every caller stay unchanged.
- `relevance_score = 1 - cosine_distance` is computed in Python or in the outer select, as today.

### 2.2 Keeping the planner off the HNSW post-filter path

- pgvector uses the HNSW index only for an ordering scan (`ORDER BY embedding <=> const LIMIT`).
  The subquery has no `ORDER BY`, and `OFFSET 0` stops PostgreSQL from flattening it into the
  outer query. The outer `ORDER BY` therefore applies to the subquery's output and cannot become
  an index-ordered scan of `document_chunks`. The plan has to be a scan of the permitted rows plus
  a top-N heapsort. Rows stream through the scan, so unlike a `MATERIALIZED` CTE nothing is
  materialized.
- `MATERIALIZED` CTE alternative: the same fence. It is rejected because it would materialize
  384-dim vectors (about 1.5 KB per row).
- Rejected options:
  - `SET LOCAL enable_indexscan = off`: lasts for the whole request transaction and disables
    useful btree indexes.
  - Ordering by `(embedding <=> q) + 0`: works by accident of expression matching and is easy to
    "clean up" later.
  - Relying on `ef_search` or iterative scan alone: see section 1.
- Checked on a throwaway pgvector 0.8.6 container, with 20k synthetic chunks and an HNSW index,
  2026-10-31.
  - The current statement shape used `Index Scan using <hnsw>` under the default planner and
    under `enable_seqscan`/`enable_sort` off.
  - The `OFFSET 0` shape never used HNSW under default, `enable_seqscan=off`, `enable_sort=off`,
    or both. With seqscan off it chose the btree path: `docs_pkey`, then
    `Bitmap Index Scan on chunks(doc_id)`, then `Sort`.
  - This was not repeated on 0.8.7 or with the real schema.
- Guard test (CI): run EXPLAIN on the new statement under the default settings, under
  `enable_seqscan=off`, under `enable_sort=off`, and under both. Assert the plan never contains
  `ix_document_chunks_embedding_hnsw_cosine`. It must stay green on pgvector 0.8.6 and 0.8.7.
  The pgvector image pin is a separate TASKS item.

### 2.3 Flag

| Name | Type | Default | Meaning |
|---|---|---|---|
| `RAG_SEMANTIC_EXACT_PERMITTED_KNN_ENABLED` | bool | `false` | `true`: exact KNN query above. `false`: current statement. |

Add it to `Settings`, `ENVIRONMENT_VARIABLES.md` and `.env.example`, with a reference to this
design. The repository chooses the statement. No API, schema or migration change.

## 3. Benchmark plan (latency)

Run on a throwaway stack only (tmpfs, own project). Never use V2, AUTH-02 or the main stack.

- **Data:** synthetic, normalized 384-dim vectors. Two shapes: uniform random, and clustered (50
  centroids) to mimic topical corpora.
- **Total chunks:** 1k, 10k, 50k, 100k.
- **Permitted fraction for the test user:** 5 %, 50 %, 100 %. The non-permitted chunks sit in a
  DEPARTMENT document of another department; in the 5 % case they cluster near the queries (the
  worst case for HNSW post-filter).
- **Queries:** 50 per cell, after warm-up. `top_k = 40`, the hybrid semantic candidate count, and
  `top_k = 10`.
- **Metrics:** p50/p95/max wall time of the statement; EXPLAIN (ANALYZE, BUFFERS) for one query
  per cell; shared/temp buffers; recall@k against brute force (section 4). Compare the old
  statement (HNSW allowed, default planner) with the new one.
- **Versions:** PostgreSQL 17.11 with pgvector 0.8.6 and 0.8.7; default `work_mem`.
- **Output:** a table per cell under `artifacts/<task>/hnsw-exact-knn-benchmark/`, with the
  script committed under `scripts/` and the raw JSON kept with the artifacts.

Expected cost: exact KNN is linear in the number of permitted chunks. The current corpus has 143
chunks, where exact KNN is already what the planner does today (see the PROMPT 3d baseline
EXPLAIN). The latency budget is proposed below and must be approved before the default changes.

## 4. Acceptance criteria

1. **Recall:** with the flag on, recall@k = 100 % against brute force in every benchmark cell.
   Brute force means NumPy cosine over all permitted, READY, non-deleted chunks, with the same
   threshold and tie-break order, comparing ordered chunk IDs.
2. **xfail tests:** today `test_semantic_retrieval_hnsw_recall.py` requires an HNSW plan; if the
   plan has no HNSW it raises `RuntimeError` on purpose. Under the new query it would therefore
   report FAILED, not XPASS. Proposed change, made in the implementation task:
   - Flag off: keep both cases as `xfail(strict)` with the HNSW precondition. They document the
     old path.
   - Flag on: the same two scenarios (more than 40 nearer unauthorized chunks; nearer dead
     tuples), with the same forced planner settings, must return the permitted chunk, and EXPLAIN
     must show no HNSW index. These are plain passing tests.
   - When the default flips and the old path is removed, delete the flag-off xfail cases. This is
     the "xfail -> remove xfail" step.
3. **Safety:** `permission_leak_count = 0`. The whole permission suite passes (`tests/api`
   integration, `tests/integration` permission and retrieval files, citation revalidation).
4. **Quality:** Q001-Q100 with the flag on shows no regression beyond run-to-run noise, measured
   as in PROMPT 3d (2 runs before, 2 after, groups (a)/(b)). Group (b) is graded by a person. No
   held-out set exists, so generalization stays NOT_VERIFIED until one is built.
5. **Latency (proposal, to approve):** p95 of the statement at most 150 ms at 50k permitted
   chunks, and at most 2x the old statement at 10k, on the reference machine. If this fails, keep
   the default off and go to section 6.
6. **Plan guard** from 2.2 green in CI.

## 5. Rollback

- Set `RAG_SEMANTIC_EXACT_PERMITTED_KNN_ENABLED=false` and restart API/worker. No data, schema or
  index change is involved, so rollback is immediate and lossless.
- The old statement stays in the code until the default has been on for one release with the
  benchmark and UAT evidence above.

## 6. Later optimizations

- **Partial HNSW indexes per access partition.** Denormalize the document's access attributes
  onto `document_chunks` (`access_scope`, `department_id`, and after PROMPT 7
  `classification`), kept in sync by ingestion and by document permission or scope updates.
  Then build partial HNSW indexes per partition (for example
  `WHERE access_scope = 'ORGANIZATION' AND classification <= 'INTERNAL'`). The query runs one
  ordered index scan per partition the user may read, all of whose rows are permitted, merges the
  results and applies LIMIT. Post-filter cannot lose recall there, because every index element in
  a partition is readable. Direct grants (`document_permissions`) stay on the exact path, since
  they are per-user.
- **PROMPT 7 (ADR `docs/adr/0003-document-classification.md`).** Classification must be part of
  `build_accessible_document_filter`, which this design already uses, and is the natural
  partition key above. That ADR should state whether direct grants can exceed classification,
  because this decides which partitions a grant can open.
- **Revisit `hnsw.iterative_scan`** with real `multilingual-e5-small` embeddings and pgvector
  0.8.7+. It failed on synthetic orthogonal data, but that is not evidence about real data.
- **Vacuum hygiene:** exact KNN does not depend on dead index entries. If partial HNSW is adopted,
  autovacuum settings for `document_chunks` need review, because reprocessing deletes and
  re-inserts chunks.
