# API Error Codes

| Code | HTTP | Meaning |
|---|---:|---|
| VALIDATION_ERROR | 422 | Request is invalid |
| INVALID_CREDENTIALS | 401 | Email or password is incorrect |
| ACCESS_TOKEN_INVALID | 401 | Access token is missing, malformed, has an invalid signature, or has invalid claims |
| TOKEN_EXPIRED | 401 | Access token has expired |
| REFRESH_TOKEN_INVALID | 401 | Refresh token is unknown, expired, revoked, or belongs to another user |
| USER_INACTIVE | 403 | User account is inactive |
| FORBIDDEN | 403 | User is authenticated but lacks permission |
| RESOURCE_NOT_FOUND | 404 | Resource does not exist or should not be revealed |
| USER_EMAIL_ALREADY_EXISTS | 409 | Email is already in use |
| DEPARTMENT_NAME_ALREADY_EXISTS | 409 | Department name already exists |
| DEPARTMENT_CODE_ALREADY_EXISTS | 409 | Department code already exists |
| DEPARTMENT_IN_USE | 409 | Department still has active users |
| LAST_ACTIVE_ADMIN | 409 | Cannot remove the last active Admin |
| SELF_MODIFICATION_NOT_ALLOWED | 409 | Admin cannot change their own role or active status through this API |
| DOCUMENT_NOT_READY | 409 | Document is not ready |
| DOCUMENT_PROCESSING | 409 | Document is processing |
| DOCUMENT_ALREADY_PROCESSING | 409 | Duplicate reprocess request |
| DOCUMENT_FILE_TYPE_INVALID | 415 | File extension or MIME type is not supported |
| DOCUMENT_FILE_TOO_LARGE | 413 | Uploaded file exceeds size limit |
| DOCUMENT_FILE_EMPTY | 400 | Uploaded file is empty |
| DOCUMENT_FILE_SIGNATURE_INVALID | 415 | PDF magic bytes are missing or invalid |
| DOCUMENT_FILENAME_INVALID | 400 | Filename is missing, empty, or too long |
| REQUEST_TOO_LARGE | 413 | Request body exceeds configured limit |
| DUPLICATE_DOCUMENT | 409 | Duplicate file by policy |
| DOCUMENT_FILE_UNAVAILABLE | 410 | Document metadata exists but the stored file is unavailable |
| DOCUMENT_PERMISSION_ALREADY_EXISTS | 409 | Direct Document permission grant already exists |
| DEPARTMENT_HAS_DOCUMENTS | 409 | Department is referenced by one or more Documents |
| FEEDBACK_TARGET_NOT_FOUND | 404 | Feedback target is missing, non-owned, or not an ASSISTANT message |
| FEEDBACK_RATING_INVALID | 422 | Feedback rating is invalid |
| FEEDBACK_REASON_TOO_LONG | 422 | Feedback reason exceeds the configured limit |
| FEEDBACK_DATE_RANGE_INVALID | 422 | Feedback report date range is invalid |
| FEEDBACK_REPORT_FORBIDDEN | 403 | Current User cannot access the feedback report |
| FEEDBACK_REPORT_SCOPE_UNAVAILABLE | 403 | Manager has no current Department for report scope |
| FEEDBACK_OPERATION_FAILED | 500 | Feedback operation failed safely |
| AUDIT_REPORT_FORBIDDEN | 403 | Current User cannot access the AuditLog report |
| AUDIT_DATE_RANGE_INVALID | 422 | AuditLog report date range is invalid |
| AUDIT_FILTER_INVALID | 422 | AuditLog report filter is invalid |
| AUDIT_EVENT_INVALID | internal/service validation | Audit event type or target is invalid |
| AUDIT_METADATA_INVALID | internal/service validation | Audit metadata failed sanitizer validation |
| AUDIT_OPERATION_FAILED | 500 | AuditLog operation failed safely |
| RETRIEVAL_NO_RESULTS | 200/business | No sufficiently relevant retrieval context |
| PROVIDER_UNAVAILABLE | 503 | Embedding or LLM provider is unavailable |
| LLM_NOT_CONFIGURED | 503 | LLM is disabled or selected provider configuration is missing |
| LLM_PROVIDER_UNSUPPORTED | 503 | Selected LLM provider name is not supported |
| LLM_PROVIDER_AUTHENTICATION_FAILED | 503 | Selected LLM provider rejected authentication |
| LLM_PROVIDER_RATE_LIMITED | 503 | Selected LLM provider rate-limited the request |
| LLM_PROVIDER_TIMEOUT | 504 | Selected LLM provider timed out |
| LLM_PROVIDER_UNAVAILABLE | 503 | Selected LLM provider or network is unavailable |
| LLM_PROVIDER_BAD_RESPONSE | 502 | Selected LLM provider returned malformed or empty data |
| LLM_REQUEST_REJECTED | 502 | Selected LLM provider rejected the request safely |
| STREAM_TIMEOUT | SSE event | Streaming chat exceeded the configured maximum duration |
| STREAM_INTERNAL_ERROR | SSE event | Streaming chat failed after headers were sent; details are sanitized |
| STREAM_CANCELLED | SSE event | Streaming chat was cancelled before completion |
| DATABASE_UNAVAILABLE | 503 | Database is unavailable |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests; response includes `Retry-After` |
| INTERNAL_ERROR | 500 | Unexpected error |

