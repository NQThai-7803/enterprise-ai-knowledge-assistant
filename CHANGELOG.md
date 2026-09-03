# Changelog

All notable changes to this project will be documented in this file.

Format follows a simplified Keep a Changelog style.

## [Unreleased]

### RAG Runtime Acceptance and Leave Corpus Restoration -- 2026-08-21

#### Added

- Added answer-bearing source-quality architecture across retrieval/citation selection so direct policy clauses and tables are preferred over sample-question, appendix, and reference chunks.
- Added subject/object-aware YES/NO validation so polarity is anchored to the asked actor/object rather than accepted from unrelated supported evidence.
- Added relation entailment support for replacement/supplemental relationships, including NovaCare versus mandatory BHYT.
- Added stronger citation source repair with focused evidence text, redundant marker pruning, and source-quality-based citation selection.

#### Fixed

- Fixed the annual-leave UAT corpus gap by restoring the intended soft-deleted UAT leave-policy document instead of changing RAG/runtime logic.
- Restored document `43cb2c93-52bc-44f6-8e03-1b1f075e1d89` (`Chính sách nghỉ của người lao động`, checksum `24178db420422e474326986672b6c15cc67373ee6adbe1489ba5e8addf95f4f4`) and reprocessed it through normal ingestion task `274fe326-9d28-421c-9c11-253ec7b74bc2`.
- Confirmed the restored document became `READY` with `6` pages, `12` chunks, `6458` tokens, and `384`-dimension embeddings; active corpus verification found `12` ready documents, `153` active chunks, and active leave table chunk `4b341201-f0df-4102-b9f2-5ad7091781a6`.

#### Verified

- Annual-leave runtime UAT now starts with `Không`, distinguishes `12`, `14`, and `16` day categories, cites the real active leave clause/table, avoids sample-question/test-question citations, and records claim validation `SUPPORTED`.
- Seven runtime UAT cases passed: own salary, EAP, NovaCare vs BHYT, Engineering Manager `N5 / 42 - 70 triệu`, Head / Director `N6 / 65 - 110 triệu`, annual leave, and CEO false premise `Nguyễn Anh Khoa`.
- `python -m pytest tests\unit\test_grounded_answer_service.py -q`: `75 passed in 1.33s`.
- Focused RAG/citation suite: `132 passed in 1.56s`.
- Combined RAG/citation/validation/output suite: `157 passed in 1.71s`.
- `python -m pytest tests\unit -q`: `1061 passed in 8.22s`.
- Ruff check on 21 touched Python files: `All checks passed!`.
- Ruff format check on 21 touched Python files: `21 files already formatted`.

#### Known limitations

- The restored authoritative annual-leave document is a generic/template policy in the UAT corpus, not a Nova-branded policy; replace it with canonical Nova-branded content when available.
- The configured CrossEncoder reranker was unavailable and runtime used alignment fallback reranking.
- Runtime UAT latency remains high.
- Annual-leave exact evidence highlighting is too narrow for a multi-row table and should capture the full 12 / 14 / 16 support span.

### Manual RAG / Citation Hardening — 2026-08-19

#### Added

- Added backend exact-evidence extraction that derives a focused supporting text/value from the answer and backend-selected source text without modifying original PDF/DOCX files.
- Added optional `evidence_text` metadata to validated citations, persistence, API responses, and session-history reloads.
- Added Alembic revision `cd124fa71c86_add_citation_evidence_text.py` for nullable `message_citations.evidence_text` and `ck_message_citations_evidence_text_not_blank`.
- Added frontend exact-evidence rendering so the evidence substring can be emphasized independently from the broader citation excerpt.
- Added evidence-aware Minimal Citation Selection/pruning work for redundant citations from the same internal document and same normalized evidence.

#### Fixed

- Repaired an initially empty `cd124fa71c86` migration by restoring the database revision marker to `20260803_0010` and re-running the corrected migration.
- Confirmed historical citation rows remain valid with `evidence_text = NULL`.

#### Verified

- Exact-evidence citation-mapping focused suite reached `15 passed`.
- Live PostgreSQL persistence and API/session reload verified `evidence_text = "180 người"` for a real local grounded answer.
- Minimal Citation Selection focused unit verification passed with `17 passed in 0.19s`; live new-message runtime verification remains pending before final completion.
- Verified punctuation cleanup after pruning so removed redundant markers no longer leave malformed output such as `[1] .`.
- Verified focused mapping behavior preserves distinct evidence while allowing same-document/same-evidence redundancy removal.

