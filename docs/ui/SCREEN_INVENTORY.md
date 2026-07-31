# Screen Inventory

| Screen | Route | Backend APIs | Roles | Notes |
| --- | --- | --- | --- | --- |
| Login | `/login` | `POST /api/v1/auth/login`, `GET /api/v1/auth/me` | Public | Uses bearer-token contract, no token in URL. |
| Shell | authenticated routes | `/health/ready`, `/auth/logout` | Authenticated | Role-aware navigation, backend remains authority. |
| Chat | `/chat` | `/chat/sessions`, `/chat/sessions/{id}`, streaming `/messages/stream`, feedback | Authenticated | POST SSE parser, buffer-after-validation UX. |
| Document library | `/documents` | `/documents` | Authenticated | Permission-filtered backend list. |
| Upload | `/documents/upload` | `POST /documents` | Admin, Manager | Multipart upload, processing distinction. |
| Document detail | `/documents/:id` | detail/status/download/delete | Authenticated by backend permission | No raw storage paths. |
| Permissions | `/documents/:id/permissions` | direct permissions APIs | Admin | Grant/revoke with confirmation. |
| Users | `/users` | `/users` | Admin | Create/edit/activate/deactivate. |
| Departments | `/departments` | `/departments` | Admin | Create/edit list. |
| Feedback | `/feedback` | `/feedback` | Admin, Manager | Report list; chat has answer feedback buttons. |
| Audit logs | `/audit-logs` | `/audit-logs` | Admin | Dense safe metadata display. |
| System status | `/system` | health endpoints, frontend config | Authenticated | Shows real available status; provider status unavailable unless backend exposes it. |
| Profile | `/profile` | current auth state | Authenticated | No token display. |
| Access denied | `/access-denied` | none | Any | Safe route-level denial. |
| Not found | `*` | none | Any | Safe fallback. |
| Empty states | shared | none | Any | No fake data. |
| Loading states | shared | none | Any | Stable dimensions. |
| Error states | shared | none | Any | Safe request/error messages only. |