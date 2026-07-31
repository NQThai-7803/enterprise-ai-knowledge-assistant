# Frontend Architecture

## Stack

- Framework: React 18.
- Language: TypeScript strict mode.
- Build tool: Vite.
- Router: React Router.
- Data fetching/cache: TanStack Query.
- Forms: React Hook Form.
- Validation: Zod.
- Styling: Tailwind CSS with CSS variables.
- Icons: lucide-react.
- Tests: Vitest, React Testing Library, Playwright.

## Folder Structure

`frontend/src` is split by app shell, feature areas, shared components, API integration, hooks/lib utilities, styles, and tests.

- `app/`: route tree.
- `layouts/`: authenticated shell.
- `features/`: auth, chat, documents, admin, feedback, audit, system, profile.
- `components/ui`: buttons, fields, badges, panels, states, pagination.
- `components/motion`: controlled decorative motion primitives.
- `components/feedback`: toast and error boundary.
- `components/data`: reusable table wrapper.
- `api/`: typed client, standard error mapping, SSE parser/client, token storage.
- `lib/`: config, permissions, formatting.
- `styles/`: design tokens and global CSS.

## API Client

The frontend uses one typed API client built on `fetch`. It supports:

- Base URL from `VITE_API_BASE_URL`.
- Bearer access token from session storage.
- JSON requests and multipart upload.
- Abort signals and request timeouts.
- Safe standard error parsing into `ApiError`.
- Request id propagation from backend error envelope or `X-Request-ID` header.
- 401 session-expiry event without logging token values.

## SSE Client

Native `EventSource` is not used because the backend contract uses authenticated POST with JSON body. The client uses `fetch`, `ReadableStream`, `TextDecoder`, `AbortController`, and a line-based SSE parser.

The parser handles:

- Chunk boundaries.
- Multiple events per chunk.
- Repeated data lines.
- Comment heartbeats.
- UTF-8 text.
- Malformed JSON rejection.
- Terminal event stop.

## Auth and RBAC

- Authentication uses `/auth/login`, `/auth/me`, and `/auth/logout`.
- Access tokens are never placed in URLs.
- Role-aware navigation is implemented for usability only; backend authorization remains authoritative.
- Protected routes render access denied instead of calling restricted APIs unnecessarily.

## Production Data Policy

Production screens call real backend APIs. Tests use fake responses or isolated parser/state tests. If a backend endpoint is unavailable, the UI shows an unavailable/error state rather than fake success data.
## Known Dependency Advisory

React Router is pinned to `react-router-dom@7.18.2`. `npm audit --audit-level=high` reports an advisory for React Router RSC/action handling in this version range. The TASK-028 frontend uses SPA routing only and does not enable RSC, server actions, route actions, or SSR redirects. Reassess before enabling those modes or when a clean upstream release is available.