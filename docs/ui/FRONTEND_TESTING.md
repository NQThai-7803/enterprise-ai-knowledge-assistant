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

`tests/e2e-live/smoke.spec.ts` is the redesign's smoke against a real backend, one test per role (staff: answered and refused questions, preview from a citation, no uploader names; manager: upload limited to PRIVATE or the own department, other scopes refused by the API; admin: names, audit filtered by `event_type`, system status). Run it with `E2E_LIVE=true`, the `UAT_*_PASSWORD` variables, `PLAYWRIGHT_BASE_URL` and `E2E_API_BASE_URL`: `npx playwright test -c playwright.live.config.ts smoke`. Traces, failure screenshots and videos are off in that spec so passwords never reach a file. It runs on Playwright's full Chromium build (`channel: "chromium"`, new headless), which has the PDF viewer the preview needs; the default headless shell shows an empty frame. The answerable question defaults to the public dev item ND-001 and can be changed with `SMOKE_ANSWERABLE_QUESTION`; each chat time (click to answer on screen) is appended to `timings.txt` in `SMOKE_SCREENSHOT_DIR`. `live-acceptance.spec.ts` still uses the pre-redesign English labels and needs porting before it can pass again.