#### Design constraints

- Regression/UAT questions are tests only and must never become runtime question-to-answer mappings.
- Citation deduplication must not be based on `document_id` alone; different evidence supporting different claims must remain available.


### Fixed

- Replaced document upload raw Department ID entry with a Department selector backed by `GET /api/v1/departments`, conditional scope validation, loading/empty/error/retry states, and safe validation copy.
- Replaced document permission raw Grantee ID entry with User and Department selectors backed by existing list APIs, stale-selection clearing when grantee type changes, cached display-name resolution, and safe grant-error copy.
- Extended the local deterministic UAT OpenAI-compatible provider to answer the current UAT leave follow-up and Nova Digital CEO questions from retrieved context.
- Restored project status/version metadata so TASK-035 remains not started and no Release Candidate version is marked by this UAT fix.

### Changed

- Documented that default development Compose keeps `LLM_ENABLED=false`, while `compose.uat.yaml` enables the local deterministic provider with `LLM_MODEL=uat-deterministic-model` and `LLM_OPENAI_BASE_URL=http://uat-llm:18080/v1`.

### Verified

- Verified default Compose keeps LLM disabled and UAT Compose enables only the local deterministic provider.
- Verified focused frontend selector tests, frontend typecheck/build, focused backend chat/grounding/citation/memory/streaming/permission/LLM provider tests, Docker UAT health, live deterministic chat, streaming, Ruff, format check, compileall, and security scan.
### Added

- Implemented TASK-034 Production Deployment & Observability with backend-only Prometheus metrics, request ID middleware, safe request latency logging, traceparent capture hooks, production runtime validation, and Docker secret-file configuration support.
- Added standalone `compose.prod.yaml`, `.env.production.example`, Nginx reverse proxy config, Prometheus scrape config, Grafana datasource/dashboard provisioning, and PostgreSQL/uploads backup-restore helper scripts.
- Added TASK-034 unit/API/integration tests for metrics, request IDs, logging safety, production config, reverse proxy settings, Prometheus/Grafana provisioning, backup/restore guardrails, and secret-file startup validation.
- Verified TASK-034 final acceptance: production and development Compose config/build/up/ps, production runtime health, reverse proxy, metrics safety, Celery worker ping, backup/restore, Redis/PostgreSQL failure recovery, Alembic, dependency audit, security scan, and regression suites passed.
- Implemented TASK-033 Analytics & Reporting with backend-only Admin analytics APIs under `/api/v1/admin/analytics` and report export under `/api/v1/admin/reports/export`.
- Added safe analytics schemas and `AdminAnalyticsService` for overview, chat, users, search, OCR, LLM, feedback, audit, and export aggregates using existing PostgreSQL rows.
- Added CSV and JSON report export while rejecting PDF export until safe backend PDF report infrastructure exists.
- Added TASK-033 unit/API integration tests for filters, RBAC, aggregate correctness, security non-disclosure, export, regression, and performance smoke.
- Implemented TASK-032 Admin Dashboard & System Monitoring with backend-only Admin monitoring APIs under /api/v1/admin.
- Added safe Admin health, providers, workers, queues, statistics, version, and system dashboard response schemas and service aggregation.
- Added TASK-032 unit and API integration tests for Admin RBAC, health subsystem coverage, provider safety, worker/queue reporting, statistics, version, and secret/content non-disclosure.

