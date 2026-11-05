# TASK-035.3F — backend, build and security verification

Date: 2026-10-14 (Asia/Saigon). **Independent static/host-unit evidence only.**
This is not a current candidate runtime gate or release sign-off. No backend
module, frontend production source, dependency lock, container, database,
Redis, migration or security setting was changed.

## Baseline protection

Git branch `main` remains dirty with pre-existing uncommitted H5.2 source and
release documents plus untracked experimental scripts/artifacts; no commit,
reset, tag or cleanup occurred. Checked source SHA-256 values match the 035.3E
checkpoint: grounded answer `4c9d4c648bbcef30a35c4e2ca01fad0093ed0e7a8aebb777dc78b478b345c919`,
context builder `26b2daafcc7da2448ba8933e6702e12cd58d880edb92b054edefb7dfe8884ab8`,
reranker `4fa1e470dfa097f3b881f9dfdaef3fb7771cd4953bfe99031c8b77dd882da8d0`,
and claim validator `d7e11c25b42d710b1a2ba4d325244adecb371c723dda9b3148b27bdc4f65b6e1`.
The 035.3B permission capture and historical V2 qualification hashes also
remain `b6e0f415...` and `4ebd7d1e...` respectively. The accepted V2 API,
worker, PostgreSQL and Redis containers remained up/healthy with IDs
`9d510d8b8027`, `2afc4af27fe5`, `1a5a658a2ef2`, `db2961fc9413`; local
image IDs for API and worker remain `sha256:1f057785...` and
`sha256:1e19725c...` respectively. The stopped 035.3B candidate was not
started. No protected runtime resource was a test target.

## Backend quality and dependency evidence

The host `.venv` is **Python 3.11.0**, whereas `pyproject.toml` requires
`>=3.12` and the preserved 035.3A candidate used Python **3.12.15**. Thus
host unit and dependency checks do not qualify candidate Python/package
behavior. `pyproject.toml` declares broad dependency lower bounds; it is not
a fresh-from-scratch resolved lock. The 035.3A local candidate lock is a
historical isolated snapshot, not a clean-room rebuild or current vulnerability
attestation.

| Check | Result | Scope/limit |
| --- | --- | --- |
| `ruff check --no-cache app` | **PASS** | 216 application Python files. |
| `ruff format --check --no-cache app` | **PASS** | 216 application Python files. |
| `ruff check --no-cache app tests .github/scripts` | **PASS** | Maintained app/tests/scan paths, excluding root scratch scripts. |
| `ruff check .` | **FAIL** | 24 errors in pre-existing untracked `tmp_*_trace.py` scratch files. No production module finding in the focused run. |
| `ruff format --check .` | **FAIL** | Existing `tests/unit/test_task0353c2f_eval_harness.py` plus two untracked scratch scripts; first run also showed a `.ruff_cache` access warning. No file was reformatted. |
| `ruff format --check --no-cache app tests .github/scripts` | **FAIL** | Only the existing 3C.2F experimental harness would be reformatted; app-only format passes. |
| `python -m compileall -q app` | **PASS on host 3.11** | Not candidate Python 3.12 syntax/runtime proof. |
| `python -m pip check` | **PASS on host venv** | No broken installed requirements; not a vulnerability audit or candidate lock comparison. |
| `pytest -q tests/unit` with the two known red contract modules explicitly excluded | **1423 PASS, 3 XFAIL** | Host 3.11, no integration marker/DB-cleaner path. Excluded 035.3E six newly exposed failures and 035.3C.2 eight known multilingual safety failures; therefore **not a full unit regression PASS**. |
| `.github/scripts/security_scan.py` | **PASS** | Bounded pattern scan plus production-debug rejection and Celery JSON-only checks. Not complete secret/SAST/dependency/image scanning. |

No integration/API suite against active V2 was run. CI tests that use
`tests/conftest.py` integration fixtures migrate and delete rows, so the
protected V2 database was explicitly excluded. The known 035.3B
unsupported-answer safety failure and 035.3E red tests remain open.

## Security configuration inspection

