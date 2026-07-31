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

TASK-001 through TASK-025 are completed for Phase 1.

Current project status:

- Phase 1: Completed.
- Phase 2: In Progress.
- Backend MVP: Completed.
- Docker stack: Completed.
- CI pipeline: Completed.
- MVP hardening: Completed.
- Current task: None.
- Next task: TASK-028 -- Frontend UI Foundation & Test Console.
- Frontend foundation: Planned for TASK-028; no frontend is implemented in TASK-027.

TASK-026 extends the LLM layer while preserving grounded-answer and citation contracts. Supported provider names are `openai_compatible`, `azure_openai`, `gemini`, `anthropic`, `ollama`, `lm_studio`, and `openrouter`. Ollama, LM Studio, OpenRouter, OpenAI, and custom enterprise gateways use the OpenAI-compatible adapter when configured through compatible endpoints.

The default stack still starts with `LLM_ENABLED=false`, requires no external LLM key, and adds no LLM container. Remote OpenAI-compatible endpoints require an API key; local host providers may omit it. To use a host local provider from Docker, configure `host.docker.internal` in `.env`; Linux Docker hosts may need an explicit host-gateway mapping outside the default Compose file.

See `RELEASE_CHECKLIST.md` before treating any environment as release-ready.

TASK-027 adds a backend SSE chat endpoint at `POST /api/v1/chat/sessions/{session_id}/messages/stream`. The streaming transport preserves the existing grounded-answer and citation-validation policy by buffering the generated answer, validating it, persisting the final USER/ASSISTANT message pair atomically, and then emitting the validated answer as SSE events. The existing non-streaming Chat API is unchanged.
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