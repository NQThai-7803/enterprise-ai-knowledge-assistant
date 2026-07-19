# Security Requirements

## 1. Authentication implementation

- Passwords are not stored in plaintext.
- Password verification uses the Argon2 helper from `pwdlib`.
- Access tokens are short-lived JWTs signed with `HS256`.
- Access tokens include `sub`, `type`, `jti`, `iat`, `nbf`, `exp`, `iss`, and `aud` claims.
- Access tokens do not include role, permission, or department claims as the authorization source.
- Access token decoding uses an explicit algorithm allowlist: `HS256` only.
- Access token issuer and audience are validated.
- Access tokens are not stored in the database.
- Refresh tokens are opaque random tokens generated with `secrets.token_urlsafe(48)`.
- Raw refresh tokens are returned only at login or refresh.
- PostgreSQL stores only the SHA-256 hex hash of a refresh token.
- Refresh token lookup uses the deterministic SHA-256 hash.
- Refresh token rotation revokes the old token and creates a new token in one transaction.
- Logout revokes the supplied refresh token.
- The current user is loaded from the database for authenticated requests.
- The database user row is the source of truth for role and active status.
- Passwords, access tokens, refresh tokens, token hashes, and `SECRET_KEY` must not be logged.

## 2. Authorization

TASK-006 implements RBAC dependencies and pure permission policies.

- Authorization uses the current User role from PostgreSQL.
- JWT claims are not the final source for role authorization.
- Client-provided roles from request body, query parameters, or headers are not trusted.
- Missing, malformed, expired, or invalid Bearer access tokens return `401`.
- Bearer access-token `401` responses include `WWW-Authenticate: Bearer`.
- Authenticated users with insufficient role permissions return `403 FORBIDDEN`.
- Inactive users return `403 USER_INACTIVE` and are rechecked on each authenticated request.
- Admin has system-wide access under the implemented policies.
- Manager is limited to the Manager's own Department for department-scoped policies.
- Staff is limited to the Staff user's own Department for department-scoped policies.
- Manager and Staff users without a Department have no department-scoped access.
- Numeric role hierarchy and string role ordering are not used.

Future authorization checks should happen in three layers:

1. Endpoint role check.
2. Service policy check.
3. Database query filter for documents and chunks.

Do not rely on frontend hiding controls as authorization.

## 3. Document access

Not implemented yet. Future document APIs, downloads, search, RAG retrieval, and citation validation must use a shared permission policy.

## 4. File upload security

Future upload implementation must:

- Limit file size.
- Validate extension and MIME type.
- Rename files for storage.
- Avoid using user filenames as paths.
- Compute SHA-256 checksums.
- Reject empty files.
- Prepare antivirus scanning for production.
- Avoid executing macros or embedded scripts.

## 5. Prompt injection defense

Future RAG implementation must treat document content as data, not system instructions, and must not allow document text to override policy.

## 6. Data protection

- Secrets belong in `.env`, not source control.
- Production must use a non-placeholder `SECRET_KEY`.
- Production should use TLS.
- Logs must not include passwords, tokens, API keys, or sensitive content.

## 7. API security

- Validate requests with Pydantic.
- Error responses must not expose stack traces, SQL statements, tokens, hashes, or secrets.
- Rate limiting is not implemented yet.

## 8. Audit events for future tasks

- LOGIN_SUCCESS
- LOGIN_FAILED
- LOGOUT
- USER_CREATED
- USER_UPDATED
- USER_DEACTIVATED
- DOCUMENT_UPLOADED
- DOCUMENT_VIEWED
- DOCUMENT_DOWNLOADED
- DOCUMENT_UPDATED
- DOCUMENT_DELETED
- DOCUMENT_REPROCESSED
- PERMISSION_CHANGED
- CHAT_QUESTION_SUBMITTED
- FEEDBACK_SUBMITTED

## 9. Known limitations after TASK-006

