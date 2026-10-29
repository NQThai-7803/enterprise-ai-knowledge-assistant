# TASK-035.3G — frontend delivery contract compatibility

Date: 2026-10-14. Static comparison only of `frontend/src/api/{client,sse,types,errors}.ts`,
the frontend pages, `API_SPEC.md`, backend `app/api/v1/` routers and
`app/schemas/`. No active V2 or failed-candidate request was made. A typed
TypeScript declaration is not runtime validation.

| Boundary | Static observation | Qualification |
| --- | --- | --- |
| Login/current-user/refresh/logout | Frontend paths, POST bodies, `data` token pair/user, Bearer header, 401 refresh and 204 logout correspond to `auth.py` and `schemas/auth.py`. Tokens are `sessionStorage`; backend remains authority. | Static shape/path match; actual expiry, refresh rotation, inactive-user and logout behavior unverified. |
| Documents | Frontend multipart fields and upload 202 match `documents.py`; status uses the view-protected GET and polls `UPLOADED`/`PROCESSING` every 5 s, stopping at READY/FAILED/other terminal state. Download/permissions routes exist. | Static match for used fields; upload→READY, ownership, grant/revoke and failure behavior not run. Backend has newer optional policy metadata not modeled by `DocumentItem`; UI does not use it. |
| Chat JSON | Session list/create/detail/delete and message POST paths/payload and `DataResponse[ChatAnswerResponse]` match router/schema. | Static match; no live candidate persistence/ownership/grounding proof. |
| SSE and citations | POST stream URL, Bearer header, event names/order and `message.completed` fields agree with `chat.py`, `chat_stream_service.py`, `chat/sse.py`; mocked citation UI rendered. | Mocked only; no final-image stream, permission revalidation or material-citation proof. Frontend `Citation.document_id: string` is narrower than backend `UUID | None` for Web citations, and omits optional `source_type`/`source_url`; current UI mainly renders title/page/excerpt, so runtime break is **not proven**, but the typed contract is incomplete for Web sources. |
| Feedback/audit | Upsert `/messages/{id}/feedback`, GET `/feedback`, and GET `/audit-logs` names/query wrappers match backend routes. | No live submit/report/RBAC audit run. |
| Admin/Manager | `ProtectedRoute`/`AppShell` hide paths by role; backend user/dept/document/feedback routers use server-side dependencies. | Static/mocked navigation match; frontend hiding does not enforce permission. No current live role matrix. |
| Errors | Frontend parses `{error:{code,message,details,request_id}}`, fallback HTTP codes and Retry-After; API spec/backend use standard envelope. | Static match; no live safe-error, rate-limit or malformed-payload contract run. |

`frontend/src/lib/config.ts` appends `/api/v1`; liveness/readiness use root
paths. The backend `compose.prod.yaml` reverse proxy forwards those paths to
API, but does not serve frontend assets. Production frontend origin, CORS,
TLS, same-source API/worker identity, and integrated browser operation remain
unverified. Do not promote static/mock compatibility to P10–P13 live PASS.
