# Project Status

## Current phase

UAT UX + LLM configuration fix

## Overall progress

```text
Documentation: Active for UAT fix only
Backend foundation: Completed
Database foundation: Completed
Authentication and RBAC: Completed
Administration APIs: Completed
Document management: Completed
Document processing pipeline: Completed
Semantic retrieval: Completed
Keyword retrieval: Completed
Hybrid retrieval: Completed
Chat data model: Completed
Chat session APIs: Completed
Grounded Chat: Completed
LLM provider: Completed
Grounded answer generation: Completed
Citation validation: Completed
Citation persistence: Completed
Permission revalidation: Completed
Feedback model/API: Completed
Feedback reporting: Completed
Audit log expansion: Completed
Web Search Integration: Completed
Backend Docker stack: Completed
CI pipeline: Completed
MVP hardening: Completed
Backend MVP: Completed
Frontend: Completed through TASK-028 live UI acceptance; UAT selector fix applied
Production deployment and observability: Completed in TASK-034
Final acceptance and release candidate: TASK-035 not started
```

## Completed

- TASK-001 through TASK-034 completed.
- TASK-023 completed the Docker full backend stack with PostgreSQL/pgvector, Redis, one-shot Alembic migration, FastAPI API, Celery worker, shared upload volume, shared model-cache volume, non-root application containers, and Python 3.12 runtime.
- TASK-024 completed a GitHub Actions CI pipeline for the backend with Python 3.12, pip caching, `pyproject.toml` dependency installation, PostgreSQL/pgvector and Redis service containers, Alembic verification, Ruff checks, pytest coverage across unit/API/integration/marker suites, security scanning, Docker build verification, Compose config validation, and artifact upload.
- TASK-025 completed Docker recovery, Docker runtime verification, database-backed verification, marker suites, end-to-end release smoke, persistence, failure/recovery, and final quality gates.
- TASK-026 completed Multi-LLM Provider Support and Docker runtime verification.
- TASK-027 completed backend SSE streaming chat with buffer-after-validation grounding, citation, persistence, cancellation, and safe-error tests.
- TASK-028 frontend implementation adds a React/TypeScript/Vite console in `frontend/` with authentication, role-aware shell, typed API integration, POST SSE chat, document workflows, admin screens, feedback, audit, system status, frontend tests, UI docs, and optional Docker frontend profile.
- TASK-028 live acceptance recovery verified the real Docker stack with PostgreSQL, Redis, API, worker, frontend, Alembic current/head `20260722_0009`, UAT seed idempotency, live Admin/Manager/Staff login, upload-to-READY, permissions grant/revoke, live SSE chat, citations, feedback, audit, responsive/accessibility smoke, mock E2E, live E2E, frontend quality gates, and backend regression suites.
- TASK-029 completed bounded same-session Conversation Memory with `ConversationContextBuilder`, message and token limits, retrieval-query augmentation, prompt-history formatting, non-streaming and streaming parity, no migration, and no prompt persistence.
- TASK-030 completed OCR and Image Understanding with OCR routing, Tesseract runtime support, extraction quality checks, image upload validation, and retrieval/citation compatibility.
- TASK-031 completed Web Search Integration with backend-only internal-only, hybrid, and web-only modes, provider registry/manager, mock/Bing/DuckDuckGo/Google Custom Search providers, web citation persistence, admin provider endpoints, security normalization, Docker runtime, migration, API, streaming, integration, regression, quality, and security verification.
- TASK-032 completed backend-only Admin Dashboard & System Monitoring with safe Admin-only health, provider, worker, queue, statistics, version, and system endpoints.
- TASK-033 completed backend-only Analytics & Reporting with Admin-only overview, chat, user, search, OCR, LLM, feedback, audit, and CSV/JSON export endpoints.
- TASK-034 completed backend-only Production Deployment & Observability with production Compose, reverse proxy, Prometheus/Grafana provisioning, safe metrics/logging, runtime validation, backup/restore helpers, and Docker runtime verification.
- UAT UX + LLM configuration fix completed the upload Department selector, permission User/Department selectors, safe validation errors, deterministic local UAT LLM coverage, Docker UAT config verification, live chat verification, streaming verification, and focused regressions.

