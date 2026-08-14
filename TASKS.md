
# Implementation Tasks

## Summary

TASK-001 -> TASK-034: Completed. TASK-035 is not started.

Phase 1: Completed.
Phase 2 backend roadmap: Completed through TASK-034.
Current task: UAT FIX -- UX Selectors + LLM_NOT_CONFIGURED completed. TASK-035 not started.
Next roadmap task: TASK-035 -- Final Acceptance Test & Release Candidate is pending and not started.
TASK-028 live acceptance: COMPLETED_AND_VERIFIED.
READY FOR USER EXPERIENCE: YES.
TASK-029 implementation completed: Yes.
TASK-030 implementation completed: Yes. TASK-031 status: Completed. TASK-032 status: Completed. TASK-033 status: Completed. TASK-034 status: Completed. TASK-035 status: Not started.

## Rules

- Implement tasks in order unless there is a clear technical reason.
- Each task must include tests or a documented verification path.
- After each task, update `PROJECT_STATUS.md` and `CHANGELOG.md`.

## TASK-001 — Initialize backend project

**Status:** Completed.

### Deliverables

- Python project configuration.
- `app/main.py`.
- `app/core/config.py`.
- Health live endpoint.
- First test.
- `.gitignore`.
- `.env.example`.

---

## TASK-002 — Docker infrastructure

**Status:** Completed.

### Deliverables

- Docker Compose with PostgreSQL pgvector and Redis.
- Volume persistence.
- Health checks.

---

## TASK-003 — Database foundation

**Status:** Completed.

### Deliverables

- Async SQLAlchemy session.
- Declarative base.
- Alembic config.
- Database readiness check.

---

## TASK-004 — User and department models

**Status:** Completed.

### Deliverables

- Department model.
- User model.
- Role enum.
- Initial migration.
- Development Admin seed command.

---

## TASK-005 — Authentication

**Status:** Completed.

### Deliverables

- Login.
- Access token.
- Refresh token persisted as hash.
- Refresh.
- Logout.
- Current user endpoint.

---

## TASK-006 — RBAC dependencies and policies

**Status:** Completed.

### Deliverables

- Role guards.
- Permission policy helpers.
- Tests for Admin, Manager, and Staff.

---

## TASK-007 — User and department APIs

**Status:** Completed.

### Deliverables

- Admin CRUD.
- Pagination.
- Validation.
- Basic audit log events.

---

## TASK-008 — Document data model

**Status:** Completed.

### Deliverables

- Document model.
- Access scope.
- Status enum.
- Document permission model.
- Migration.

---

## TASK-009 — Local file storage and upload

**Status:** Completed.

### Deliverables

- Storage abstraction.
- Local implementation.
- PDF validation.
- Upload endpoint.
- Checksum.
- 202 response.

---

## TASK-010 — Document listing and access control

**Status:** Completed.

### Deliverables

- List/detail/download/update/delete.
- Permission-aware filters.
- Direct User and Department grants.

---

## TASK-011 — Celery and Redis worker

**Status:** Completed.

### Deliverables

- Celery app.
- Redis broker and result backend configuration.
- Document queue.
- Worker ping task.
- Document task skeleton.
- Worker-specific database session.

---

## TASK-012 — PDF extraction

**Status:** Completed.

### Deliverables

- TextExtractor abstraction.
- PyMuPDF extractor.
- Page-level text.
- Unicode and whitespace normalization.
- Extraction result models.

---

## TASK-013 — Chunking

**Status:** Completed.

### Deliverables

- Token-aware chunker.
- Overlap.
- Metadata.
- Unit tests.

---

## TASK-014 — pgvector and embeddings

**Status:** Completed.

### Deliverables

- Extension migration.
- Chunk model with vector.
- Embedding provider interface.
- Batch embedding.

---

## TASK-015 — Document processing pipeline

**Status:** Completed.

### Deliverables

- End-to-end worker.
- Idempotent reprocess.
- READY/FAILED state.

---

## TASK-016 — Retrieval service

**Status:** Completed.

### Deliverables

- Semantic search.
- Permission filtering.
- Top-k and threshold.
- Leakage tests.

