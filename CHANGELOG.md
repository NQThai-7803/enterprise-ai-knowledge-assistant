# Changelog

All notable changes to this project will be documented in this file.

Format follows a simplified Keep a Changelog style.

## [Unreleased]

### Added

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

### Changed

- None.

### Fixed

- Released the Document download read transaction before streaming file bytes and kept download response metadata detached from ORM state.

