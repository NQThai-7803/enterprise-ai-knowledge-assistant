# Changelog

All notable changes to this project will be documented in this file.

Format follows a simplified Keep a Changelog style.

## [Unreleased]

### Added

- Initialized Phase 2 roadmap.
- Started TASK-026 Multi-LLM Provider Support.
- Completed TASK-026 recovery with missing-usage normalization, explicit provider connectivity health, remote OpenAI-compatible API key validation, and Docker runtime verification.
- Completed TASK-027 Streaming Chat with Server-Sent Events.
- Added a protected SSE chat endpoint, centralized SSE serializer/state machine, bounded heartbeat/stream timeout settings, and Docker streaming integration tests.
- Verified streaming preserves grounded-answer policy, citation validation, atomic final-message persistence, safe provider errors, cancellation cleanup, and the non-streaming Chat API.
- Added TASK-028 Frontend UI Foundation & Test Console to the roadmap.

- Production configuration validation for environment mode, debug policy, placeholder secrets, database password, CORS, trusted hosts, request limits, database pool, Redis timeouts, rate limits, and Celery time limits.
- Configurable API docs policy.
- CORS middleware with explicit origin, method, header, and credentials configuration.
- Trusted-host enforcement.
- API security headers and HTTPS-only production HSTS behavior.
- Global request-size middleware with `413 REQUEST_TOO_LARGE` responses.
- Upload hardening error codes for file size, empty file, file type, PDF signature, and filename validation.
- Redis-backed fixed-window rate limiting for login, refresh, upload, chat messages, and feedback.
- Database pool and Redis timeout configuration.
- Celery soft/hard time-limit configuration.
- Safe generic unhandled-exception responses.
- Logging redaction for secrets and business-content fields.
- Docker Compose `no-new-privileges:true` runtime hardening for application services.
- Backup/restore documentation and release readiness checklist.
- TASK-025 hardening regression tests.
- GitHub Actions backend CI workflow.
- Python 3.12 CI setup with pip caching and `pyproject.toml` dependency installation.
- PostgreSQL pgvector and Redis CI service-container verification.
- Alembic CI migration, single-head, and current-head verification.
- Ruff lint and format checks in CI.
- Unit, API, integration, and marker pytest execution with combined coverage XML.
- CI security scan for `create_all`, pickle serialization, raw SQL interpolation, hardcoded secrets, production debug, and unsafe logging.
- Docker runtime build and Docker Compose config verification in CI.
- CI artifact upload for `coverage.xml`, pytest reports, and logs.
- Generated CI verification artifact ignores for local runs.
- Expanded append-only AuditLog coverage.
- Sanitized Audit event metadata.
- Audit events for selected authentication, administration, Document, Chat, and Feedback operations.
- Atomic success AuditLog persistence.
- Best-effort failure AuditLog persistence.
- Admin-only AuditLog report.
- Audit filters and stable pagination.
- Audit privacy and transaction tests.
- FeedbackRating enum.
- Feedback model and migration.
- Atomic per-message feedback upsert.
- Owner-only Assistant-message feedback.
- Manager Department-scoped Feedback report.
- Admin global Feedback report.
- Feedback pagination and filters.
- Feedback concurrency and privacy tests.
- Backend-managed LLM source markers.
- Strict citation-marker validation.
- Citation source mapping.
- Public citation-number normalization.
- Permission revalidation after LLM generation.
- MessageCitation model and migration.
- Server-generated citation excerpts.
- Atomic message and citation persistence.
- Citation-enriched Chat responses and history.
- Citation security and race-condition tests.
- LLMProvider abstraction.
- Configurable OpenAI-compatible LLM provider.
- Grounded Chat prompt builder.
- Permission-aware Hybrid Retrieval integration.
- Context-token budgeting.
- Recent Chat history prompting.
- Fixed no-answer behavior.
- No-answer sentinel handling.
- Atomic USER and ASSISTANT message persistence.
- Chat answer token and response-time tracking.
- Chat message submission API.
- ChatSession and ChatMessage models.
- PostgreSQL ChatMessageRole enum.
- Owner-only chat-session access.
- Chat-session create API.
- Chat-session list API.
- Chat-session detail and history API.
- Paginated chat-session and message-history queries.
- Internal chat-message persistence service.
- SYSTEM-message hiding.
- Chat ownership security tests.
- PostgreSQL full-text keyword retrieval.
- GIN full-text index for DocumentChunk text.
- Permission-aware keyword ranking.
- Exact identifier retrieval.
- Weighted Reciprocal Rank Fusion.
- Semantic and keyword candidate deduplication.
- Stable hybrid retrieval results.
- Hybrid permission-leakage tests.
- Real Vietnamese hybrid-retrieval tests.
- Semantic RetrievalService abstraction.
- Query embedding integration for retrieval.
- Permission-aware pgvector retrieval.
- READY-only Document filtering for retrieval.
- Soft-delete and archived-document exclusion during retrieval.
- Configurable retrieval top-k.
- Configurable relevance threshold.
- Stable typed RetrievalHit results.
- Permission leakage and real semantic-retrieval tests.
- Automatic Document processing enqueue after upload.
- End-to-end Celery Document-processing pipeline.
- PDF extraction integration.
- Page-aware chunking integration.
- Local embedding integration.
- Atomic DocumentChunk persistence.
- READY and FAILED Document transitions.
- Bounded pipeline retries.
- Processing idempotency and concurrent-claim protection.
- End-to-end worker and pipeline tests.
- EmbeddingProvider abstraction.
- Local Sentence Transformers embedding provider.
- Multilingual query and passage embeddings.
- Batch embedding and normalization.
- Embedding validation.
- DocumentChunk SQLAlchemy model.
- PostgreSQL pgvector extension.
- HNSW cosine vector index.
- Atomic chunk replacement.
- Embedding and pgvector tests.
- TokenCounter abstraction.
- Tiktoken token counter.
- Page-aware token chunker.
- Paragraph-first chunk splitting.
- Sentence splitting fallback.
- Token-window fallback.
- Configurable token overlap.
- Stable page metadata for chunks.
- Deterministic chunk SHA-256 checksums.
- Chunking unit and integration tests.
- TextExtractor abstraction.
- PyMuPDF PDF text extractor.
- Page-level text extraction.
- Unicode and whitespace normalization.
- PDF extraction result models.
- Encrypted PDF detection.
- Corrupted PDF handling.
- PDF page-limit validation.
- No-usable-text detection.
- PDF extraction unit and integration tests.
- Celery application.
- Redis broker and result backend configuration.
- Document-processing queue.
- Worker connectivity task.
- Document-processing task skeleton.
- Atomic Document processing claim.
- Document processing status transitions.
- Bounded task retries.
- Worker-specific async database handling.
- Celery unit and integration tests.
- Permission-aware Document listing.
- Reusable Document access filters.
- Document detail endpoint.
- Document status endpoint.
- Secure Document download.
- Document metadata update endpoint.
- Document soft-delete endpoint.
- Direct User and Department permission APIs.
- Department document-reference protection.
- Document access-control tests.
- FileStorage abstraction.
- Secure LocalFileStorage implementation.
- PDF multipart upload endpoint.
- Streaming upload size enforcement.
- PDF extension, MIME and signature validation.
- SHA-256 file checksum.
- UUID-based storage keys.
- Duplicate-document detection.
- Filesystem/database failure compensation.
- Document upload tests.

