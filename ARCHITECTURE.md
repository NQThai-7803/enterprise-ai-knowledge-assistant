# System Architecture

## 1. Kiáº¿n trÃºc tá»•ng thá»ƒ

```text
Web Client
    |
    v
FastAPI Application
    â”œâ”€â”€ Auth Module
    â”œâ”€â”€ User & Department Module
    â”œâ”€â”€ Document Module
    â”œâ”€â”€ Chat Module
    â”œâ”€â”€ Retrieval Module
    â”œâ”€â”€ Feedback Module
    â””â”€â”€ Audit Module
          |
          +--> PostgreSQL + pgvector
          +--> Redis
          +--> Celery Worker
          +--> File Storage
          +--> Embedding Provider
          +--> LLM Provider
```

## 2. Kiáº¿n trÃºc backend

```text
app/
â”œâ”€â”€ api/
â”‚   â”œâ”€â”€ dependencies.py
â”‚   â””â”€â”€ v1/
â”‚       â”œâ”€â”€ auth.py
â”‚       â”œâ”€â”€ users.py
â”‚       â”œâ”€â”€ departments.py
â”‚       â”œâ”€â”€ documents.py
â”‚       â”œâ”€â”€ chat.py
â”‚       â”œâ”€â”€ feedback.py
â”‚       â””â”€â”€ audit_logs.py
â”œâ”€â”€ core/
â”‚   â”œâ”€â”€ config.py
â”‚   â”œâ”€â”€ security.py
â”‚   â”œâ”€â”€ logging.py
â”‚   â””â”€â”€ exceptions.py
â”œâ”€â”€ db/
â”‚   â”œâ”€â”€ base.py
â”‚   â”œâ”€â”€ session.py
â”‚   â””â”€â”€ migrations/
â”œâ”€â”€ models/
â”œâ”€â”€ schemas/
â”œâ”€â”€ repositories/
â”œâ”€â”€ services/
â”œâ”€â”€ rag/
â”‚   â”œâ”€â”€ chunking.py
â”‚   â”œâ”€â”€ embeddings.py
â”‚   â”œâ”€â”€ retrieval.py
â”‚   â”œâ”€â”€ reranking.py
â”‚   â”œâ”€â”€ prompts.py
â”‚   â””â”€â”€ citations.py
â”œâ”€â”€ workers/
â”‚   â”œâ”€â”€ celery_app.py
â”‚   â””â”€â”€ document_tasks.py
â”œâ”€â”€ storage/
â”œâ”€â”€ tests/
â””â”€â”€ main.py
```

## 3. Layer responsibilities

### API layer

- Nháº­n request.
- Validate dá»¯ liá»‡u báº±ng schema.
- Gá»i service.
- Chuyá»ƒn exception thÃ nh HTTP response.
- KhÃ´ng chá»©a truy váº¥n database phá»©c táº¡p.

### Service layer

- Chá»©a business logic.
- Äiá»u phá»‘i repository, storage, RAG vÃ  audit.
- Quáº£n lÃ½ transaction khi cáº§n.

### Repository layer

- Truy váº¥n database.
- KhÃ´ng chá»©a logic HTTP.
- Ãp dá»¥ng filter permission á»Ÿ query phÃ¹ há»£p.

### RAG layer

- Chunking.
- Embedding.
- Retrieval.
- Reranking.
- Prompt building.
- Citation validation.

### Worker layer

- Xá»­ lÃ½ document báº¥t Ä‘á»“ng bá»™.
- Retry cÃ³ kiá»ƒm soÃ¡t.
- Cáº­p nháº­t tráº¡ng thÃ¡i vÃ  error message.

## 4. Dependency rules

```text
API â†’ Service â†’ Repository â†’ Database
               â†˜ RAG Provider
               â†˜ Storage Provider
               â†˜ Audit Service
```

KhÃ´ng cho phÃ©p:

- Model import router.
- Repository gá»i HTTP response.
- RAG module truy cáº­p global user mÃ  khÃ´ng truyá»n permission scope.
- Router gá»i trá»±c tiáº¿p Celery hoáº·c database ngoÃ i service.