---

## TASK-017 — Keyword and hybrid search

**Status:** Completed.

### Deliverables

- PostgreSQL full-text search.
- Hybrid score merge.
- Permission-aware hybrid retrieval.

---

## TASK-018 — Chat data model and APIs

**Status:** Completed.

### Deliverables

- Session and message models.
- Create/list/read session.
- Ownership checks.
- Visible message history.

---

## TASK-019 — LLM provider and grounded answer

**Status:** Completed.

### Deliverables

- LLM provider interface.
- OpenAI-compatible provider.
- Grounded prompt builder.
- Context token budget.
- No-answer behavior.
- Atomic USER/ASSISTANT persistence.
- POST Chat message endpoint.

---

## TASK-020 — Citation validation

**Status:** Completed.

### Deliverables

- Source markers.
- Citation mapping.
- Permission revalidation.
- Excerpt response.
- MessageCitation model and migration.
- Citation-enriched Chat responses and history.

---

## TASK-021 — Feedback

**Status:** Completed.

### Deliverables

- Upsert feedback.
- Manager/Admin reporting scope.

---

## TASK-022 — Audit log expansion

**Status:** Completed.

### Deliverables

- Audit service.
- Admin filters.
- Events for documents and chat.

---

## TASK-023 — Docker full backend stack

**Status:** Completed.

### Deliverables

- Backend container.
- Worker container.
- Startup/migration flow.

---

## TASK-024 — CI pipeline

**Status:** Completed.

### Deliverables

- GitHub Actions workflow in `.github/workflows/ci.yml`.
- Python 3.12 setup with pip cache.
- Dependency installation from `pyproject.toml`.
- PostgreSQL service container with pgvector extension verification.
- Redis service container with health verification.
- Alembic `upgrade head` with single-head and current-equals-head checks.
- Ruff lint and format checks.
- Unit, API, integration, and marker pytest suites.
- Combined coverage XML report.
- Security scan for forbidden schema creation, pickle serialization, raw SQL interpolation, hardcoded secrets, production debug, and unsafe logging.
- Docker runtime build verification.
- Docker Compose config validation.
- Artifact upload for `coverage.xml`, pytest reports, and logs.

---

## TASK-025 — MVP hardening

**Status:** Completed.

### Deliverables

- Rate limiting.
- CORS config.
- Upload edge cases.
- Retrieval evaluation set.
- Security regression tests.
- Static retrieval evaluation fixture.

### TASK-025 verification

- Production configuration validation.
- CORS and trusted-host enforcement.
- Security headers and request-size limiting.
- Upload edge-case hardening and error-code coverage.
- Redis-backed rate limiting.
- Database/Redis timeout and pool configuration.
- Celery JSON-only and bounded time-limit configuration.
- Safe generic exception responses and logging redaction.
- Docker `no-new-privileges` runtime hardening.
- Backup/restore and release checklist documentation.

### Final recovery verification

- Docker Desktop API recovered; `docker version`, `docker info`, `docker ps`, and Compose v5.2.0 worked.
- Compose config passed with PostgreSQL, Redis, migration, API, worker, and test profile services.
- PostgreSQL and Redis were healthy; migration exited 0; Alembic current/head stayed at `20260722_0009`.
- API and worker ran Python 3.12.13 as non-root UID 10001.
- DB-backed auth, administration, document, chat, citation, feedback, and audit tests passed with no zero-match suite counted.
- Celery, embedding, processing, semantic, hybrid, and LLM provider marker suites passed.
- End-to-end Docker API smoke passed with login, department/user creation, PDF upload, worker processing to READY, permission grant, chat session, expected `LLM_NOT_CONFIGURED` grounded path with runtime LLM disabled, feedback, feedback report, audit report, RBAC checks, and rate-limit checks.
- Persistence survived `docker compose down` / `docker compose up -d` without `-v`; database rows, upload file, READY status, chat session, feedback, audit rows, and model cache were retained.
- PostgreSQL and Redis failure/recovery checks passed.
- Security scan, Ruff, format check, compile, Docker `pip check`, and host `pip-audit` passed.
---

## Phase 2 Roadmap

