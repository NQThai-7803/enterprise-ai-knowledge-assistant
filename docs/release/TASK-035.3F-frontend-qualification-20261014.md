# TASK-035.3F — independent frontend qualification

Date: 2026-10-14 (Asia/Saigon). Scope: current `frontend/` working tree with
already-installed dependencies. This is **not** an integrated RC frontend or
live V2 acceptance. No production frontend source or lockfile was changed.

## Contract and baseline

`TASKS.md` TASK-028, `README.md` frontend quality gates, `frontend/package.json`,
the 035.2 matrix P10–P14/R19, `FUNCTIONAL_REQUIREMENTS.md`, and
`RELEASE_CHECKLIST.md` require a typed API client, login/protected/role-aware
navigation, document/chat/citation/feedback/admin flows and current quality
and browser evidence. The React UI is not the security authority: backend
RBAC and citation checks remain mandatory. Existing `frontend/node_modules`
and `package-lock.json` were used; no install, upgrade or audit-network call
was made. Node `v24.14.0`, npm `11.9.0`; package-lock SHA-256
`1fdf9b6d438cedc1f4027a43195407bcc1f2363f4acac50862f3403c6aa195d5`.

## Executed checks

| Check | Result | Evidence and qualification |
| --- | --- | --- |
| `npm run typecheck` | **PASS** | Both `tsconfig.json` and `tsconfig.node.json` completed. |
| `npm run lint` | **PASS with 7 warnings** | Zero errors; five hook dependency warnings plus React Compiler incompatible-library warning and another hook warning in `ChatPage`, `DocumentPermissionsPage`, `DocumentUploadPage`. These are not silently labeled clean. |
| `npm run test -- --run` | **PASS 36/36, 7 files** | Initial sandbox run failed before tests (`EPERM` renaming a sandbox temp file). An authorized unsandboxed rerun using the same installed dependencies completed. Initial failure was infrastructure, not a passing first run. |
| `npm run test:e2e` | **PASS 9/9 mocked Chromium tests** | Local Vite server, intercepted API responses; unauthenticated routing, form validation, reduced-motion mobile login, Admin/Staff navigation, mobile menu, mocked SSE/citation rendering, and mocked admin user/department operations. It did not call V2 or the failed candidate. |
| `npm run build -- --outDir ../artifacts/task-035-3f-20261014/frontend-dist` | **PASS** | Typecheck plus Vite 8.1.5, 1,978 modules, bundle 411.05 kB JS / 23.80 kB CSS. New isolated output directory, not `frontend/dist`. |
| Installed dependency tree | **PASS for local consistency** | `npm ls --depth=0` exited 0; this is not vulnerability or clean-room install evidence. |

Build artifacts: `artifacts/task-035-3f-20261014/frontend-dist/`.
SHA-256: `index.html` `1b833f284ce8a1d30aa2a723b82d68d74eb0fec5badd5c7da81bed517b9edf3e`;
`index-CLGKBjLe.js` `b7da151c971806e1969e093afac0bc3a49d1109f0b8a4c74c39b38d72a27e5db`;
`index-Ccq93-Z4.css` `d81c980750ff91eeb143c7caedd2c6d0527adc85c68bb9daab8acc9755899448`.
The output also contains a JS
source map because `frontend/vite.config.ts` sets `build.sourcemap: true`.

## Interface and security inspection

`frontend/src/app/App.tsx` declares protected routes for chat, documents,
upload, permissions, users, departments, feedback, audit, system and profile;
`ProtectedRoute` and `AppShell` enforce/hide role-aware UI routes. Auth uses
`frontend/src/api/tokenStore.ts` sessionStorage, `frontend/src/api/client.ts`
Bearer headers/refresh/logout and safe error mapping. Document pages include
list/detail/upload/permission workflows. `ChatPage` and `sse.ts` handle
normalized stream events, citation display and feedback; chat content renders
as text rather than raw HTML. Frontend API configuration is only
`VITE_APP_NAME` and `VITE_API_BASE_URL` in `src/lib/config.ts`; a pattern search
of the built output found no `SECRET_KEY`, `DATABASE_URL`, Redis URL,
`LLM_API_KEY` or `POSTGRES_PASSWORD` marker. This is a narrow pattern check,
not a complete secret audit or a proof that browser token storage has no XSS
risk.

The isolated build used the default `VITE_API_BASE_URL=http://127.0.0.1:8000`,
and that literal is in the generated bundle. It is suitable for the documented
local setup, but **must not be promoted unchanged to a remote production
browser** without an approved reachable API origin. The production frontend
Dockerfile also defaults to that URL at build time. Because the production
bundle includes a `.js.map` and the static server serves files under `dist`,
source-map exposure should be reviewed for the intended deployment. These are
configuration/privacy review risks, not a demonstrated secret leak.

Accessibility evidence is limited: accessible status and role-name assertions,
mobile layout and reduced-motion behavior are tested. No axe/WCAG audit,
keyboard-wide screen-reader review, or dedicated accessibility CI gate was
found. **Accessibility qualification is EVIDENCE_GAP**, not PASS.

## Acceptance boundary

Static typecheck, lint, unit, mocked browser and build checks passed in their
scopes. No current live frontend-to-backend flow on a same-source candidate,
real authentication/refresh/logout, upload→READY, chat/SSE/citation, feedback,
audit, or production API-origin/TLS behavior was exercised. P10–P14/R19 gain
new source/mock evidence but remain **EVIDENCE_GAP** for their live or broader
acceptance portions. The mandatory unsupported-answer safety blocker is
unaffected; RC remains NO-GO.