## 5. Provider abstractions

NÃªn táº¡o interface hoáº·c protocol cho:

- `EmbeddingProvider`
- `LLMProvider`
- `FileStorage`
- `TextExtractor`
- `Reranker`

Má»¥c tiÃªu lÃ  cÃ³ thá»ƒ thay provider mÃ  khÃ´ng sá»­a toÃ n bá»™ há»‡ thá»‘ng.

## 6. Async strategy

- FastAPI endpoint dÃ¹ng async khi thao tÃ¡c I/O phÃ¹ há»£p.
- Document processing cháº¡y báº±ng Celery worker.
- KhÃ´ng gá»i OCR hoáº·c embedding hÃ ng loáº¡t trá»±c tiáº¿p trong request upload.

## 7. Error handling

Error response thá»‘ng nháº¥t:

```json
{
  "error": {
    "code": "DOCUMENT_NOT_READY",
    "message": "Document is not ready for search.",
    "details": null,
    "request_id": "..."
  }
}
```

## 8. TASK-011 worker foundation

Implemented asynchronous processing foundation:

```text
FastAPI producer
    -> Redis broker
    -> Celery worker
    -> PostgreSQL
```

- Celery application name: `enterprise_ai`.
- Redis broker is configured by `CELERY_BROKER_URL`.
- Redis result backend is configured by `CELERY_RESULT_BACKEND` and stores only temporary task metadata.
- Document processing tasks are routed to the `documents` queue.
- Worker connectivity task `system.worker_ping` uses the default queue.
- Document task arguments contain only the Document UUID string.
- Worker database access uses a worker-specific async SQLAlchemy engine/session with `NullPool`.
- PostgreSQL remains the source of truth for Document processing status.
- TASK-011 does not implement PDF extraction, chunking, embeddings, or READY transition.
- Upload does not automatically enqueue Document processing in TASK-011.
## 9. TASK-012 PDF extraction foundation

Implemented PDF extraction flow:

```text
FileStorage
    -> bounded PDF bytes
    -> TextExtractor
    -> PyMuPDFTextExtractor
    -> ExtractionResult
```

- `TextExtractor` is a provider abstraction and does not depend on FastAPI, Celery, SQLAlchemy, or Document ORM models.
- `PyMuPDFTextExtractor` extracts plain text page by page from bounded PDF bytes.
- Page numbers in `ExtractionResult` are 1-based.
- Blank pages are preserved as empty `ExtractedPage` entries.
- Extracted text is normalized per page and held only in the in-memory result.
- Extracted text is not persisted to PostgreSQL or Redis in TASK-012.
- The extractor is not connected to the full Celery processing task yet.
- Upload still does not automatically enqueue processing.
- Chunking, embeddings, pgvector, retrieval, and READY transition are not implemented in TASK-012.
## 10. TASK-013 Chunking foundation

Implemented extraction-to-chunking in-memory flow:

```text
FileStorage
    -> PDF bytes
    -> PyMuPDFTextExtractor
    -> ExtractionResult
    -> PageAwareTokenChunker
    -> ChunkingResult
```

- `TokenCounter` is the tokenizer abstraction.
- `TiktokenTokenCounter` is the current token-counting implementation.
- `TextChunker` is the chunking abstraction.
- `PageAwareTokenChunker` chunks extracted page text with paragraph-first splitting, sentence fallback, and token-window fallback.
- Chunk metadata keeps stable chunk indexes, token counts, character counts, page numbers, overlap counts, and deterministic SHA-256 checksums.
- Chunking is deterministic for the same extraction result, configuration, and tokenizer encoding.
- Chunks are not persisted in TASK-013.
- Embeddings, pgvector storage, retrieval, and READY transition are not implemented in TASK-013.
- The full Celery document-processing pipeline is not connected yet.
- There is no API endpoint for viewing chunks.

## 11. TASK-014 Embeddings and vector storage

Implemented chunk embedding and vector persistence flow:

```text
FileStorage
    -> PyMuPDFTextExtractor
    -> ExtractionResult
    -> PageAwareTokenChunker
    -> ChunkingResult
    -> EmbeddingProvider
    -> SentenceTransformer provider
    -> PostgreSQL document_chunks + pgvector
```

- Embedding runs locally through Sentence Transformers.
- The default model is `intfloat/multilingual-e5-small`.
- Passage chunks use the `passage: ` prefix only while embedding.
- Query verification uses the `query: ` prefix.
- Embedding vectors are normalized by default.
- The persisted vector dimension is fixed at 384 for this MVP schema.
- PostgreSQL stores vectors in `document_chunks.embedding` using pgvector `vector(384)`.
- A HNSW cosine index exists on chunk embeddings.
- The worker does not call extraction, chunking, embedding, or persistence yet.
- Upload does not automatically enqueue processing yet.
- There is no public semantic retrieval API in TASK-014.

## 12. TASK-015 end-to-end document processing pipeline

Implemented asynchronous ingestion flow:

```text
FastAPI Upload
    -> LocalFileStorage
    -> PostgreSQL Document: UPLOADED
    -> Celery/Redis queue
    -> Worker atomic claim: PROCESSING
    -> PyMuPDF extraction
    -> Page-aware chunking
    -> SentenceTransformer embedding
    -> document_chunks + pgvector
    -> Document: READY
```

Failure flow:

```text
PROCESSING -> FAILED
```

- Upload returns HTTP 202 before processing finishes.
- The upload service enqueues only after file save and database commit succeed.
- The Celery task receives only the Document UUID string.
- Redis does not carry PDF bytes, page text, chunk text, token IDs, vectors, storage keys, or user data.
- PostgreSQL remains the source of truth for status.
- The worker claims only `UPLOADED` and `FAILED` Documents atomically.
- Chunk replacement and the `READY` transition are committed in the same database transaction.
- Permanent processing failures store sanitized `FAILED` messages.
- There is no public search, chunk, embedding, chat, or citation API in TASK-015.
## 13. TASK-016 semantic retrieval foundation

Implemented internal semantic retrieval flow:

```text
User query
    -> query validation
    -> query embedding
    -> permission-aware pgvector query
    -> relevance threshold
    -> top-k RetrievalHit results
```

- Retrieval embeds user questions with the configured query embedding path.
- Retrieval joins `document_chunks` to `documents` and considers only `READY` Documents.
- Soft-deleted Documents and `ARCHIVED` Documents are excluded.
- The reusable TASK-010 Document access filter is applied inside the PostgreSQL vector query before ordering and `LIMIT`.
- Query embeddings are request-time values and are not persisted to PostgreSQL, Redis, Celery results, or logs.
- Semantic retrieval is an internal service only in TASK-016.
- There is no public Search API, keyword retrieval, hybrid retrieval, reranking, context assembly, Chat API, LLM answer generation, or citation response yet.

## 14. TASK-017 keyword and hybrid retrieval foundation

Implemented internal keyword and hybrid retrieval flow:

```text
User query
|-- Semantic retrieval
|   `-- query embedding + pgvector cosine
|-- Keyword retrieval
|   `-- PostgreSQL full-text search
`-- Weighted Reciprocal Rank Fusion
    `-- HybridRetrievalResult
```

- Semantic retrieval continues to use the TASK-016 pgvector cosine-distance path and the HNSW cosine index.
- Keyword retrieval uses PostgreSQL full-text search with the fixed `simple` text-search configuration.
- Keyword retrieval uses the `ix_document_chunks_text_fts_simple` GIN expression index on `to_tsvector('simple'::regconfig, text)`.
- Each retrieval branch joins `document_chunks` to `documents`, filters to `READY` Documents, excludes soft-deleted and archived Documents, and applies the shared permission filter in PostgreSQL.
- Permission filtering happens before branch ranking and branch `LIMIT`; unauthorized chunks are not loaded into application memory for later filtering.
- Hybrid retrieval fuses authorized semantic and keyword candidates with weighted Reciprocal Rank Fusion and deduplicates by `chunk_id`.
- Hybrid ranking is deterministic through stable tie-breaks on channel coverage, branch ranks, Document ID, chunk index, and chunk ID.
- Keyword and hybrid retrieval are internal services only.
- There is still no public Search API, Chat API, LLM answer generation, context assembly, reranking, or citation response.