- Implemented TASK-031 Web Search Integration with backend-only internal-only, hybrid, and web-only source modes.
- Added `WebSearchProvider` abstraction, web search provider registry/manager, mock provider, Bing provider, DuckDuckGo provider, and Google Custom Search provider.
- Added web search configuration for enabled state, provider, max results, timeout, max content length, external-call allow flag, user agent, retries, endpoints, and provider credentials.
- Added intent detection for current/web questions and no-internal-hit fallback while preserving internal hybrid retrieval first in hybrid mode.
- Added web content and URL normalization to strip unsafe HTML/script/style/hidden/comment content, bound result content, and reject unsafe URLs.
- Added `CitationSourceType` and web citation persistence fields with migration `20260803_0010_add_web_search_citations`.
- Added Admin-only web search provider status and provider search-test endpoints.
- Added TASK-031 unit, API, streaming, and migration tests for web search, citation, provider failure, timeout/retry, and source-mode behavior.
- Initialized Phase 2 roadmap.
- Started TASK-026 Multi-LLM Provider Support.
- Completed TASK-026 recovery with missing-usage normalization, explicit provider connectivity health, remote OpenAI-compatible API key validation, and Docker runtime verification.
- Completed TASK-027 Streaming Chat with Server-Sent Events.
- Added a protected SSE chat endpoint, centralized SSE serializer/state machine, bounded heartbeat/stream timeout settings, and Docker streaming integration tests.
- Verified streaming preserves grounded-answer policy, citation validation, atomic final-message persistence, safe provider errors, cancellation cleanup, and the non-streaming Chat API.
- Added TASK-028 Frontend UI Foundation & Test Console to the roadmap.
- Completed TASK-029 Conversation Memory.
- Added `ConversationContextBuilder` for same-session memory loading, ordering, de-duplication, message-limit trimming, token-budget trimming, prompt-history formatting, and bounded retrieval-query construction.
- Added `CHAT_HISTORY_MAX_TOKENS` configuration alongside `CHAT_HISTORY_MAX_MESSAGES`.
- Updated grounded prompt construction to use SYSTEM policy, Conversation History, Retrieved Context, and Current Question while preserving grounded no-answer and citation policy.
- Added non-streaming and SSE streaming regressions for same-session Conversation Memory.
- Production configuration validation for environment mode, debug policy, placeholder secrets, database password, CORS, trusted hosts, request limits, database pool, Redis timeouts, rate limits, and Celery time limits.
- Configurable API docs policy.
- CORS middleware with explicit origin, method, header, and credentials configuration.
- Trusted-host enforcement.
- API security headers and HTTPS-only production HSTS behavior.
- Global request-size middleware with `413 REQUEST_TOO_LARGE` responses.
- Upload hardening error codes for file size, empty file, file type, PDF signature, and filename validation.
- Redis-backed fixed-window rate limiting for login, refresh, upload, chat messages, and feedback.
- Database pool and Redis timeout configuration.
- Celery soft/hard time-limit configuration.
- Safe generic unhandled-exception responses.
- Logging redaction for secrets and business-content fields.
- Docker Compose `no-new-privileges:true` runtime hardening for application services.
- Backup/restore documentation and release readiness checklist.
- TASK-025 hardening regression tests.
- GitHub Actions backend CI workflow.
- Python 3.12 CI setup with pip caching and `pyproject.toml` dependency installation.
- PostgreSQL pgvector and Redis CI service-container verification.
- Alembic CI migration, single-head, and current-head verification.
- Ruff lint and format checks in CI.
- Unit, API, integration, and marker pytest execution with combined coverage XML.
- CI security scan for `create_all`, pickle serialization, raw SQL interpolation, hardcoded secrets, production debug, and unsafe logging.
- Docker runtime build and Docker Compose config verification in CI.
- CI artifact upload for `coverage.xml`, pytest reports, and logs.
- Generated CI verification artifact ignores for local runs.
- Expanded append-only AuditLog coverage.
- Sanitized Audit event metadata.
- Audit events for selected authentication, administration, Document, Chat, and Feedback operations.
- Atomic success AuditLog persistence.
- Best-effort failure AuditLog persistence.
- Admin-only AuditLog report.
- Audit filters and stable pagination.
- Audit privacy and transaction tests.
- FeedbackRating enum.
- Feedback model and migration.
- Atomic per-message feedback upsert.
- Owner-only Assistant-message feedback.
- Manager Department-scoped Feedback report.
- Admin global Feedback report.
- Feedback pagination and filters.
- Feedback concurrency and privacy tests.
- Backend-managed LLM source markers.
- Strict citation-marker validation.
- Citation source mapping.
- Public citation-number normalization.
- Permission revalidation after LLM generation.
- MessageCitation model and migration.
- Server-generated citation excerpts.
- Atomic message and citation persistence.
- Citation-enriched Chat responses and history.
- Citation security and race-condition tests.
- LLMProvider abstraction.
- Configurable OpenAI-compatible LLM provider.
- Grounded Chat prompt builder.
- Permission-aware Hybrid Retrieval integration.
- Context-token budgeting.
- Recent Chat history prompting.
- Fixed no-answer behavior.
- No-answer sentinel handling.
- Atomic USER and ASSISTANT message persistence.
- Chat answer token and response-time tracking.
- Chat message submission API.
- ChatSession and ChatMessage models.
- PostgreSQL ChatMessageRole enum.
- Owner-only chat-session access.
- Chat-session create API.
- Chat-session list API.
- Chat-session detail and history API.
- Paginated chat-session and message-history queries.
- Internal chat-message persistence service.
- SYSTEM-message hiding.
- Chat ownership security tests.
- PostgreSQL full-text keyword retrieval.
- GIN full-text index for DocumentChunk text.
- Permission-aware keyword ranking.
- Exact identifier retrieval.
- Weighted Reciprocal Rank Fusion.
- Semantic and keyword candidate deduplication.
- Stable hybrid retrieval results.
- Hybrid permission-leakage tests.
- Real Vietnamese hybrid-retrieval tests.
- Semantic RetrievalService abstraction.
- Query embedding integration for retrieval.
- Permission-aware pgvector retrieval.
- READY-only Document filtering for retrieval.
- Soft-delete and archived-document exclusion during retrieval.
- Configurable retrieval top-k.
- Configurable relevance threshold.
- Stable typed RetrievalHit results.
- Permission leakage and real semantic-retrieval tests.
- Automatic Document processing enqueue after upload.
- End-to-end Celery Document-processing pipeline.
- PDF extraction integration.
- Page-aware chunking integration.
- Local embedding integration.
- Atomic DocumentChunk persistence.
- READY and FAILED Document transitions.
- Bounded pipeline retries.
- Processing idempotency and concurrent-claim protection.
- End-to-end worker and pipeline tests.
- EmbeddingProvider abstraction.
- Local Sentence Transformers embedding provider.
- Multilingual query and passage embeddings.
- Batch embedding and normalization.
- Embedding validation.
- DocumentChunk SQLAlchemy model.
- PostgreSQL pgvector extension.
- HNSW cosine vector index.
- Atomic chunk replacement.
- Embedding and pgvector tests.
- TokenCounter abstraction.
- Tiktoken token counter.
- Page-aware token chunker.
- Paragraph-first chunk splitting.
- Sentence splitting fallback.
- Token-window fallback.
- Configurable token overlap.
- Stable page metadata for chunks.
- Deterministic chunk SHA-256 checksums.
- Chunking unit and integration tests.
- TextExtractor abstraction.
- PyMuPDF PDF text extractor.
- Page-level text extraction.
- Unicode and whitespace normalization.
- PDF extraction result models.
- Encrypted PDF detection.
- Corrupted PDF handling.
- PDF page-limit validation.
- No-usable-text detection.
- PDF extraction unit and integration tests.
- Celery application.
- Redis broker and result backend configuration.
- Document-processing queue.
- Worker connectivity task.
- Document-processing task skeleton.
- Atomic Document processing claim.
- Document processing status transitions.
- Bounded task retries.
- Worker-specific async database handling.
- Celery unit and integration tests.
- Permission-aware Document listing.
- Reusable Document access filters.
- Document detail endpoint.
- Document status endpoint.
- Secure Document download.
- Document metadata update endpoint.
- Document soft-delete endpoint.
- Direct User and Department permission APIs.
- Department document-reference protection.
- Document access-control tests.
- FileStorage abstraction.
- Secure LocalFileStorage implementation.
- PDF multipart upload endpoint.
- Streaming upload size enforcement.
- PDF extension, MIME and signature validation.
- SHA-256 file checksum.
- UUID-based storage keys.
- Duplicate-document detection.
- Filesystem/database failure compensation.
- Document upload tests.

