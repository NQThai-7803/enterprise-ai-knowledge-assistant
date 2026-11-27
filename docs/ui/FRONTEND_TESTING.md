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

## Secrets in Tests

A failing assertion prints both its received and its expected value: to the terminal, to CI logs and into Playwright's `error-context.md`. So:

- **Never assert on the value of a token, password, secret or cookie**, neither as what `expect()` receives nor as the expected value. Compare only key names (which storage keys exist), a length, or presence: `expect(Boolean(token)).toBe(true)`, `expect(token !== null).toBe(true)`, `expect(token.length).toBeGreaterThan(20)`. Presence matchers do not help on their own: `expect(token).toBeNull()` still prints the token when it fails.
- **Scope:** every test that touches real credentials, that is everything under `frontend/tests/` (live runs against a real backend) and any test that reads a password from the environment. Unit tests under `src/` may compare fixed fake values written in the test itself (e.g. `"new-access"`), because those are not secrets.
- **Enforced by ESLint** for `tests/**` (`no-restricted-syntax` in `frontend/eslint.config.js`; `npm run lint`, which Frontend CI runs). An `expect()` whose subject or expected value is a variable, property, call or storage key named like token, password, secret or cookie fails the lint, awaited or not. The check goes by names, so name a helper after what it returns (`storedAuthKeys()` returns key names, not tokens). `src/test/secretAssertionRule.test.ts` keeps the rule working.
- Live specs keep traces, failure screenshots and videos off. Delete `frontend/test-results/` after a local live run. It is ignored by git and never uploaded: Frontend CI uploads only five summary text files.
- **If a secret was printed anyway:**
  1. Delete the output files.
  2. Revoke the token: `POST /api/v1/auth/logout` with it.
  3. Check that it is now refused.
  4. Report it.

## Future Expansion

When a seeded test backend is available, add E2E coverage for admin user management, manager document permission flow, staff document upload and chat, SSE success/error, citation display, logout/expired session, unauthorized direct route access, and mobile layout checks.
## Live UAT Suite

`npm run test:e2e:live` runs Playwright against a real frontend and backend. It requires `E2E_LIVE=true`, seeded UAT account passwords in environment variables, Docker Compose with `compose.uat.yaml`, PostgreSQL, Redis, API, worker, frontend, and the local deterministic UAT LLM provider.

The suite must not route/intercept API calls to fake responses. It may use backend API requests only for setup verification, ID lookup, and polling asynchronous document processing status.

`tests/e2e-live/smoke.spec.ts` is the redesign's smoke against a real backend, one test per role (staff: answered and refused questions, the opened citation highlights exactly the excerpt's text at the API's `evidence_spans` (BR-15), preview from a citation, no uploader names; manager: upload limited to PRIVATE or the own department, other scopes refused by the API; admin: names, audit filtered by `event_type`, system status), plus a session-boundary test: in one tab, without a reload, a manager loads a PRIVATE document and a chat, logs out, staff signs in, and a MutationObserver checks that no manager text is ever shown, transient frames included. A second session test covers a token refresh racing a logout: staff signs in, the browser clock is set 10 s before the access token's `exp` so the next question starts a real refresh, the server's answer is held until after Đăng xuất, and a reload must open the sign-in page with no `/auth/me` request. Token assertions compare key names only, so a failure never prints a token. `tests/e2e-live/deploy.spec.ts` checks what only shows behind a production build and its reverse proxy (DEMO.md): signing in works from the other loopback host name (`localhost` for a `127.0.0.1` base URL and the reverse) with every API request on the page's own origin (BR-13), SSE events arrive one by one and the stream closes (`stream.started` well before `message.completed`), a token refresh through the proxy keeps the session, the citation excerpts hold no Private Use Area code point (Symbol-font bullets drawn as boxes, BR-14), the cited PDF opens at its page (`?page=N`, `blob:` frame with `#page=N`, `application/pdf`), and a reload on deep routes serves the app for each role. Run it with `PLAYWRIGHT_BASE_URL` set to the proxy origin: `npx playwright test -c playwright.live.config.ts deploy --workers=1`. Run it with `E2E_LIVE=true`, the `UAT_*_PASSWORD` variables, `PLAYWRIGHT_BASE_URL` and `E2E_API_BASE_URL`: `npx playwright test -c playwright.live.config.ts smoke`. Traces, failure screenshots and videos are off in that spec so passwords never reach a file. It runs on Playwright's full Chromium build (`channel: "chromium"`, new headless), which has the PDF viewer the preview needs; the default headless shell shows an empty frame. The answerable question defaults to the public dev item ND-001 and can be changed with `SMOKE_ANSWERABLE_QUESTION`; each chat time (click to answer on screen) is appended to `timings.txt` in `SMOKE_SCREENSHOT_DIR`. `live-acceptance.spec.ts` (ported to the Vietnamese labels) keeps the flows the smoke does not cover. The unit test `src/app/sessionIsolation.test.tsx` checks the same session boundary with a fake `fetch`: the cache is empty when the next user's first request leaves.

### Run order on the demo stack

Right after `demo.ps1 reset`, run `deploy.spec.ts` **first**, before anything else asks a question, so the SSE check measures a real answer time. Then run `smoke.spec.ts` and `live-acceptance.spec.ts`.

- `demo.ps1 warmup`, which `reset` runs, already asks UAT Q016, Q027 and Q061 as staff. An answer the model has just given comes back in 1-3 s.
- So set `SMOKE_SSE_QUESTION` to a dev question that warmup does not ask (for example Q084 in DEMO.md). It defaults to `SMOKE_ANSWERABLE_QUESTION`.
- When `message.completed` arrives less than 2 s after `stream.started`, buffering cannot be told apart from streaming. The test still passes, but it marks the SSE check inconclusive: an `sse-inconclusive` annotation and an `SSE INCONCLUSIVE` console line. Report it as inconclusive, not as passed, and rerun after the next reset.
