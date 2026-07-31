
# Implementation Tasks

## Summary

TASK-001 -> TASK-028: Completed.

Phase 1: Completed.
Phase 2: In Progress.
Current task: None.
Next task: TASK-029.
TASK-028 live acceptance: COMPLETED_AND_VERIFIED.
READY FOR USER EXPERIENCE: YES.
TASK-029 implementation started: No.

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
- TASK-029 Conversation Memory was not started. TASK-032 analytics was not implemented.

### Acceptance criteria

- Frontend foundation runs locally and communicates with the backend through a typed API client.
- Authenticated and permission-aware navigation is implemented.
- Core backend workflows can be operated from the UI without fake production data.
- Chat UI can display standard and streaming answer states, citations, provider/model status when allowed, and safe error/rate-limit feedback.
- Reusable design-system components cover forms, tables, navigation, skeletons, empty states, errors, notifications, and theme readiness.
- Frontend tests or documented verification cover primary workflows and permission-aware states.

---

## TASK-029 — Conversation Memory

**Status:** Pending.

### Goal

Add configurable conversation memory that improves follow-up questions without allowing old chat content to bypass document permissions or grounded-answer policy.

### Acceptance criteria

- Memory strategy is explicit, bounded, and configurable.
- Permission changes are respected when memory references prior answers or cited sources.
- Memory content is not logged and is not exposed outside the owning ChatSession.
- No-answer and citation rules continue to apply.

---

## TASK-030 — OCR & Image Understanding

**Status:** Pending.

### Goal

Extend ingestion and retrieval to support OCR and image-based document understanding with safe processing limits.

### Acceptance criteria

- OCR/image processing is asynchronous and bounded.
- Extracted text keeps page/source metadata for retrieval and citations.
- Unsupported, encrypted, oversized, or low-quality files fail safely.
- No OCR model download or external call occurs during import/startup.

---

## TASK-031 — Web Search Integration

**Status:** Pending.

### Goal

Add controlled web search as an optional source with clear provenance and policy separation from internal enterprise documents.

### Acceptance criteria

- Web search is disabled by default and configured explicitly.
- Search results are marked separately from internal document sources.
- Data residency and external transfer warnings are documented.
- Citations distinguish web sources from internal document citations.

---

## TASK-032 — Admin Analytics Dashboard

**Status:** Pending.

### Goal

Provide advanced administrative analytics for usage, feedback trends, document processing, retrieval quality, and system operations.

### Acceptance criteria

- Dashboard scope is analytics/reporting, not the core operating console from TASK-028.
- Aggregations avoid exposing chat content, prompts, retrieved context, citation excerpts, feedback reasons, or secrets.
- Role-based access is enforced server-side.
- Metrics are documented and tested for safe filtering/pagination.

---

## TASK-033 — Monitoring & Observability

**Status:** Pending.

### Goal

Add production-grade operational telemetry without logging sensitive business content.

### Acceptance criteria

- Structured metrics cover safe request, dependency, retrieval, LLM, worker, and queue metadata.
- Logs remain redacted and content-free.
- Health/readiness and alerting guidance are documented.
- Trace/span data does not contain prompts, document text, answers, or secrets.

---

## TASK-034 — Kubernetes Deployment

**Status:** Pending.

### Goal

Create Kubernetes deployment artifacts and operational guidance for production-like environments.

### Acceptance criteria

- API, worker, migration, PostgreSQL/Redis dependency assumptions, storage, secrets, and health probes are documented.
- Manifests avoid baking secrets into images or source files.
- Startup, rollback, scaling, and migration behavior are defined.
- Local Docker Compose remains supported.

---

## TASK-035 — Enterprise Authentication

**Status:** Pending.

### Goal

Add enterprise authentication options such as SSO/OIDC while preserving existing local authentication where appropriate.

### Acceptance criteria

- Authentication provider configuration is explicit and secret-safe.
- Role/department mapping is documented and auditable.
- Existing RBAC and database user source-of-truth rules remain coherent.
- Token handling, logout, inactive-user behavior, and tests are updated.

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