Phase 2 extends the completed backend MVP with multi-provider LLM support, streaming UX readiness, a working frontend console, conversation memory, multimodal and web inputs, operational analytics, observability, production deployment, enterprise authentication, and the v2.0 release.

---

## TASK-026 — Multi-LLM Provider Support

**Status:** Completed.

### Goal

Extend the current LLM abstraction to support multiple safely configurable providers without changing grounded-answer or citation-validation contracts.

### Provider scope

- OpenAI-compatible providers, including OpenAI, OpenRouter, Ollama OpenAI endpoint, LM Studio OpenAI endpoint, and custom enterprise gateways.
- Azure OpenAI.
- Google Gemini.
- Anthropic Claude.

### Acceptance criteria

- Provider registry/factory validates supported provider names and creates providers lazily.
- LLM disabled requires no provider keys.
- Only the selected enabled provider requires its provider-specific configuration.
- Provider secrets are hidden from repr, logs, and validation errors.
- No provider network call happens during import or application startup.
- Provider calls use bounded timeout, bounded retry, backoff, and safe error normalization.
- Raw provider request/response bodies, prompts, retrieved context, answers, document text, citation excerpts, API keys, and authorization headers are not logged or returned.
- OpenAI-compatible, Azure OpenAI, Gemini, and Anthropic adapters normalize content, finish reason, usage, provider name, model, and safe request id when available.
- Ollama, LM Studio, and OpenRouter are supported through the shared OpenAI-compatible adapter.
- Grounded-answer, selected-context, citation-validation, no-answer, and rollback behavior remain provider-independent.
- Existing Chat API request/response compatibility is preserved.
- Docker startup works with `LLM_ENABLED=false` and no LLM container is added.
- No database migration is introduced unless provider/model metadata storage becomes strictly required.
- Unit, API, integration, LLM provider marker, security scan, Ruff, format, and compile checks pass.

### TASK-026 verification

- Completed Docker/Python 3.12 runtime verification after safe storage cleanup and Docker Desktop/WSL backend recovery.
- Verified default Docker stack starts with `LLM_ENABLED=false`, no external provider container, no provider credentials required, and no LLM provider network call on import.
- Verified Alembic head/current remained `20260722_0009` with a single source head and no migration created.
- Verified Multi-LLM provider marker, provider unit, Chat API, grounded-answer, citation, rollback, privacy, Docker `pip check`, security scan, Ruff, format, and compile checks.

---

## TASK-027 — Streaming Chat with Server-Sent Events

**Status:** Completed.

### Goal

Add controlled streaming chat responses using Server-Sent Events while preserving grounded-answer, citation validation, audit, feedback, and persistence guarantees.

### Acceptance criteria

- Streaming endpoint or mode is designed without breaking the existing non-streaming Chat API.
- Partial tokens are never persisted as final answers before citation validation succeeds.
- Provider streaming errors return safe standardized errors and do not leak raw provider content.
- Client disconnect, timeout, retry, and cancellation behavior are bounded and tested.
- Citation markers are validated before final answer persistence and public citation display.
- Rate limiting and authentication apply to streaming requests.

### TASK-027 completion notes

- Added `POST /api/v1/chat/sessions/{session_id}/messages/stream` using `text/event-stream`.
- SSE event ordering is centralized and tested for started, delta, citations, completed, error, cancelled, and heartbeat events.
- Strategy is buffer-after-validation: no provisional provider tokens are public or persisted before grounding and citation validation pass.
- Provider streaming capability is represented as safe fallback metadata; native provider stream parsing is deferred until incremental grounding is designed.
- Docker runtime verification passed with Python 3.12.13, streaming marker, LLM provider marker, chat regression, citation regression, and provider unit tests.
- No schema migration was created; Alembic head remains `20260722_0009`.

---

## TASK-028 — Frontend UI Foundation & Test Console

**Status:** Completed.

### Goal

Create a professional, usable frontend interface for operating and testing the Enterprise AI Knowledge Assistant.

### Required frontend capabilities

