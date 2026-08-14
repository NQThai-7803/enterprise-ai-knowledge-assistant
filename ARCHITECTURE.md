# System Architecture

## 1. Kiến trúc tổng thể

```text
Web Client
    |
    v
FastAPI Application
    ├── Auth Module
    ├── User & Department Module
    ├── Document Module
    ├── Chat Module
    ├── Retrieval Module
    ├── Feedback Module
    └── Audit Module
          |
          +--> PostgreSQL + pgvector
          +--> Redis
          +--> Celery Worker
          +--> File Storage
          +--> Embedding Provider
          +--> LLM Provider
```

## 2. Kiến trúc backend

```text
app/
├── api/
│   ├── dependencies.py
│   └── v1/
│       ├── auth.py
│       ├── users.py
│       ├── departments.py
│       ├── documents.py
│       ├── chat.py
│       ├── feedback.py
│       └── audit_logs.py
├── core/
│   ├── config.py
│   ├── security.py
│   ├── logging.py
│   └── exceptions.py
├── db/
│   ├── base.py
│   ├── session.py
│   └── migrations/
├── models/
├── schemas/
├── repositories/
├── services/
├── rag/
│   ├── chunking.py
│   ├── embeddings.py
│   ├── retrieval.py
│   ├── reranking.py
│   ├── prompts.py
│   └── citations.py
├── workers/
│   ├── celery_app.py
│   └── document_tasks.py
├── storage/
├── tests/
└── main.py
```

## 3. Layer responsibilities

### API layer

- Nhận request.
- Validate dữ liệu bằng schema.
- Gọi service.
- Chuyển exception thành HTTP response.
- Không chứa truy vấn database phức tạp.

### Service layer

- Chứa business logic.
- Điều phối repository, storage, RAG và audit.
- Quản lý transaction khi cần.

### Repository layer

- Truy vấn database.
- Không chứa logic HTTP.
- Áp dụng filter permission ở query phù hợp.

### RAG layer

- Chunking.
- Embedding.
- Retrieval.
- Reranking.
- Prompt building.
- Citation validation.

### Worker layer

- Xử lý document bất đồng bộ.
- Retry có kiểm soát.
- Cập nhật trạng thái và error message.

## 4. Dependency rules

```text
API → Service → Repository → Database
               ↘ RAG Provider
               ↘ Storage Provider
               ↘ Audit Service
```

Không cho phép:

- Model import router.
- Repository gọi HTTP response.
- RAG module truy cập global user mà không truyền permission scope.
- Router gọi trực tiếp Celery hoặc database ngoài service.

## 5. Provider abstractions

Nên tạo interface hoặc protocol cho:

- `EmbeddingProvider`
- `LLMProvider`
- `FileStorage`
- `TextExtractor`
- `Reranker`

Mục tiêu là có thể thay provider mà không sửa toàn bộ hệ thống.

## 6. Async strategy

- FastAPI endpoint dùng async khi thao tác I/O phù hợp.
- Document processing chạy bằng Celery worker.
- Không gọi OCR hoặc embedding hàng loạt trực tiếp trong request upload.

## 7. Error handling

Error response thống nhất:

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
    -> ConversationContextBuilder same-session memory
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
- Prompt, conversation prompt history, retrieved chunks, embeddings, token usage internals, and retrieval scores are not exposed in public Chat responses.

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
## TASK-029 Conversation Memory Architecture

TASK-029 adds bounded same-session memory without adding long-term memory or schema state.

```text
Question
    -> owned ChatSession lookup
    -> ConversationContextBuilder
       -> chat_messages for current owned session only
       -> USER, ASSISTANT, internal SYSTEM roles
       -> order by created_at ASC, id ASC
       -> de-duplicate by message id
       -> trim by CHAT_HISTORY_MAX_MESSAGES and CHAT_HISTORY_MAX_TOKENS
       -> format conversation history
       -> build bounded retrieval query
    -> HybridRetrievalService
    -> retrieved-context token budget
    -> grounded prompt
    -> LLMProvider
    -> citation validation
    -> atomic USER/ASSISTANT/citation/audit persistence
```

`app.chat.conversation_context_builder.ConversationContextBuilder` owns loading, trimming, token-budget accounting, retrieval-query construction, and prompt-history formatting. The Chat API and streaming service do not implement memory logic directly; both non-streaming and `/messages/stream` continue to call `GroundedAnswerService.answer_question()`.

Conversation history is a prompt aid only. It can resolve references in the current question, but it does not replace Hybrid Retrieval, does not create citations, and does not authorize access to document content. The prompt order is SYSTEM policy, Conversation History, Retrieved Context, then Current Question. Citation validation still maps only backend-generated source markers from selected retrieved context.

