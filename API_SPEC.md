# API Specification

## 1. Base conventions

- Base path: `/api/v1`
- Content type: `application/json`
- File upload: `multipart/form-data`
- Authentication: `Authorization: Bearer <access_token>`
- Pagination: `page`, `page_size`
- Sort: `sort_by`, `sort_order`

## 2. Standard success response

Single-resource responses use the wrapper:

```json
{
  "data": {},
  "meta": null
}
```

List response:

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

## 3. Standard error response

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "You do not have permission to perform this action.",
    "details": null,
    "request_id": null
  }
}
```

## 4. Authentication

Access tokens are short-lived JWTs signed with `HS256`. Refresh tokens are opaque random tokens. Raw refresh tokens are returned only on login or refresh; PostgreSQL stores only their SHA-256 hash. Refresh rotates the refresh token and revokes the old token. Refresh does not require an access token. Logout and `/auth/me` require a Bearer access token.

### POST `/auth/login`

Request:

```json
{
  "email": "admin@example.com",
  "password": "strong-password"
}
```

Success: `HTTP 200`

```json
{
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
      "id": "uuid",
      "email": "admin@example.com",
      "full_name": "Development Admin",
      "role": "ADMIN",
      "department_id": null,
      "department_name": null,
      "is_active": true
    }
  },
  "meta": null
}
```

`user.department_name` (BR-4) is the name of the user's own Department, `null` without one; `POST /auth/refresh` returns the same `user` object.

Errors:

- `401 INVALID_CREDENTIALS` for an unknown email or wrong password.
- `403 USER_INACTIVE` for an inactive user.

### POST `/auth/refresh`

Request:

```json
{
  "refresh_token": "opaque-refresh-token"
}
```

Success: `HTTP 200`

```json
{
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
      "id": "uuid",
      "email": "admin@example.com",
      "full_name": "Development Admin",
      "role": "ADMIN",
      "department_id": null,
      "is_active": true
    }
  },
  "meta": null
}
```

Errors:

- `401 REFRESH_TOKEN_INVALID` for an unknown, expired, or revoked refresh token.
- `403 USER_INACTIVE` if the token owner is inactive.

### POST `/auth/logout`

Requires:

```text
Authorization: Bearer <access_token>
```

Request:

```json
{
  "refresh_token": "opaque-refresh-token"
}
```

Success: `HTTP 204 No Content`

Behavior:

- Revokes only the supplied refresh token.
- Logout of an already revoked refresh token owned by the current user is idempotent.
- Access tokens remain valid until expiration.

Errors:

- `401 ACCESS_TOKEN_INVALID` or `401 TOKEN_EXPIRED` for Bearer token problems.
- `401 REFRESH_TOKEN_INVALID` for unknown tokens or tokens owned by another user.
- `403 USER_INACTIVE` for inactive current users.

### GET `/auth/me`

Requires:

```text
Authorization: Bearer <access_token>
```

Success: `HTTP 200`

```json
{
  "data": {
    "id": "uuid",
    "email": "admin@example.com",
    "full_name": "Development Admin",
    "role": "MANAGER",
    "department_id": "uuid",
    "department_name": "Nhân sự",
    "is_active": true
  },
  "meta": null
}
```

`department_name` (BR-4): the name of the caller's own Department, `null` without one. It is the only name of another record this endpoint returns.

The response never includes `hashed_password` or refresh token hashes. The current user is loaded from the database on each request.

Errors:

- `401 ACCESS_TOKEN_INVALID`
- `401 TOKEN_EXPIRED`
- `403 USER_INACTIVE`

## 5. Users

Implemented in TASK-007. All User responses are wrapped and never include `password`, `hashed_password`, `refresh_tokens`, or `token_hash`.

### GET `/users`

Requires Admin.

Query parameters:

- `page` default `1`, must be `>= 1`.
- `page_size` default `20`, must be between `1` and `100`.
- `search` searches `email` and `full_name`.
- `role` filters `ADMIN`, `MANAGER`, or `STAFF`.
- `department_id` filters by Department UUID.
- `is_active` filters active status.
- `sort_by` allowlist: `email`, `full_name`, `role`, `created_at`, `updated_at`.
- `sort_order`: `asc` or `desc`, default `desc`.

Success: `HTTP 200`

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 0,
    "total_pages": 0
  }
}
```

### POST `/users`

Requires Admin. Creates an active user.

Request:

```json
{
  "email": "staff@example.com",
  "full_name": "Staff User",
  "password": "StrongPassword123!",
  "role": "STAFF",
  "department_id": "uuid"
}
```

Rules:

- Email is stripped and lowercased.
- Password must be at least 12 characters.
- Manager and Staff must have an existing Department.
- Admin may have `department_id = null`.
- Duplicate email returns `409 USER_EMAIL_ALREADY_EXISTS`.

Success: `HTTP 201`

### GET `/users/{user_id}`

Requires authentication. Admin can read any user. A user can read their own profile. Manager or Staff reading another user returns `404 RESOURCE_NOT_FOUND`.

Success: `HTTP 200`

### PATCH `/users/{user_id}`

Requires Admin. Supports `email`, `full_name`, `role`, `department_id`, and `is_active`. Password changes are not supported by this endpoint. Empty payloads are rejected with `422 VALIDATION_ERROR`.

Rules:

- Final role/department state is validated after merging current values with the patch.
- Admin cannot deactivate themselves or change their own role through this API.
- The last active Admin cannot be deactivated or demoted.
- Reactivating a user does not restore old refresh tokens.

Success: `HTTP 200`

### DELETE `/users/{user_id}`

Requires Admin. This is a soft deactivate, not a hard delete.

Behavior:

- Sets `is_active = false`.
- Revokes active refresh tokens for the user.
- Is idempotent for already inactive users.
- Does not allow self-deactivation or deactivating the last active Admin.

Success: `HTTP 204 No Content`

## 6. Departments

Implemented in TASK-007. Department CRUD is Admin-only.

### GET `/departments`

Requires Admin.

Query parameters:

- `page` default `1`, must be `>= 1`.
- `page_size` default `20`, must be between `1` and `100`.
- `search` searches `name` and `code`.
- `sort_by` allowlist: `name`, `code`, `created_at`.
- `sort_order`: `asc` or `desc`, default `asc`.

Success: `HTTP 200`

### POST `/departments`

Requires Admin.

Request:

```json
{
  "name": "Information Technology",
  "code": "it",
  "description": "Internal IT department"
}
```

Rules:

- Name is trimmed and cannot be empty.
- Code is trimmed, uppercased, and may contain only Latin letters, digits, `_`, and `-`.
- Duplicate name returns `409 DEPARTMENT_NAME_ALREADY_EXISTS`.
- Duplicate code returns `409 DEPARTMENT_CODE_ALREADY_EXISTS`.

Success: `HTTP 201`

### GET `/departments/{department_id}`

Requires Admin. Missing resources return `404 RESOURCE_NOT_FOUND`.