- Authentication.
- Current-user profile.
- Department management.
- User management.
- Document upload.
- Upload progress.
- Document processing status.
- Document list and detail.
- Document permissions.
- Chat sessions.
- Chat messages.
- Streaming response UI.
- Citation display.
- Feedback submission.
- Feedback report access.
- Audit-log access.
- LLM provider/model selection when permitted.
- Health/readiness status.
- Rate-limit feedback.
- Standard loading, empty, and error states.

### Interface requirements

- Professional enterprise visual design.
- Responsive desktop-first layout.
- Accessible controls.
- Clear navigation.
- Consistent design system.
- Dark/light theme readiness.
- Reusable components.
- Typed API client.
- Authentication state management.
- Error boundary.
- Loading skeletons.
- Empty states.
- Toast/notification system.
- Form validation.
- Permission-aware navigation.
- No fake production data.

### Scope boundary

TASK-028 is the working and testing interface for the existing system. TASK-032 is the advanced analytics dashboard and must not duplicate TASK-028 scope.

### TASK-028 verification notes

- React/TypeScript/Vite frontend implemented in `frontend/` with typed API client, auth state, protected routes, role-aware navigation, documents, chat with POST SSE, citations, users, departments, feedback, audit logs, system status, profile, reusable states, and controlled motion primitives.
- Stitch workflow, screen prompts, design system, screen inventory, React Bits inventory, frontend architecture, and frontend testing docs created in `docs/ui/`.
- Frontend lint, typecheck, Vitest, Playwright smoke E2E, production build, and Docker frontend build passed.
- Docker backend regression passed for streaming chat marker, LLM provider marker, auth/RBAC, documents, chat, citations, feedback, audit logs, rate limiting, security scan, Ruff, format, compile, host pip check, and Docker pip check.
- TASK-028 live UI acceptance recovery passed with the real Docker frontend/backend stack, idempotent UAT seed, verified Admin/Manager/Staff accounts, upload-to-READY, permissions grant/revoke, live SSE chat, citations, feedback, audit, responsive and keyboard smoke, frontend quality gates, mock E2E, live E2E, and backend regression suites.
- UAT account stability fix keeps Development Admin separate from fixed UAT Admin/Manager/Staff accounts and makes `compose.uat.yaml` run an idempotent one-shot `uat-seed` without resetting volumes or deleting unrelated users.
- TASK-029 Conversation Memory is completed. TASK-030 OCR and Image Understanding recovery is in progress and is not completed until Docker/API/integration acceptance passes. TASK-032 analytics was not implemented.

### Acceptance criteria

- Frontend foundation runs locally and communicates with the backend through a typed API client.
- Authenticated and permission-aware navigation is implemented.
- Core backend workflows can be operated from the UI without fake production data.
- Chat UI can display standard and streaming answer states, citations, provider/model status when allowed, and safe error/rate-limit feedback.
- Reusable design-system components cover forms, tables, navigation, skeletons, empty states, errors, notifications, and theme readiness.
- Frontend tests or documented verification cover primary workflows and permission-aware states.

---

## TASK-029 -- Conversation Memory

**Status:** Completed.

### Goal

Add configurable same-session conversation memory that improves follow-up questions without allowing old chat content to bypass document permissions or grounded-answer policy.

### Implemented

- Added `ConversationContextBuilder` in `app/chat/conversation_context_builder.py`.
- Loads USER, ASSISTANT, and internal SYSTEM messages from the current owned ChatSession only.
- Orders memory by `created_at ASC, id ASC` and removes duplicate message IDs.
- Trims the memory window by `CHAT_HISTORY_MAX_MESSAGES` and `CHAT_HISTORY_MAX_TOKENS`.
- Formats prompt history as a bounded `<conversation_history>` block.
- Builds a bounded retrieval query that includes selected recent history plus the current question.
- Keeps Hybrid Retrieval mandatory and preserves grounded no-answer behavior.
- Keeps citations tied only to retrieved context source markers.
- Applies the same behavior to non-streaming `/messages` and streaming `/messages/stream` because both use `GroundedAnswerService.answer_question()`.
- Adds no migration, schema, memory table, cache, vector memory, summary memory, or LLM summarization.
- Does not persist formatted prompts or formatted conversation history.

