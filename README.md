# Enterprise AI Knowledge Assistant

Hệ thống trợ lý AI nội bộ giúp doanh nghiệp upload, quản lý, tìm kiếm và hỏi đáp trên tài liệu bằng RAG, có phân quyền, citation, lịch sử chat, feedback và audit log.

## Mục tiêu chính

- Tập trung tài liệu nội bộ vào một hệ thống có kiểm soát.
- Cho phép người dùng hỏi đáp bằng ngôn ngữ tự nhiên.
- Chỉ sử dụng tài liệu mà người dùng được phép truy cập.
- Trả lời kèm tài liệu nguồn và số trang.
- Giảm hallucination bằng retrieval threshold và fallback rõ ràng.
- Theo dõi hoạt động bằng audit log.

## Vai trò

- **Admin:** quản lý người dùng, phòng ban, tài liệu, quyền và hệ thống.
- **Manager:** quản lý tài liệu và quy trình trong phạm vi phòng ban.
- **Staff:** tìm kiếm, chat, xem tài liệu và gửi feedback.

## Phạm vi MVP

1. Authentication bằng JWT.
2. RBAC cho Admin, Manager, Staff.
3. Quản lý người dùng và phòng ban.
4. Upload PDF.
5. Trích xuất text theo trang.
6. Chunking và embedding.
7. PostgreSQL + pgvector.
8. Hybrid retrieval cơ bản.
9. Chat với tài liệu.
10. Citation theo file và trang.
11. Lịch sử chat.
12. Feedback.
13. Audit log cơ bản.
14. Docker Compose.

## Công nghệ dự kiến

- Python 3.12+
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- pgvector
- Redis
- Celery
- PyMuPDF
- React + TypeScript ở giai đoạn frontend
- Docker và Docker Compose

## Cấu trúc tài liệu

- `CODEX_START_HERE.md`: quy tắc làm việc cho Codex.
- `PROJECT_OVERVIEW.md`: tổng quan nghiệp vụ.
- `PRODUCT_REQUIREMENTS.md`: yêu cầu sản phẩm.
- `ARCHITECTURE.md`: kiến trúc hệ thống.
- `DATABASE_DESIGN.md`: thiết kế dữ liệu.
- `API_SPEC.md`: đặc tả API.
- `SECURITY.md`: nguyên tắc bảo mật.
- `RAG_DESIGN.md`: thiết kế pipeline AI/RAG.
- `SETUP.md`: hướng dẫn cài đặt.
- `PROJECT_ROADMAP.md`: lộ trình phát triển.
- `PROJECT_STATUS.md`: tiến độ hiện tại.
- `TASKS.md`: danh sách task triển khai.

## Thứ tự triển khai

```text
Project Setup
→ Database
→ Authentication
→ RBAC
→ User Management
→ Document Upload
→ Document Processing
→ Vector Search
→ AI Chat
→ Citation
→ Feedback
→ Audit Log
→ Frontend
→ Workflow
→ Deployment
```

## Quick Start

```powershell
Copy-Item .env.example .env
docker compose build
docker compose up -d
docker compose ps
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

The default Compose stack runs PostgreSQL with pgvector, Redis, a one-shot Alembic migration, the FastAPI API, and the Celery document worker. It keeps PostgreSQL, Redis, uploads, and model cache data in named Docker volumes.

Stop the stack without deleting development data:

```powershell
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to remove local named volumes.

## Status

TASK-001 through TASK-034 are completed. TASK-035 -- Final Acceptance Test & Release Candidate is not started.

Current project status:

- Phase 1: Completed.
- Phase 2 backend roadmap: Completed through TASK-034.
- Backend MVP: Completed.
- Docker stack: Completed.
- CI pipeline: Completed.
- MVP hardening: Completed.
- Frontend foundation: Completed through TASK-028 live acceptance.
- Conversation memory: Completed in TASK-029.
- Current UAT fix: UX selectors and UAT LLM configuration completed.
- Next roadmap task: TASK-035 -- Final Acceptance Test & Release Candidate is pending and not started.