### PATCH `/departments/{department_id}`

Requires Admin. Supports `name`, `code`, and `description`. Empty payloads are rejected. `description: null` clears the description.

Success: `HTTP 200`

### DELETE `/departments/{department_id}`

Requires Admin. Department rows are hard deleted.

Rules:

- If any active user belongs to the Department, returns `409 DEPARTMENT_IN_USE`.
- Inactive users do not block deletion.
- The `users.department_id` foreign key uses `ON DELETE SET NULL`.

Success: `HTTP 204 No Content`

## 7. Documents

### POST `/documents/upload`

Implemented through TASK-030 recovery. Accepts one supported document file (`application/pdf`, `image/png`, or `image/jpeg`), stores it through `FileStorage`, creates a `documents` row with status `UPLOADED`, commits the database transaction, then enqueues `documents.process_document` asynchronously. The response remains HTTP 202 and does not wait for OCR, extraction, embedding, or processing to finish.

Requires Admin or Manager. Staff receives `403 FORBIDDEN`.

Content type: `multipart/form-data` with file MIME type `application/pdf`, `image/png`, or `image/jpeg`.

Fields (form):

| Field | Type | Rule |
|---|---|---|
| `file` | file | required; PDF, PNG or JPEG |
| `title` | string | required, at most 255 characters, trimmed, not blank |
| `description` | string | optional; blank becomes `null` |
| `access_scope` | `PRIVATE` / `DEPARTMENT` / `ORGANIZATION` | required |
| `department_id` | UUID | required for `DEPARTMENT`; must be absent for `PRIVATE` and `ORGANIZATION` |
| `document_code` | string | optional, at most 128 characters, trimmed; blank becomes `null` |
| `document_version` | string | optional, at most 64 characters, trimmed; blank becomes `null` |
| `effective_from` | date `YYYY-MM-DD` | optional |
| `effective_to` | date `YYYY-MM-DD` | optional; not before `effective_from` |
| `lifecycle_status` | `ACTIVE` / `SUPERSEDED` / `ARCHIVED` / `DRAFT` | optional, default `ACTIVE`. With `RAG_DRAFT_DOCUMENT_POLICY=exclude` (the default, DEC-033/036) a `DRAFT` document is listed and downloadable as usual but never used in an answer. |
| `supersedes_document_id` | UUID | optional; a Document the caller can view, not the Document itself |

Who may upload what:

- Staff: `403 FORBIDDEN`.
- Admin: any scope; `DEPARTMENT` with any existing Department.
- Manager: `PRIVATE`, or `DEPARTMENT` with the Manager's own `department_id`. `department_id` is not filled in or replaced by the server: it must be sent and must equal the Manager's own Department. `ORGANIZATION`, another Department, or a Manager without a Department: `403 FORBIDDEN`.

Errors: `422 VALIDATION_ERROR` for a field outside its rule (too long, blank title, bad date, `effective_to` before `effective_from` with message `effective_to must not precede effective_from.`, `department_id` missing for `DEPARTMENT` or present for another scope); `404 RESOURCE_NOT_FOUND` for an unknown `department_id` or a `supersedes_document_id` the caller cannot view; `409 DUPLICATE_DOCUMENT`; `413`, `415` and `400` for the file itself. Validation runs before the file is stored.

The response is `HTTP 202 Accepted` and never includes `storage_key`, `checksum_sha256`, local paths, `error_message`, or permissions.

Document response fields (upload `202`, `GET /documents` items, `GET /documents/{document_id}`):

```json
{
  "id": "uuid",
  "title": "Quy định nghỉ phép",
  "description": null,
  "document_code": "ND-HR-007",
  "document_version": "1.0",
  "effective_from": "2026-09-01",
  "effective_to": null,
  "lifecycle_status": "ACTIVE",
  "supersedes_document_id": null,
  "original_filename": "nghi-phep.pdf",
  "mime_type": "application/pdf",
  "file_size": 182340,
  "status": "UPLOADED",
  "access_scope": "DEPARTMENT",
  "department_id": "uuid",
  "uploaded_by": "uuid",
  "created_at": "2026-11-20T08:00:00Z",
  "updated_at": "2026-11-20T08:00:00Z"
}
```

Duplicate detection is scoped to the same uploader and checksum where `is_deleted = false`.

### GET `/documents`

Implemented in TASK-010. Requires any active authenticated User.

Query parameters:

- `page`, default `1`, must be `>= 1`.
- `page_size`, default `20`, must be between `1` and `100`.
- `search`, searches `title`, `original_filename`, `description` and `document_code` (case-insensitive substring, so a prefix of a code matches too), max 200 characters. It applies inside the access filter: a Document the caller cannot view is never found, by code or otherwise.
- `status`: `UPLOADED`, `PROCESSING`, `READY`, `FAILED`, or `ARCHIVED`.
- `access_scope`: `PRIVATE`, `DEPARTMENT`, or `ORGANIZATION`.
- `department_id`: Department UUID filter.
- `sort_by`: `title`, `status`, `created_at`, `updated_at`, or `file_size`.
- `sort_order`: `asc` or `desc`.

List uses PostgreSQL permission filters and counts only accessible, non-deleted Documents. It does not load all Documents and filter them in Python.

Success: `HTTP 200`

### GET `/documents/{document_id}`

Implemented in TASK-010. Requires view access. Missing or inaccessible Documents return `404 RESOURCE_NOT_FOUND` to reduce enumeration. The response does not include `storage_key`, `checksum_sha256`, file paths, or permission rows.

### GET `/documents/{document_id}/status`

Implemented in TASK-010. Uses the same view policy as detail. Returns `id`, `status`, sanitized `error_message`, and `updated_at`. Missing or inaccessible Documents return `404 RESOURCE_NOT_FOUND`.

### GET `/documents/{document_id}/download`

Implemented in TASK-010. Uses the same view policy as list/detail and streams bytes from `FileStorage`.

Response headers:

- `Content-Type`: stored document MIME type (`application/pdf`, `image/png`, or `image/jpeg`)
- `Content-Disposition: attachment`
- `X-Content-Type-Options: nosniff`
- `Cache-Control: private, no-store`

Storage keys and local paths are never returned. If metadata exists but the local file is missing, the endpoint returns `410 DOCUMENT_FILE_UNAVAILABLE`.

### GET `/documents/{document_id}/preview`

BR-2. The same bytes, view policy, errors and audit event (`DOCUMENT_DOWNLOADED`) as `/download`, for showing the file in the browser:

- `Content-Type`: stored MIME type (`application/pdf`, `image/png`, or `image/jpeg`; uploads accept nothing else)
- `Content-Disposition: inline; filename="..."`
- `X-Content-Type-Options: nosniff`
- `Cache-Control: private, no-store`

