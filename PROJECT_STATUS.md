# Project Status

## Current phase

Phase 5 — Retrieval foundation

## Overall progress

```text
Documentation: In progress
Backend foundation: Completed
Database foundation: Completed
Authentication and RBAC: Completed
Administration APIs: Completed
Document management: Completed
Document processing pipeline: Completed
Embeddings and vector storage: Completed
Semantic retrieval: Completed
Keyword retrieval: Completed
Hybrid retrieval: Completed
Reranking: Not started
Chat: Not started
Frontend: Not started
Deployment: Partial
```

## Completed

- TASK-001 completed.
- TASK-002 completed.
- TASK-003 completed.
- TASK-004 completed.
- TASK-005 completed.
- TASK-006 completed.
- TASK-007 completed.
- TASK-008 completed.
- TASK-009 completed.
- TASK-010 completed.
- TASK-011 completed.
- TASK-012 completed.
- TASK-013 completed.
- TASK-014 completed.
- TASK-015 completed.
- TASK-016 completed.
- TASK-017 completed.
- Authentication and refresh-token rotation.
- RBAC dependencies and core policies.
- User and Department administration APIs.
- Document data model, upload, listing, detail, status, download, update, soft delete, and direct grants.
- Celery worker foundation with Redis broker/result backend, Document queue, worker ping, atomic claim, and bounded retry helpers.
- PyMuPDF PDF text extraction.
- Page-aware token chunking with overlap, page metadata, and deterministic checksums.
- EmbeddingProvider abstraction and local Sentence Transformers provider.
- DocumentChunk model, pgvector extension, and HNSW cosine index.
- Atomic chunk persistence.
- Upload auto enqueue after database commit.
- End-to-end Celery document processing.
- Extraction, chunking, embedding, and chunk/vector persistence pipeline.
- READY and FAILED transitions.
- Retry and idempotency behavior.
- Real Celery pipeline tests.
- Query embedding for retrieval.
- Permission-aware semantic retrieval.
- READY-only vector search.
- Top-k controls.
- Relevance threshold.
- Stable RetrievalHit models.
- Permission leakage tests.
- Real Vietnamese semantic-retrieval tests.
- PostgreSQL full-text keyword retrieval.
- GIN full-text index for DocumentChunk text.
- Permission-aware keyword retrieval.
- Exact-code search tests.
- Weighted Reciprocal Rank Fusion.
- Semantic and keyword candidate deduplication.
- Hybrid permission leakage tests.
- Real Vietnamese hybrid-retrieval tests.

## Current task

TASK-018 — Chat data model and APIs

## Files changed in latest task

- `app/core/config.py`
- `.env.example`
- `app/models/document_chunk.py`
- `app/retrieval/__init__.py`
- `app/retrieval/base.py`
- `app/retrieval/errors.py`
- `app/retrieval/models.py`
- `app/retrieval/query_validation.py`
- `app/retrieval/semantic_service.py`
- `app/retrieval/keyword_repository.py`
- `app/retrieval/keyword_service.py`
- `app/retrieval/fusion.py`
- `app/retrieval/hybrid_service.py`
- `app/retrieval/factory.py`
- `app/db/migrations/versions/20260718_0006_add_document_chunk_full_text_index.py`
- `pyproject.toml`
- `tests/unit/test_retrieval_configuration.py`
- `tests/unit/test_keyword_retrieval_models.py`
- `tests/unit/test_hybrid_retrieval_models.py`
- `tests/unit/test_rrf_fusion.py`
- `tests/unit/test_keyword_retrieval_service.py`
- `tests/unit/test_hybrid_retrieval_service.py`
- `tests/integration/test_full_text_index_migration.py`
- `tests/integration/test_keyword_retrieval_repository.py`
- `tests/integration/test_permission_aware_keyword_retrieval.py`
- `tests/integration/test_hybrid_retrieval.py`
- `tests/integration/test_real_hybrid_retrieval.py`
- `ARCHITECTURE.md`
- `DATABASE_DESIGN.md`
- `RAG_DESIGN.md`
- `SECURITY.md`
- `ENVIRONMENT_VARIABLES.md`
- `SETUP.md`
- `PROJECT_STATUS.md`
- `TASKS.md`
- `CHANGELOG.md`

## How to test

```powershell
docker compose up -d postgres redis
alembic upgrade head
python -m pytest -v
python -m pytest -m integration -v
python -m pytest -m celery_integration -v
python -m pytest -m embedding_model_integration -v
python -m pytest -m processing_pipeline_model_integration -v
python -m pytest -m processing_pipeline_celery_integration -v
python -m pytest -m semantic_retrieval_model_integration -v
python -m pytest -m hybrid_retrieval_model_integration -v
python -m ruff check .
python -m ruff format --check .
```

## Known limitations

- Retrieval has no public API.
- No reranking.
- No context assembly.
- No Chat API.
- No conversation history.
- No citations response.
- No frontend React implementation.
- Keyword search is accent-sensitive.
- No typo or fuzzy keyword search.
- No retrieval audit event.
- No retrieval-specific rate limiting.
- Broker enqueue is not backed by a transactional outbox; broker failure can leave a committed Document in `UPLOADED` until manually enqueued.
- No worker container in Compose.