- Document status enum.
- Document access-scope enum.
- Document permission-level enum.
- Document SQLAlchemy model.
- Document permission SQLAlchemy model.
- Document access-scope database constraint.
- Exactly-one permission grantee constraint.
- Document and permission indexes.
- Document Alembic migration.
- Document model unit and integration tests.

- User administration APIs.
- Department administration APIs.
- Pagination, filtering and sorting.
- User soft deactivation.
- Refresh-token revocation on deactivation.
- Last active Admin protection.
- Basic audit-log model and migration.
- User and Department audit events.
- User and Department API tests.

- Generic role-based dependency factory.
- Admin-only authorization guard.
- Manager-or-Admin authorization guard.
- Department-scoped access policies.
- User management policies.
- Role assignment policies.
- RBAC unit and API dependency tests.
- JWT access token generation and validation.
- Opaque refresh token generation.
- Hashed refresh token persistence.
- Refresh token rotation.
- Login endpoint.
- Refresh endpoint.
- Logout endpoint.
- Current user endpoint.
- Authentication tests.
- Department SQLAlchemy model.
- User SQLAlchemy model.
- UserRole enum.
- User-Department relationship.
- Password hashing and verification helpers.
- User and Department Alembic migration.
- Development Admin seed command.
- User and Department model tests.
- Initial project documentation package.
- Product requirements.
- Architecture specification.
- Database design.
- API specification.
- Security and RBAC rules.
- RAG and document processing design.
- Roadmap and task breakdown.
- Async SQLAlchemy engine.
- Async database session factory.
- Declarative SQLAlchemy base.
- Async Alembic configuration.
- Database foundation baseline migration.
- Database readiness endpoint.
- Database readiness tests.