### Verification

- Unit tests cover builder formatting, ordering, de-duplication, message limit, token budget, retrieval-query bounding, prompt format, citation-source separation, and service behavior.
- Integration tests cover leave-policy and working-policy follow-ups, no-answer follow-ups, repository filtering, internal SYSTEM memory handling, and citation mapping with source-like markers in history.
- API tests cover non-streaming same-session isolation.
- Streaming tests cover `/messages/stream` memory parity.

### Acceptance criteria

- AI remembers conversation within the same session.
- AI does not remember other sessions.
- ConversationContextBuilder owns memory load, trim, token budget, and format.
- Message and token limits are configurable.
- No migration or schema change is introduced.
- Prompts are not persisted.
- Streaming, non-streaming, citation, grounding, no-answer, Docker, regression, and documentation checks are required for completion.

---
## TASK-030 -- OCR and Image Understanding

**Status:** In Progress.

### Goal

Extend ingestion and retrieval to support OCR and image-based document understanding with safe processing limits.

### Implemented during recovery

- Upload validation accepts `application/pdf`, `image/png`, and `image/jpeg` with matching extensions and signatures.
- Storage keys use the server-selected primary extension (`.pdf`, `.png`, `.jpg`) and never trust client paths.
- `ExtractionRouter` keeps native PDF text when usable, OCRs low-quality/scanned PDF pages, and OCRs standalone PNG/JPEG documents.
- OCR runs through an `OCRProvider` abstraction backed by Tesseract; no OCR subprocess runs at import/startup.
- Image safety validation uses Pillow verify/reopen, EXIF transpose, RGB conversion, PNG normalization, and bounded width/height/pixel limits.
- Extracted pages preserve `page_number`, `extraction_method`, `source_type`, optional confidence, width, height, and warnings for downstream chunk/retrieval/citation metadata.
- The existing Celery document-processing pipeline passes stored MIME metadata to the extractor without changing the upload or Chat API contracts.
- Dockerfile runtime installs `tesseract-ocr`, `tesseract-ocr-eng`, and `tesseract-ocr-vie`.
- No schema migration was added; Alembic source head remains `20260722_0009`.

### Recovery verification completed

- `python -m pytest tests/unit -q` passed: 876 passed.
- TASK-030 focused OCR suite passed: 152 passed.
- Conversation/grounding/citation/OCR-source unit compatibility passed: 65 passed.
- Default non-integration suite passed: 957 passed, 643 deselected by configured integration marker filtering.
- Default API directory passed: 46 passed, 226 deselected.
- Default integration directory non-integration selection passed: 26 passed, 417 deselected.
- `python -m ruff check .` passed.
- `python -m ruff format --check .` passed.
- `python .github/scripts/security_scan.py` passed.
- `python -m compileall app tests` passed.
- `alembic heads` reports `20260722_0009 (head)`.

### Current blocker

Docker runtime acceptance is blocked in the local environment. Docker Desktop Service is stopped; `Start-Service com.docker.service` is denied even with escalation; `docker compose ps`, `docker version`, `docker info`, and `docker desktop restart` time out. Local Postgres port `55432` is open, but asyncpg connection startup times out, so Alembic `upgrade head/current` and Docker-backed API/integration suites cannot be counted as passing.

### Acceptance criteria

- OCR/image processing is asynchronous and bounded: implemented locally, Docker worker runtime not verified.
- Extracted text keeps page/source metadata for retrieval and citations: implemented and unit verified.
- Unsupported, encrypted, oversized, or low-quality files fail safely: implemented and unit verified.
- No OCR model download or external call occurs during import/startup: implemented by subprocess-only Tesseract provider and unit verified.
- Docker/API/worker/Postgres/Redis/migration verification: blocked by Docker runtime availability.

---

## TASK-031 -- Web Search Integration

**Status:** Completed.

### Goal

Add controlled web search as an optional source with clear provenance and policy separation from internal enterprise documents.

### Implemented