- Access tokens cannot be revoked immediately; they expire by `exp`.
- Logout revokes only the supplied refresh token.
- No fine-grained permission table.
- No custom roles.
- No authorization audit log.
- No resource ownership policy beyond Department.
- No permission cache.
- No User or Department API applies the guards yet.
- No rate limiting yet.
- No multi-factor authentication.
- No password reset.
- No document permissions yet.
## 10. TASK-007 administration API security

- Passwords are accepted only when an Admin creates a User.
- User PATCH does not accept `password` or `hashed_password`.
- Passwords and password hashes are not returned by User APIs.
- Passwords, password hashes, access tokens, refresh tokens, token hashes, authorization headers, secret keys, and database URLs are not stored in audit metadata.
- User deactivation revokes active refresh tokens for that User.
- Existing access tokens for deactivated Users are rejected because `get_current_user` reloads the User from PostgreSQL and checks `is_active`.
- The last active Admin cannot be deactivated or demoted.
- An Admin cannot deactivate themselves or change their own role through the User administration API.
- User and Department list sorting uses explicit allowlists; client sort strings are not passed to SQL text.
- Audit log insertion uses the same transaction as the User or Department mutation.
- Client IP is taken from the direct request client only when it is a valid IP address. `X-Forwarded-For` and other proxy headers are not trusted in TASK-007.

## 11. Known limitations after TASK-007

- No password invitation flow.
- No password reset.
- No audit log query API.
- No audit retention policy.
- No trusted-proxy configuration.
- No rate limiting.
- Audit logs currently cover User and Department administration events only.


## 12. TASK-008 document data security

Document database security rules now implemented:

- `storage_key` is an internal storage identifier, not a public URL.
- `original_filename` is stored only for display and must not be used as a storage path.
- Access-scope consistency is protected by database constraint: `DEPARTMENT` requires `department_id`, while `PRIVATE` and `ORGANIZATION` require no `department_id`.
- Permission grants must have exactly one grantee: either one User or one Department.
- Direct document permissions are explicit allow grants only; explicit deny is not supported.
- Document soft delete via `is_deleted` is separate from `ARCHIVED` status.
- Department-scoped Documents cannot be orphaned by Department hard delete because `documents.department_id` uses `ON DELETE RESTRICT`.
- `error_message` is intended only for sanitized processing errors and must not contain stack traces, absolute file-system paths, API keys, database URLs, or full document content.

Known limitations after TASK-008:

- No real file validation.
- No upload size enforcement.
- No antivirus interface.
- No signed download URL.
- No Document API access checks.
- No permission-aware retrieval.
- No document audit events.
- No storage abstraction or local file persistence.
- No PDF processing, chunks, embeddings, or pgvector extension.
## 13. TASK-009 local upload security

Implemented upload security controls:

- Only Admin and Manager can call `POST /api/v1/documents/upload`; Staff receives `403 FORBIDDEN`.
- Manager upload scope is restricted to `PRIVATE` or the Manager's own `DEPARTMENT`.
- Manager cannot upload `ORGANIZATION` documents or documents for another Department.
- Upload accepts only PDF files in MVP.
- Validation checks filename extension `.pdf`, MIME type `application/pdf`, and binary signature `%PDF-`.
- Upload bytes are streamed in chunks; the endpoint does not read the whole file into memory.
- Actual streamed byte count enforces `MAX_UPLOAD_SIZE_MB`; `Content-Length` is not trusted as the only control.
- Empty files are rejected.
- SHA-256 checksum is computed while streaming the same bytes that are saved.
- Original filename is reduced to a basename and is never used as a filesystem path.
- Storage keys are generated from UTC date and UUID, not from client-controlled filename, title, email, or Department name.
- Local storage validates every storage key as a relative path, rejects traversal and absolute paths, and verifies resolved paths stay under storage root.
- Local saves use a temporary file followed by atomic replace into the final path.
- Temporary and partial files are removed on validation, stream, or storage failures.
- Files saved before duplicate detection or database failure are deleted as compensation.
- Upload response does not expose `storage_key`, checksum, local absolute path, or sanitized processing errors.
- Local files are not public URLs and no signed URL is created in TASK-009.