## 15. TASK-018 chat foundation

Implemented owner-only ChatSession flow:

```text
Authenticated User
    -> ChatSession API
    -> ChatSessionService
    -> PostgreSQL chat_sessions/chat_messages
```

- Chat sessions are private to the owning User.
- Admin does not bypass chat-session ownership.
- Ownership checks run in PostgreSQL before history, retrieval, LLM, or message persistence.
- Public history returns only USER and ASSISTANT messages; SYSTEM messages are hidden.
- Chat history pagination runs in SQL.

## 16. TASK-019 grounded answer flow

Implemented grounded answer generation:

```text
POST message
    -> owned-session lookup
    -> recent visible history
    -> HybridRetrievalService
    -> context token budget
    -> grounded prompt
    -> LLMProvider
    -> no-answer mapping
    -> atomic USER + ASSISTANT persistence
```

- The Chat service calls HybridRetrievalService instead of querying chunks directly.
- Retrieved context is treated as untrusted data and is not sent as a SYSTEM message.
- Empty retrieval or empty context skips the LLM and returns the configured fixed no-answer.
- USER and ASSISTANT messages are committed together after the answer is ready.
- Prompt, retrieved chunks, embeddings, token usage internals, and retrieval scores are not exposed in public Chat responses.

## 17. TASK-020 citation validation flow

Implemented citation validation:

```text
Hybrid Retrieval
    -> Source registry
    -> Source-marked grounded prompt
    -> LLM answer markers
    -> Backend marker validation
    -> Permission revalidation
    -> Server-generated citations
    -> Atomic message/citation persistence
```

- The model only emits source markers such as [SOURCE_1].
- The backend owns source metadata and maps markers to selected authorized context hits.
- Unknown, missing, malformed, or over-limit markers are rejected before persistence.
- Permission is revalidated after LLM generation and before response/persistence.
- Revoked or unavailable cited sources downgrade the response to the fixed no-answer with no citations.
- No-answer responses have an empty citations array.
- Citation excerpts are generated from server-side chunk text, not from the LLM answer.
- Stored and public assistant answers use normalized numeric markers such as [1] and [2].

## 18. TASK-021 feedback flow

Implemented feedback submission and reporting:

```text
Authenticated User
    -> owned ASSISTANT message lookup
    -> PostgreSQL atomic Feedback upsert
    -> Feedback response
```

Reporting scope:

```text
Admin   -> all feedback
Manager -> feedback submitted by Users in the Manager current Department
Staff   -> report forbidden
```

- Feedback upsert uses the unique `(message_id, user_id)` conflict target.
- The target lookup joins `chat_messages` to `chat_sessions` and filters role/ownership in PostgreSQL.
- Admin and Manager do not bypass ownership when submitting feedback on a message.
- Feedback report does not return Chat content, session title, citations, retrieval query, token usage, prompts, or Document metadata.
- Feedback does not call LLM, retrieval, Redis, or Celery.
- Feedback upsert records a sanitized `FEEDBACK_UPSERTED` audit event in the same transaction as the Feedback row.

## 19. TASK-022 audit log expansion

Implemented audit flow:

```text
Business action
    -> domain service
    -> AuditService
    -> same PostgreSQL transaction for successful mutations
    -> append-only audit_logs
```

Failure flow:

```text
Business transaction rollback
    -> best-effort failure AuditLog transaction
    -> original error preserved
```

Report flow:

```text
Admin
    -> GET /api/v1/audit-logs
    -> PostgreSQL filters
    -> stable paginated sanitized results
```

