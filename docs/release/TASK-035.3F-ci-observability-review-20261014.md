# TASK-035.3F — CI/CD and observability evidence review

Date: 2026-10-14. Source/config review only; no GitHub job, production stack,
Prometheus scrape, Grafana session or alert delivery was run.

| Criterion | Status | Verified source and remaining limit |
| --- | --- | --- |
| Backend automated quality | **PARTIALLY_VERIFIED** | `.github/workflows/ci.yml` has Python 3.12, PostgreSQL/Redis services, Alembic head check, Ruff, unit/API/integration/model marker suites, coverage, custom security scan, backend Docker build and Compose config. Workflow existence is verified; no current run on the dirty/uncommitted source was inspected. The newly added red 035.3E contract would fail if included in a current full unit run. |
| Frontend automated quality | **EVIDENCE_GAP** | Only one workflow file exists and it has no Node install, typecheck, ESLint, Vitest, Playwright, frontend build or accessibility job. Manual local 035.3F checks passed in their scopes but are not automated CI gates. |
| Dependency/image/secret scanning | **EVIDENCE_GAP** | Custom `security_scan.py` checks limited source patterns, production debug and Celery serializer. CI does not run a current package-advisory audit, container image scan, comprehensive secret scanner or SBOM verification. Mutable Docker/base tags and unpinned action major versions weaken immutable provenance. |
| Migration safeguards | **PARTIALLY_VERIFIED** | CI creates an isolated `enterprise_ai_ci` database, runs Alembic upgrade and compares current/head; this is a valid CI design, not a fresh production migration/rollback proof. No active V2 migration was run. |
| Deployment approval/CD | **EVIDENCE_GAP** | No deployment workflow, environment approval gate, signed release tag, image promotion or automatic rollback pipeline is present. This is consistent with the documented no-CD roadmap limitation; it is not an approved release deferral. |
| Health/readiness/worker | **PARTIALLY_VERIFIED** | Compose healthchecks, `/health/live`, `/health/ready`, and Celery inspect ping are configured. Accepted V2 containers were observed healthy read-only, but no new production-like failure-path/worker task gate was run. |
| Structured/content-safe logging | **PARTIALLY_VERIFIED** | `app/core/logging.py` redacts sensitive keys; request middleware logs request ID, route template, status and latency. Host unit/security scan passed. No current candidate log stream or red-team payload review was captured. |
| Metrics/trace hooks | **PARTIALLY_VERIFIED** | `/metrics`, `app/observability/metrics.py`, private-network Prometheus scrape config, Grafana dashboard/provisioning, request IDs and traceparent capture exist. No production scrape/dashboard history, retention/export verification, trace backend or SLO measurement was run. |
| Worker monitoring/alerting | **EVIDENCE_GAP** | Admin monitoring/Celery inspection code and healthcheck exist; no alert rule, alert delivery, on-call response, SIEM shipping or historical Celery-accounting proof. |
| Proxy/metrics isolation | **PARTIALLY_VERIFIED** | `deploy/nginx/conf.d/app.conf` returns 404 for `/metrics`; production Compose exposes only proxy host port by default. No live external access test or TLS handshake in this checkpoint. |

CI's `EMBEDDING_LOCAL_FILES_ONLY=false` can require model download during a
fresh CI run. Its backend Dockerfile also resolves broad PyPI requirements and
CPU Torch online unless a prebuilt local snapshot is used. Thus the workflow
does not prove a network-isolated clean-room rebuild or fixed wheel-byte
provenance. The 035.3A filtered build was isolated but used an existing local
base image; that result is preserved, not promoted into complete
reproducibility.

The `RELEASE_CHECKLIST.md` asks for lint/format, compilation, security scan,
dependency audit, tests, Docker build, and operational checks. This checkpoint
ran the non-mutating local subset. CI/static configuration is not operational
monitoring evidence. No alerting or CD requirement is invented beyond the
documented TASK-035 release coverage and the explicitly listed limitations.
Current RC remains NO-GO due to the independent unsupported-answer safety
failure, regardless of any CI/observability result.
