# Testing Strategy

## 1. Test levels

### Unit tests

- Security helpers.
- Permission policies.
- Chunking.
- Prompt builder.
- Citation parser/validator.
- Text normalization.

### Integration tests

- Repository vá»›i PostgreSQL test database.
- Login vÃ  refresh flow.
- Document CRUD.
- Permission-aware list vÃ  retrieval.
- Celery task á»Ÿ eager/test mode náº¿u phÃ¹ há»£p.

### API tests

- Status code.
- Response schema.
- Role restrictions.
- Pagination vÃ  validation.

### RAG evaluation tests

- Known answer.
- No answer.
- Unauthorized source.
- Exact keyword.
- Multi-page answer.

## 2. Critical security tests

1. Staff khÃ´ng gá»i Ä‘Æ°á»£c user management.
2. Staff phÃ²ng A khÃ´ng xem document phÃ²ng B.
3. Search khÃ´ng tráº£ title cá»§a tÃ i liá»‡u trÃ¡i quyá»n.
4. Retrieval khÃ´ng tráº£ chunk trÃ¡i quyá»n.
5. Citation khÃ´ng expose document trÃ¡i quyá»n.
6. User khÃ´ng xem chat session cá»§a ngÆ°á»i khÃ¡c.
7. Deleted hoáº·c archived document khÃ´ng Ä‘Æ°á»£c retrieve.

## 3. Fixtures

Táº¡o fixtures:

- admin_user
- manager_department_a
- staff_department_a
- staff_department_b
- organization_document
- department_a_document
- private_document
- ready_document_chunks

## 4. Test naming

```python
def test_staff_cannot_access_admin_user_list(): ...
def test_retrieval_excludes_other_department_chunks(): ...
def test_chat_returns_no_answer_when_score_below_threshold(): ...
```

## 5. Mocking

Mock external provider:

- Embedding API.
- LLM API.
- Object storage.

KhÃ´ng mock permission query trong integration test quan trá»ng.

## 6. Coverage priority

Æ¯u tiÃªn coverage cao cho:

- auth
- RBAC
- document permission
- retrieval
- citation validation

Coverage tá»•ng chá»‰ lÃ  chá»‰ bÃ¡o; khÃ´ng thay tháº¿ test case nghiá»‡p vá»¥.

## 7. Manual acceptance test

Má»—i task pháº£i ghi cÃ¡ch test báº±ng Swagger hoáº·c command line náº¿u chÆ°a cÃ³ frontend.


## 8. TASK-023 Docker stack verification

Docker acceptance checks should verify the real stack, not only static files:

```powershell
docker compose config
docker compose build
docker compose up -d
docker compose ps
docker compose exec api python --version
docker compose exec worker python --version
docker compose exec api alembic current
docker compose exec api alembic heads
curl.exe -i http://127.0.0.1:8000/health/live
curl.exe -i http://127.0.0.1:8000/health/ready
```

Regression checks:

```powershell
docker compose run --rm test
python -m ruff check .
python -m ruff format --check .
python -m compileall app
```

For integration tests in Docker, use a separate non-production test database. Stop the application worker while running Celery integration tests against the same Redis queues, because those tests launch their own worker on `default,documents`.

Required TASK-023 smoke coverage includes authentication, document upload to `READY`, shared API/worker upload storage, pgvector extension, HNSW index, FTS index, feedback report, audit report, restart persistence, PostgreSQL-unavailable readiness, and Redis-unavailable readiness.

## TASK-025 hardening tests

TASK-025 adds focused security regression coverage for:

- Production config validation and secret redaction.
- CORS policy and trusted hosts.
- Security headers and HSTS policy.
- Global request-size limiting for `Content-Length` and streamed bodies.
- Upload filename/type/signature/size edge cases.
- Redis-backed rate-limit behavior and sanitized `429` responses.
- Generic unhandled-exception sanitization.
- Log redaction for secrets and business content keys.
- Database pool and Redis timeout configuration.
- Celery JSON-only serialization and bounded task time limits.
- API docs enable/disable policy.
- Static retrieval evaluation fixture shape in `tests/fixtures/retrieval_evaluation_set.json`.

Primary local commands:

```powershell
python -m pytest tests/unit -v
python -m pytest tests/api -m "not integration" -v
python -m pytest tests/api -m integration -v
python .github\scripts\security_scan.py
python -m ruff check .
python -m ruff format --check .
python -m compileall app
```

Dependency review commands:

```powershell
python -m pip check
python -m pip list --outdated
$env:PYTHONUTF8='1'; python -m pip_audit
```

`pip-audit` is not a project dependency or CI gate in TASK-025; it was used as a local dependency review tool.


## TASK-026 multi-LLM provider tests

TASK-026 provider tests must use mocked HTTP transports or local mock servers by default. Unit/default CI must not call real OpenAI, Azure OpenAI, Gemini, Anthropic, Ollama, LM Studio, OpenRouter, or other external providers.

Required focused suites:

```powershell
python -m pytest tests/unit/test_llm_models.py -v
python -m pytest tests/unit/test_llm_provider_config.py -v
python -m pytest tests/unit/test_llm_registry.py -v
python -m pytest tests/unit/test_llm_provider_manager.py -v
python -m pytest tests/unit/test_openai_compatible_provider.py -v
python -m pytest tests/unit/test_azure_openai_provider.py -v
python -m pytest tests/unit/test_gemini_provider.py -v
python -m pytest tests/unit/test_anthropic_provider.py -v
python -m pytest tests/unit/test_grounded_answer_service.py -v
python -m pytest -m llm_provider_integration -v
```

Coverage expectations:

- Registry supported names, unknown-provider rejection, lazy creation, and no import-time network behavior.
- Configuration rules for disabled LLM, selected-provider requirements, unselected provider settings, and secret redaction.
- OpenAI-compatible mapping, response parsing, usage parsing, timeout/error mapping, missing-usage `None` behavior, explicit connectivity health, and shared use by OpenRouter, Ollama, and LM Studio.
- Azure URL/header mapping and safe error mapping.
- Gemini system instruction, user/assistant message mapping, candidate parsing, usage parsing, finish reason mapping, and safe safety/error mapping.
- Anthropic system field, message content blocks, max tokens, version/key headers, response parsing, usage parsing, and safe error mapping.
- Grounded-answer provider independence, no-answer provider independence, unselected citation rejection, and no assistant message persistence on provider error.
- Privacy checks for prompt, context, response, provider key, and raw provider error leakage.

Real-provider integration marker:

- Marker name: `real_llm_provider_integration`.
- Skipped by default and never required in CI unless explicitly opted in.
- Must use synthetic non-sensitive content, strict timeout, bounded cost, and no prompt/response logging.

TASK-026 full local verification includes:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m compileall app
python .github/scripts/security_scan.py
python -m pytest tests/unit -v
python -m pytest tests/api -v
python -m pytest -m integration -v
python -m pytest -m llm_provider_integration -v
```
## TASK-027 streaming chat tests

TASK-027 uses mocked providers and deterministic fake retrieval by default. No test in the default suite calls a live external provider.

Required focused suites:

```powershell
python -m pytest tests/unit/test_sse.py -v
python -m pytest -m streaming_chat_integration -v
python -m pytest -m llm_provider_integration -v
python -m pytest -m integration tests/api/test_chat_messages.py -v
python -m pytest tests/unit/test_grounded_answer_service.py tests/unit/test_citation_validation_service.py -v
```

Docker verification uses the same marker:

```powershell
docker compose --profile test run --rm test python -m pytest -m streaming_chat_integration -v
```

Coverage expectations:

- SSE serializer format, UTF-8 JSON, Unicode, newline-injection resistance, and terminal blank line.
- Event ordering, monotonic sequence, terminal-once enforcement, and no event after terminal state.
- SSE endpoint auth, ownership, rate limiting, headers, no `Content-Length`, success payload, safe errors, provider rollback, citation rollback, no-answer behavior, disconnect cancellation, and non-streaming Chat API compatibility.
- Privacy assertions for no raw provider error, prompt, context, API key, authorization, or provider payload leakage.
## TASK-028 Frontend Testing Strategy

Frontend checks are run from `frontend/`:

```powershell
npm run lint
npm run typecheck
npm run test
npm run test:e2e
npm run build
```

Current test layers:

- Unit: API error parser, permission helpers, formatting-ready utility boundaries.
- SSE: split chunks, multiple events per chunk, unicode, heartbeat comments, final event flushing, terminal event stop, malformed event rejection.
- State machine: stream started, monotonic deltas, completed/error/cancelled terminal behavior, stale event ignore.
- Components: loading, empty, error state rendering and retry action.
- E2E smoke: unauthenticated protected-route redirect, login validation before network submission, mobile reduced-motion usability, admin/staff role-aware navigation, and SSE chat completed-answer/citation rendering with test-only mocked backend responses.

Frontend tests must not call live external LLM providers. Production code must use the real backend API client; mocks are confined to tests. Additional seeded-backend E2E should be added for full chat, document upload, permissions, feedback, audit, and role-specific flows when a deterministic browser test fixture is available.
## TASK-028 live UI acceptance

Live UI acceptance uses `compose.uat.yaml`, a seeded PostgreSQL database, Redis, the real FastAPI backend, the real frontend container, and a deterministic local OpenAI-compatible provider. It does not mock HTTP responses and does not call live external LLM providers.

Commands:

```powershell
$env:E2E_LIVE="true"

