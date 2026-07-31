# Release Checklist

Use this checklist before treating the backend MVP as release-ready for a production-like environment.

## Configuration

- [ ] `APP_ENV=production` is set for production runtime.
- [ ] `APP_DEBUG=false` or `DEBUG=false` is set.
- [ ] `SECRET_KEY` is a generated non-placeholder secret.
- [ ] `DATABASE_URL` contains a non-placeholder password and does not appear in logs.
- [ ] Redis URLs do not use localhost in production.
- [ ] `API_DOCS_ENABLED` follows the environment policy.
- [ ] Production CORS origins are explicit, reviewed, and contain no path/query/fragment.
- [ ] `TRUSTED_HOSTS` contains the expected production hostnames and no wildcard.
- [ ] Rate limits are enabled and sized for expected traffic.
- [ ] LLM provider settings and data residency have been reviewed.

## Database And Data

- [ ] Alembic migrations are applied.
- [ ] Alembic current revision equals head `20260722_0009`.
- [ ] PostgreSQL backup was created and restored on an isolated stack.
- [ ] Upload volume backup was created and restored on an isolated stack.
- [ ] Restored stack can download an existing Document and process a new upload.
- [ ] Plaintext DB fields and lack of PII masking are accepted for MVP scope.

## Runtime

- [ ] Docker images build successfully.
- [ ] API and worker containers run as non-root.
- [ ] Compose application services use `no-new-privileges:true`.
- [ ] No `.env`, upload data, model cache, Docker socket, or host root path is baked or mounted unsafely.
- [ ] API liveness and readiness checks pass.
- [ ] Celery worker health check passes.
- [ ] Logs were reviewed for secrets, questions, answers, document text, feedback reason, and citation excerpts.

## Verification

- [ ] `python -m ruff check .` passes.
- [ ] `python -m ruff format --check .` passes.
- [ ] `python -m compileall app` passes.
- [ ] `python .github\scripts\security_scan.py` passes.
- [ ] `python -m pip check` passes.
- [ ] Dependency audit reports no known vulnerabilities or documented accepted findings.
- [ ] Unit tests pass.
- [ ] API tests pass.
- [ ] Integration tests pass.
- [ ] Marker suites pass or have documented unavailable external/model dependencies.
- [ ] End-to-end smoke test covers login, admin setup, upload, processing READY, permissions, chat, citations, feedback report, and audit report.
- [ ] Security smoke test covers oversized request, invalid PDF signature, untrusted host, unknown CORS origin, login/chat rate limits, unsafe production config, safe 500, RBAC, and ownership isolation.

## Known MVP Limitations

- [ ] No malware scanning.
- [ ] No automatic chat/audit retention cleanup.
- [ ] No feedback deletion workflow.
- [ ] No PII masking.
- [ ] No TLS/reverse proxy, production secret manager, SIEM, Kubernetes, Terraform, or CD automation in this roadmap.
