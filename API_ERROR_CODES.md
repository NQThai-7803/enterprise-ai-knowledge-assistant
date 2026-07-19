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
| INVALID_FILE_TYPE | 415 | File type is not supported |
| FILE_TOO_LARGE | 413 | File exceeds size limit |
| EMPTY_FILE | 400 | File is empty |
| DUPLICATE_DOCUMENT | 409 | Duplicate file by policy |
| DOCUMENT_FILE_UNAVAILABLE | 410 | Document metadata exists but the stored file is unavailable |
| DOCUMENT_PERMISSION_ALREADY_EXISTS | 409 | Direct Document permission grant already exists |
| DEPARTMENT_HAS_DOCUMENTS | 409 | Department is referenced by one or more Documents |
| RETRIEVAL_NO_RESULTS | 200/business | No sufficiently relevant retrieval context |
| PROVIDER_UNAVAILABLE | 503 | Embedding or LLM provider is unavailable |
| DATABASE_UNAVAILABLE | 503 | Database is unavailable |
| RATE_LIMITED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Unexpected error |

## Rules

- Do not reveal whether a user email exists during login failure.
- Bearer access-token `401` responses include `WWW-Authenticate: Bearer`.
- Client logic should use `code`, not `message`.
- Responses must not include raw tokens, token hashes, SQL statements, stack traces, or secrets.


## TASK-009 upload error mapping

- `INVALID_FILE_TYPE` is returned with HTTP `415` for non-`.pdf` filenames, non-`application/pdf` MIME types, or missing `%PDF-` binary signature.
- `FILE_TOO_LARGE` is returned with HTTP `413` when streamed bytes exceed `MAX_UPLOAD_SIZE_MB`.
- `EMPTY_FILE` is returned with HTTP `400` for zero-byte uploads.
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