It needs the Bearer header like every other endpoint, so a plain link cannot open it: the client fetches it and shows the result through a `blob:` URL. The server ignores a `#page=N` fragment (browsers never send it); the client adds it to the `blob:` URL of a PDF. Errors: `401` without a valid token, `404 RESOURCE_NOT_FOUND` when the caller cannot view the Document (or it does not exist or is deleted), `410 DOCUMENT_FILE_UNAVAILABLE` when the stored file is missing. Signed, time-limited URLs are not implemented.

### PATCH `/documents/{document_id}`

Implemented in TASK-010. Requires edit permission for `title` and `description`; changing `access_scope` or `department_id` requires manage permission.

Accepted fields:

- `title`
- `description`
- `access_scope`
- `department_id`

Rejected fields include storage metadata, checksum, file size, MIME type, status, uploader, soft-delete state, and processing errors.

Admin may set `PRIVATE`, `DEPARTMENT`, or `ORGANIZATION`. Manager may set only `PRIVATE` or the Manager's own `DEPARTMENT`. Staff cannot edit or manage Documents in MVP. Users who can view but cannot edit receive `403 FORBIDDEN`; inaccessible Documents return `404 RESOURCE_NOT_FOUND`.

### DELETE `/documents/{document_id}`

Implemented in TASK-010 as soft delete. Requires manage permission. It sets `is_deleted = true`, returns `204 No Content`, keeps the database row, keeps the local file, and keeps direct permission rows. Deleted Documents are hidden from list, detail, status, and download, and direct grants do not bypass deletion.

### Direct permission endpoints

Implemented in TASK-010. These endpoints are Admin-only:

- `GET /documents/{document_id}/permissions`
- `POST /documents/{document_id}/permissions`
- `PATCH /documents/{document_id}/permissions/{permission_id}`
- `DELETE /documents/{document_id}/permissions/{permission_id}`

Direct grants support exactly one grantee per row: either `user_id` or `department_id`. Permission levels are `VIEW`, `EDIT`, and `MANAGE`. Duplicate User or Department grants return `409 DOCUMENT_PERMISSION_ALREADY_EXISTS`. Missing inactive Users or missing Departments return `404 RESOURCE_NOT_FOUND`.

Direct grant changes take effect immediately because document access is read from PostgreSQL, not cached in JWTs. Direct grants are explicit allow grants only; implicit Admin, uploader, Organization scope, and Department scope access are not returned by permission list.

Not implemented yet:

- Reprocess endpoint.
- PDF extraction.
- Celery processing task dispatch.
- Document chunks.
- Embeddings.
- Signed download URLs.

## 8. Chat

Implemented Chat endpoints require an active authenticated User. Admin, Manager, and Staff can create and read only their own sessions; Admin does not bypass chat-session ownership.

### POST `/chat/sessions`

Request body is optional:

```json
{
  "title": "Quy dinh nghi phep"
}
```

Success: `HTTP 201`. The response contains session metadata only.

### GET `/chat/sessions`

Query parameters:

- `page`, default `1`, must be `>= 1`.
- `page_size`, default from `CHAT_SESSION_LIST_PAGE_SIZE`, maximum `CHAT_SESSION_LIST_MAX_PAGE_SIZE`.
- `include_archived`, optional boolean, default `false`.

Behavior:

- Returns only sessions owned by the current User.
- Ordering is `updated_at DESC, id DESC`.
- `message_count` counts visible USER and ASSISTANT messages only.

### GET `/chat/sessions/{session_id}`

Query parameters:

- `message_page`, default `1`, must be `>= 1`.
- `message_page_size`, default from `CHAT_HISTORY_PAGE_SIZE`, maximum `CHAT_HISTORY_MAX_PAGE_SIZE`.

Behavior:

- Missing and non-owned sessions both return `404 CHAT_SESSION_NOT_FOUND`.
- History returns USER and ASSISTANT messages only, ordered by `created_at ASC, id ASC`.
- SYSTEM messages are hidden.
- Assistant messages include `citations` for the current page, loaded in a batch query.
- Every message has `grounding_status` (BR-3): `ANSWERED` or `NO_ANSWER` on an ASSISTANT message, as returned when it was sent; `null` on USER messages and on ASSISTANT messages stored before migration `20261120_0013`. The `assistant_message` of `POST .../messages` carries the same field; the stream's `message.completed` already has `grounding_status` at the top level. Example:

  ```json
  { "id": "uuid", "role": "ASSISTANT", "content": "Chưa có câu trả lời…", "response_time_ms": 900,
    "citations": [], "created_at": "2026-11-20T08:00:00Z", "grounding_status": "NO_ANSWER" }
  ```
- **Sentences naming an unverified part (BR-3).** An `ANSWERED` answer may contain sentences that name a part of the question the documents do not confirm. The prompt asks for the fixed form `Chưa xác minh được từ tài liệu bạn được phép truy cập: …` (English question: `Could not be verified from the documents you can access: …`). In the default answer path (simple mode, s1) the model writes these sentences, so the wording after the prefix, and occasionally the prefix itself, may vary. The server recognises a sentence containing `chưa xác minh được`, `không xác minh được` or `could not be verified` (case- and accent-insensitive), never validates it as a claim, and removes its source markers, so it carries no citation number. The exception is a sentence holding a number the question does not: it stays a claim with its marker. The legacy compound path (`RAG_COMPOUND_PARTIAL_ANSWER_ENABLED`, off) builds the Vietnamese sentence itself, `Chưa xác minh được từ tài liệu bạn được phép truy cập: <part>.`. A client may style such a sentence differently, but must still show it.
- **`segments` (BR-3 follow-up, migration `20261120_0014`).** Every ASSISTANT message stored with an `ANSWERED` status carries `segments`: the displayed `content` cut into sentences by the same step and rule as above, each `{ "kind": "verified" | "unverified", "text": ..., "citation_ids": [...] }`. `text` is the sentence without its citation numbers; `citation_ids` are the `citation_order` values of the citations it shows (only numbers that are real citations of the message; any other bracketed number stays in `text`). `content` is unchanged. `segments` is `null` on USER messages, on `NO_ANSWER` messages (their `content` is the fixed no-answer text) and on answers stored before that migration. `POST .../messages` (`assistant_message.segments`) and the stream's `message.completed` (`segments`) return the same value. Example:

  ```json
  { "role": "ASSISTANT", "grounding_status": "ANSWERED",
    "content": "Nhân viên được nghỉ 12 ngày phép năm. [1] Chưa xác minh được từ tài liệu bạn được phép truy cập: mức phụ cấp.",
    "segments": [
      { "kind": "verified", "text": "Nhân viên được nghỉ 12 ngày phép năm.", "citation_ids": [1] },
      { "kind": "unverified", "text": "Chưa xác minh được từ tài liệu bạn được phép truy cập: mức phụ cấp.", "citation_ids": [] }
    ] }
  ```

  The recognition is a heuristic on three phrases; it is the same one the server uses to decide which sentences it validates.