## Current task

UAT FIX -- UX Selectors + LLM_NOT_CONFIGURED remediation is completed and verified locally.

This is not TASK-035. TASK-035 -- Final Acceptance Test & Release Candidate is not started. No backend Release Candidate version is marked.

Roadmap status: TASK-001 through TASK-034 completed for the backend roadmap. TASK-028.1 Localization is deferred. Frontend UI Foundation exists. TASK-035 is pending and not started.

## Phase 2 roadmap initialized

- TASK-026 -- Multi-LLM Provider Support: Completed.
- TASK-027 -- Streaming Chat with Server-Sent Events: Completed.
- TASK-028 -- Frontend UI Foundation & Test Console: Completed.
- TASK-029 -- Conversation Memory: Completed.
- TASK-030 -- OCR and Image Understanding: Completed.
- TASK-031 -- Web Search Integration: Completed.
- TASK-032 -- Admin Dashboard & System Monitoring: Completed.
- TASK-033 -- Analytics & Reporting: Completed.
- TASK-034 -- Production Deployment & Observability: Completed.
- TASK-035 -- Final Acceptance Test & Release Candidate: Not started.
- TASK-036 -- Enterprise Release v2.0: Pending.

## Current blockers

- None for the scoped UAT UX + LLM configuration fix.

## Files changed in latest task

UAT fix relevant files:

- `frontend/src/features/documents/DocumentUploadPage.tsx`
- `frontend/src/features/documents/DocumentUploadPage.test.tsx`
- `frontend/src/features/documents/DocumentPermissionsPage.tsx`
- `frontend/src/features/documents/DocumentPermissionsPage.test.tsx`
- `frontend/tests/e2e-live/fake-openai-provider.mjs`
- `tests/integration/test_docker_stack_config.py`
- `README.md`
- `SETUP.md`
- `ENVIRONMENT_VARIABLES.md`
- `TESTING_STRATEGY.md`
- `PROJECT_STATUS.md`
- `TASKS.md`
- `CHANGELOG.md`

## UAT UX + LLM configuration snapshot

- Document upload no longer exposes a raw Department ID input. `DEPARTMENT` scope loads `GET /api/v1/departments`, displays department names/codes, validates a required selection, and sends the selected `department.id`.
- Document permission grants no longer expose a raw Grantee ID input. `USER` loads `GET /api/v1/users`; `DEPARTMENT` loads `GET /api/v1/departments`; changing grantee type clears stale selections.
- Default `compose.yaml` keeps `LLM_ENABLED=false` and does not start a local LLM container.
- UAT mode uses `docker compose -f compose.yaml -f compose.uat.yaml up -d` and enables the local deterministic OpenAI-compatible provider at `http://uat-llm:18080/v1` with `LLM_MODEL=uat-deterministic-model`.
- UAT chat verification uses the local deterministic provider only; no real provider API key or external LLM call is required.
- UAT account lifecycle fix: `compose.uat.yaml` runs one-shot `uat-seed` before API/worker startup. The seed updates known UAT users in place, including password hash, full name, role, department, active flag, and lowercase email normalization, while preserving unrelated users.

## Known limitations

