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
$env:UAT_SEED_ENABLED="true"
$env:UAT_ADMIN_PASSWORD="<local-only-password>"
$env:UAT_MANAGER_PASSWORD="<local-only-password>"
$env:UAT_STAFF_PASSWORD="<local-only-password>"
$env:E2E_LIVE="true"

docker compose -f compose.yaml -f compose.uat.yaml --profile frontend --profile test build
docker compose -f compose.yaml -f compose.uat.yaml --profile frontend up -d
docker compose -f compose.yaml -f compose.uat.yaml run --rm api python -m app.scripts.seed_uat_data
cd frontend
npm run test:e2e:live
```

Screenshots are written under `artifacts/uat/screenshots/` and are ignored by Git.
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
