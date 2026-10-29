# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Internal RAG knowledge assistant: FastAPI + SQLAlchemy 2 (async) + PostgreSQL/pgvector + Redis/Celery backend in `app/`, React/TypeScript/Vite frontend in `frontend/`. The corpus and UAT questions are mostly Vietnamese. The project docs (`ARCHITECTURE.md`, `RAG_DESIGN.md`, `API_SPEC.md`, `DATABASE_DESIGN.md`, `SECURITY.md`, `RBAC.md`, `TESTING_STRATEGY.md`) are the source of truth for design. The latest handoff and current task state are in `CODEX_START_HERE.md` (the top section is the newest), `PROJECT_STATUS.md` and `TASKS.md`.

## Commands

Backend (Python 3.12+, install with `pip install -e ".[dev]"`):

```powershell
python -m pytest tests\unit -q                                   # fast unit suite (no DB needed)
python -m pytest tests\unit\test_grounded_answer_service.py -q   # single file
python -m pytest tests\unit\test_x.py::test_name -q              # single test
python -m pytest tests\api -m integration                         # needs real PostgreSQL via DATABASE_URL
python -m ruff check .
python -m ruff format --check .
python -m alembic upgrade head
```

- `pyproject.toml` adds `-m "not integration"` by default. The other markers (`celery_integration`, `embedding_model_integration`, `hybrid_retrieval_model_integration`, `llm_provider_integration`, `real_llm_acceptance`, ...) select tests that need real infrastructure or models. `.github/workflows/ci.yml` shows the exact marker combinations CI runs.
- CI runs `tests/unit` with `APP_ENV`, `LLM_BASE_URL` and `SECRET_KEY` unset, so unit tests must not depend on those env vars.
- Integration fixtures (`tests/conftest.py`) run `alembic upgrade head` themselves and refuse to run against production-looking database URLs.
- CI requires exactly one Alembic head. Every schema change needs a migration in `app/db/migrations/versions/`.

Frontend (`cd frontend`, Node 24 / npm 11 in CI):

```powershell
npm run dev          # http://127.0.0.1:5173, API from VITE_API_BASE_URL (default http://127.0.0.1:8000)
npm run lint
npm run typecheck
npm run test         # vitest
npx vitest run src/api/sse.test.ts   # single vitest file
npm run test:e2e     # Playwright with mocked backend
npm run build
```

Docker stacks:

```powershell
docker compose up -d                                      # postgres, redis, migrate, api, worker (Swagger at :8000/docs)
docker compose -f compose.yaml -f compose.uat.yaml up -d  # + deterministic fake LLM + seeded *.uat@example.test accounts
docker compose --profile frontend up -d frontend
docker compose --env-file .env.production -f compose.prod.yaml up -d   # prod: nginx on :8080, optional observability profile
```

Never run `docker compose down -v`, because it deletes the local corpus volumes.

## Architecture

The layering is strict: `api/v1` routers → `services` → `repositories` → DB. Routers hold no business logic and never call Celery or the DB directly. Services raise domain exceptions (`app/core/exceptions.py`), not `HTTPException`. Repositories apply permission filters in their queries. External systems sit behind provider interfaces built by factories: `app/llm` (OpenAI-compatible, Azure, Gemini, Anthropic; Ollama, LM Studio and OpenRouter go through the OpenAI-compatible adapter), `app/embeddings` (sentence-transformers, `multilingual-e5-small`, 384 dims), `app/storage`, `app/web_search`, and the reranker in `app/retrieval/reranker_factory.py`.

**Ingestion**: upload (`document_service`) → Celery task (`app/workers/document_tasks.py`) → `document_processing_pipeline`: extraction (PyMuPDF plus Tesseract OCR for images and scanned pages) → page-aware chunking → embeddings → `document_chunks` with pgvector. The document status goes UPLOADED → … → READY. Fix corpus problems by reprocessing documents through this pipeline, never by editing `document_chunks` directly.

**Chat / grounded answer** (the core logic; `app/services/grounded_answer_service.py` orchestrates it):
1. Same-session memory via `app/chat/conversation_context_builder.py` and `follow_up_resolver.py`.
2. Question analysis and subclaims (`app/retrieval/question_analysis.py`, `subclaims.py`, `structured.py`).
3. Permission-scoped hybrid retrieval (`hybrid_service.py` = semantic + keyword + `fusion.py`), then reranking and evidence quality/authority ranking (`evidence_quality.py`, `authority.py`).
4. Context admission and token budget (`app/chat/context_builder.py`), then a source-marked prompt (`app/chat/prompt_builder.py`). Retrieved text is untrusted data and never goes into a SYSTEM message.
5. The LLM emits only `[SOURCE_n]` markers. The backend (`app/citations/`: registry, parser, mapper, pruning, evidence) validates the markers, re-checks permissions, builds the citations and `evidence_text` server-side, and prunes redundant same-document/same-evidence citations before numbering.
6. Claim-level validation (`claim_evidence_validation_service.py`, `citation_validation_service.py`). If validation fails, the answer becomes the fixed no-answer with no citations.
7. The USER and ASSISTANT messages and the citations are persisted atomically.

SSE streaming (`chat_stream_service.py`, `app/chat/sse.py`) buffers the full answer and validates it before emitting anything, so it follows the same rules as non-streaming chat. Web search (disabled by default) merges results into the same context and cites them as `source_type=WEB`.

Admin monitoring and analytics (`/api/v1/admin/*`) return only safe aggregates. They never expose prompts, context, chat content, excerpts, keys or URLs. Request logs follow the same restriction.

## Non-negotiable rules

- **No question-specific runtime logic.** Regression/UAT questions (e.g. under `tests/acceptance/`, `uat/`) are test inputs only. Never add question→answer mappings or hard-coded expected answers. Improve query understanding, retrieval, reranking, evidence selection and validation in general ways.
- The AI must never retrieve or cite documents the user isn't authorized for. Citations come only from authorized retrieved chunks.
- Don't add libraries without justification. Keep each task's changes scoped to the relevant modules.
- After each task, update `PROJECT_STATUS.md`, `CHANGELOG.md` and `TASKS.md`, plus any affected spec/design doc.
- Commits use Conventional Commits (`feat(rag): ...`, `fix(citations): ...`).
- Ruff: line length 100, rules `B,E,F,I,SIM,UP`. Use the structured logger, never `print`, in application code.