Auth dependencies decode Bearer JWT then load the active user from PostgreSQL;
role guards are server-side. Document/retrieval repositories apply READY and
permission filters. Static implementation and unit tests support these
contracts, but this run did not execute the full current RBAC/document/citation
matrix or candidate security smoke. `Settings` uses `SecretStr` for provider
keys, supports `*_FILE` mounts, validates production debug/placeholder secret/
database password/CORS/trusted-host/Redis settings, and rejects remote LLM/
web-search HTTP in production. The custom security scan passed its limited
rules. Logging redaction and content-free request metrics/audit metadata have
unit coverage; no new runtime log capture or privacy review was done.

Frontend `sessionStorage` retains bearer tokens (documented XSS exposure
trade-off). The fresh bundle pattern search found no named backend secret
markers, but source maps are generated and should be reviewed before public
serving. No real `.env`, secret value, database URL or private document text
was printed or uploaded.

`npm audit --offline --audit-level=high` reported **0 from local cache**;
this is **not** a sufficiently current advisory check. `SECURITY.md` records
a prior React Router advisory for the installed 7.18.2 range, so the local
offline zero does not resolve that documented risk. `pip-audit` is installed
but failed before scanning: its `pip_api` subprocess could not UTF-8-decode
the Windows path in `pip --version`. No backend vulnerability result is
claimed. No network advisory, image scan, malware scan, or comprehensive
secret scan was executed. Dependency vulnerability state is **UNKNOWN**.

## Docker and deployment contract

`docker compose --env-file .env.example -f compose.yaml config --quiet`,
production `config --quiet`, and production observability-profile
`config --quiet` all **PASS**. This validates syntax/interpolation using
examples, not production secrets or runtime startup. No image was rebuilt.

The backend runtime Dockerfile uses `USER app` UID 10001; frontend runtime
uses `USER node`; production app services have `no-new-privileges` and resource
limits. Production `volume-init` intentionally runs as root to set named-volume
ownership, a separately scoped startup privilege to review. PostgreSQL/Redis/
API/worker/Prometheus/Grafana share a private Compose `backend` network; only
the reverse proxy publishes a localhost host port by default. Development
Compose publishes API, PostgreSQL, Redis and frontend only on loopback.
Persistent PG/Redis/uploads/model volumes are declared. Healthchecks and
worker entrypoint are present; their behavior was not exercised in this run.

Image references use mutable tags (`python:3.12-slim`, `node:24-alpine`,
`pgvector/pgvector:pg17`, `redis:7-alpine`, `nginx:1.27-alpine` and application
tags), not registry digests. Production API/worker share one Compose image
reference, but the *active V2* API and worker still have different image IDs
and the documented source/package skew. The stopped 035.3B candidate's
same-source image evidence does not make the active V2 pair uniform or
authorize promotion. `FORWARDED_ALLOW_IPS` defaults to `*` in production
Compose while proxy headers are enabled; acceptable trust must be assessed
for the actual network/deployment topology. No change is made here.

The active Nginx config listens HTTP 8080 and blocks external `/metrics` in
configuration. The HTTPS example is disabled, no real certificate/key or
TLS handshake was verified, and the production host binding is loopback.
**PRODUCTION TLS: NOT VERIFIED.** `RELEASE_CHECKLIST.md` has a stale “no TLS/
reverse proxy” limitation while `DEPLOYMENT.md` requires TLS and proxy files
exist; this is a documentation conflict, not a waiver. `RELEASE_CHECKLIST.md`
also names obsolete migration head `20260722_0009`; the established current
head is `20260822_0011`. `README.md`/`SECURITY.md` retain historical freeze
and task-status claims that do not supersede the current RC NO-GO.

## Decision

Static application lint/format/compile, host dependency consistency, host
non-red unit tests and bounded security scan passed in the stated scopes.
Repo-wide lint/format **fail** on existing scratch/experimental files. Current
vulnerability, full security, production TLS, clean-room build, current
candidate integration and rollback evidence are absent. No new production
security defect was proven by this static task, but the known mandatory RAG
safety defect and active API/worker skew remain critical release blockers.
TASK-035 remains IN PROGRESS; RC decision remains NO-GO.
