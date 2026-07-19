# Project Roadmap

## Phase 0 — Documentation and repository

- [x] Tạo bộ tài liệu nền tảng.
- [ ] Khởi tạo Git repository.
- [ ] Tạo project structure.
- [ ] Tạo `.gitignore`, `.env.example`, `pyproject.toml` hoặc requirements.

## Phase 1 — Core backend

- [ ] FastAPI application factory hoặc entrypoint.
- [ ] Configuration management.
- [ ] Structured logging.
- [ ] PostgreSQL connection.
- [ ] SQLAlchemy base.
- [ ] Alembic.
- [ ] Health endpoints.

## Phase 2 — Authentication and RBAC

- [ ] User, department models.
- [ ] Password hashing.
- [ ] JWT access token.
- [ ] Refresh token rotation/revocation.
- [ ] Login/logout/me.
- [ ] Role dependencies.
- [ ] Permission tests.

## Phase 3 — User administration

- [ ] Admin user CRUD.
- [ ] Department CRUD.
- [ ] Pagination and filters.
- [ ] Audit events.

## Phase 4 — Document management

- [ ] Document model.
- [ ] Upload validation.
- [ ] Local storage service.
- [ ] Document CRUD.
- [ ] Access scopes.
- [ ] Permission-aware queries.
- [ ] Status endpoint.

## Phase 5 — Async document processing

- [ ] Redis.
- [ ] Celery worker.
- [ ] PyMuPDF extractor.
- [ ] Normalization.
- [ ] Chunking.
- [ ] Embedding provider.
- [ ] pgvector storage.
- [ ] Reprocess.

## Phase 6 — Retrieval and chat

- [ ] Semantic retrieval.
- [ ] Keyword retrieval.
- [ ] Permission filter.
- [ ] Threshold.
- [ ] LLM provider.
- [ ] Prompt builder.
- [ ] Chat sessions/messages.
- [ ] Citation validation.

## Phase 7 — Feedback and audit

- [ ] Feedback API.
- [ ] Audit log API.
- [ ] Usage metrics.

## Phase 8 — Frontend

- [ ] Login.
- [ ] Dashboard shell.
- [ ] User management.
- [ ] Document management.
- [ ] Chat interface.
- [ ] Citation viewer.
- [ ] Feedback.

## Phase 9 — Quality and deployment

- [ ] Full test suite.
- [ ] Docker Compose full stack.
- [ ] CI pipeline.
- [ ] Nginx.
- [ ] Production configuration.
- [ ] Demo data and documentation.

## Future phases

- OCR.
- DOCX/XLSX/TXT.
- Versioning.
- Workflow approval.
- Notifications.
- Contract comparison.
- Cloud storage integration.
- Multi-tenant architecture.