- Audit events use stable string event types and `SUCCESS`/`FAILURE` outcomes.
- Success audit events for mutating business actions are inserted with the same `AsyncSession` transaction as the business mutation.
- Failure audit events use a separate best-effort transaction and never replace the original business error if failure-audit persistence also fails.
- Audit metadata is built through a central allowlist sanitizer and does not store passwords, tokens, Chat question/answer text, prompts, retrieved context, citation excerpts, Feedback reason, Document filenames, storage keys, user email, or full names.
- Audit report access is Admin-only; Manager and Staff users are forbidden.
- Audit report filters and total counts run in PostgreSQL before pagination.
- Reading AuditLog does not create another AuditLog event.
- Audit does not use Redis, Celery, Kafka, webhooks, LLM providers, retrieval, export, dashboards, SIEM, signing, or retention cleanup in the MVP.


## 20. TASK-023 Docker full backend stack

Implemented local Docker runtime flow:

```text
Docker Compose
|-- postgres: pgvector PostgreSQL on postgres:5432
|-- redis: Redis broker/backend on redis:6379
|-- migration: alembic upgrade head, one-shot
|-- api: uvicorn app.main:app on 0.0.0.0:8000
`-- worker: celery -A app.workers.celery_app:celery_app worker
```

- API, worker, migration, and test service are built from the same Dockerfile.
- The runtime image uses Python 3.12 and a non-root `app` user.
- API and worker share `uploads_data` at `/app/data/uploads`.
- API and worker share `model_cache` at `/app/data/models` for Sentence Transformers cache.
- Compose overrides container database and Redis URLs to use service names, not host localhost ports.
- API and worker depend on PostgreSQL and Redis health plus successful migration completion.
- The default API command does not use `--reload`.
- LLM is disabled by default and is not a Compose dependency.
- No schema migration is created by TASK-023; Alembic head remains `20260722_0009`.

## TASK-025 MVP hardening architecture

The backend MVP now applies hardening at the application boundary without changing the domain model or Alembic schema.

- `app.core.config.Settings` validates `development`, `test`, and `production` modes, production debug policy, placeholder secrets, database password presence, CORS origins, trusted hosts, request-size limits, database pool bounds, Redis timeouts, rate-limit windows, and Celery time limits.
- `app.main.create_app()` installs request-size limiting, CORS, trusted-host enforcement, security headers, and safe exception handlers before registering the existing API routers.
- `app.core.middleware.RequestSizeLimitMiddleware` rejects oversized `Content-Length` early and enforces actual streamed bytes while the request body is read.
- `app.core.rate_limit` implements a Redis-backed fixed-window limiter. Auth endpoints use direct client IP identity; authenticated upload/chat/feedback endpoints use current User ID. Proxy forwarding headers are not trusted.
- `app.core.logging.SensitiveDataRedactionFilter` redacts secrets and business-content fields from log records without mutating application data.
- The API SQLAlchemy engine uses bounded pool settings and `pool_pre_ping=True`; worker sessions remain isolated per task with `NullPool` and bounded connect timeout.
- Celery remains JSON-only and now has configured soft/hard task time limits.
- Docker Compose keeps the local development topology and adds `no-new-privileges:true` to application services.

No database migration was introduced for TASK-025; Alembic head remains `20260722_0009`.

## TASK-026 multi-LLM provider architecture

TASK-026 keeps answer grounding, citation validation, and persistence independent from provider-specific code.

```text
GroundedAnswerService
    -> LLMProviderManager
    -> LLMProviderRegistry
    -> provider adapter
    -> bounded HTTP client
