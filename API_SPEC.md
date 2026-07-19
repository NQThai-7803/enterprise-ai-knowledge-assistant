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
      "is_active": true
    }
  },
  "meta": null
}
```

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
    "role": "ADMIN",
    "department_id": null,
    "is_active": true
  },
  "meta": null
}
```

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

Implemented through TASK-015. Accepts one PDF, stores it through `FileStorage`, creates a `documents` row with status `UPLOADED`, commits the database transaction, then enqueues `documents.process_document` asynchronously. The response remains HTTP 202 and does not wait for processing to finish.

Requires Admin or Manager. Staff receives `403 FORBIDDEN`.

Content type: `multipart/form-data`

Fields: `file`, `title`, `description`, `access_scope`, `department_id`.

The response is `HTTP 202 Accepted` and never includes `storage_key`, `checksum_sha256`, local paths, `error_message`, or permissions.

Duplicate detection is scoped to the same uploader and checksum where `is_deleted = false`.

### GET `/documents`

Implemented in TASK-010. Requires any active authenticated User.

Query parameters:

- `page`, default `1`, must be `>= 1`.
- `page_size`, default `20`, must be between `1` and `100`.
- `search`, searches `title`, `original_filename`, and `description`, max 200 characters.
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

- `Content-Type: application/pdf`
- `Content-Disposition: attachment`
- `X-Content-Type-Options: nosniff`
- `Cache-Control: private, no-store`

Storage keys and local paths are never returned. If metadata exists but the local file is missing, the endpoint returns `410 DOCUMENT_FILE_UNAVAILABLE`.

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
- Preview endpoint.
- Signed download URLs.
## 8. Chat

Not implemented yet.

## 9. Feedback

Not implemented yet.

## 10. Audit logs

Not implemented yet.

## 11. Health

- `GET /health/live`
- `GET /health/ready`

Readiness checks database connectivity.