- TASK-035 is not started and the backend is not marked Release Candidate in this UAT fix.
- The default Docker stack is for local development and binds API, PostgreSQL, and Redis to `127.0.0.1` host ports.
- LLM is disabled by default. UAT LLM behavior requires `compose.uat.yaml`; host or production LLM providers require explicit operator configuration.
- Web search is disabled by default; external provider calls require explicit configuration and `WEB_SEARCH_ALLOW_EXTERNAL=true`.
- Feedback reason, Chat content, citation excerpts, chunk text, and selected fields are still stored plaintext in PostgreSQL.
- Frontend `npm audit --audit-level=high` reports a React Router RSC/action advisory for `react-router-dom@7.18.2`; TASK-028 uses SPA-only routing and does not enable RSC/actions. Reassess when a clean upstream release is available.
- No malware scanning, PII masking, automatic chat retention, audit retention, or feedback deletion workflow is implemented.
- Broker enqueue is not backed by a transactional outbox; broker failure can leave a committed Document in `UPLOADED` until manually enqueued.
- Worker crash can leave a Document in `PROCESSING` until recovery logic is added.
- Current local UAT data may include documents from earlier verification runs. The UAT fix did not delete documents, reset the database, or remove Docker volumes.
## TASK-031 verification snapshot

Final verification passed:

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
- Docker runtime verified PostgreSQL, Redis, API, worker, and migration service; migration exited 0.
- API `/health/live` and `/health/ready` passed.
- `alembic current`, `alembic heads`, and `alembic upgrade head` passed in the API container; current/head is `20260803_0010`.
- Runtime smoke verified default disabled/internal-only provider status, no-answer chat, SSE streaming, UAT internal citation, mock-provider `internal_only`, `web_only`, `hybrid`, no-internal-hit intent, and web citation source typing.

## TASK-032 verification snapshot

TASK-032 completed backend-only Admin Dashboard & System Monitoring:

- Added Admin-only `/api/v1/admin/system`, `/api/v1/admin/health`, `/api/v1/admin/providers`, `/api/v1/admin/workers`, `/api/v1/admin/statistics`, `/api/v1/admin/queues`, and `/api/v1/admin/version`.
- Added `AdminMonitoringService` with safe read-only health/status aggregation for API uptime, PostgreSQL, Redis, Celery worker, OCR, embedding configuration, LLM provider configuration, Web Search provider configuration, streaming registration, conversation memory configuration, queues, statistics, and version.
- Added safe schemas for admin health, providers, workers, queues, statistics, version, and system dashboard responses.
- Added unit and API integration tests for Admin RBAC, health subsystem coverage, provider safety, queue reporting, worker status, aggregate statistics, version, and secret/content non-disclosure.
- No frontend, React, Stitch, Localization, Chat API, Streaming behavior, Conversation Memory behavior, Citation behavior, OCR processing behavior, Web Search behavior, Celery architecture, or database schema migration was changed.
- Alembic source/current/head remained `20260803_0010`; no migration was created.

Verification completed:

- `python -m pytest tests/unit/test_admin_monitoring_service.py -v`: 4 passed.
- `python -m pytest tests/api/test_admin_monitoring.py -m integration -v`: 4 passed.
- `python -m pytest tests/api/test_admin_monitoring.py tests/api/test_web_search_admin.py tests/api/test_rbac_dependencies.py -m integration -v`: 10 passed, 11 deselected.
- `python -m pytest -q`: 1001 passed, 654 deselected.
- Docker test profile TASK-032 unit/API suites passed on Python 3.12.13.
- `python -m ruff check .`, `python -m ruff format --check .`, `python -m compileall app tests`, and `python .github/scripts/security_scan.py` passed.
- `alembic heads`, `alembic current`, and `alembic upgrade head` passed with `20260803_0010`.
- `docker version`, `docker info`, `docker compose config`, `docker compose build`, `docker compose up -d`, and `docker compose ps` passed.
- Docker runtime verified API health, worker health, PostgreSQL health, Redis health, migration service exited 0, pgvector extension, Tesseract OCR binary, Celery worker ping, and live Admin monitoring endpoints.

Note: broad all-file `tests/api -m integration` commands were attempted but timed out and are not counted; focused TASK-032/RBAC/provider integration and default backend regression passed.
## TASK-033 verification snapshot