docker compose -f compose.yaml -f compose.uat.yaml up -d
docker compose -f compose.yaml -f compose.uat.yaml --profile frontend up -d frontend
cd frontend
npm run test:e2e:live
```

Screenshots are written under `artifacts/uat/screenshots/` and are ignored by Git.

UAT seed stability coverage includes first-run creation, repeated idempotent runs, password hash updates after password env changes, repair of stale known UAT users, reactivation, manager/staff department correction, and preservation of unrelated users. The UAT overlay runs `uat-seed` automatically before API/worker startup; manual reruns use `docker compose -f compose.yaml -f compose.uat.yaml run --rm uat-seed`.

UAT selector and LLM configuration coverage includes:

- Document upload scope behavior: Organization and Private hide Department, Department loads the Department selector, sends `department.id`, blocks empty selection, and handles list API errors safely.
- Permission grant behavior: User and Department selectors load from existing APIs, display friendly labels, send selected UUIDs, clear stale values on grantee-type changes, refresh after success, and map failures to safe UI messages.
- Compose configuration behavior: default Compose keeps LLM disabled; UAT Compose enables the local deterministic OpenAI-compatible provider only and requires no real provider key.
- Live chat behavior: UAT verification uses retrieved documents, grounded answers, citations, no-answer behavior, and SSE events against the local deterministic provider.

TASK-028 live recovery verification on 2026-07-30 also passed:

```powershell
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
npm run test:e2e:live