- Historical citation metadata may be omitted if the current User no longer has access to the cited Document.
- The historical Assistant answer text is not redacted in TASK-020.
- `retrieval_query`, token usage, prompt, vectors, scores, storage keys, permission metadata, and internal source markers are not returned.

### POST `/chat/sessions/{session_id}/messages`

Request:

```json
{
  "content": "Nhan vien duoc nghi phep bao nhieu ngay?"
}
```

Rules:

- Only `content` is accepted from the client.
- Clients cannot set role, `user_id`, body `session_id`, model, temperature, max tokens, system prompt, Document IDs, retrieval mode, citations, or sources.
- Missing and non-owned sessions both return `404 CHAT_SESSION_NOT_FOUND`.
- Ownership is checked before history, retrieval, LLM, or persistence.
- Conversation memory is loaded from the current owned ChatSession only before retrieval.
- Memory includes USER, ASSISTANT, and internal SYSTEM messages, ordered by `created_at ASC, id ASC`, with duplicate message IDs removed.
- The memory window is bounded by server settings `CHAT_HISTORY_MAX_MESSAGES` and `CHAT_HISTORY_MAX_TOKENS`; clients cannot override it.
- Conversation memory can help resolve follow-up references, but answers still require retrieved context.
- Conversation memory is not a citation source; citations are valid only for backend-generated markers from selected retrieved context.
- Formatted prompts and formatted conversation history are never returned by the API and are not persisted.
- The service calls permission-aware `HybridRetrievalService` for context.
- Empty retrieval or empty context returns a successful fixed no-answer and does not call the LLM.
- LLM source markers are validated before the generated answer is returned or persisted.
- Unknown, malformed, missing, or too many source markers trigger bounded structured retry/repair. If the markers are still invalid afterwards, the request fails safe: `HTTP 201` (SSE: `message.completed`) with `grounding_status=NO_ANSWER`, empty citations, and the USER/ASSISTANT pair persisted with the fixed `CHAT_NO_ANSWER_MESSAGE`. No MessageCitation rows, `[SOURCE_n]` markers, or generated answer text are returned or persisted. A citation mapping failure after valid markers still returns `502 CITATION_MAPPING_FAILED`.
- Permission revalidation failure after LLM generation downgrades to the fixed no-answer with empty citations.
- USER, ASSISTANT, and MessageCitation rows are persisted atomically.

Success: `HTTP 201`.

Answered response example:

```json
{
  "data": {
    "session_id": "uuid",
    "user_message": {
      "id": "uuid",
      "role": "USER",
      "content": "Nhan vien duoc nghi phep bao nhieu ngay?",
      "citations": [],
      "created_at": "2026-07-20T00:00:00Z"
    },
    "assistant_message": {
      "id": "uuid",
      "role": "ASSISTANT",
      "content": "Nhan vien duoc huong 12 ngay nghi phep moi nam [1].",
      "citations": [
        {
          "document_id": "uuid",
          "document_title": "Quy che nhan su",
          "chunk_id": "uuid",
          "page_number": 14,
          "excerpt": "Nhan vien chinh thuc duoc huong 12 ngay nghi phep...",
          "relevance_score": 0.87,
          "citation_order": 1
        }
      ],
      "created_at": "2026-07-20T00:00:01Z"
    },
    "grounding_status": "ANSWERED",
    "retrieved_chunk_count": 3
  },
  "meta": null
}
```

No-answer response:

- `grounding_status` is `NO_ANSWER`.
- Assistant `citations` is `[]`.
- The answer contains no `[SOURCE_n]` marker.

Inline answer markers are public numeric markers `[1]`, `[2]`, and match `citation_order`. The API does not expose citations as a top-level `sources` array.

### POST `/chat/sessions/{session_id}/messages/stream`

TASK-027 adds a backward-compatible SSE transport for chat answers. The existing `POST /chat/sessions/{session_id}/messages` endpoint keeps its JSON request, JSON response, status code, and error contract.

TASK-029 conversation memory behavior is identical for streaming and non-streaming chat because both endpoints call the same grounded answer service after authentication and rate limiting.

Request:

```http
POST /api/v1/chat/sessions/{session_id}/messages/stream
Accept: text/event-stream
Content-Type: application/json
Authorization: Bearer <access-token>
```

```json
{
  "content": "Synthetic question"
}
```

Response headers on a started stream:

```text
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

The response does not set `Content-Length`. Authentication, active-user checks, request validation, and chat rate limiting run before the stream is opened where possible. The endpoint does not accept JWTs in query strings.

Event contract:

```text
stream.started
message.delta
citations.ready
message.completed
stream.error
stream.cancelled
heartbeat
```

Each event frame is UTF-8 SSE:

```text
id: <request-id>-<sequence>
event: <event_name>
data: <JSON>