TASK-033 completed backend-only Analytics & Reporting:

- Added Admin-only `/api/v1/admin/analytics/overview`, `/api/v1/admin/analytics/chat`, `/api/v1/admin/analytics/users`, `/api/v1/admin/analytics/search`, `/api/v1/admin/analytics/ocr`, `/api/v1/admin/analytics/llm`, `/api/v1/admin/analytics/feedback`, `/api/v1/admin/analytics/audit`, and `/api/v1/admin/reports/export`.
- Added `AdminAnalyticsService` with read-only PostgreSQL aggregates for chat, users, citation-inferred search, image-document OCR status, LLM token/latency/failure metrics, feedback ratings, audit categories, and overview summaries.
- Added safe analytics schemas and CSV/JSON export helpers. PDF export returns `422 VALIDATION_ERROR` because no backend PDF export infrastructure exists.
- Added unit and API integration tests for filters, RBAC, aggregate correctness, security non-disclosure, export behavior, regression coverage, and performance smoke.
- No frontend, React, charts, Localization, Chat API, Streaming behavior, Conversation Memory behavior, Citation behavior, OCR processing behavior, Web Search behavior, Celery architecture, or database schema migration was changed.
- Alembic source/current/head remained `20260803_0010`; no migration was created.

Verification completed:

- `python -m pytest tests/unit/test_admin_analytics_service.py -q`: 5 passed.
- `python -m pytest tests/api/test_admin_analytics.py -m integration -q`: 6 passed.
- `python -m pytest tests/api/test_admin_analytics.py tests/api/test_admin_monitoring.py tests/api/test_web_search_admin.py tests/api/test_rbac_dependencies.py -m integration -q`: 16 passed, 11 deselected.
- `python -m pytest -q`: 1006 passed, 660 deselected.
- `python -m ruff check .`, `python -m ruff format --check .`, `python -m compileall app tests`, and `python .github/scripts/security_scan.py` passed.
- `python -m alembic heads`, `python -m alembic current`, and `python -m alembic upgrade head` passed with `20260803_0010`.
- `docker compose config`, `docker compose build`, `docker compose up -d`, and `docker compose ps` passed.
- Docker runtime verified API health, PostgreSQL health, Redis health, migration service exit 0, Celery worker ping, container Alembic heads/current/upgrade, and live Admin analytics route RBAC (`401 ACCESS_TOKEN_INVALID` without bearer token).

Known data limitations: retrieval duration, per-message streaming usage, OCR duration, exact scanned-PDF OCR page attribution, and historical per-message LLM provider/model attribution are not persisted and are reported as unavailable or partially inferred.
## TASK-034 verification snapshot

TASK-034 completed backend-only Production Deployment & Observability:

- Added standalone production Compose with PostgreSQL, Redis, one-shot migration, API, worker, reverse proxy, volume initialization, restart policies, healthchecks, CPU/RAM/PID limits, log-size limits, and Docker secret-file compatibility.
- Added Nginx reverse proxy config for forward headers, request/upload limits, SSE compatibility, security headers, HTTPS readiness without committed certificates, and external `/metrics` blocking.
- Added request ID context, traceparent capture hooks, structured content-free request logging, in-process HTTP metrics, and Prometheus runtime metrics for API, worker, Redis, PostgreSQL, OCR, embedding, LLM, Web Search, Streaming, Conversation, queues, version, and uptime.
- Added Prometheus scrape config and Grafana provisioning/dashboard files.
- Added PostgreSQL and uploads backup/restore helpers with verification and guarded restore behavior.
- No frontend/UI/React/Stitch/Localization/Chat/RAG/Citation/Conversation/Streaming/OCR/Web Search behavior was changed.
- No database migration was created; Alembic source/current/head remains `20260803_0010`.

Verification completed:

- `python -m pytest tests/unit/test_admin_monitoring_service.py tests/unit/test_observability_metrics.py tests/unit/test_runtime_validation.py tests/api/test_observability.py tests/integration/test_production_deployment_config.py -q`: 21 passed, 2 deselected.
- `python -m pytest tests/unit -k "ocr or image or document_processing or extractor" -q`: 91 passed, 843 deselected.
- `python -m pytest -q`: 1023 passed, 662 deselected.
- `python -m pytest -m "integration or not integration" tests/api/test_observability.py tests/api/test_admin_monitoring.py tests/api/test_admin_analytics.py tests/api/test_rbac_dependencies.py tests/api/test_chat_streaming.py tests/integration/test_production_deployment_config.py tests/integration/test_docker_stack_config.py -q`: 55 passed.
- `python -m ruff check .`, `python -m ruff format --check .`, `python -m compileall app tests .github\scripts`, `python .github\scripts\security_scan.py`, `python -m pip check`, and `python -m pip_audit` passed.
- `python -m alembic heads`, `python -m alembic current`, and `python -m alembic upgrade head` passed with `20260803_0010`.
- `docker compose config`, `docker compose build`, `docker compose up -d`, and `docker compose ps` passed for the development stack.
- `docker compose --env-file <production env> -f compose.prod.yaml config`, `build`, `up -d`, and `ps` passed for the production stack.
- Production runtime verified API, worker, Redis, PostgreSQL, migration, and reverse proxy health; API `/health/ready` returned ready through Nginx; worker Celery ping returned `pong`; API container Alembic current remained `20260803_0010`; final image contains `Pillow 12.3.0`.
- Internal `/metrics` returned safe Prometheus text and did not contain the sensitive `context` marker; production reverse proxy returned `404` for external `/metrics`.
- Backup/restore verification created and validated a PostgreSQL dump, restored it into an isolated check database, created and validated an uploads archive, restored it into an isolated check volume, and confirmed restore guardrails refuse production overwrite without explicit switches.
- Failure recovery verified API restart, worker restart, Redis unavailable/readiness degradation/recovery, PostgreSQL unavailable/readiness degradation/recovery, and safe degraded responses without secrets.

Known TASK-034 limitations: real TLS certificates, cloud secret manager integration, SIEM/log shipping, alert rules, distributed tracing backend, Kubernetes, Terraform, cloud resources, CD automation, WAF, malware scanning, automatic retention deletion, and cloud backup are not included. In-process HTTP metrics reset on API restart.

## TASK-034.1 status snapshot

TASK-034.1 -- Real / Local LLM Strict Grounded Runtime Acceptance is current and in progress. TASK-034.2 is not started. TASK-035 is not started.

Completed in the repository for TASK-034.1:

- Audited LLM provider architecture, grounded answer service, citation validation, retrieval, web search, streaming, frontend chat integration, Compose, and environment documentation.
- Strengthened the grounded system prompt for strict evidence-only behavior, preservation of numbers/dates/names/conditions/exceptions, conflict handling, and no unsupported inference.
- Added a runtime invariant that `ANSWERED` results must include validated citations.
- Added focused unit coverage for strict prompt text and answered-without-citations rejection.
- Added disabled-by-default `real_llm_acceptance` report validator.
- Created local ignored synthetic acceptance PDFs and a report template under `artifacts/task-034-1/`.
- TASK-034.1 local Ollama streaming timeout fix verified `qwen3:4b` through buffer-after-validation SSE for Nova Digital CEO, CTO, and NovaAssist questions twice each with no `STREAM_TIMEOUT`.

Current remaining completion requirements:

- Full strict real-LLM matrix must be rerun and recorded in the manual acceptance report.
- Manual claim-level support remains required for every factual claim; automated claim-level entailment is deferred.
- Permission, failure, no-answer, and cross-document acceptance cases must remain green after the local streaming timeout fix.

TASK-034.1 cannot be marked completed until real/local or explicitly configured external provider acceptance passes against the new unseen document set with manual claim verification.