- Added `app/web_search/` with provider protocol, provider registry, provider manager, mock provider, Bing provider, DuckDuckGo provider, and Google Custom Search provider.
- Added backend-only `WEB_SEARCH_MODE` values: `internal_only`, `hybrid`, and `web_only`.
- Added config for enabled state, provider, max results, timeout, max content length, external-call allow flag, user agent, retry, provider endpoints, and provider credentials.
- Added `WebSearchIntentClassifier` so hybrid mode keeps internal retrieval first and adds web search only for current/web intent or empty internal hits.
- Integrated web search into `GroundedAnswerService` without changing non-streaming or streaming Chat API request bodies.
- Added web content and URL normalization that strips HTML/script/style/hidden/comment/control data, bounds content, rejects unsafe URLs, and does not fetch raw webpages.
- Added `CitationSourceType` with `INTERNAL` and `WEB`.
- Added web citation persistence fields and migration `20260803_0010_add_web_search_citations.py`.
- Internal citations keep document/chunk permission revalidation; web citations use backend provider title and URL and no internal document IDs.
- Added Admin-only `/api/v1/web-search/provider-status` and `/api/v1/web-search/test` endpoints.
- Added unit, API, streaming, and migration tests for web search behavior.

### Final verification completed

- Focused TASK-031 unit suite: 137 passed.
- Web Search unit suite: 25 passed.
- Web Search admin API integration suite: 3 passed.
- Chat/citation/streaming API integration acceptance suite: 8 passed.
- Web citation migration integration suite: 2 passed.
- Conversation Memory integration suite: 4 passed.
- Grounded answer citation/persistence integration suites: 8 passed.
- Hybrid retrieval integration suite: 19 passed.
- Citation revalidation and message citation migration integration suites: 17 passed.
- Default non-integration regression suite: 997 passed, 650 deselected.
- `python -m ruff check .` passed.
- `python -m ruff format --check .` passed.
- `python -m compileall app tests` passed.
- `python .github/scripts/security_scan.py` passed.
- `docker version`, `docker info`, `docker compose config`, `docker compose build --quiet`, `docker compose up -d`, and `docker compose ps` passed.
- PostgreSQL, Redis, API, worker, migration, API health, and Alembic current/head/upgrade checks passed in Docker.
- Runtime smoke verified default disabled/internal-only provider status, no-answer chat, SSE streaming, UAT internal citation, mock-provider `internal_only`, `web_only`, `hybrid`, no-internal-hit intent, and web citation source typing.

### Acceptance criteria
- Web search is disabled by default and configured explicitly: implemented and unit tested.
- Search results are marked separately from internal document sources: implemented through `source_type` and schema/migration.
- Data residency and external transfer warnings are documented: implemented in README, SECURITY, SETUP, ENVIRONMENT_VARIABLES, RAG_DESIGN, and API_SPEC.
- Citations distinguish web sources from internal document citations: implemented and verified by unit, API, streaming, DB-backed migration, and runtime smoke checks.

---

## TASK-032 -- Admin Dashboard & System Monitoring

**Status:** Completed.

### Goal

Provide backend-only administrative monitoring for system health, providers, workers, queues, version, uptime, and safe aggregate statistics.

### Acceptance criteria

- Dashboard scope is analytics/reporting, not the core operating console from TASK-028.
- Aggregations avoid exposing chat content, prompts, retrieved context, citation excerpts, feedback reasons, or secrets.
- Role-based access is enforced server-side.
- Metrics are documented and tested for safe filtering/pagination.

---


### TASK-032 completion notes

Implemented backend-only Admin Monitoring APIs under `/api/v1/admin`:

- `GET /api/v1/admin/system`
- `GET /api/v1/admin/health`
- `GET /api/v1/admin/providers`
- `GET /api/v1/admin/workers`
- `GET /api/v1/admin/statistics`
- `GET /api/v1/admin/queues`
- `GET /api/v1/admin/version`

The APIs reuse existing Admin RBAC, return safe aggregate/status data only, and do not expose secrets, prompts, retrieved context, chat content, citation excerpts, feedback reasons, storage keys, database URLs, Redis URLs, or API keys.

Monitoring covers API uptime, PostgreSQL, Redis, Celery worker, OCR, embedding configuration, LLM provider configuration, Web Search provider configuration, streaming registration, conversation memory configuration, queue state, statistics, and version/Alembic metadata.