## Rules

- Do not reveal whether a user email exists during login failure.
- Bearer access-token `401` responses include `WWW-Authenticate: Bearer`.
- Client logic should use `code`, not `message`.
- Responses must not include raw tokens, token hashes, SQL statements, stack traces, or secrets.


## TASK-009 upload error mapping

- `DOCUMENT_FILE_TYPE_INVALID` is returned with HTTP `415` for non-`.pdf` filenames or non-`application/pdf` MIME types. `DOCUMENT_FILE_SIGNATURE_INVALID` is returned with HTTP `415` when `%PDF-` binary signature validation fails.
- `DOCUMENT_FILE_TOO_LARGE` is returned with HTTP `413` when streamed upload bytes exceed `MAX_UPLOAD_SIZE_MB`. `REQUEST_TOO_LARGE` is returned with HTTP `413` when the whole request body exceeds `MAX_REQUEST_BODY_BYTES`.
- `DOCUMENT_FILE_EMPTY` is returned with HTTP `400` for zero-byte uploads. `DOCUMENT_FILENAME_INVALID` is returned with HTTP `400` for missing, empty, or overlong filenames.
- `DUPLICATE_DOCUMENT` is returned with HTTP `409` only for same-uploader, non-deleted checksum duplicates. The response must not reveal the existing document id or metadata.
- Unexpected local storage failures are reported as `INTERNAL_ERROR` without exposing filesystem paths.
## TASK-010 document access error mapping

- `RESOURCE_NOT_FOUND` is returned with HTTP `404` for missing Documents and for Documents the caller is not allowed to know exist.
- `FORBIDDEN` is returned with HTTP `403` when an authenticated caller can view a Document but cannot edit, manage, delete, or manage direct permissions.
- `DOCUMENT_FILE_UNAVAILABLE` is returned with HTTP `410` when Document metadata is accessible but the local file is missing from storage.
- `DOCUMENT_PERMISSION_ALREADY_EXISTS` is returned with HTTP `409` for duplicate direct User or Department grants.
- `DEPARTMENT_HAS_DOCUMENTS` is returned with HTTP `409` when hard-deleting a Department that is still referenced by `documents.department_id`.
- Error responses must not include storage keys, local paths, SQL statements, token data, checksum values, or stack traces.

## TASK-015 processing errors

The document status endpoint continues to expose the sanitized `error_message` stored on the Document. Internal pipeline codes include extraction, chunking, embedding, storage, and retry outcomes, but raw exceptions and tracebacks are not exposed through API responses.

No new HTTP endpoint is added for pipeline error inspection in TASK-015.

## TASK-018/TASK-026 chat and LLM errors

- `CHAT_SESSION_NOT_FOUND` (`404`): missing ChatSession or session not owned by the current User. Admin receives the same response for a non-owned session.
- `CHAT_SESSION_TITLE_TOO_LONG` (`422`): title exceeds the configured service limit.
- `CHAT_MESSAGE_CONTENT_INVALID` (`422`): message content is blank or invalid.
- `CHAT_MESSAGE_CONTENT_TOO_LONG` (`422`): message content exceeds `CHAT_MESSAGE_MAX_CHARACTERS`.
- `CHAT_MESSAGE_METRICS_INVALID` (`422`): internal timing or token metrics are invalid.
- `CHAT_RETRIEVAL_FAILED` (`503`): permission-aware retrieval failed before answer generation.
- `LLM_NOT_CONFIGURED` (`503`): LLM is disabled or the selected provider is missing required configuration.
- `LLM_PROVIDER_UNSUPPORTED` (`503`): configured provider name is not supported.
- `LLM_PROVIDER_AUTHENTICATION_FAILED` (`503`): selected provider rejected authentication.
- `LLM_PROVIDER_RATE_LIMITED` (`503`): selected provider rate-limited the request under the current API convention.
- `LLM_PROVIDER_TIMEOUT` (`504`): bounded provider timeout.
- `LLM_PROVIDER_UNAVAILABLE` (`503`): provider network, 5xx, or availability failure.
- `LLM_PROVIDER_BAD_RESPONSE` (`502`): successful provider response is malformed, empty, or missing required fields.
- `LLM_REQUEST_REJECTED` (`502`): provider rejected the request safely without exposing provider content.