Known limitations after TASK-009:

- No antivirus scanner.
- No malware sandbox.
- No detection for password-protected PDFs.
- No validation that the PDF contains extractable text.
- No S3 or MinIO backend.
- No signed download URL.
- No scheduled orphan-file cleanup job.
- Concurrent duplicate uploads by the same user may still race before a later idempotency or locking improvement.
- No document audit events yet.
- Local storage is not suitable for multi-instance production without shared storage.
## 14. TASK-010 document access and download security

Implemented document access controls:

- Document list, detail, status, and download use a shared PostgreSQL permission filter; unauthorized data is not loaded in bulk and filtered by the frontend.
- Inaccessible Document detail, status, and download requests return `404 RESOURCE_NOT_FOUND` to reduce resource enumeration.
- Download uses the same view policy as list and detail.
- Download streams file chunks from `FileStorage`; it does not use storage `open()` to load the whole PDF into memory.
- Download copies safe response metadata and ends the read transaction before streaming file bytes.
- Download responses set `X-Content-Type-Options: nosniff` and `Cache-Control: private, no-store`.
- `Content-Disposition` uses a sanitized display filename only. The filename is never used as a storage path.
- `storage_key`, local paths, checksums, SQL statements, and storage exception messages are not returned to clients.
- Soft-deleted Documents are excluded from list/detail/status/download, and direct grants do not bypass `is_deleted = true`.
- Direct grants are read from PostgreSQL and take effect immediately without changing access tokens.
- Staff can view accessible Documents but cannot edit, delete, or manage permissions in MVP.
- Sort fields use an allowlist; client strings are not passed to raw SQL text.
- Department hard delete checks scoped Document references and returns `DEPARTMENT_HAS_DOCUMENTS` instead of exposing a foreign-key error.

Known limitations after TASK-010:

- No document audit events yet.
- No preview endpoint.
- No signed download URL.
- No HTTP Range request support.
- No storage encryption layer.
- No Celery processing worker.
- No permission-aware RAG retrieval yet.
- Local storage is not suitable for multi-instance production without shared storage.
## 15. TASK-011 Celery worker security

Implemented worker security controls:

- Celery accepts JSON content only; pickle serialization is not accepted.
- Celery task serializer and result serializer are JSON.
- Document processing task arguments contain only a Document UUID string.
- Access tokens, refresh tokens, password hashes, storage keys, absolute paths, file bytes, extracted text, API keys, database URLs, and Redis credentials are not sent in Celery task messages.
- Worker database access uses a worker-specific async SQLAlchemy engine and session with `NullPool`.
- Worker does not reuse FastAPI request sessions or the FastAPI global connection pool.
- Atomic SQL claim prevents two workers from processing the same eligible Document at the same time.
- Retries are bounded by configuration and are not infinite.
- Placeholder and failure messages stored in `documents.error_message` are sanitized and do not include tracebacks.
- PostgreSQL remains the source of truth for Document status.
- Redis result backend has expiration and stores only temporary task metadata.

Known limitations after TASK-011:

- Celery is run on Windows only with `--pool=solo` for local development.
- Native Windows Celery execution is not treated as a production performance target.
- A worker crash after claiming a Document may leave it stuck in `PROCESSING` until recovery logic is added.
- No watchdog, processing timeout recovery, task cancellation, dead-letter queue, or worker container is implemented yet.
- PDF extraction, chunks, embeddings, and READY transition are not implemented yet.
- Upload does not automatically enqueue processing yet.
## 16. TASK-012 PDF extraction security

Implemented PDF extraction security controls:

- PDF parsing is implemented for worker-side processing use and is not run inside the upload request path.
- Extractor code does not log document text or PDF bytes.
- `ExtractedPage` hides page text from `repr()`.
- `ExtractionResult` does not expose page text through representation.
- Password-protected PDFs are rejected with `ENCRYPTED_PDF`.
- Invalid or corrupted PDFs return a stable safe error message.
- Page count is limited by `PDF_MAX_PAGES` before page extraction starts.
- Blank and image-only PDFs are rejected as `PDF_NO_USABLE_TEXT`; OCR is not attempted.
- Extracted text is not stored in Redis, not returned by Celery task results, not returned by API responses, and not persisted in PostgreSQL in TASK-012.
- No-usable-text content is not sent to an LLM.

Known limitations after TASK-012:

- PyMuPDF processes PDF content inside the worker process; there is no separate sandbox yet.
- No antivirus scanning.
- No hard per-PDF processing timeout.
- Bounded PDF bytes are currently materialized in worker memory.
- Reading order can be wrong for complex layouts.
- Repeated header/footer detection and removal are not implemented.
- Table reconstruction is not implemented.
- OCR for image-only PDFs is not implemented.
- Content redaction and PII masking are not implemented.
## 17. TASK-013 chunking security

Implemented chunking security controls:

- Chunk text is not logged.
- Page text is not logged.
- Token IDs are not logged.
- `TextChunk` hides chunk text from `repr()`.
- `ChunkingResult` does not expose chunk text through nested representations.
- Chunk text is not returned through an API in TASK-013.
- Chunk text is not returned through Celery or Redis task results in TASK-013.
- Chunks are not persisted in TASK-013.
- Chunk checksums use deterministic lowercase SHA-256 over UTF-8 chunk text bytes.
- Page metadata is kept on chunks for future citation support.
- Token limits, hard maximum chunk size, and bounded overlap protect resource usage.
- `TiktokenTokenCounter` uses local tokenization and does not call network APIs.
- TASK-013 does not add LangChain, LlamaIndex, transformers, OCR, embedding calls, or automatic content-sending frameworks.

Known limitations after TASK-013:

- Text will still be processed in worker memory when the full pipeline is connected in a future task.
- Chunk persistence encryption is not implemented because chunk persistence is not implemented.
- Sentence splitting is heuristic.
- Repeated header/footer removal is not implemented.
- Table layout is not fully preserved beyond extracted text order.
- Overlap intentionally duplicates tail content between chunks.
- PII redaction is not implemented.
- Content classification is not implemented.
- Embeddings are not implemented.

## 18. TASK-014 embedding and vector storage security

Implemented controls:

- Default embedding is local Sentence Transformers, not an external API.
- Chunk text is not sent to OpenAI or any external embedding API by application code.
- `trust_remote_code=false` is hard-coded for model loading.
- Model loading is lazy and does not run at import, FastAPI startup, Alembic startup, worker import, or health check.
- Model weights are cached under `data/models/`, which is ignored by Git.
- Vector values are hidden from embedding result `repr()`.
- Chunk text and vector values are not logged by embedding or persistence code.
- Embeddings are not returned through API responses or Celery results.
- Vector dimensions are validated before persistence and by pgvector `vector(384)`.
- NaN and infinity values are rejected.
- Chunk replacement is atomic and rolls back on persistence failure.
- Soft-deleted Documents are rejected by chunk replacement; future retrieval must also filter them out.

Known limitations after TASK-014:

- `EMBEDDING_MODEL_REVISION` is empty by default, so future model downloads may differ.
- First model download depends on Hugging Face/network availability unless cached.
- The future worker pipeline will process chunk text and vectors in worker memory.
- Chunk text is stored plaintext in PostgreSQL.
- Database encryption at rest is not configured by the app layer.
- Permission-aware semantic retrieval is not implemented.
- PII redaction is not implemented.
- Embedding model evaluation on real enterprise data is not implemented.
- HNSW parameters are not benchmarked.

## 19. TASK-015 processing pipeline security