### Verified

- Verified TASK-033 final acceptance: focused unit/API integration suites, Admin/RBAC/Web Search regression, default backend regression, Ruff, format check, compileall, security scan, Alembic current/head/upgrade, Docker Compose config/build/up/ps, API/worker/PostgreSQL/Redis/migration runtime checks, Celery worker ping, and live Docker Admin analytics route RBAC smoke passed.

- Verified TASK-032 final acceptance: focused unit/API integration suites, RBAC/provider API regression, default backend regression, Ruff, format check, compileall, security scan, Alembic current/head/upgrade, Docker Compose config/build/up/ps, API/worker/PostgreSQL/Redis/migration/OCR runtime checks, Celery worker ping, and live Docker Admin monitoring endpoint smoke passed.

- Verified TASK-031 final Docker acceptance: Docker version/info, Compose config/build/up/ps, PostgreSQL, Redis, API, worker, one-shot migration exit 0, API health, and Alembic current/heads/upgrade head all passed with head `20260803_0010`.
- Verified TASK-031 final test acceptance: focused Web Search unit suite, Web Search admin API integration, chat/citation/streaming API integration, web citation migration integration, Conversation Memory integration, grounded answer citation/persistence integration, full hybrid retrieval integration, citation revalidation/message citation migration integration, and full default regression passed.
- Verified TASK-031 quality/security acceptance: Ruff check, Ruff format check, compileall, and security scan passed; runtime smoke covered internal-only disabled provider status, web-only/hybrid mock-provider paths, no-answer, SSE streaming, internal citation, and web citation source typing.
- Verified TASK-030 local gates: full unit suite, focused OCR suite, default non-integration suite, default API/integration selections, Ruff lint, Ruff format, security scan, compileall, and Alembic source head 20260722_0009.
- Attempted TASK-030 Docker/API/integration runtime verification; completion remains blocked by local Docker Desktop daemon unavailability and asyncpg connection timeout to the Docker-backed PostgreSQL endpoint.

- Verified TASK-029 focused unit, integration, API, and streaming regression suites for Conversation Memory, no-answer, grounding, citation, token-budget, message-limit, and same-session isolation behavior.
- Verified TASK-029 Docker build, Docker restart, healthy API/worker/Postgres/Redis, API readiness, host quality gates, runtime API `pip check`, default pytest, streaming integration marker, chat API integration, and focused conversation-memory integration regressions.
- Verified TASK-028 live UI acceptance recovery against the real local Docker frontend/backend stack with PostgreSQL, Redis, deterministic UAT LLM provider, idempotent UAT seed, live role workflows, upload-to-READY, permissions, SSE chat, citations, feedback, audit, responsive/accessibility smoke, frontend gates, mock E2E, live E2E, and backend regressions.
- Completed Docker/Python 3.12 runtime verification for TASK-026.
- Verified Multi-LLM providers, grounding, privacy, and LLM-disabled startup in Docker.
- Completed Docker runtime verification.
- Completed DB-backed hardening regression.
- Completed end-to-end release smoke test.
- Completed persistence and failure-recovery verification.

### Changed

- UAT overlay now runs `python -m app.scripts.seed_uat_data` before API/worker startup with fixed local-only test credentials for Admin, Manager, and Staff UAT accounts.

### Fixed