No migration, table, Redis cache, vector memory, summary memory, or LLM summarization was added. PostgreSQL continues to persist the normal chat message pair and citations; formatted prompts and formatted conversation history are not stored.
## TASK-030 OCR Architecture

TASK-030 extends document ingestion without changing the upload API contract, Chat API contract, streaming architecture, Conversation Memory, or citation architecture.

```text
Upload request
    -> validate and store PDF/PNG/JPEG
    -> enqueue document_id only
    -> Celery worker
    -> ExtractionRouter
       -> PyMuPDF native PDF text
       -> Tesseract OCR fallback for scanned/low-quality PDF pages
       -> Tesseract OCR for standalone images
    -> chunking, embeddings, pgvector
    -> existing retrieval, grounding, and citation flow
```

OCR is not executed in the FastAPI upload request. It is bounded by document/page timeouts, page count, image dimensions, image pixels, extracted-character limits, and text-quality thresholds. Tesseract is invoked only by the OCR provider during worker processing or explicit provider health checks; no OCR model download or external service call occurs during import/startup.

No migration was added for TASK-030 recovery. Existing `documents.mime_type`, `documents.storage_key`, and `document_chunks` page metadata are sufficient for the implemented PDF/PNG/JPEG OCR path.

## TASK-031 Web Search Integration Architecture

TASK-031 adds `app/web_search/` as a provider-backed subsystem beside retrieval and LLM providers. The Chat API contract remains unchanged.

```text
Question
  -> same-session ConversationContextBuilder
  -> internal HybridRetrievalService unless WEB_SEARCH_MODE=web_only
  -> WebSearchIntentClassifier
  -> WebSearchProviderManager / WebSearchProviderRegistry
  -> WebSearchService normalize/dedupe/limit
  -> selected internal + web context
  -> grounded prompt
  -> LLM provider
  -> CitationValidationService
  -> atomic chat/citation persistence
```

Provider boundaries:

- `WebSearchProvider` is the protocol.
- `WebSearchProviderRegistry` validates and lazily creates `mock`, `bing`, `duckduckgo`, or `google_custom_search` providers.
- `WebSearchProviderManager` owns provider lifecycle in `app.state`, parallel to the LLM manager.
- Real HTTP providers use bounded timeout, bounded retry, no redirects, safe error codes, and no raw request/response logging.
- `WEB_SEARCH_ALLOW_EXTERNAL=false` blocks external provider calls.

Citation boundaries:

- `MessageCitation.source_type` distinguishes `INTERNAL` from `WEB`.
- Internal citations retain `document_id`/`chunk_id` and permission revalidation.
- Web citations require backend-sourced `source_url`/`source_title` and do not use internal document IDs.
- The LLM can only cite backend source markers; it cannot create trusted URLs or document IDs.

## TASK-032 Admin Monitoring Architecture

TASK-032 adds a backend-only Admin monitoring layer without changing domain workflows.

```text
Admin request
    -> /api/v1/admin/* router
    -> require_admin RBAC dependency
    -> AdminMonitoringService
       |-- PostgreSQL aggregate counts and Alembic revision
       |-- Redis ping and Celery broker queue length
       |-- Celery inspect ping/stats for workers
       |-- Tesseract OCR health check
       |-- Embedding configuration health without model load
       |-- LLMProviderManager configuration health without external call
       |-- WebSearchProviderManager configuration health without external call
       |-- Streaming route/configuration registration
       `-- Conversation memory configuration