- Upload enqueue happens only after database commit.
- Celery task arguments contain only the Document UUID string.
- File content is not sent through Redis.
- Page text, chunk text, token IDs, and embedding vectors are not sent through Redis.
- Worker tasks use fresh database sessions and do not share `AsyncSession` globally.
- The embedding model remains lazy-loaded in the worker process.
- Atomic claim prevents duplicate workers from processing the same eligible Document.
- Chunk replacement and `READY` transition are committed atomically.
- Permanent failures store sanitized `FAILED` messages without raw paths, storage keys, raw provider exceptions, or tracebacks.
- Existing chunks are preserved when extraction, chunking, embedding, or final persistence fails.
- No external embedding API is called.
- Soft-deleted Documents are not marked `READY`.
- Processing logs must not include Document content or vector values.

Known limitations after TASK-015:

- Broker enqueue is not backed by a transactional outbox.
- Broker enqueue failure can leave a committed Document in `UPLOADED` until manually enqueued.
- Worker crash can leave a Document stuck in `PROCESSING` until a future watchdog/recovery task.
- Bounded PDF bytes, chunks, and vectors are materialized in worker memory during processing.
- Chunk text is stored plaintext in PostgreSQL.
- OCR, permission-aware retrieval, PII redaction, and worker containerization are not implemented.
## 20. TASK-016 semantic retrieval security

Implemented controls:

- Permission filtering is applied inside the PostgreSQL vector query before top-k `LIMIT`.
- Unauthorized chunks are not loaded into application memory and then filtered in Python.
- Retrieval considers only `READY` Documents.
- Soft-deleted and `ARCHIVED` Documents are excluded, even when direct grants exist.
- Direct User and Department grants are read from PostgreSQL and take effect immediately.
- Removed grants remove retrieval access immediately without requiring a new login.
- Query text, chunk text, Document title, and vector values are not logged by retrieval code.
- Query embeddings are not persisted to PostgreSQL, Redis, Celery messages, or Celery results.
- Relevance threshold is applied in SQL with cosine distance before `LIMIT`.
- SQLAlchemy parameter binding is used for query vectors; user query text is not interpolated into SQL.
- Search-like injection strings such as `' OR 1=1 --` do not bypass Document permissions.

Known limitations after TASK-016:

- No keyword or hybrid search yet.
- Exact identifiers may not work well with semantic-only retrieval.
- No reranking yet.
- No retrieval cache.
- No retrieval audit event.
- No retrieval-specific rate limit.
- No PII redaction.
- Semantic score is not a probability.
- The embedding model has not been fully evaluated on real enterprise data.
- The internal retrieval service is not exposed through a public API.

## 21. TASK-017 keyword and hybrid retrieval security

- Keyword retrieval applies the shared Document access filter in PostgreSQL.
- Permission filtering is applied before keyword ranking and branch `LIMIT`.
- Hybrid retrieval only fuses candidates returned by permission-aware semantic and keyword SQL queries.
- Unauthorized chunks are not loaded into application memory and then filtered in Python.
- Keyword queries use SQLAlchemy parameter binding with PostgreSQL `websearch_to_tsquery`; query text is not interpolated into SQL strings.
- `READY` is required for both semantic and keyword branches.
- Soft-deleted, archived, uploaded, processing, and failed Documents are excluded from retrieval.
- Direct User and Department grants are read from the database, so removed grants stop granting access immediately.
- Query text, chunk text, Document title, tsquery values, semantic vectors, user email, Department name, storage keys, and file paths are not logged by retrieval code.
- Semantic relevance, keyword rank, and hybrid RRF score are ranking signals, not confidence or probability values.

Known limitations:

- Keyword search is accent-sensitive in the current MVP.
- Typo and fuzzy matching are not implemented.
- `unaccent` and trigram search are not enabled.
- Reranking and query rewriting are not implemented.
- Retrieval cache, retrieval audit events, and retrieval-specific rate limiting are not implemented.
- PII redaction in retrieved chunk text is not implemented.
- The internal hybrid retrieval service is not exposed through a public API.