TASK-026 extends the LLM layer while preserving grounded-answer and citation contracts. Supported provider names are `openai_compatible`, `azure_openai`, `gemini`, `anthropic`, `ollama`, `lm_studio`, and `openrouter`. Ollama, LM Studio, OpenRouter, OpenAI, and custom enterprise gateways use the OpenAI-compatible adapter when configured through compatible endpoints.

The default stack still starts with `LLM_ENABLED=false`, requires no external LLM key, and adds no LLM container. Remote OpenAI-compatible endpoints require an API key; local host providers may omit it. To use a host local provider from Docker, configure `host.docker.internal` in `.env`; Linux Docker hosts may need an explicit host-gateway mapping outside the default Compose file.

For local UAT chat without a real provider, use the deterministic overlay:

```powershell
docker compose -f compose.yaml -f compose.uat.yaml up -d
```

If API or worker containers were already started without the overlay, recreate only the affected services without deleting volumes:

```powershell
docker compose -f compose.yaml -f compose.uat.yaml up -d --force-recreate uat-seed api worker uat-llm
```

The UAT overlay sets `LLM_ENABLED=true`, `LLM_PROVIDER=openai_compatible`, `LLM_MODEL=uat-deterministic-model`, and `LLM_OPENAI_BASE_URL=http://uat-llm:18080/v1`. It also runs the idempotent `uat-seed` service, which upserts the fixed local test accounts `admin.uat@example.test`, `manager.uat@example.test`, and `staff.uat@example.test` with deterministic test-only passwords. It does not require a real provider API key.

No Release Candidate version is marked by the current UAT fix. Python package version remains `0.1.0`. Alembic head: `20260803_0010`. TASK-035 has not started.

See RELEASE_CHECKLIST.md before treating any environment as release-ready.

TASK-027 adds a backend SSE chat endpoint at `POST /api/v1/chat/sessions/{session_id}/messages/stream`. The streaming transport preserves the existing grounded-answer and citation-validation policy by buffering the generated answer, validating it, persisting the final USER/ASSISTANT message pair atomically, and then emitting the validated answer as SSE events. The existing non-streaming Chat API is unchanged.

TASK-029 adds same-session Conversation Memory for both non-streaming and SSE chat. The backend loads USER, ASSISTANT, and internal SYSTEM messages only from the current ChatSession, orders them by `created_at ASC, id ASC`, trims them with `CHAT_HISTORY_MAX_MESSAGES` and `CHAT_HISTORY_MAX_TOKENS`, and formats them through `ConversationContextBuilder` before retrieval and prompt construction. Conversation history helps resolve follow-up questions, but retrieval remains mandatory, citations still come only from retrieved context, and formatted prompts are not persisted.

## Frontend Console

TASK-028 adds a production React/TypeScript frontend in `frontend/`.

```powershell
cd frontend
npm install
npm run dev
```

Default local URL:

```text
http://127.0.0.1:5173
```

The browser API base URL is configured with `VITE_API_BASE_URL` and defaults to `http://127.0.0.1:8000`. The frontend uses real backend APIs for authentication, documents, chat, SSE streaming, citations, users, departments, feedback, audit logs, and system status. It does not embed LLM provider keys, database credentials, Redis credentials, or JWT signing secrets.

Document upload uses a Department selector for `DEPARTMENT` access scope and sends `department.id`. Document permission grants use User or Department selectors and send the selected UUID according to the existing backend API contract; raw UUID entry is not exposed in the normal UI.

Frontend documentation:

- `docs/ui/STITCH_WORKFLOW.md`
- `docs/ui/STITCH_SCREEN_PROMPTS.md`
- `docs/ui/DESIGN_SYSTEM.md`
- `docs/ui/SCREEN_INVENTORY.md`
- `docs/ui/REACT_BITS_INVENTORY.md`
- `docs/ui/FRONTEND_ARCHITECTURE.md`
- `docs/ui/FRONTEND_TESTING.md`

Frontend quality gates:

```powershell
cd frontend
npm run lint
npm run typecheck
npm run test
npm run test:e2e
npm run build
```

Docker Compose includes a frontend profile:

```powershell
docker compose --profile frontend up -d frontend
```
## OCR recovery status

TASK-030 recovery added PDF/PNG/JPEG ingestion with bounded Tesseract OCR for image documents and scanned/low-quality PDF pages. Later Docker/API/worker/PostgreSQL/Redis/migration verification recovered and TASK-030 is tracked as completed.
## Web Search Integration Status

TASK-031 adds optional hybrid knowledge grounding across internal KB and web search. Web search is disabled by default. Backend configuration selects `WEB_SEARCH_MODE=internal_only`, `hybrid`, or `web_only` and a provider from `mock`, `bing`, `duckduckgo`, or `google_custom_search`.

The Chat API request body is unchanged. When enabled, the backend still runs the existing internal hybrid retrieval path first unless mode is `web_only`; intent detection decides whether web search is needed. Web results are cleaned, normalized, length-limited, merged into the same retrieved-context prompt, and cited as `source_type=WEB`. Internal citations keep the existing response shape; web citations include `source_type` and `source_url` from backend provider results, not from LLM output.

External calls require `WEB_SEARCH_ALLOW_EXTERNAL=true` and provider-specific configuration. The mock provider is available for local tests without network access.

## Admin Monitoring APIs

TASK-032 adds backend-only Admin monitoring endpoints under `/api/v1/admin`. These endpoints do not add a UI and do not change Chat, Streaming, Conversation Memory, Citation, OCR processing, or Web Search behavior.

Admin-only endpoints:

```text
GET /api/v1/admin/system
GET /api/v1/admin/health
GET /api/v1/admin/providers
GET /api/v1/admin/workers
GET /api/v1/admin/statistics
GET /api/v1/admin/queues
GET /api/v1/admin/version
```

The monitoring payloads expose safe aggregate state for API uptime, PostgreSQL, Redis, Celery worker, OCR, embedding configuration, LLM provider configuration, Web Search provider configuration, streaming registration, conversation memory configuration, document queue state, and database statistics. They do not return API keys, database or Redis URLs, prompts, retrieved context, chat content, citation excerpts, feedback reasons, storage keys, or raw provider payloads.


## Admin Analytics APIs

TASK-033 adds backend-only Admin analytics and report export endpoints under `/api/v1/admin`. These endpoints do not add a UI, React screens, charts, or localization changes.

Admin-only analytics endpoints:

```text
GET /api/v1/admin/analytics/overview
GET /api/v1/admin/analytics/chat
GET /api/v1/admin/analytics/users
GET /api/v1/admin/analytics/search
GET /api/v1/admin/analytics/ocr
GET /api/v1/admin/analytics/llm
GET /api/v1/admin/analytics/feedback
GET /api/v1/admin/analytics/audit
GET /api/v1/admin/reports/export
```

All analytics endpoints support `period=today`, `7d`, `30d`, `90d`, or `custom`. Custom ranges require timezone-aware `date_from` and `date_to` values. Analytics use UTC windows.

Exports support `format=json` and `format=csv`. `format=pdf` returns a validation error because the backend does not currently include PDF report export infrastructure. Analytics responses return aggregate counts, trends, hashed top queries, safe document titles for top cited documents, and token totals as `input_tokens` and `output_tokens`. They do not return prompts, retrieved context, chat content, citation excerpts, feedback reasons, storage keys, database URLs, Redis URLs, API keys, or raw provider payloads.

## Production Deployment & Observability

TASK-034 adds backend-only production deployment and observability assets. The development `compose.yaml` remains unchanged for local work. Production uses `compose.prod.yaml` with PostgreSQL, Redis, migration, API, worker, Nginx reverse proxy, and optional Prometheus/Grafana profile.

Production configuration starts from `.env.production.example`, but real deployments must provide private values through `.env.production`, injected environment variables, or Docker secret files referenced by `*_FILE` variables. The example file intentionally contains placeholders and must not be used as a real secret source.