```

Provider responsibilities:

- Validate selected provider configuration without exposing secrets.
- Build the provider-specific request from standardized `LLMRequest` and `LLMMessage` values.
- Send a bounded HTTP request with explicit connect/read/write/pool timeouts.
- Retry only bounded transient failures with backoff.
- Parse and normalize content, provider name, model, finish reason, safe request id, and usage data.
- Map provider failures to safe `LLMFailureCode` values.

Provider boundaries:

- Providers do not perform retrieval, source selection, citation parsing, citation mapping, permission checks, persistence, fallback decisions, cost estimation, or audit writes.
- Providers must not log prompts, retrieved context, user questions, assistant answers, document text, citation excerpts, request bodies, response bodies, authorization headers, or API keys.

Provider groups:

- OpenAI-compatible: OpenAI, OpenRouter, Ollama OpenAI endpoint, LM Studio OpenAI endpoint, and custom enterprise gateways.
- Provider-specific: Azure OpenAI, Google Gemini, and Anthropic Claude.

Registry and lifecycle:

- Provider names are centralized in `app.llm.provider_names`.
- `LLMProviderRegistry` validates provider names and creates providers lazily.
- `LLMProviderManager` is attached to `app.state`, creates the selected provider only on first use, reuses the lazy `httpx.AsyncClient`, and closes it during FastAPI shutdown.
- No provider instance or HTTP client is created at import time.
- No provider network call is made during import, migration, startup, liveness, or readiness.

Configuration health:

- `ProviderHealth` exposes safe provider status fields for future Admin/UI use: provider name, display name, model, configured flag, status, safe message, and optional request id.
- Connectivity checks are explicit through `health_check(check_connectivity=True)`, use safe GET probes with bounded timeouts, send no prompt or context body, and can report `reachable` or `unreachable` without affecting default readiness.
- Readiness remains limited to internal dependencies and does not fail because an external LLM is temporarily unavailable.
- TASK-026 does not add a public provider-status endpoint; TASK-028 can consume a future Admin-only endpoint built from the registry/manager without exposing secrets.

No database migration is introduced by TASK-026. Alembic head remains `20260722_0009`.
## TASK-027 streaming chat architecture

TASK-027 adds an SSE transport without replacing the existing Chat API.

```text
POST /chat/sessions/{id}/messages/stream
    -> authentication and chat rate limit
    -> ChatStreamService
    -> GroundedAnswerService.answer_question
    -> retrieval, provider generation, citation validation
    -> atomic final USER/ASSISTANT/citation/audit persistence
    -> SSE serializer emits validated events
```

The selected strategy is `buffer_after_validation`. Provider output is generated and validated as a complete answer before any answer text is emitted to the client. This keeps grounded-only, selected-context, citation-validation, no-answer, and rollback behavior identical to the non-streaming endpoint.

`app.chat.sse` owns SSE JSON encoding and event-state enforcement. It emits UTF-8 JSON data lines, safe event ids, monotonic delta sequence numbers, one terminal event, and no events after terminal state.

`app.services.chat_stream_service.ChatStreamService` owns timeout, heartbeat, safe stream-error payloads, and client-disconnect cancellation. It does not keep a long-running database transaction open while waiting for provider generation; persistence still happens inside `GroundedAnswerService` after validation.

Provider capability metadata now distinguishes safe streaming fallback from native provider streaming. OpenAI-compatible, Azure, Gemini, Anthropic, Ollama, LM Studio, and OpenRouter are supported through the same buffer-after-validation fallback in TASK-027. Native parser-level provider streaming is intentionally deferred until incremental grounding can preserve the same security contract.

No database migration is introduced by TASK-027. Alembic head remains `20260722_0009`.
## TASK-028 Frontend Architecture

The frontend console lives in `frontend/` and is a React 18 + TypeScript + Vite application. It is separate from the FastAPI container and consumes the existing backend API contracts instead of introducing mock production services.

Frontend layers:

- `src/api`: typed fetch client, token storage, standard `ApiError` parsing, and POST-based SSE streaming client.
- `src/features`: route-level business screens for auth, chat, documents, admin, feedback, audit, system status, and profile.
- `src/components`: shared accessible UI, data display, feedback/toast, and controlled motion primitives.
- `src/layouts`: authenticated application shell with role-aware navigation.
- `src/styles`: CSS variables and Tailwind token integration.

The chat route consumes TASK-027 SSE through `fetch` and `ReadableStream`, not `EventSource`, because the backend stream requires POST body and Authorization header. The UI reflects the backend `buffer_after_validation` strategy: it can show waiting/heartbeat state while retrieval, answer generation, grounding, and citation validation complete, then renders final validated content and citations.

The frontend Docker image builds static assets and serves them from a small Node HTTP server as the non-root `node` user. Compose exposes this through the optional `frontend` profile and keeps browser API configuration public via `VITE_API_BASE_URL`.