```

The service is read-only. It does not enqueue tasks, modify Celery routing, load the embedding model during health checks, call live LLM providers, call live Web Search providers, read prompts, read retrieved context, read chat content for monitoring responses, read citation excerpts, or expose secrets. OCR health runs the existing bounded Tesseract health probe only when OCR is enabled.

Queue reporting reflects the existing Celery architecture: `documents` is the only document-processing queue. OCR and embedding run inside `documents.process_document`; retry uses Celery retry/backoff without a dedicated retry queue; no dead-letter queue is configured.

No database migration is introduced for TASK-032 because all statistics use existing tables and the system version endpoint reads the existing Alembic metadata.


## TASK-033 Analytics & Reporting Architecture

TASK-033 adds a backend-only Admin analytics layer without changing Chat, Streaming, Conversation Memory, Citation, OCR, Web Search, Celery routing, or the database schema.

```text
Admin request
    -> /api/v1/admin/analytics/* router
    -> require_admin RBAC dependency
    -> AdminAnalyticsService
       |-- PostgreSQL time-window aggregates
       |-- Chat message/session counts and token totals
       |-- Citation source-type inference for internal/web/hybrid search usage
       |-- Image-document OCR status inference
       |-- LLM latency/token/failure aggregates from existing chat/audit rows
       |-- Feedback rating aggregates without reasons
       `-- Audit action/outcome category aggregates without metadata payloads
```

Analytics are read-only and use existing persisted rows. No `create_all()` call, migration, queue change, analytics worker, dashboard UI, charting layer, or frontend route is introduced.

Data availability is explicit. Average response time and token usage are available from assistant messages. Retrieval duration, per-message streaming usage, OCR duration, exact scanned-PDF OCR page counts, and historical per-message LLM provider/model attribution are not persisted, so the API reports those metrics as unavailable or partially inferred rather than manufacturing values.

Report export is implemented server-side for safe JSON and CSV payloads. PDF export is not implemented because the project has no existing PDF report infrastructure.

## TASK-034 Production Deployment & Observability Architecture

TASK-034 adds production deployment and observability without changing Chat, RAG, Citation, Conversation Memory, Streaming, OCR, Web Search, or Celery task routing.

```text
Client / load balancer
    -> Nginx reverse-proxy container
       |-- security headers
       |-- request and upload limits
       |-- X-Forwarded-* and X-Request-ID forwarding
       `-- SSE buffering disabled for /messages/stream
    -> FastAPI API container
       -> RequestObservabilityMiddleware
          |-- safe request ID context
          |-- bounded route-template request metrics
          |-- latency/status logging without bodies or queries
       -> existing routers and services

Prometheus profile
    -> scrape api:8000/metrics on backend network
    -> Grafana provisioning reads Prometheus datasource and dashboards
```

Production Compose is independent from development Compose. `compose.prod.yaml` defines PostgreSQL, Redis, one-shot migration, API, worker, reverse-proxy, and optional Prometheus/Grafana services with restart policy, healthchecks, json-file log rotation, CPU/RAM/PID limits, and `no-new-privileges:true` where supported.

Metrics are Prometheus text format and are intentionally low-cardinality. HTTP labels use method, safe route template, and status code. Runtime gauges reuse `AdminMonitoringService` for API, PostgreSQL, Redis, worker, OCR, embedding, LLM, Web Search, streaming, conversation, providers, queues, version, and uptime. Metrics do not select prompts, retrieved context, document text, storage keys, citation excerpts, feedback reasons, API keys, Redis URLs, or database URLs.

Secret-file support is implemented through `*_FILE` settings for JWT secret, database URL, Redis/Celery URLs, LLM provider keys, and Web Search provider keys. Secret-file validation errors are generic and never print file contents. The committed production env file is an example only.

Backup and restore remain operator-run procedures. PostgreSQL backup uses `pg_dump` custom format and verifies with `pg_restore --list`; upload backup archives the uploads Docker volume and verifies with `tar tzf`. Restore helpers default to isolated check databases/volumes to avoid accidental production overwrite.

## TASK-035 Architecture Freeze

- Release version: v1.0.0-rc1.
- TASK-035 made no architecture changes and added no new service, queue, storage backend, API surface, or database schema.
- Final acceptance validated the existing FastAPI, PostgreSQL/pgvector, Redis, Celery worker, local storage, OCR, embedding, retrieval, LLM, Web Search, analytics, monitoring, metrics, backup/restore, and production reverse-proxy architecture.
- Alembic head remains 20260803_0010.

## TASK-034.1 Real LLM Grounded Runtime Acceptance Architecture

TASK-034.1 does not add a new provider architecture. It uses the existing TASK-026 provider registry and the existing TASK-019/TASK-020 grounded-answer and citation contracts.

```text
Local real acceptance
    -> Docker API/worker/PostgreSQL/Redis
    -> uploaded unseen PDF artifacts
    -> document processing to READY
    -> permission-aware hybrid retrieval
    -> strict grounded prompt
    -> local real LLM provider through LLMProviderRegistry
    -> citation validation and permission revalidation
    -> atomic persistence only after validation
```

Provider mode separation:

- `compose.uat.yaml` plus `fake-openai-provider.mjs` remains deterministic regression infrastructure only.
- `LLM_PROVIDER=ollama` and `LLM_PROVIDER=lm_studio` reuse the OpenAI-compatible adapter and require no new service or database schema.
- External providers are explicit deployment choices and can transfer selected prompt/context to the provider.

Streaming keeps the existing `buffer_after_validation` strategy. No provider token stream is public before grounding, citation validation, permission revalidation, and persistence succeed.

TASK-034.1 adds stricter prompt policy and an extra service invariant that `ANSWERED` results must carry validated citations. It still does not implement claim-level semantic entailment verification; manual claim verification is required for this acceptance track and automated claim-level verification is deferred to a later task.