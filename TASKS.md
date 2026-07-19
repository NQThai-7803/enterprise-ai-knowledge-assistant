# Implementation Tasks

## Quy tÃƒÂ¡Ã‚ÂºÃ‚Â¯c

- LÃƒÆ’Ã‚Â m theo thÃƒÂ¡Ã‚Â»Ã‚Â© tÃƒÂ¡Ã‚Â»Ã‚Â± trÃƒÂ¡Ã‚Â»Ã‚Â« khi cÃƒÆ’Ã‚Â³ lÃƒÆ’Ã‚Â½ do kÃƒÂ¡Ã‚Â»Ã‚Â¹ thuÃƒÂ¡Ã‚ÂºÃ‚Â­t rÃƒÆ’Ã‚Âµ rÃƒÆ’Ã‚Â ng.
- MÃƒÂ¡Ã‚Â»Ã¢â‚¬â€i task phÃƒÂ¡Ã‚ÂºÃ‚Â£i cÃƒÆ’Ã‚Â³ test hoÃƒÂ¡Ã‚ÂºÃ‚Â·c cÃƒÆ’Ã‚Â¡ch kiÃƒÂ¡Ã‚Â»Ã†â€™m thÃƒÂ¡Ã‚Â»Ã‚Â­.
- Sau mÃƒÂ¡Ã‚Â»Ã¢â‚¬â€i task cÃƒÂ¡Ã‚ÂºÃ‚Â­p nhÃƒÂ¡Ã‚ÂºÃ‚Â­t `PROJECT_STATUS.md` vÃƒÆ’Ã‚Â  `CHANGELOG.md`.

---

## TASK-001 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Initialize backend project

**Status:** Completed.

### Goal

TÃƒÂ¡Ã‚ÂºÃ‚Â¡o nÃƒÂ¡Ã‚Â»Ã‚Ân tÃƒÂ¡Ã‚ÂºÃ‚Â£ng FastAPI cÃƒÆ’Ã‚Â³ cÃƒÂ¡Ã‚ÂºÃ‚Â¥u trÃƒÆ’Ã‚Âºc rÃƒÆ’Ã‚Âµ rÃƒÆ’Ã‚Â ng vÃƒÆ’Ã‚Â  chÃƒÂ¡Ã‚ÂºÃ‚Â¡y Ãƒâ€žÃ¢â‚¬ËœÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£c trÃƒÆ’Ã‚Âªn Visual Studio Code.

### Deliverables

- Python project configuration.
- `app/main.py`.
- `app/core/config.py`.
- Health live endpoint.
- Test Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚ÂºÃ‚Â§u tiÃƒÆ’Ã‚Âªn.
- `.gitignore`.
- `.env.example`.

### Acceptance criteria

- Backend chÃƒÂ¡Ã‚ÂºÃ‚Â¡y bÃƒÂ¡Ã‚ÂºÃ‚Â±ng uvicorn.
- `/health/live` trÃƒÂ¡Ã‚ÂºÃ‚Â£ 200.
- Test pass.
- Ruff hoÃƒÂ¡Ã‚ÂºÃ‚Â·c lint setup hoÃƒÂ¡Ã‚ÂºÃ‚Â¡t Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ng.

---

## TASK-002 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Docker infrastructure

**Status:** Completed.

### Deliverables

- Docker Compose vÃƒÂ¡Ã‚Â»Ã¢â‚¬Âºi PostgreSQL pgvector vÃƒÆ’Ã‚Â  Redis.
- Volume persistence.
- Health checks.

### Acceptance criteria

- `docker compose up -d` chÃƒÂ¡Ã‚ÂºÃ‚Â¡y thÃƒÆ’Ã‚Â nh cÃƒÆ’Ã‚Â´ng.
- PostgreSQL vÃƒÆ’Ã‚Â  Redis healthy.

---

## TASK-003 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Database foundation

**Status:** Completed.

### Deliverables

- Async SQLAlchemy session.
- Declarative base.
- Alembic config.
- Database readiness check.

### Acceptance criteria

- Migration chÃƒÂ¡Ã‚ÂºÃ‚Â¡y Ãƒâ€žÃ¢â‚¬ËœÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£c.
- `/health/ready` kiÃƒÂ¡Ã‚Â»Ã†â€™m tra database.

---

## TASK-004 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â User and department models

**Status:** Completed.

### Deliverables

- Department model.
- User model.
- Role enum.
- Initial migration.
- Seed Admin development command.

### Acceptance criteria

- Tables Ãƒâ€žÃ¢â‚¬ËœÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£c tÃƒÂ¡Ã‚ÂºÃ‚Â¡o.
- Unique email hoÃƒÂ¡Ã‚ÂºÃ‚Â¡t Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ng.
- Password khÃƒÆ’Ã‚Â´ng lÃƒâ€ Ã‚Â°u plaintext.

---

## TASK-005 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Authentication

**Status:** Completed.

### Deliverables

- Login.
- Access token.
- Refresh token persisted as hash.
- Refresh.
- Logout.
- Current user endpoint.

### Acceptance criteria

- Active user login thÃƒÆ’Ã‚Â nh cÃƒÆ’Ã‚Â´ng.
- Wrong password thÃƒÂ¡Ã‚ÂºÃ‚Â¥t bÃƒÂ¡Ã‚ÂºÃ‚Â¡i.
- Inactive user bÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ tÃƒÂ¡Ã‚Â»Ã‚Â« chÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi.
- Revoked refresh token khÃƒÆ’Ã‚Â´ng dÃƒÆ’Ã‚Â¹ng lÃƒÂ¡Ã‚ÂºÃ‚Â¡i Ãƒâ€žÃ¢â‚¬ËœÃƒâ€ Ã‚Â°ÃƒÂ¡Ã‚Â»Ã‚Â£c.