Common production checks:

```powershell
docker compose --env-file .env.production -f compose.prod.yaml config
docker compose --env-file .env.production -f compose.prod.yaml build
docker compose --env-file .env.production -f compose.prod.yaml up -d
docker compose --env-file .env.production -f compose.prod.yaml ps
curl.exe -i http://127.0.0.1:8080/health/live
curl.exe -i http://127.0.0.1:8080/health/ready
```

The API exposes Prometheus text metrics at `/metrics` for internal scraping. The production reverse proxy returns `404` for external `/metrics`; Prometheus scrapes `api:8000/metrics` on the Docker backend network. Request IDs are returned in `X-Request-ID`, request latency is recorded in memory, and request logs do not include bodies, query strings, prompts, context, document text, citation excerpts, feedback reasons, credentials, or provider payloads.

Backup and restore helpers live in `scripts/backup/` for PostgreSQL dumps and upload volume archives. Restore scripts default to isolated check targets and require an explicit overwrite switch before touching production targets.

TASK-034 verification on 2026-08-04 passed production Compose config/build/up/ps, development Compose config/build/up/ps, reverse proxy health, internal Prometheus metrics, external metrics blocking, Celery worker ping, Alembic current/head `20260803_0010`, backup/restore checks, Redis/PostgreSQL degraded readiness and recovery, dependency audit, security scan, and backend regression suites.

## TASK-034.1 Real/Local LLM Strict Grounded Acceptance

TASK-034.1 is a strict real-runtime acceptance track before TASK-035. It is not a release-candidate sign-off and does not start TASK-035.

Provider modes are intentionally separate:

- Deterministic UAT mode uses `compose.uat.yaml` and `frontend/tests/e2e-live/fake-openai-provider.mjs`. This is for CI/UAT regression only and must not be used for real answer-quality claims.
- Local real LLM mode is explicit opt-in. Preferred local provider is Ollama through the existing `ollama` provider alias. LM Studio is also supported through `lm_studio`.
- External real LLM mode is optional and explicit. Retrieved document context is sent to the configured external provider.

Recommended local acceptance configuration for Docker Desktop on this machine:

```env
LLM_ENABLED=true
LLM_PROVIDER=ollama
LLM_OLLAMA_BASE_URL=http://host.docker.internal:11434
LLM_OLLAMA_MODEL=qwen3:4b
LLM_OLLAMA_REASONING_EFFORT=none
LLM_TIMEOUT_SECONDS=180
LLM_STREAM_HEARTBEAT_SECONDS=15
LLM_STREAM_MAX_DURATION_SECONDS=300
LLM_TEMPERATURE=0.0
LLM_MAX_OUTPUT_TOKENS=1024
WEB_SEARCH_ENABLED=false
WEB_SEARCH_MODE=internal_only
```

If `qwen3:4b` is too slow or does not fit memory, use a smaller multilingual instruct model such as `qwen2.5:3b`. Do not download a multi-GB model silently; install/start the local provider and pull the selected model deliberately.

TASK-034.1 acceptance uses new local artifacts under `artifacts/task-034-1/`, which is git-ignored. These documents are not encoded in the fake provider, tests, or source code. Manual acceptance must upload/process them through the real document pipeline, ask the required questions, and record claim-level citation support in `artifacts/task-034-1/real-llm-acceptance-report.json`.

The disabled-by-default report validator is:

```powershell
$env:RUN_REAL_LLM_ACCEPTANCE="true"
$env:REAL_LLM_ACCEPTANCE_REPORT="artifacts/task-034-1/real-llm-acceptance-report.json"
python -m pytest tests/integration/test_real_llm_strict_grounded_acceptance.py -m real_llm_acceptance -q
```

Current local status: Ollama `qwen3:4b` connectivity and SSE streaming have been verified for the Nova Digital CEO, CTO, and NovaAssist live questions with no `STREAM_TIMEOUT`. Run the full strict matrix and manual claim report before marking TASK-034.1 complete.
