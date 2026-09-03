# Project Status

## CURRENT STATUS -- 2026-08-21

> This block supersedes older 2026-08-19 RAG handoffs. TASK-034.1.2 runtime RAG acceptance is complete for the agreed seven-case set. TASK-035 is still not started.

### Completed

- Restored the intended UAT leave-policy evidence through the normal ingestion/indexing pipeline instead of changing runtime RAG logic or inserting direct chunk answers.
- Verified active non-deleted indexed evidence for the 12 / 14 / 16 annual-leave distinctions before runtime UAT.
- Completed answer-bearing source-quality, subject/object-aware YES/NO validation, relation entailment, and citation repair work.
- Passed all seven runtime UAT cases in new chats against the local real LLM runtime.
- Re-ran focused RAG suites, full unit tests, Ruff lint, and Ruff format check with actual counts.

### Corpus action

Restored document `43cb2c93-52bc-44f6-8e03-1b1f075e1d89`, `Chính sách nghỉ của người lao động`, checksum `24178db420422e474326986672b6c15cc67373ee6adbe1489ba5e8addf95f4f4`, storage key `documents/2026/08/951776f4-88c3-4c98-8401-c8ce5edad268.pdf`, uploaded by `admin.uat@example.test`, `ORGANIZATION` scope.

The document was restored from soft delete by setting `is_deleted=false`, reset to `UPLOADED`, and processed by normal worker task `274fe326-9d28-421c-9c11-253ec7b74bc2`. Final ingestion result: `READY`, `page_count=6`, `chunk_count=12`, `total_tokens=6458`, embeddings `384` dimensions. Active corpus verification after processing: `12` active ready documents, `153` active chunks, and authoritative active leave clause chunk `4b341201-f0df-4102-b9f2-5ad7091781a6` on page `3`.

Provenance is clear enough for UAT restoration because the file was UAT-admin uploaded, organization scoped, HR-policy themed, and contained the exact authoritative annual-leave table. Remaining corpus limitation: it is generic/template-branded; no Nova-branded PDF with the 12 / 14 / 16 table was found, and the active Nova-branded leave policy only had the 12-day normal-work clause.

### Runtime UAT

| Case | Result |
| --- | --- |
| Own salary | PASS -- `Có`; salary policy pages 10-11; `SUPPORTED`. |
| EAP | PASS -- `Không`; benefits policy page 8; `SUPPORTED`. |
| NovaCare vs BHYT | PASS -- `Không`; benefits policy page 4; `SUPPORTED`. |
| Engineering Manager | PASS -- `N5`, `42 - 70 triệu đồng`; salary table page 4; `SUPPORTED`. |
| Head / Director | PASS -- `N6`, `65 - 110 triệu đồng`; salary table page 4; `SUPPORTED`. |
| Annual leave | PASS -- starts `Không`, distinguishes `12 / 14 / 16`, cites real active leave clause/table page 3, no sample-question citation, `SUPPORTED`. |
| CEO false premise | PASS -- starts `Không`, identifies `Nguyễn Anh Khoa`; organization source page 6; `SUPPORTED`. |

### Verification

```text
tests/unit/test_grounded_answer_service.py: 75 passed in 1.33s
focused RAG/citation suite: 132 passed in 1.56s
combined RAG/citation/validation/output suite: 157 passed in 1.71s
tests/unit: 1061 passed in 8.22s
ruff check on 21 touched Python files: All checks passed
ruff format --check on 21 touched Python files: 21 files already formatted
```

### Remaining technical debt

- Replace the restored generic/template leave policy with canonical Nova-branded content once available.
- Hydrate/cache the configured CrossEncoder reranker or formally accept alignment fallback for local UAT.
- Profile runtime UAT latency; observed wall-clock case times were about 94s-186s.
- Improve table evidence highlighting so annual leave captures the full 12 / 14 / 16 support span, not only a narrow value.
- Remove sample-question/test-question sections from production knowledge documents through corpus curation.
- Convert the manual seven-case runtime UAT runner into an automated acceptance artifact.

## CURRENT MANUAL STATUS — 2026-08-19

> This block is the latest project handoff and should be read before older status snapshots below.

### Current phase

