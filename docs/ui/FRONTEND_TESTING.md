# Frontend Testing

## Commands

```bash
npm install
npm run lint
npm run typecheck
npm run test
npm run test:e2e
npm run build
```

## Current Coverage

Unit and component tests cover:

- API error parser and safe fallback messages.
- Permission helpers.
- SSE parser split chunks, multiple events, unicode JSON escaping, comment heartbeat, terminal flush, unknown event rejection, malformed JSON rejection.
- POST SSE transport request shape and terminal event handling.
- Chat stream state machine terminal behavior and stale delta handling.
- Shared loading, empty, and error state components.

Playwright smoke tests cover:

- Unauthenticated protected-route redirect to login.
- Login form client validation before network submission.

## Backend-Safe Testing

Frontend tests must not call live external LLM providers. Tests use deterministic local streams and fake fetch responses. Browser E2E smoke tests do not require a backend token.

## Future Expansion

When a seeded test backend is available, add E2E coverage for admin user management, manager document permission flow, staff document upload and chat, SSE success/error, citation display, logout/expired session, unauthorized direct route access, and mobile layout checks.
## Live UAT Suite

`npm run test:e2e:live` runs Playwright against a real frontend and backend. It requires `E2E_LIVE=true`, seeded UAT account passwords in environment variables, Docker Compose with `compose.uat.yaml`, PostgreSQL, Redis, API, worker, frontend, and the local deterministic UAT LLM provider.

The suite must not route/intercept API calls to fake responses. It may use backend API requests only for setup verification, ID lookup, and polling asynchronous document processing status.
