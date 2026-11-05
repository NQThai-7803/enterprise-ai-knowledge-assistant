# TASK-035.3G — frontend API origin and bundle exposure

Date: 2026-10-14. Read-only source and local artifact review. No production
frontend, external URL, or active V2 API was contacted. Git HEAD at baseline:
`04ebd73aae737414fb591fe2e8b2c286134cdcd8`; the accepted working tree is
dirty. Frontend package-lock SHA-256 remains
`1fdf9b6d438cedc1f4027a43195407bcc1f2363f4acac50862f3403c6aa195d5`.

## API-origin chain

`frontend/src/lib/config.ts` reads `import.meta.env.VITE_API_BASE_URL` at
build time, trims trailing slashes, and falls back to
`http://127.0.0.1:8000`. No runtime configuration loader was found.
`frontend/.env.example`, `frontend/Dockerfile` build ARG, and optional
`compose.yaml` frontend build ARG use the same local fallback. No
`frontend/.env*` file other than `.env.example` was present and the checked
process had no `VITE_API_BASE_URL` variable. The new local bundle contains the
loopback literal; this is attributable to the **development/default build
configuration**, not evidence that a production deployment uses it.

`frontend/src/api/client.ts` constructs `/api/v1` URLs from this base for
authentication, document upload/status, chat, feedback, audit and other JSON
requests; `/health/live` and `/health/ready` omit the prefix. It attaches a
Bearer access token where required and performs one refresh/retry on 401.
`frontend/src/api/sse.ts` uses the same base for authenticated POST
`/api/v1/chat/sessions/{id}/messages/stream`. Tokens live in `sessionStorage`
per `frontend/src/api/tokenStore.ts`; this is not a backend authorization
boundary. A browser on a different host cannot use its own loopback to reach
this server. The intended production API origin/domain and TLS endpoint are
not recorded here and must be chosen and verified before deployment.

`compose.prod.yaml` defines backend API and HTTP Nginx reverse proxy but no
frontend service. `deploy/nginx/conf.d/app.conf` forwards `/` to backend API,
not frontend assets. The optional development frontend in `compose.yaml` is
host-loopback-bound. Therefore no repository evidence establishes a deployed
production frontend origin or same-origin routing contract. This is a
**configuration risk / deployment evidence gap**, not a demonstrated
production misconfiguration. No production domain is inferred.

## Bundle and source-map inspection

The 035.3F output remains under
`artifacts/task-035-3f-20261014/frontend-dist/`. A new isolated build wrote
only to `artifacts/task-035-3g-20261014/frontend-dist/` (the Vite outDir was
outside the project root and was not emptied automatically). Vite 8.1.5
transformed 1,978 modules; output is HTML 0.47 kB, CSS 23.83 kB, JS
411.05 kB and JS map 1,614.25 kB. New SHA-256:

| File | SHA-256 |
| --- | --- |
| `index.html` | `0ca1ed4ec5795fe62c158ce2794b36b328ffa0b426da3c7c71491798fca2bf4f` |
| `assets/index-D8LSrnmb.css` | `5ce03a2b9ab8936b7ed5bf225002bfc74aef3c9f491f7816a052a4148a9f3312` |
| `assets/index-DIjLj-_9.js` | `49e5eb356861078379239b12220072e41e44717c60d31003f207c938ee984c51` |
| `assets/index-DIjLj-_9.js.map` | `f1322d0e93455b78091f177cd15c37acbefeadcc752f021a445d251800c9bc76` |
`frontend/vite.config.ts` sets `build.sourcemap: true`; the JS ends with a
`sourceMappingURL` reference. The map contains 136 source entries and all
136 `sourcesContent` entries (1,104,708 characters), including 42 paths under
`frontend/src/`. Paths are relative; no absolute drive/UNC/root source path
was found. No test/spec, `.env`, or `tmp_*` source path was found in this map.
This exposes implementation detail if served, regardless of whether it
contains credentials. The local `frontend/server.mjs` serves existing files
under `dist` without a `.map` deny rule, and `frontend/Dockerfile` copies the
whole `dist` directory into that server image. Thus **a frontend deployment
using that image/build would serve the map**; no externally accessible
frontend deployment or public URL was tested. Production Nginx in this repo
does not serve these assets.

The checked JS contains the public loopback API URL. A pattern scan of the
new built output found no `SECRET_KEY`, `DATABASE_URL`, `POSTGRES_PASSWORD`,
`LLM_API_KEY`, or `redis://` marker. No actual sensitive credential was
identified; this narrow scan is not a comprehensive secret audit. Public
`VITE_*` settings are expected in browser assets. Vendor source and relative
application source are internal implementation details, not secrets by
themselves. No generated output appeared to include tests or scratch traces.

Disposition: choose an approved reachable API origin at build time and a
source-map serving policy before any frontend deployment. This report makes
no configuration edit, secret-leak claim, or TLS/live-E2E claim.