Legacy TASK-019 internal aliases remain covered for backward-compatible tests and fakes: `LLM_TIMEOUT`, `LLM_AUTHENTICATION_FAILED`, `LLM_RATE_LIMITED`, `LLM_RESPONSE_INVALID`, and `LLM_GENERATION_FAILED`.

Provider bodies, prompts, questions, answers, context, API keys, authorization headers, endpoint credentials, SQL details, and stack traces are not returned.

TASK-027 SSE errors use the same safe chat/LLM/citation codes inside `stream.error` after SSE headers have been sent. `STREAM_TIMEOUT`, `STREAM_INTERNAL_ERROR`, and `STREAM_CANCELLED` are stream-event codes, not JSON error-envelope HTTP responses.
## TASK-020 citation errors

- `CITATION_VALIDATION_FAILED` (`502`): provider answer contains missing, malformed, unknown, unselected, or over-limit source markers.
- `CITATION_MAPPING_FAILED` (`502`): validated markers could not be safely mapped to backend sources, page metadata, excerpt, or relevance constraints.
- `CITATION_PERSISTENCE_FAILED` (`500`): citation persistence failed after answer validation.

Internal detailed codes include `CITATION_MARKER_MISSING`, `CITATION_MARKER_UNKNOWN`, `CITATION_MARKER_INVALID`, `CITATION_MAPPING_FAILED`, `CITATION_PERMISSION_REVALIDATION_FAILED`, and `CITATION_PERSISTENCE_FAILED`. Public errors do not include generated answers, source registry contents, excerpts, provider bodies, or markers from invalid output.

Permission revalidation failure after LLM generation is downgraded to a successful NO_ANSWER response with empty citations rather than a public error.

## TASK-021 feedback errors

- `FEEDBACK_TARGET_NOT_FOUND` (`404`): message is missing, non-owned, or not an ASSISTANT message. The response does not reveal which condition applied.
- `FEEDBACK_RATING_INVALID` (`422`): rating is not `HELPFUL` or `NOT_HELPFUL`.
- `FEEDBACK_REASON_TOO_LONG` (`422`): reason exceeds `FEEDBACK_REASON_MAX_CHARACTERS`.
- `FEEDBACK_DATE_RANGE_INVALID` (`422`): report date filters are not timezone-aware or `date_from > date_to`.
- `FEEDBACK_REPORT_FORBIDDEN` (`403`): Staff or otherwise unauthorized User tried to access the report endpoint.
- `FEEDBACK_REPORT_SCOPE_UNAVAILABLE` (`403`): Manager has no current Department scope.
- `FEEDBACK_OPERATION_FAILED` (`500`): sanitized database/upsert failure.

Feedback errors must not expose raw database errors, constraint names, session owner, message role, message content, User email, or Department names outside scope.

## TASK-022 audit errors

- `AUDIT_REPORT_FORBIDDEN` (`403`): non-Admin caller tried to access `GET /api/v1/audit-logs`.
- `AUDIT_DATE_RANGE_INVALID` (`422`): audit date filters are not timezone-aware or `date_from > date_to`.
- `AUDIT_FILTER_INVALID` (`422`): audit filter or pagination input is invalid.
- `AUDIT_EVENT_INVALID` (internal/service validation): audit event type, target type, target id, or request id is invalid.
- `AUDIT_METADATA_INVALID` (internal/service validation): metadata is not allowlisted scalar metadata.
- `AUDIT_OPERATION_FAILED` (`500`): sanitized audit operation failure.

Audit errors must not expose raw SQL errors, constraint names, metadata payloads, exception text, stack traces, request bodies, response bodies, passwords, tokens, Chat content, Feedback reason, citation excerpts, Document filenames, or storage keys.