docker compose --profile test run --rm test python -m pytest -m streaming_chat_integration -v
docker compose --profile test run --rm test python -m pytest -m llm_provider_integration -v
docker compose --profile test run --rm -e RATE_LIMIT_LOGIN_REQUESTS=10000 -e RATE_LIMIT_REFRESH_REQUESTS=10000 -e RATE_LIMIT_CHAT_REQUESTS=10000 -e RATE_LIMIT_UPLOAD_REQUESTS=10000 -e RATE_LIMIT_FEEDBACK_REQUESTS=10000 test python -m pytest -q -m integration tests/api/test_auth_endpoints.py tests/api/test_users_api.py tests/api/test_departments_api.py tests/api/test_documents_api.py tests/api/test_document_upload_api.py tests/api/test_chat_sessions.py tests/api/test_chat_messages.py tests/api/test_feedback.py tests/api/test_audit_logs.py tests/api/test_rbac_dependencies.py
```

The dedicated rate-limit API tests remain the source of truth for `429` behavior. The broad business-flow integration command raises rate limits so repeated login/setup calls do not consume the login limiter before non-rate-limit assertions run.

## TASK-029 Conversation Memory Tests

TASK-029 uses deterministic fake retrieval and fake LLM providers for memory behavior. No test calls a live external provider.

Required focused suites:

```powershell
python -m pytest tests/unit/test_conversation_context_builder.py tests/unit/test_grounded_prompt_builder.py tests/unit/test_chat_context_builder.py tests/unit/test_grounded_answer_service.py tests/unit/test_retrieval_configuration.py
python -m pytest -m integration tests/integration/test_conversation_memory.py
python -m pytest -m integration tests/api/test_chat_messages.py::test_non_streaming_chat_uses_current_session_conversation_memory_only tests/api/test_chat_streaming.py::test_stream_uses_current_session_conversation_memory
python -m pytest -m integration tests/integration/test_chat_session_repository.py::test_memory_messages_include_internal_system_and_filter_owned_session tests/integration/test_grounded_answer_persistence.py::test_internal_system_messages_are_memory_only_not_llm_system_role tests/integration/test_grounded_answer_citations.py::test_answer_persists_citations_with_assistant_message
```

Coverage expectations:

- ConversationContextBuilder loads same-session USER, ASSISTANT, and internal SYSTEM messages through the repository.
- Memory ordering is `created_at ASC, id ASC`; duplicate message IDs are removed.
- History is trimmed by `CHAT_HISTORY_MAX_MESSAGES` and `CHAT_HISTORY_MAX_TOKENS` before formatting.
- Follow-up questions for leave policy and working policy include prior same-session context in the retrieval query and grounded prompt.
- Follow-ups after no-answer cases still return NO_ANSWER when retrieval finds no context and do not call the LLM.
- Non-streaming and `/messages/stream` endpoints use the same memory behavior.
- Citation validation still maps only retrieved context sources; history source-looking markers are not citation sources.
- Prompt, formatted history, retrieval internals, and token-budget internals are not exposed in API responses or audit metadata.
## TASK-030 OCR and Document Image Understanding Tests

Required local suites:

```powershell
python -m pytest tests/unit/test_document_types.py tests/unit/test_image_safety.py tests/unit/test_extraction_models.py tests/unit/test_extraction_router.py tests/unit/test_tesseract_provider.py tests/unit/test_document_image_upload_validation.py tests/unit/test_pymupdf_extractor.py tests/unit/test_document_file_validation.py tests/unit/test_document_processing_pipeline.py tests/unit/test_ocr_retrieval_citation_integration.py tests/unit/test_retrieval_configuration.py -q
python -m pytest tests/unit/test_conversation_context_builder.py tests/unit/test_grounded_prompt_builder.py tests/unit/test_grounded_answer_service.py tests/unit/test_citation_mapping.py tests/unit/test_citation_validation_service.py tests/unit/test_ocr_retrieval_citation_integration.py -q
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python .github/scripts/security_scan.py
python -m compileall app tests
```

Required Docker/runtime suites before TASK-030 can be Completed:

```powershell
docker compose config
docker compose build
docker compose up -d
docker compose ps
docker compose exec api alembic upgrade head
docker compose exec api alembic heads
docker compose exec api alembic current
docker compose exec postgres psql -U app_user -d enterprise_ai -tAc "SELECT extname FROM pg_extension WHERE extname = 'vector';"
docker compose exec redis redis-cli ping
docker compose exec worker tesseract --version
docker compose exec worker tesseract --list-langs
curl.exe -s -S http://127.0.0.1:8000/health/ready
python -m pytest -m integration tests/api/test_document_upload_api.py -q
python -m pytest -m integration tests/integration/test_document_upload_service.py -q
python -m pytest -m integration tests/integration/test_end_to_end_document_processing_pipeline.py -q
```

TASK-030 recovery currently has a runtime blocker: Docker Desktop CLI/status/build/up commands time out and Alembic cannot connect to the Docker-backed PostgreSQL endpoint, so Docker/API/integration results must not be reported as passing until rerun successfully.

## TASK-031 Web Search Tests

TASK-031 tests must not call live internet providers by default. Unit tests use the mock provider, fake services, or `httpx.MockTransport`.

Focused suites:

```powershell
python -m pytest tests/unit/test_web_search_content.py -v
python -m pytest tests/unit/test_web_search_intent.py -v
python -m pytest tests/unit/test_web_search_service.py -v
python -m pytest tests/unit/test_web_search_providers.py -v
python -m pytest tests/unit/test_web_search_registry.py -v
python -m pytest tests/unit/test_grounded_answer_service.py -v
python -m pytest tests/unit/test_citation_mapping.py tests/unit/test_citation_validation_service.py -v
python -m pytest tests/api/test_web_search_admin.py -m integration -v
python -m pytest tests/api/test_chat_messages.py::test_answered_response_returns_web_citations -m integration -v
python -m pytest tests/api/test_chat_streaming.py::test_stream_success_returns_web_citations_ready_event -m integration -v
python -m pytest tests/integration/test_web_search_citation_migration.py -m integration -v
```

Coverage expectations:

- Internal-only, hybrid, and web-only source modes.
- Intent detection for current/web queries, no internal hits, and internal-context-available queries.
- Provider registry support and unsupported-provider rejection.
- Mock provider behavior, provider timeout/failure, retryable HTTP status retry, and external-call blocking.
- Web content sanitization for script/style/hidden/comment/control-character and large-content attacks.
- URL normalization and rejection of unsafe protocols, credentials, local/private/link-local hosts, and fragments.
- Web citation mapping with backend URL/title and no internal document IDs.
- Internal citation permission revalidation remains unchanged.
- Chat and SSE response compatibility for web citations.
- Admin-only provider status and search-test endpoints.

Full verification should also run Ruff, format check, compile, security scan, Alembic heads/current, Docker Compose config/build/up, API/worker/Postgres/Redis health, and non-integration regression suites.

## TASK-032 Admin Monitoring Tests

TASK-032 coverage includes unit, API, integration, RBAC, security, health, provider, worker, queue, statistics, and regression checks.

Focused suites:

```powershell
python -m pytest tests/unit/test_admin_monitoring_service.py -v
python -m pytest tests/api/test_admin_monitoring.py -m integration -v
```

Coverage expectations:

- `/api/v1/admin/*` endpoints are Admin-only.
- Health response covers API, PostgreSQL, Redis, worker, OCR, embedding, LLM, Web Search, streaming, and conversation subsystems.
- Provider responses distinguish disabled, healthy/configured, misconfigured, and unhealthy states without exposing secrets.
- Queue responses report the existing document queue and clearly mark OCR, embedding, retry, and dead-letter queues as not dedicated/configured under the current Celery architecture.
- Statistics return aggregate counts only and do not select or expose plaintext business content.
- System and provider payloads do not contain API keys, authorization headers, database URLs, Redis URLs, passwords, storage keys, prompts, context, citation excerpts, feedback reasons, or raw provider data.

Full verification for TASK-032 also requires Ruff, format check, compile, security scan, Alembic head/current checks, Docker Compose config/build/up/ps, API/worker/PostgreSQL/Redis health, and backend regression suites.


## TASK-033 Admin Analytics Tests

TASK-033 coverage includes unit, API, integration, RBAC, security, export, regression, and performance smoke checks.

Focused suites:

```powershell
python -m pytest tests/unit/test_admin_analytics_service.py -v
python -m pytest tests/api/test_admin_analytics.py -m integration -v
python -m pytest tests/api/test_admin_analytics.py tests/api/test_admin_monitoring.py tests/api/test_web_search_admin.py tests/api/test_rbac_dependencies.py -m integration -v
```

Coverage expectations:

- All `/api/v1/admin/analytics/*` and `/api/v1/admin/reports/export` routes are Admin-only.
- Date filters support today, 7 days, 30 days, 90 days, and timezone-aware custom ranges.
- Chat analytics cover questions, sessions, average response time, unavailable retrieval/streaming metrics, trends, and token totals.
- User analytics cover active users, top users, top departments, and new users without exposing email or full name.
- Search analytics infer internal, hybrid, and web usage from citation source type; top queries are hashed and top documents omit filenames/storage keys/chunk text.
- OCR analytics return image-document success/failure aggregates and explicitly mark OCR duration as unavailable.
- LLM analytics return safe latency, failure, token, and current provider/model metadata without raw provider payloads.
- Feedback analytics omit feedback reasons.
- Audit analytics omit metadata, IP address, user-agent, request body, and target identifiers.
- JSON and CSV exports reuse sanitized analytics payloads; PDF export returns validation error.
- Performance smoke verifies the overview endpoint responds within a bounded local integration threshold on seeded data.

Full verification for TASK-033 also requires Ruff, format check, compile, security scan, Alembic head/current/upgrade checks, Docker Compose config/build/up/ps, API/worker/PostgreSQL/Redis health, migration exit status, and backend regression suites.

## TASK-034 Production Deployment & Observability Tests

TASK-034 coverage includes unit, API, integration, Docker config, health, metrics, logging, backup/restore safety, failure recovery, and regression checks.

Focused suites:

```powershell
python -m pytest tests/unit/test_observability_metrics.py tests/unit/test_runtime_validation.py -q
python -m pytest tests/api/test_observability.py -q
python -m pytest tests/integration/test_production_deployment_config.py -q
```

Required production runtime checks:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m compileall app tests
python .github/scripts/security_scan.py
python -m alembic heads
python -m alembic current
python -m alembic upgrade head
docker compose --env-file .env.production -f compose.prod.yaml config
docker compose --env-file .env.production -f compose.prod.yaml build
docker compose --env-file .env.production -f compose.prod.yaml up -d
docker compose --env-file .env.production -f compose.prod.yaml ps
```

Metrics tests must verify `/metrics` returns Prometheus text, includes API/worker/PostgreSQL/Redis/OCR/embedding/LLM/Web Search/streaming/conversation status gauges, and does not expose prompts, context, OCR text, citation excerpts, feedback reasons, API keys, Redis URLs, database URLs, storage keys, tokens, or passwords.

Logging tests must verify `X-Request-ID`, route-template labels, latency/status fields, and no request body/query logging.

Backup/restore acceptance must create a PostgreSQL backup, verify it with `pg_restore --list`, restore it into an isolated check database, create an uploads archive, verify it with `tar tzf`, and restore it into an isolated check volume.

Failure recovery acceptance should restart API and worker, simulate Redis/PostgreSQL unavailable states in a controlled environment, verify readiness degrades safely, restart dependencies, and verify API/worker/migration/queue health recovers. LLM and Web Search unavailable states must remain safe configuration/provider failures without exposing provider payloads.

## TASK-035 Final Acceptance Status

TASK-035 -- Final Acceptance Test & Release Candidate is not started. Focused UAT selector, Docker UAT, fake-provider, chat, streaming, frontend, backend, and quality regressions from the UAT UX + LLM configuration fix are not a release-candidate sign-off.
## TASK-034.1 Real LLM Strict Grounded Acceptance Tests

TASK-034.1 has two separate test lanes:

- Deterministic UAT/regression: uses `compose.uat.yaml` and `fake-openai-provider.mjs`; allowed in CI/UAT; not valid for real answer-quality claims.
- Real LLM acceptance: opt-in only; uses a real local provider such as Ollama/LM Studio or an explicitly configured external provider; disabled by default.

The opt-in marker is `real_llm_acceptance` and is not included in default pytest runs. The test validator does not contain expected facts or hard-coded answers. It validates a manually completed report for provider authenticity, required case coverage, citation presence, and claim support flags.

Manual real-LLM acceptance must cover:

- exact fact, number, date, named entity
- conditional rule and exception
- multi-source synthesis and paraphrase
- unsupported fact, hallucination trap, false premise
- cross-document contamination
- existing work-policy, leave-policy, and Nova Digital regressions
- same-session Conversation Memory
- non-streaming and streaming chat parity
- organization/department/private/direct grant/revoked grant permissions
- provider unavailable, timeout, malformed response, invalid citation markers
- logging/security and safe metrics

Run the skipped-by-default validator only after the manual report is complete:

```powershell
$env:RUN_REAL_LLM_ACCEPTANCE="true"
$env:REAL_LLM_ACCEPTANCE_REPORT="artifacts/task-034-1/real-llm-acceptance-report.json"
python -m pytest tests/integration/test_real_llm_strict_grounded_acceptance.py -m real_llm_acceptance -q
```

Acceptance rule: any unsupported material factual claim, wrong number/date/name, missing material condition, or irrelevant citation fails TASK-034.1. If full claim-level verifier is not implemented, do not fake it; record manual claim support instead.
### TASK-034.1 Local Ollama Streaming Reliability

The real-LLM acceptance lane must warm up `qwen3:4b` before measuring chat latency. The streaming endpoint remains `buffer_after_validation`: it may emit heartbeats while waiting, but it must not emit `message.delta`, citations, or completion until the grounded answer has been validated and persisted.

Timeout tests cover provider completion before deadline, heartbeat while waiting, single terminal event, cancellation on timeout, and no message/citation persistence after timeout. Deterministic UAT tests continue to use the fake provider and must not depend on real Ollama.

## TASK-034.1.2 RAG Accuracy / Citation Regression Strategy

### Hard rule: regression is not runtime knowledge

Curated questions and expected criteria exist only under tests/UAT.

Do not import them into application runtime code and do not implement question-specific answer branches to make tests pass.

A valid fix must improve a general capability and should also work for paraphrases and unseen questions with the same evidence structure.

### Exact evidence coverage

Focused citation-mapping coverage verifies:

- exact time/range evidence;
- rate/unit preservation such as `8 giờ/ngày`;
- named-entity supporting passages;
- weak-match fallback to `None`;
- backend mapping of `evidence_text`.

Completion checkpoint for exact evidence:

```text
15 passed
```

Persistence UAT additionally verified:

- PostgreSQL stores `message_citations.evidence_text`;
- GET session reload returns the same evidence metadata;
- historical rows without evidence remain compatible.

### Minimal citation selection coverage

Required behavior:

1. Same internal document + same exact evidence => one strongest citation.
2. Same document + different evidence => preserve multiple citations.
3. Public markers are renumbered contiguously after pruning.
4. Removed markers do not leave malformed whitespace/punctuation.
5. Web citations must not be incorrectly grouped through internal `document_id` logic.
6. Multi-claim answers retain enough evidence to support all material claims.

Final focused suite checkpoint:

```text
17 passed in 0.19s
```

The formatting regression is fixed: pruned markers no longer leave `[1] .`; output normalizes to `[1].`.

### Accuracy UAT categories

The current Vietnamese multi-document UAT should include paraphrases across these general categories:

- direct fact / named entity;
- grade/title and salary table lookup;
- neighboring table-row discrimination;
- conditional/exception rules;
- permission/prohibition contradiction;
- workflow/approver role resolution;
- sickness/leave intent separation;
- no-answer;
- multi-document synthesis;
- redundant citation suppression;
- distinct multi-evidence preservation.

When a UAT case fails, record:

- question;
- expected evidence location/criterion;
- retrieved sources;
- final citations;
- failure class (retrieval, reranking, table row, generation, claim validation, citation selection);
- whether a paraphrased variant also fails.

Do not store an expected runtime answer dictionary.


Minimal Citation Selection is not considered fully accepted until a live new Chat message that previously produced duplicate same-evidence citations returns a single citation in both API payload and UI.


## RAG-H2.1 Reranker Authority Tests

Regression coverage must verify that post-processing cannot invert reranker order.

Verified on 2026-08-19:

```text
pytest tests/unit/test_grounded_answer_service.py -q
61 passed in 2.46s

pytest tests/unit/test_rag_accuracy_components.py -q
27 passed in 0.68s

focused combined suite
147 passed in 2.38s
```

Runtime acceptance additionally requires diagnostics to be enabled in the API container and representative live questions to be inspected through the real retrieval/reranking/context flow.


## Runtime LLM failure regression checkpoint

The 2026-08-19 `LLM_GENERATION_FAILED` incident was traced to an application `NameError`, not provider availability.

Recovery verification:

```text
pytest tests/unit/test_grounded_answer_service.py -q
61 passed in 1.34s

focused combined RAG/retrieval suite
147 passed in 2.41s
```

The provider was separately verified through the application's OpenAI-compatible Ollama path before declaring the runtime incident resolved.

Accuracy acceptance is still pending. A NO_ANSWER result for a known-answer salary query must not be treated as provider failure.

## Salary amount regression checkpoint

Added/verified regression behavior for salary AMOUNT questions so grade labels are not treated as number/unit requirements.

Results:
- grounded-answer unit suite: 63 passed.
- focused combined RAG/retrieval suite: 149 passed.
- live Head salary: PASS.
- live Engineering Manager salary: PASS.

## YES/NO next acceptance

For a supported YES/NO question:
- retrieval/source selection must remain correct;
- claim validation must remain supported;
- answer must not be discarded solely because the model omitted the leading polarity token;
- final UX should begin with an explicit `Có.` / `Không.` (or Yes/No for English) plus a short grounded explanation;
- unrelated supported evidence must not determine polarity.

## Citation evidence acceptance

Evidence highlighting should underline the minimal source passage actually supporting the answer. A missing `evidence_text` must not be mistaken for a frontend CSS failure.

## Runtime RAG Acceptance -- 2026-08-21

The seven-case runtime acceptance set passed after restoring the intended UAT annual-leave source through normal ingestion. No runtime question-answer mappings, direct `document_chunks` inserts, or hard-coded annual-leave values were added.

### Pre-UAT corpus verification

Restored source:

- Document ID: `43cb2c93-52bc-44f6-8e03-1b1f075e1d89`
- Title: `Chính sách nghỉ của người lao động`
- Checksum: `24178db420422e474326986672b6c15cc67373ee6adbe1489ba5e8addf95f4f4`
- Storage key: `documents/2026/08/951776f4-88c3-4c98-8401-c8ce5edad268.pdf`
- Worker task: `274fe326-9d28-421c-9c11-253ec7b74bc2`
- Ingestion result: `READY`, `page_count=6`, `chunk_count=12`, `total_tokens=6458`, `embedding_dimensions=384`

Active indexed evidence check before annual-leave UAT:

```text
active ready documents: 12
active chunks: 153
active 12/14/16 leave clause chunks: 1
primary active clause chunk: 4b341201-f0df-4102-b9f2-5ad7091781a6, page 3
```

The active Nova-branded leave policy still only contains the 12-day normal-work clause. The restored UAT document provides the authoritative 12 / 14 / 16 distinctions, but it is generic/template-branded; this remains corpus debt.

### Seven-case runtime UAT

All cases were run as new staff chat sessions against the real local runtime using `qwen2.5:7b-instruct-8k`.

| Case | Expected | Result |
| --- | --- | --- |
| Own salary | `Có`; employee may discuss own salary | PASS |
| EAP | `Không`; EAP does not send counseling contents to manager | PASS |
| NovaCare vs BHYT | `Không`; NovaCare does not replace mandatory BHYT | PASS |
| Engineering Manager | `N5`, `42 - 70 triệu đồng` | PASS |
| Head / Director | `N6`, `65 - 110 triệu đồng` | PASS |
| Annual leave | starts `Không`, distinguishes `12 / 14 / 16`, real leave clause citation, no sample-question citation, `SUPPORTED` | PASS |
| CEO false premise | starts `Không`, identifies `Nguyễn Anh Khoa` from source | PASS |

Observed annual-leave answer:

```text
Không. 12 ngày Công việc trong điều kiện bình thường; 14 ngày Người chưa thành niên, người khuyết tật hoặc công việc nặng nhọc, độc hại, nguy hiểm theo danh mục pháp luật; 16 ngày Công việc đặc biệt nặng nhọc, độc hại, nguy hiểm theo danh mục pháp luật; 12 ngày làm việc/năm khi đủ [1] [2]
```

Annual-leave citations used the restored active leave table on page `3` plus the active Nova leave clause on page `3`. No sample-question/test-question section was cited as factual evidence. Final claim validation status was `SUPPORTED`.

### Unit and static verification

```text
python -m pytest tests\unit\test_grounded_answer_service.py -q
75 passed in 1.33s

python -m pytest tests\unit\test_grounded_answer_service.py tests\unit\test_rag_accuracy_components.py tests\unit\test_citation_mapping.py -q
132 passed in 1.56s

python -m pytest tests\unit\test_grounded_answer_service.py tests\unit\test_rag_accuracy_components.py tests\unit\test_citation_mapping.py tests\unit\test_citation_validation_service.py tests\unit\test_grounded_output.py -q
157 passed in 1.71s

python -m pytest tests\unit -q
1061 passed in 8.22s

python -m ruff check <21 touched Python files>
All checks passed!

python -m ruff format --check <21 touched Python files>
21 files already formatted
```

### Acceptance coverage added by this checkpoint

- Answer-bearing evidence/source-quality selection prefers real policy clauses/tables over sample-question text.
- YES/NO claim validation is subject/object aware.
- Replacement/supplemental relation entailment is covered by NovaCare versus BHYT.
- Citation source repair is covered by no sample-question citation in annual leave and by citation pruning/marker repair suites.

### Remaining testing debt

- Automate the seven-case runtime UAT so each run captures prompt, answer, citations, evidence text, claim-validation diagnostics, provider/model, and latency.
- Add a regression that asserts multi-row/table `evidence_text` can cover the full annual-leave 12 / 14 / 16 support span.
- Add an explicit runtime reranker availability check so fallback reranking is visible in acceptance reports.
- Add corpus-quality checks that flag sample-question/test-question sections inside production factual documents.