---

## TASK-006 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â RBAC dependencies and policies

**Status:** Completed.

### Deliverables

- Role guard.
- Permission policy helpers.
- Tests for Admin, Manager, Staff.

### Acceptance criteria

- Staff khÃƒÆ’Ã‚Â´ng truy cÃƒÂ¡Ã‚ÂºÃ‚Â­p Admin endpoint.

---

## TASK-007 Ã¢â‚¬â€ User and department APIs

**Status:** Completed.

### Deliverables

- Admin CRUD.
- Pagination.
- Validation.
- Audit log cÃƒâ€ Ã‚Â¡ bÃƒÂ¡Ã‚ÂºÃ‚Â£n.

---

## TASK-008 Ã¢â‚¬â€ Document data model

**Status:** Completed.

### Deliverables

- Document model.
- Access scope.
- Status enum.
- Document permission model.
- Migration.

---

## TASK-009 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Local file storage and upload

**Status:** Completed.

### Deliverables

- Storage abstraction.
- Local implementation.
- PDF validation.
- Upload endpoint.
- Checksum.
- 202 response.

### Acceptance criteria

- Upload hÃƒÂ¡Ã‚Â»Ã‚Â£p lÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¡ tÃƒÂ¡Ã‚ÂºÃ‚Â¡o document UPLOADED.
- File sai loÃƒÂ¡Ã‚ÂºÃ‚Â¡i bÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ tÃƒÂ¡Ã‚Â»Ã‚Â« chÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi.
- File rÃƒÂ¡Ã‚Â»Ã¢â‚¬â€ng bÃƒÂ¡Ã‚Â»Ã¢â‚¬Â¹ tÃƒÂ¡Ã‚Â»Ã‚Â« chÃƒÂ¡Ã‚Â»Ã¢â‚¬Ëœi.

---

## TASK-010 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Document listing and access control

**Status:** Completed.

### Deliverables

- List/detail/download/update/delete.
- Permission-aware filters.

### Acceptance criteria

- Department B khÃƒÆ’Ã‚Â´ng thÃƒÂ¡Ã‚ÂºÃ‚Â¥y document Department A.
- Direct grant hoÃƒÂ¡Ã‚ÂºÃ‚Â¡t Ãƒâ€žÃ¢â‚¬ËœÃƒÂ¡Ã‚Â»Ã¢â€žÂ¢ng.

---

## TASK-011 - Celery and Redis worker

**Status:** Completed.

### Deliverables

- Celery app.
- Redis broker and result backend configuration.
- Default and Document queues.
- Worker ping task.
- Document task skeleton.
- Worker-specific database session.
- Atomic status transitions.
- Bounded retry foundation.
- Unit, PostgreSQL integration, and real Redis/Celery worker tests.

---
## TASK-012 - PDF extraction

**Status:** Completed.

### Deliverables

- TextExtractor abstraction.
- PyMuPDF extractor.
- Page-level text.
- Unicode and whitespace normalization.
- Extraction result models.
- Encrypted/corrupt PDF handling.
- Page-limit validation.
- No-usable-text detection.
- Unit and storage integration tests.

---
## TASK-013 - Chunking

**Status:** Completed.

### Deliverables

- Token-aware chunker.
- Overlap.
- Metadata.
- Unit tests.

---

## TASK-014 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â pgvector and embeddings

**Status:** Completed.

### Deliverables

- Extension migration.
- Chunk model with vector.
- Embedding provider interface.
- Batch embedding.

---

## TASK-015 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Document processing pipeline

**Status:** Completed.

### Deliverables

- End-to-end worker.
- Idempotent reprocess.
- READY/FAILED state.

---

## TASK-016 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Retrieval service

**Status:** Completed.

### Deliverables

- Semantic search.
- Permission filtering.
- Top-k and threshold.
- Tests for leakage.

---

## TASK-017 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Keyword and hybrid search

**Status:** Completed.

### Deliverables

- PostgreSQL full-text search.
- Hybrid score merge.

---

## TASK-018 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Chat data model and APIs


**Status:** Next.

### Deliverables

- Session and message models.
- Create/list/read session.
- Ownership checks.

---

## TASK-019 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â LLM provider and grounded answer

### Deliverables

- LLM provider interface.
- Prompt builder.
- No-answer behavior.
- Token usage tracking.

---

## TASK-020 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Citation validation

### Deliverables

- Source markers.
- Citation mapping.
- Permission revalidation.
- Excerpt response.

---

## TASK-021 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Feedback

### Deliverables

- Upsert feedback.
- Manager/Admin reporting scope.

---

## TASK-022 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Audit log expansion

### Deliverables

- Audit service.
- Admin filters.
- Events for documents and chat.

---

## TASK-023 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Docker full backend stack

### Deliverables

- Backend container.
- Worker container.
- Startup/migration flow.

---

## TASK-024 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â CI pipeline

### Deliverables

- Lint.
- Type check.
- Tests.
- Build validation.

---

## TASK-025 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â MVP hardening

### Deliverables

- Rate limiting.
- CORS config.
- Upload edge cases.
- Retrieval evaluation set.
- Security regression tests.