- Document status enum.
- Document access-scope enum.
- Document permission-level enum.
- Document SQLAlchemy model.
- Document permission SQLAlchemy model.
- Document access-scope database constraint.
- Exactly-one permission grantee constraint.
- Document and permission indexes.
- Document Alembic migration.
- Document model unit and integration tests.

- User administration APIs.
- Department administration APIs.
- Pagination, filtering and sorting.
- User soft deactivation.
- Refresh-token revocation on deactivation.
- Last active Admin protection.
- Basic audit-log model and migration.
- User and Department audit events.
- User and Department API tests.

- Generic role-based dependency factory.
- Admin-only authorization guard.
- Manager-or-Admin authorization guard.
- Department-scoped access policies.
- User management policies.
- Role assignment policies.
- RBAC unit and API dependency tests.
- JWT access token generation and validation.
- Opaque refresh token generation.
- Hashed refresh token persistence.
- Refresh token rotation.
- Login endpoint.
- Refresh endpoint.
- Logout endpoint.
- Current user endpoint.
- Authentication tests.
- Department SQLAlchemy model.
- User SQLAlchemy model.
- UserRole enum.
- User-Department relationship.
- Password hashing and verification helpers.
- User and Department Alembic migration.
- Development Admin seed command.
- User and Department model tests.
- Initial project documentation package.
- Product requirements.
- Architecture specification.
- Database design.
- API specification.
- Security and RBAC rules.
- RAG and document processing design.
- Roadmap and task breakdown.
- Async SQLAlchemy engine.
- Async database session factory.
- Declarative SQLAlchemy base.
- Async Alembic configuration.
- Database foundation baseline migration.
- Database readiness endpoint.
- Database readiness tests.

### Verified

- Verified TASK-028 live UI acceptance recovery against the real local Docker frontend/backend stack with PostgreSQL, Redis, deterministic UAT LLM provider, idempotent UAT seed, live role workflows, upload-to-READY, permissions, SSE chat, citations, feedback, audit, responsive/accessibility smoke, frontend gates, mock E2E, live E2E, and backend regressions.
- Completed Docker/Python 3.12 runtime verification for TASK-026.
- Verified Multi-LLM providers, grounding, privacy, and LLM-disabled startup in Docker.
- Completed Docker runtime verification.
- Completed DB-backed hardening regression.
- Completed end-to-end release smoke test.
- Completed persistence and failure-recovery verification.
### Changed

- None.

### Fixed

- Fixed TASK-028 live acceptance blockers for `.example.test` UAT email validation, Admin user edit/reactivation controls, Department edit/delete controls, toast click interception, mobile drawer Escape handling, and feedback controls on completed live SSE answers.
- Released the Document download read transaction before streaming file bytes and kept download response metadata detached from ORM state.



### Added

- Implemented TASK-028 frontend console foundation with React, TypeScript, Vite, role-aware shell, authentication, typed API client, POST SSE chat client, documents, users, departments, feedback, audit logs, system status, and profile routes.
- Added UI documentation for Stitch workflow, Stitch screen prompts, design system, screen inventory, React Bits motion policy, frontend architecture, and frontend testing.
- Added controlled motion primitives for login background, chat spotlight, and waiting text with reduced-motion support.
- Added frontend lint, typecheck, Vitest, Playwright smoke E2E, production build, and optional Docker Compose frontend profile.