- Made UAT account seeding deterministic and idempotent across Docker rebuild/recreate/mode switching by adding a one-shot `uat-seed` service and repairing existing known UAT users in place.
- Fixed TASK-034.1 local Ollama SSE `STREAM_TIMEOUT` by separating provider timeout, stream max duration, and heartbeat budgets while preserving buffer-after-validation grounding.
- Disabled Ollama reasoning effort for local `qwen3:4b` requests where supported and stripped visible `<think>` blocks before citation validation.
- Fixed OCR configuration validation so maximum width, height, and pixel caps remain independent bounded limits.
- Fixed TASK-030 Ruff import ordering and formatting issues in OCR/document-processing code and tests.

- Fixed TASK-028 live acceptance blockers for `.example.test` UAT email validation, Admin user edit/reactivation controls, Department edit/delete controls, toast click interception, mobile drawer Escape handling, and feedback controls on completed live SSE answers.
- Released the Document download read transaction before streaming file bytes and kept download response metadata detached from ORM state.



### Added

- Implemented TASK-028 frontend console foundation with React, TypeScript, Vite, role-aware shell, authentication, typed API client, POST SSE chat client, documents, users, departments, feedback, audit logs, system status, and profile routes.
- Added UI documentation for Stitch workflow, Stitch screen prompts, design system, screen inventory, React Bits motion policy, frontend architecture, and frontend testing.
- Added controlled motion primitives for login background, chat spotlight, and waiting text with reduced-motion support.
- Added frontend lint, typecheck, Vitest, Playwright smoke E2E, production build, and optional Docker Compose frontend profile.

### TASK-034.1 In Progress

- Audited real/local LLM grounded runtime boundaries before implementation.
- Strengthened grounded prompt policy to require retrieved-context-only evidence, no unsupported inference, exact preservation of numbers/dates/names/conditions/exceptions, conflict reporting, and no approximate-to-exact conversion.
- Added a grounded-answer service guard so `ANSWERED` results without validated citations are rejected before persistence.
- Added focused unit tests for strict prompt requirements and invalid answered/no-citation rejection.
- Added a skipped-by-default `real_llm_acceptance` report validator and marker for manual real-provider acceptance.
- Created local ignored synthetic acceptance PDFs and report template under `artifacts/task-034-1/`.
- Documented deterministic UAT versus real LLM acceptance, local Ollama/LM Studio configuration, external-provider privacy implications, and current local runtime blockers.

### TASK-034.1 Runtime Status

- Docker Desktop, PostgreSQL, Redis, API, worker, and host Ollama `qwen3:4b` are reachable in the current local environment.
- Live SSE verification for Nova Digital CEO, CTO, and NovaAssist completed twice each with no `STREAM_TIMEOUT`.
- TASK-034.1 remains in progress until the full strict real-LLM matrix and manual claim report are complete.


#### RAG-H2.1 — Reranker Authority

- Fixed `_preserve_reranked_hit_order()` so reranker output remains authoritative over later prompt heuristic ranking.
- Added regression coverage for reranker-order preservation.
- Verified `61 passed`, `27 passed`, and `147 passed` across focused RAG/retrieval unit suites.
- Recorded runtime limitation: cross-encoder model is unavailable and falls back to alignment reranking.
- Recorded diagnostics limitation: API container currently has no `RAG_DIAGNOSTICS_ENABLED` environment variable.


#### Fixed — LLM_GENERATION_FAILED runtime incident

- Removed invalid `question=grounding_question` argument from `_draft_from_generation()` claim validation call.
- Root cause was a `NameError` caused by an incomplete H5.1 change, not an Ollama failure.
- Verified Ollama OpenAI-compatible `/v1/chat/completions` provider path independently.
- Regression verification: `61 passed` and `147 passed` focused suites.
- Live generation failure is resolved; RAG accuracy issue for salary lookup remains open.

#### Fixed — salary amount false NO_ANSWER

- Prevented generic quantity completeness checks from incorrectly handling `AMOUNT` salary questions.
- Prevented grade labels such as `N6 Head` from behaving like answer number/unit requirements.
- Preserved quantity regression behavior for genuine COUNT/DURATION/NUMBER questions.
- Added salary-band regression coverage.
- Verification: 63 grounded-answer tests passed; 149 focused combined tests passed.
- Live UAT: Head 65-110 million and Engineering Manager 42-70 million/month both pass with citations.