Manual RAG Accuracy Hardening + UI-04B Exact Evidence / citation quality.

### Current task

Minimal Citation Selection is **IMPLEMENTED + UNIT VERIFIED; LIVE RUNTIME VERIFICATION PENDING** after Exact Evidence persistence/API work was verified.

Current checkpoint:

- Exact evidence extraction: implemented and focused tests passed (`15 passed` at completion checkpoint).
- `message_citations.evidence_text`: implemented and persisted.
- API/session history exposes optional `evidence_text`.
- Frontend exact-evidence rendering is visibly active in citation cards.
- Original source PDF/DOCX files remain unchanged.
- Minimal citation pruning: focused citation-mapping suite passed `17 passed in 0.19s`; one live new-message runtime check is still required before final completion.
- Document Viewer navigation to exact document/page/evidence is still pending.
- RAG answer-quality hardening is the next active work based on manual Vietnamese multi-document UAT.

### Mandatory runtime principle

Regression/UAT questions are not a runtime knowledge base. No hard-coded question-to-answer mappings are allowed. Answers must be generated from currently authorized retrieved document evidence.

### Accuracy findings requiring general fixes

Manual UAT showed recurring classes of errors:

- retrieval misses even when the source contains direct answers;
- wrong row selection in tables with neighboring percentages/conditions;
- contradictions such as `Có` vs `Không`;
- semantic intent confusion between related HR concepts;
- role/workflow confusion;
- redundant citations that support the same factual evidence.

The remediation path is capability-level:

```text
Query Understanding
-> Hybrid Retrieval
-> Reranking
-> Table/Row Discrimination
-> Minimal Evidence Selection
-> Claim/Evidence Validation
-> Grounded Answer
```

### Documentation policy during manual work

After each completed change, update:

- `TASKS.md`
- `PROJECT_STATUS.md`
- `CHANGELOG.md`

Also update the affected spec/design docs (`RAG_DESIGN.md`, `API_SPEC.md`, `DATABASE_DESIGN.md`, `TESTING_STRATEGY.md`, `FRONTEND_SPEC.md`) when their contracts/designs change.


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


### RAG-H2.1 checkpoint — 2026-08-19

- Post-reranker ordering bug fixed: reranked hits are now preserved before prompt-ranked supplemental hits.
- Regression coverage added.
- Focused verification passed: `61`, `27`, and combined `147` tests.
- Runtime cross-encoder is currently unavailable and falls back to `HeuristicRetrievalReranker`.
- `RAG_DIAGNOSTICS_ENABLED` is not present in the API container; `Settings().rag_diagnostics_enabled` remains `False`.
- Runtime H2 acceptance is pending after diagnostics injection and real query verification.


### Runtime recovery checkpoint — 2026-08-19

- `LLM_GENERATION_FAILED` incident resolved.
- Ollama/provider path verified healthy; 8K model alias runs with context 8192.
- Actual backend root cause was `NameError` from a partially applied `question=grounding_question` claim-validation call inside `_draft_from_generation()`.
- Restored current claim-validator call contract.
- Tests passed: `61` focused grounded-answer tests and `147` combined RAG/retrieval tests.
- Live `Head` salary query now fails as NO_ANSWER rather than generation failure; accuracy investigation continues.
- `RAG_DIAGNOSTICS_ENABLED=True`, but INFO diagnostic events are not appearing in `docker compose logs`; logging visibility investigation is next.

### RAG accuracy checkpoint — salary amount PASS

Salary-band runtime probes are now passing:
- Head / Director: 65 - 110 triệu đồng.
- Engineering Manager / N5: 42 - 70 triệu đồng/tháng.

Regression verification:
- grounded-answer unit suite: 63 passed.
- combined focused RAG/retrieval suite: 149 passed.

Current open issue:
`Nhân viên có được nói về mức lương của chính mình không?` still returns NO_ANSWER. Diagnostics show correct YES_NO retrieval and three `SUPPORTED` claim validations, followed each time by `reason=yes_no_missing_leading_polarity`. This is a presentation/quality-gate failure, not a retrieval miss.

Citation UX decision pending implementation: evidence highlighting should represent the source passage(s) that materially support the answer/inference.