No migration was created; Alembic head remains `20260803_0010`. No frontend/UI/Localization/Chat/Streaming/Conversation/Citation/OCR/Web Search behavior was changed.

Verification: focused unit/API integration, RBAC/provider API regression, default backend regression, Ruff, format check, compile, security scan, Alembic, Docker Compose, API/worker/PostgreSQL/Redis/migration/OCR runtime checks, Celery worker ping, and live Docker Admin monitoring endpoint smoke passed.

## TASK-033 -- Analytics & Reporting

**Status:** Completed.

### Goal

Add analytics and reporting for usage, feedback trends, document processing, retrieval quality, and safe operational reporting.

### Acceptance criteria

- Structured metrics cover safe request, dependency, retrieval, LLM, worker, and queue metadata.
- Logs remain redacted and content-free.
- Health/readiness and alerting guidance are documented.
- Trace/span data does not contain prompts, document text, answers, or secrets.


### TASK-033 completion notes

Implemented backend-only Admin Analytics APIs under `/api/v1/admin`:

- `GET /api/v1/admin/analytics/overview`
- `GET /api/v1/admin/analytics/chat`
- `GET /api/v1/admin/analytics/users`
- `GET /api/v1/admin/analytics/search`
- `GET /api/v1/admin/analytics/ocr`
- `GET /api/v1/admin/analytics/llm`
- `GET /api/v1/admin/analytics/feedback`
- `GET /api/v1/admin/analytics/audit`
- `GET /api/v1/admin/reports/export`

The APIs reuse existing Admin RBAC, support today/7d/30d/90d/custom UTC date filters, return safe aggregate analytics only, and export sanitized JSON/CSV reports. PDF export is intentionally rejected until safe backend PDF report infrastructure exists.

Analytics cover chat questions, sessions, average response time, token usage, active users, top users, top departments, new users, citation-inferred internal/hybrid/web searches, hashed top queries, top cited documents, image-document OCR success/failure, LLM latency/failures/token usage, feedback percentages/trends, and audit categories.

No migration was created; Alembic head remains `20260803_0010`. No frontend/UI/React/charts/Localization/Chat/Streaming/Conversation/Citation/OCR/Web Search/Celery behavior was changed.

Verification: unit analytics, API integration analytics, Admin/RBAC/Web Search monitoring regression, default backend regression, Ruff, format check, compile, security scan, Alembic, Docker Compose, API/worker/PostgreSQL/Redis/migration runtime checks, Celery worker ping, and live Docker Admin analytics route smoke passed.
---

## TASK-034 -- Production Deployment & Observability

**Status:** Completed.

### Goal

Prepare backend production deployment and observability without adding AI features, frontend UI, charting, localization, or changes to Chat/RAG/Citation/Conversation/Streaming/OCR/Web Search behavior.

### Acceptance criteria

- Production Compose provides PostgreSQL, Redis, one-shot migration, API, worker, reverse proxy, runtime validation, startup validation, restart policy, healthchecks, resource limits, and log limits.
- Reverse proxy supports forward headers, request/upload limits, SSE compatibility, security headers, and HTTPS-ready example configuration without committed certificates.
- Observability exposes safe Prometheus metrics for API, worker, Redis, PostgreSQL, OCR, embedding, LLM, Web Search, Streaming, Conversation, queues, version, and uptime.
- Request IDs, trace hooks, latency metrics, and structured request logging avoid prompts, context, OCR text, citation excerpts, secrets, credentials, tokens, Redis URLs, and database passwords.
- PostgreSQL and uploads backup/restore helpers include verification and guarded restore behavior.
- Development Docker Compose remains supported.

### TASK-034 completion notes

Implemented backend-only production deployment and observability:

- Added `compose.prod.yaml`, `.env.production.example`, runtime validation, Docker secret-file compatibility, resource limits, restart policies, healthchecks, log-size limits, and volume ownership initialization.
- Added Nginx reverse proxy config with forward headers, security headers, upload/request limits, SSE buffering disabled for streaming routes, HTTPS example config, and external `/metrics` blocking.
- Added in-process Prometheus metrics, request ID context, traceparent capture hooks, request latency/status logging, and `/metrics` for internal scrape use.
- Added Prometheus scrape config and Grafana provisioning/dashboard files under `deploy/`.
- Added PostgreSQL and uploads backup/restore PowerShell helpers with verification and guarded overwrite switches.
- Added unit, API, and integration tests for metrics, logging safety, runtime validation, production compose, reverse proxy, Prometheus/Grafana provisioning, backup/restore guardrails, RBAC/security regression, and Docker config.
- No database migration was created; Alembic head remains `20260803_0010`.
- Verification passed: Ruff, format check, compileall, security scan, pip dependency audit, pip check, Alembic heads/current/upgrade, default regression, focused integration/API suites, production Compose config/build/up/ps, development Compose config/build/up/ps, API/worker/PostgreSQL/Redis/migration health, reverse proxy health, internal metrics safety, external metrics blocking, Celery ping, backup/restore checks, Redis/PostgreSQL degraded readiness and recovery, API restart, and worker restart.

---

## TASK-035 -- Final Acceptance Test & Release Candidate

**Status:** Not started.

### Goal

Run final acceptance, release-candidate verification, and release-readiness documentation without starting post-release feature work.

### Acceptance criteria

- All completed-task acceptance criteria are verified or explicitly documented as deferred.
- Release candidate checks cover backend, frontend status, security, Docker, deployment, observability, data protection, backup/restore, failure recovery, and rollback.
- Documentation is current and does not include real secrets or fake production data.
- TASK-035 status is marked completed only after final acceptance verification passes.

### Notes

- The UAT UX + LLM configuration fix is not TASK-035.
- TASK-035 must not be marked completed by selector UX changes, fake UAT LLM verification, or focused UAT regressions alone.

---
## TASK-036 — Enterprise Release v2.0

**Status:** Pending.

### Goal

Prepare, verify, and document the Enterprise AI Knowledge Assistant v2.0 release.

### Acceptance criteria

- Release checklist covers backend, frontend, security, deployment, observability, data protection, and rollback.
- All Phase 2 acceptance criteria are verified or explicitly deferred.
- Documentation is current and does not include real secrets or fake production data.
- TASK-027 through TASK-035 statuses are accurate before release sign-off.

## TASK-034.1 -- Real / Local LLM Strict Grounded Runtime Acceptance

**Status:** In Progress.

TASK-034.1 stream timeout follow-up: local Ollama `qwen3:4b` SSE was verified for Nova Digital CEO, CTO, and NovaAssist twice each with no `STREAM_TIMEOUT`; full strict matrix acceptance remains required before completion.

### Goal

Verify the system as a real Enterprise RAG Assistant using a real/local LLM, newly uploaded unseen documents, permission-aware retrieval, strict grounded prompting, citation validation, no-answer behavior, streaming parity, failure safety, and content-free logging.

### Implemented so far

- Completed audit before coding.
- Kept deterministic UAT fake provider unchanged and excluded from real answer-quality acceptance.
- Reused existing TASK-026 provider architecture; no new provider was added.
- Selected Ollama as the recommended local acceptance provider path, with LM Studio as an alternative.
- Strengthened grounded prompt policy for strict evidence-only behavior.
- Added post-validation guard so `ANSWERED` cannot persist with zero validated citations.
- Added focused unit tests for strict prompt and invalid answered/no-citation behavior.
- Added skipped-by-default `real_llm_acceptance` report validator.
- Created ignored local acceptance artifacts under `artifacts/task-034-1/`.

### Remaining acceptance work

- Start Docker Desktop and verify PostgreSQL, Redis, API, worker, and migration health.
- Install/start a real local provider or configure an explicitly approved external provider.
- Upload/process the new unseen acceptance documents to READY.
- Run all required real-LLM question cases and existing regressions through non-streaming and streaming chat.
- Verify permissions and provider failures.
- Manually verify every factual claim against cited source excerpts.
- Validate the completed acceptance report with the `real_llm_acceptance` marker.

TASK-034.2 implementation started: No.
TASK-035 implementation started: No.