```

Valid success order is `stream.started -> heartbeat* -> message.delta -> citations.ready? -> message.completed`. Valid failure order is `stream.started -> heartbeat* -> stream.error`. A terminal event is emitted at most once; no delta, citation, heartbeat, or completed event is emitted after a terminal event.

`stream.started` includes safe metadata: `request_id`, `session_id`, selected provider name, selected model when configured, and `strategy="buffer_after_validation"`.

`message.delta` contains:

```json
{
  "sequence": 1,
  "content": "Validated answer text"
}
```

TASK-027 deliberately emits the validated final answer as one delta. It does not public-stream raw provider chunks because grounding and citation validation currently operate on the complete answer.

`citations.ready` contains only the same safe citation payload shape used by the non-streaming Chat API. It is omitted when there are no citations.

`message.completed` contains the final `message_id`, `session_id`, `content`, `citations`, selected `provider`, selected `model`, optional token `usage`, `grounding_status`, and `retrieved_chunk_count`.

`stream.error` contains only safe client-facing fields:

```json
{
  "code": "LLM_PROVIDER_BAD_RESPONSE",
  "message": "Safe client-facing message",
  "retryable": false
}
```

The stream never sends API keys, provider headers, raw provider events, raw provider response bodies, prompts, retrieved context, chunk text, citation source registries, SQL details, stack traces, or internal exceptions.

Persistence behavior matches the grounded Chat service: the USER message, ASSISTANT message, citations, and audit events are committed atomically only after retrieval, generation, grounding, citation validation, and final persistence succeed. Provider failure, grounding failure, citation failure, timeout, or disconnect persists no partial ASSISTANT message.

Client disconnect is the TASK-027 stop-generation mechanism. The serving instance cancels active provider work where the underlying coroutine is cancellable and closes the HTTP stream. A cross-instance cancel endpoint is not included.

Reverse proxies must disable buffering for SSE, avoid caching, and use a read timeout longer than `LLM_STREAM_MAX_DURATION_SECONDS` plus deployment margin.

TASK-026 multi-LLM behavior:

- Chat request bodies do not accept provider names, model names, API keys, endpoint URLs, or provider headers.
- The default provider and model are selected server-side from configuration.
- Provider/model override is not exposed in the public Chat API in TASK-026.
- Safe provider display name, selected model display name, enabled/disabled state, configuration status, and standardized provider errors are prepared in the backend LLM service/registry layer for future Admin/UI use.
- LLM disabled or misconfigured responses use the standard error envelope and safe LLM error codes from `API_ERROR_CODES.md`.
- Provider timeout, rate limit, authentication, unavailable, rejected-request, and bad-response failures never include raw provider bodies, prompts, retrieved context, answers, citation excerpts, endpoint credentials, API keys, or request headers.


## 8A. Exact Evidence Citation Metadata — 2026-08-19

Chat request bodies are unchanged.

Citation responses may now include optional `evidence_text`:

```json
{
  "document_id": "uuid",
  "document_title": "Giới thiệu và cơ cấu tổ chức Công ty Công nghệ Nova Digital",
  "chunk_id": "uuid",
  "page_number": 3,
  "excerpt": "Answer-focused evidence: ... khoảng 180 người ...",
  "evidence_text": "180 người",
  "relevance_score": 0.89,
  "citation_order": 1
}
```

Rules:

- `evidence_text` is backend-generated from the validated answer and backend-selected source text.
- `evidence_text` is optional for backward compatibility; historical citations may omit it.
- Blank evidence is not persisted.
- `excerpt` remains the broader server-generated context snapshot.
- `evidence_text` must never be supplied by the client or trusted from arbitrary LLM metadata.
- Original PDF/DOCX content is not modified.
- `GET /chat/sessions/{session_id}`, non-streaming message responses, and SSE citation payloads use the same safe citation metadata contract.
- Frontend clients must fall back to the existing excerpt when `evidence_text` is absent.
- Minimal Citation Selection may remove redundant backend markers before public `[1]`, `[2]` numbering; this optimization must preserve distinct evidence required by multi-claim answers.

## 9. Feedback

### PUT `/messages/{message_id}/feedback`

Upserts the authenticated User's feedback for an owned ASSISTANT message.

Request:

```json
{
  "rating": "NOT_HELPFUL",
  "reason": "Nguon chua phu hop"
}
```

Rules:

- `rating` must be `HELPFUL` or `NOT_HELPFUL`.
- `reason` is optional, trimmed, and blank values become `null`.
- `reason` must not exceed `FEEDBACK_REASON_MAX_CHARACTERS` and the database hard maximum of `1000` characters.
- Client cannot send `message_id`, `user_id`, feedback id, timestamps, role, Department, or arbitrary metadata in the body.
- The target query filters `chat_messages.id`, `chat_messages.role = ASSISTANT`, and `chat_sessions.user_id = current_user.id` in PostgreSQL.
- Missing, non-owned, USER, and SYSTEM messages all return `404 FEEDBACK_TARGET_NOT_FOUND`.
- Admin and Manager cannot submit feedback on another User's message.
- Assistant no-answer messages can receive feedback.
- The upsert is atomic through PostgreSQL `ON CONFLICT(message_id, user_id) DO UPDATE`.

Success: `HTTP 200` for both create and update.

Response:

```json
{
  "data": {
    "id": "uuid",
    "message_id": "uuid",
    "rating": "NOT_HELPFUL",
    "reason": "Nguon chua phu hop",
    "created_at": "2026-07-20T00:00:00Z",
    "updated_at": "2026-07-20T00:00:00Z"
  },
  "meta": null
}
```

The upsert response does not expose `user_id`, message content, question text, citations, retrieval query, token usage, Document metadata, or internal metadata.

### GET `/feedback`

Returns a paginated management report for Admin and Manager users.

Query parameters:

- `page`, default `1`, must be `>= 1`.
- `page_size`, default `FEEDBACK_REPORT_PAGE_SIZE`, maximum `FEEDBACK_REPORT_MAX_PAGE_SIZE`.
- `rating`, optional `HELPFUL` or `NOT_HELPFUL`.
- `date_from`, optional timezone-aware datetime.
- `date_to`, optional timezone-aware datetime.
- `department_id`, optional Admin filter; Manager scope is still restricted to the Manager current Department.
- `user_id`, optional Admin filter; Manager scope is still restricted to the Manager current Department.

Behavior:

- Admin sees all feedback after filters.
- Manager sees only feedback submitted by Users whose current `users.department_id` matches the Manager current Department.
- Manager with no Department receives `403 FEEDBACK_REPORT_SCOPE_UNAVAILABLE`.
- Staff receives `403 FEEDBACK_REPORT_FORBIDDEN` and no partial own rows.
- Scope and filters are applied in PostgreSQL before `LIMIT/OFFSET` and before `total` is computed.
- Date filters use `feedback.updated_at`; invalid ranges return `422 FEEDBACK_DATE_RANGE_INVALID`.
- Sorting is stable: `updated_at DESC, id DESC`.

Response:

```json
{
  "data": [
    {
      "id": "uuid",
      "message_id": "uuid",
      "user_id": "uuid",
      "department_id": "uuid",
      "rating": "HELPFUL",
      "reason": null,
      "created_at": "2026-07-20T00:00:00Z",
      "updated_at": "2026-07-20T00:00:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

The report does not return Assistant answers, User questions, session titles, Chat history, SYSTEM messages, retrieval query, token usage, prompts, citation excerpts, Document titles, storage keys, or permission metadata.

## 10. Audit logs

### Audit event types (BR-9)

The stable `event_type` values (`app/audit/events.py`, `AuditEventType`). The filter accepts every value; the server writes all but the two marked reserved.

| `event_type` | Written when | `target_type` |
|---|---|---|
| `AUTH_LOGIN_SUCCEEDED` | a login succeeds | `USER` |
| `AUTH_LOGIN_FAILED` | a login fails (outcome `FAILURE`, `error_code` set) | none |
| `USER_CREATED` | an Admin creates a User | `USER` |
| `USER_UPDATED` | a User's profile fields change | `USER` |
| `USER_STATUS_CHANGED` | a User is deactivated or reactivated (metadata `status_before`, `status_after`) | `USER` |
| `USER_DEACTIVATED` | reserved, not written (deactivation writes `USER_STATUS_CHANGED`) | — |
| `USER_REACTIVATED` | reserved, not written (reactivation writes `USER_STATUS_CHANGED`) | — |
| `DEPARTMENT_CREATED` / `DEPARTMENT_UPDATED` / `DEPARTMENT_DELETED` | Department changes | `DEPARTMENT` |
| `DOCUMENT_UPLOADED` / `DOCUMENT_UPDATED` / `DOCUMENT_DELETED` | Document changes | `DOCUMENT` |
| `DOCUMENT_DOWNLOADED` | a download, or a preview (`/documents/{id}/preview`) | `DOCUMENT` |
| `DOCUMENT_PERMISSION_GRANTED` / `DOCUMENT_PERMISSION_UPDATED` / `DOCUMENT_PERMISSION_REVOKED` | direct grant changes | `DOCUMENT_PERMISSION` |
| `CHAT_SESSION_CREATED` / `CHAT_SESSION_DELETED` | chat session changes | `CHAT_SESSION` |
| `CHAT_QUESTION_SUBMITTED` | a question is stored | `CHAT_MESSAGE` |
| `CHAT_ANSWER_GENERATED` / `CHAT_NO_ANSWER_GENERATED` | an answer is stored, `ANSWERED` / `NO_ANSWER` | `CHAT_MESSAGE` |
| `FEEDBACK_UPSERTED` | feedback is set or changed | `FEEDBACK` |

Audit items never include the client IP address or raw headers.

### GET `/audit-logs`

Returns an Admin-only paginated AuditLog report.

Query parameters:

- `page`, default `1`, must be `>= 1`.
- `page_size`, default `AUDIT_REPORT_PAGE_SIZE`, maximum `AUDIT_REPORT_MAX_PAGE_SIZE`.
- `event_type`, optional stable audit event type, one of the values below; any other value returns `422 AUDIT_FILTER_INVALID`.
- `outcome`, optional `SUCCESS` or `FAILURE`.
- `actor_user_id`, optional actor UUID.
- `target_type`, optional safe target type: `USER`, `DEPARTMENT`, `DOCUMENT`, `DOCUMENT_PERMISSION`, `CHAT_SESSION`, `CHAT_MESSAGE`, or `FEEDBACK`.
- `target_id`, optional target UUID.
- `date_from`, optional timezone-aware datetime using `audit_logs.created_at`.
- `date_to`, optional timezone-aware datetime using `audit_logs.created_at`.
- `request_id`, optional exact correlation id.
- `error_code`, optional sanitized error code.

Behavior:

- Admin receives global AuditLog rows after filters.
- Manager and Staff receive `403 AUDIT_REPORT_FORBIDDEN` and no partial rows.
- Missing or invalid Bearer token receives the standard authentication error.
- Filters and total counts are applied in PostgreSQL before `LIMIT/OFFSET`.
- Sorting is stable: `created_at DESC, id DESC`.
- Invalid date ranges return `422 AUDIT_DATE_RANGE_INVALID`.
- Invalid enum/string filters return `422 AUDIT_FILTER_INVALID`.
- Reading AuditLog does not create an audit event.
- There is no public create, update, delete, export, dashboard, or SIEM AuditLog API.

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "event_type": "FEEDBACK_UPSERTED",
      "outcome": "SUCCESS",
      "actor_user_id": "uuid",
      "target_type": "FEEDBACK",
      "target_id": "uuid",
      "request_id": null,
      "error_code": null,
      "metadata": {
        "rating": "HELPFUL"
      },
      "created_at": "2026-07-22T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 1,
  "total_pages": 1
}
```

The report does not return actor email, actor full name, request/response bodies, raw headers, exceptions, stack traces, Chat question/answer content, prompts, retrieved context, citation excerpts, Feedback reason, Document filename, storage path, storage key, API key, access token, or refresh token.

## 11. Health

- `GET /health/live`
- `GET /health/ready`

Readiness checks database connectivity.

`GET /health/ready` also returns `reranker_mode`: `cross_encoder`, `lexical_fallback` or `disabled`. It says what ranks candidates at that moment; the eval runners read it.

## TASK-025 hardening errors

All API error responses keep the standard envelope:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Safe message.",
    "details": null,
    "request_id": null
  }
}
```

Additional hardening responses:

- `REQUEST_TOO_LARGE` with HTTP `413` for request bodies over `MAX_REQUEST_BODY_BYTES`.
- `RATE_LIMIT_EXCEEDED` with HTTP `429` and `Retry-After` for configured endpoint rate limits.
- `DOCUMENT_FILE_TOO_LARGE` with HTTP `413` for upload stream size violations.
- `DOCUMENT_FILE_EMPTY` with HTTP `400` for empty uploads.
- `DOCUMENT_FILE_TYPE_INVALID` with HTTP `415` for unsupported extension or MIME type.
- `DOCUMENT_OCR_DISABLED` for image/scanned-document OCR paths when OCR is disabled.
- `DOCUMENT_OCR_PAGE_LIMIT_EXCEEDED`, `DOCUMENT_IMAGE_DIMENSIONS_EXCEEDED`, `DOCUMENT_IMAGE_INVALID`, `DOCUMENT_OCR_TIMEOUT`, and `DOCUMENT_OCR_FAILED` for bounded OCR processing failures.
- `DOCUMENT_FILE_SIGNATURE_INVALID` with HTTP `415` for missing/invalid `%PDF-` signature.
- `DOCUMENT_FILENAME_INVALID` with HTTP `400` for missing, empty, or overlong filenames.

Production can disable `/docs`, `/redoc`, and `/openapi.json` with `API_DOCS_ENABLED=false`; health and API routes remain available.


## TASK-031 Web Search API Addendum

Chat request compatibility:

- `POST /chat/sessions/{session_id}/messages` and `/messages/stream` request bodies are unchanged.
- Clients cannot select web/internal mode, provider, result count, URLs, or citation sources per request.
- Web search behavior is controlled only by backend configuration.

Citation response compatibility:

- Internal citations preserve the existing response shape and omit `source_type` and `source_url`.
- Web citations include `source_type="WEB"`, `source_url`, `document_title`, `page_number=1`, `excerpt`, `relevance_score=null`, and `citation_order`.
- Web citation `document_id` and `chunk_id` are `null`.
- `source_url` is backend-normalized provider metadata, not a URL generated by the LLM.

Example web citation:

```json
{
  "document_id": null,
  "document_title": "Microsoft Learn",
  "chunk_id": null,
  "page_number": 1,
  "excerpt": "Microsoft Learn describes Azure AI services.",
  "relevance_score": null,
  "citation_order": 2,
  "source_type": "WEB",
  "source_url": "https://learn.microsoft.com/en-us/azure/ai-services/"
}
```

Admin-only web search endpoints:

### GET `/web-search/provider-status`

Requires Admin. Returns provider configuration status without secrets.

```json
{
  "data": {
    "provider": "mock",
    "display_name": "Mock Provider",
    "status": "disabled",
    "configured": false,
    "external_allowed": false,
    "connectivity_checked": false,
    "message": "Web search is disabled.",
    "request_id": null
  },
  "meta": null
}
```

### POST `/web-search/test`

Requires Admin. Runs a bounded provider search using current backend configuration. Intended for configuration testing only.

Request:

```json
{
  "query": "OpenAI Docs"
}
```

Success returns normalized title, source URL, snippet, provider, and rank. It does not return raw HTML, JavaScript, CSS, provider headers, API keys, or raw provider response bodies.

## TASK-032 Admin Monitoring API

All endpoints in this section require an active Admin bearer token. Manager and Staff users receive `403 FORBIDDEN`; missing or invalid bearer tokens receive the standard authentication error. Responses use the standard `DataResponse` wrapper and never include secrets, prompts, retrieved context, chat content, citation excerpts, feedback reasons, storage keys, database URLs, Redis URLs, or API keys.

### GET `/admin/system`

Returns the aggregate backend dashboard payload: version, uptime, health checks, provider status, worker status, queue status, and safe statistics.

Example (BR-8; test stack, shortened lists). `version`, `health`, `providers`, `workers`, `queues` and `statistics` have the shapes of `/admin/version`, `/admin/health`, `/admin/providers`, `/admin/workers`, `/admin/queues` and `/admin/statistics`:

```json
{
  "data": {
    "generated_at": "2026-11-20T11:09:09Z",
    "version": { "app_name": "Enterprise AI Knowledge Assistant", "version": "0.1.0",
                 "environment": "production", "python_version": "3.12.16", "api_prefix": "/api/v1",
                 "migration_head": "20261120_0013", "database_revision": "20261120_0013",
                 "started_at": "2026-11-20T11:09:05Z", "uptime_seconds": 3 },
    "uptime_seconds": 3,
    "health": { "status": "healthy", "generated_at": "2026-11-20T11:09:09Z",
                "checks": [ { "name": "api", "status": "ok", "enabled": true,
                              "message": "API process is running.", "details": { "uptime_seconds": 3 } } ] },
    "providers": { "llm": { "provider_type": "llm", "provider": "ollama", "status": "healthy",
                            "enabled": true, "configured": true, "display_name": "Ollama",
                            "model": "qwen3.5-text:4b", "external_allowed": null,
                            "connectivity_checked": false, "message": "…" },
                   "web_search": { "provider_type": "web_search", "provider": "mock",
                                   "status": "disabled", "enabled": false, "configured": false,
                                   "display_name": "Mock Web Search", "model": null,
                                   "external_allowed": false, "connectivity_checked": false,
                                   "message": "Web search is disabled." } },
    "workers": { "status": "healthy", "active_worker_count": 1,
                 "workers": [ { "name": "worker@host", "status": "ok",
                                "queues": ["default", "documents"], "pool": "prefork" } ],
                 "registered_tasks": ["documents.process_document", "system.worker_ping"],
                 "message": null },
    "queues": { "status": "healthy",
                "queues": [ { "kind": "document", "name": "documents", "status": "ok",
                              "configured": true, "pending": 2,
                              "consumer": "documents.process_document",
                              "message": "Document queue is reachable." } ] },
    "statistics": { "documents": { "total": 12, "deleted": 0, "by_status": { "READY": 12 } },
                    "chunks": { "total": 340 }, "embeddings": { "total": 340 },
                    "users": { "total": 4, "active": 4, "inactive": 0,
                               "by_role": { "ADMIN": 1, "MANAGER": 1, "STAFF": 2 } },
                    "departments": { "total": 2 }, "chat_sessions": { "total": 9, "archived": 0 },
                    "messages": { "total": 36, "by_role": { "USER": 18, "ASSISTANT": 18 } },
                    "feedback": { "total": 3, "by_rating": { "HELPFUL": 2, "NOT_HELPFUL": 1 } },
                    "audit_logs": { "total": 120 } }
  },
  "meta": null
}
```

### GET `/admin/health`

Returns component health for:

- API
- PostgreSQL
- Redis
- Celery worker
- OCR
- Embedding configuration
- LLM configuration
- Web Search configuration
- Streaming subsystem
- Conversation subsystem

LLM and Web Search checks are configuration checks only by default and do not call external providers. Embedding health does not load the model.

Example (BR-8; the test stack, LLM disabled). `status` is `healthy`, `degraded` or `unhealthy`; each check's `status` is `ok`, `degraded`, `unavailable`, `disabled`, `misconfigured` or `not_configured`; `details` holds only safe scalars and lists of strings, and its keys differ per check:

```json
{
  "data": {
    "status": "healthy",
    "generated_at": "2026-11-20T11:09:08Z",
    "checks": [
      { "name": "api", "status": "ok", "enabled": true, "message": "API process is running.",
        "details": { "uptime_seconds": 2 } },
      { "name": "postgres", "status": "ok", "enabled": true, "message": "PostgreSQL is reachable.", "details": {} },
      { "name": "redis", "status": "ok", "enabled": true, "message": "Redis is reachable.", "details": {} },
      { "name": "worker", "status": "ok", "enabled": true,
        "message": "At least one Celery worker responded.", "details": { "active_worker_count": 1 } },
      { "name": "ocr", "status": "ok", "enabled": true, "message": "OCR engine is available.",
        "details": { "engine": "tesseract", "requested_languages": ["vie", "eng"],
                     "version": "tesseract 5", "available_languages": ["eng", "vie"] } },
      { "name": "embedding", "status": "ok", "enabled": true,
        "message": "Embedding provider configuration is valid.",
        "details": { "provider": "sentence_transformers", "model": "intfloat/multilingual-e5-small",
                     "dimensions": 384, "model_loading_checked": false } },
      { "name": "llm", "status": "disabled", "enabled": false, "message": "LLM is disabled.",
        "details": { "provider": "openai_compatible", "display_name": "OpenAI-compatible",
                     "model": null, "connectivity_checked": false } },
      { "name": "web_search", "status": "disabled", "enabled": false, "message": "Web search is disabled.",
        "details": { "provider": "mock", "display_name": "Mock Web Search",
                     "external_allowed": false, "connectivity_checked": false } },
      { "name": "streaming", "status": "ok", "enabled": true, "message": "Streaming subsystem is registered.",
        "details": { "strategy": "buffer_after_validation", "heartbeat_seconds": 15.0,
                     "max_duration_seconds": 120.0 } },
      { "name": "conversation", "status": "ok", "enabled": true, "message": "Conversation memory is enabled.",
        "details": { "max_messages": 10, "max_tokens": 1200 } }
    ]
  },
  "meta": null
}
```

On the default deployment the `llm` check reads `"status": "ok"`, `"enabled": true` with `details.provider` `ollama`, `details.display_name` `Ollama` and `details.model` `qwen3.5-text:4b` when its configuration is valid (a configuration check: the model is not called).

### GET `/admin/providers`

Returns safe LLM and Web Search provider state: provider name, display name, enabled/disabled, configured flag, healthy/disabled/misconfigured/unhealthy status, selected model where applicable, external-call policy where applicable, and safe message. Provider secrets are never returned.

Example (BR-8; test stack, LLM disabled). On the default deployment `llm` reads `"provider": "ollama"`, `"display_name": "Ollama"`, `"model": "qwen3.5-text:4b"`, `"enabled": true`, `"configured": true`, and `"status": "healthy"` when the configuration is valid. `connectivity_checked` stays `false`: the endpoint does not call the provider.

```json
{
  "data": {
    "llm": { "provider_type": "llm", "provider": "openai_compatible", "status": "disabled",
             "enabled": false, "configured": false, "display_name": "OpenAI-compatible",
             "model": null, "external_allowed": null, "connectivity_checked": false,
             "message": "LLM is disabled." },
    "web_search": { "provider_type": "web_search", "provider": "mock", "status": "disabled",
                    "enabled": false, "configured": false, "display_name": "Mock Web Search",
                    "model": null, "external_allowed": false, "connectivity_checked": false,
                    "message": "Web search is disabled." }
  },
  "meta": null
}
```

### GET `/admin/workers`

Returns Celery worker inspect status, active worker count, worker names, active queues, pool implementation when available, and registered task names. It does not return broker URLs or task payloads.

### GET `/admin/statistics`

Returns safe aggregate counts only:

- Documents and status counts
- Chunks
- Embeddings
- Users and role/active counts
- Departments
- Chat Sessions
- Messages by role
- Feedback by rating
- Audit Logs

It does not return document titles, filenames, chat text, feedback reasons, audit metadata details, chunk text, vectors, or citations.

### GET `/admin/queues`

Returns queue state for the existing architecture:

- Document Queue: configured Celery document queue and pending length when Redis broker is reachable.
- OCR Queue: reported as not configured because OCR runs inside document processing.
- Embedding Queue: reported as not configured because embedding runs inside document processing.
- Retry Queue: reported as not configured because no dedicated retry queue exists.
- Dead Letter Queue: reported as not configured unless future architecture adds one.

### GET `/admin/version`

Returns app name, package version, environment, Python version, API prefix, source Alembic head, database Alembic revision when readable, startup timestamp, and uptime seconds. It does not return hostnames, connection strings, environment variables, or secrets.

Example (BR-8; `database_revision` and `started_at` may be `null`):

```json
{
  "data": {
    "app_name": "Enterprise AI Knowledge Assistant",
    "version": "0.1.0",
    "environment": "production",
    "python_version": "3.12.16",
    "api_prefix": "/api/v1",
    "migration_head": "20261120_0013",
    "database_revision": "20261120_0013",
    "started_at": "2026-11-20T11:09:05Z",
    "uptime_seconds": 3
  },
  "meta": null
}
```

The answer path itself (simple or legacy mode, retrieval settings) is not exposed by these endpoints.


## TASK-033 Admin Analytics API

All endpoints in this section require an active Admin bearer token. Manager and Staff users receive `403 FORBIDDEN`; missing or invalid bearer tokens receive the standard authentication error. Responses use safe aggregate data only and never include prompts, retrieved context, chat content, retrieval query text, citation excerpts, feedback reasons, storage keys, database URLs, Redis URLs, API keys, or raw provider payloads.

Supported filters:

- `period=today|7d|30d|90d|custom`, default `30d`.
- `date_from` and `date_to` are accepted only with `period=custom` and must include timezone offsets.
- Analytics windows are evaluated in UTC.

### GET `/admin/analytics/overview`

Returns a compact cross-domain summary: questions, sessions, active users, documents, feedback, audit events, internal/hybrid/web search counts, inferred OCR jobs, LLM message count, and total tokens.

### GET `/admin/analytics/chat`

Returns question count, session count, assistant message count, average response time, token totals as `input_tokens`, `output_tokens`, and `total_tokens`, and question trends by day. Retrieval duration and streaming usage are returned as unavailable metrics because they are not persisted separately.

### GET `/admin/analytics/users`

Returns active users in the selected window, total active accounts, new users, top users by question count, and top departments by question count. Top user rows expose user IDs and department IDs only; they do not expose email or full name.

### GET `/admin/analytics/search`

Returns internal, hybrid, and web search counts inferred from persisted citation `source_type` values. Top queries are returned as stable hashes with counts, never raw query text. Top documents return document ID, title, and citation count only; filenames, storage keys, chunk text, and citation excerpts are omitted.

### GET `/admin/analytics/ocr`

Returns inferred OCR jobs, success/failure counts and rates, pages processed, and status counts for image documents. OCR duration is unavailable because the pipeline does not persist OCR timing. Scanned-PDF OCR page counts are not exact because OCR/native extraction method metadata is not persisted per chunk.

### GET `/admin/analytics/llm`

Returns safe LLM token usage, latency from assistant message response times, failure counts inferred from LLM-prefixed audit error codes, and current configured provider/model metadata. Provider/model usage is marked as non-historical attribution because chat messages do not persist provider/model per generation.

### GET `/admin/analytics/feedback`

Returns helpful/not-helpful counts, percentages, and daily trend counts. Feedback reasons are never returned.

### GET `/admin/analytics/audit`

Returns aggregate audit counts for login, upload, download, delete, permission, admin actions, success/failure outcomes, and top actions. Audit metadata, IP addresses, user agents, request bodies, target IDs, and business content are not returned.

### GET `/admin/reports/export`

Query parameters:

- `report=overview|chat|users|search|ocr|llm|feedback|audit`
- `format=json|csv|pdf`, default `json`
- the same `period`, `date_from`, and `date_to` filters as analytics endpoints

JSON export returns a `DataResponse` wrapper with a safe report payload. CSV export returns flattened `field,value` rows. PDF export returns `422 VALIDATION_ERROR` because no backend PDF report infrastructure exists.

## TASK-034 Observability Metrics API

### GET `/metrics`

Returns Prometheus text format for internal scraping. This endpoint is not an Admin data API and does not return business content.

Metrics include:

- HTTP request totals by method, safe route template, and status code.
- HTTP latency sum/count/max by method, safe route template, and status code.
- Observability and tracing-hook enabled flags.
- Application version, environment, Alembic source head, database revision, and uptime.
- Component health gauges for API, PostgreSQL, Redis, worker, OCR, embedding, LLM, Web Search, streaming, and conversation.
- Provider enabled/configured/healthy gauges for LLM and Web Search providers.
- Worker active count and registered task count.
- Queue configured and pending gauges for available queues.

Security rules:

- No authentication secrets, API keys, database URLs, Redis URLs, storage keys, tokens, prompts, retrieved context, chat content, OCR text, citation excerpts, feedback reasons, raw provider payloads, request bodies, SQL statements, or stack traces are returned.
- Production Nginx blocks external `/metrics` by default; Prometheus scrapes `api:8000/metrics` on the Docker backend network.
- Metrics labels use bounded safe route templates and do not include query strings.

`METRICS_ENABLED=false` returns `404` for this endpoint.

## TASK-035 API Freeze

- Release version: v1.0.0-rc1.
- TASK-035 did not change API contracts, request bodies, response bodies, status codes, authentication requirements, streaming event names, or database schema.
- Final acceptance verified Authentication, RBAC, Departments, Users, Documents, OCR, Embedding, Semantic Retrieval, Keyword Retrieval, Hybrid Retrieval, Conversation Memory, Grounded Answer, Citation, Streaming, Feedback, Audit, Web Search, Analytics, Monitoring, and Production Deployment endpoints against the existing contract.

