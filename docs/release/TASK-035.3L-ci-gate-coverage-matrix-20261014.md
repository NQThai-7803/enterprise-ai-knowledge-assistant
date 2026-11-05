# TASK-035.3L — CI gate coverage matrix

Date: 2026-10-14. The sole workflow is `.github/workflows/ci.yml`, SHA-256 `d2627b5d7042154757948a52736a7980b24e59f77d0e2322379b476ca9ee1264`. It is configured for every `push` and `pull_request` on `**`, job `backend` on `ubuntu-latest`, Python 3.12, `permissions: contents: read`. This review did **not** inspect a GitHub run or branch-protection rules; “required” below means command failure fails this configured job, **not** a verified required merge status. Current uncommitted source is not proven exercised in CI. `actions/checkout@v4`, `setup-python@v5`, `upload-artifact@v4`, service tags and online pip resolution are mutable inputs.

| # / gate | Configured command and trigger | Configured effect; actual execution / gap |
| --- | --- | --- |
| 1 Backend lint | `python -m ruff check .` on push/PR | Job-failing. No current CI run; known local full-tree 24-error FAIL, app-only PASS. |
| 2 Backend format | `python -m ruff format --check .` on push/PR | Job-failing. No current CI run; known local full-tree FAIL (3 files), app-only PASS. |
| 3 Backend unit | `coverage run --parallel-mode -m pytest tests/unit` on push/PR | Job-failing. No current CI run; broad unit suite not executed in this checkpoint. |
| 4 Backend integration | Separate API/integration/Celery/model marker `coverage run … pytest` commands, JUnit and coverage outputs | Job-failing. CI uses isolated `enterprise_ai_ci` DB/Redis design; no current workflow run or protected V2 integration run. Model download may be required. |
| 5 Red safety contracts | Included implicitly by `pytest tests/unit` if both contract modules are present in the committed checkout | Not excluded by YAML and would fail current full unit run; 035.3E has 6 and 035.3C.2 has 8 known red cases per 3F. No dedicated named gate, current CI run or guarantee untracked modules reach GitHub. **Must stay red/visible, not suppressed.** |
| 6 Frontend typecheck | None | No Node job; local `npm run typecheck` PASS only. |
| 7 Frontend lint | None | Local `npm run lint` 0 errors/7 warnings only. |
| 8 Frontend unit | None | Local `npm run test` PASS 8 files, 40/40 after redirecting sandbox temp to writable artifacts path. |
| 9 Frontend mocked-browser | None | Local `npm run test:e2e` PASS 15/15 Chromium against local mock server, `VITE_API_BASE_URL=http://127.0.0.1:9`; first sandbox startup attempt was stopped before collection. No live V2 E2E inference. |
| 10 Frontend production build | None | Local isolated `npm run build -- --outDir ../artifacts/task-035-3l-20261014/frontend-dist` PASS, 1,978 modules; not a candidate image or CI artifact. |
| 11 Dependency advisories | None | No npm/pip advisory gate. Targeted official checks found vulnerable frontend dev-tool lock versions; backend fresh audit failed DNS. |
| 12 Secret scan | `.github/scripts/security_scan.py` limited source-pattern/config checks | Job-failing if its narrow rules fail; local PASS. No comprehensive secrets-history/binary/manual publication review. |
| 13 Container advisories | `docker build --target runtime …` only | Builds backend, does not scan. No image vulnerability/SBOM gate. |
| 14 Migration safety | `python -m alembic upgrade head`; compare `alembic current`/`heads` on CI DB | Job-failing configured check, no current run. Not production rollback/data-migration proof. |
| 15 Lock integrity | None | Frontend uses lock in Docker `npm ci`, but CI never validates it; backend has no current exact lock. Local npm manifest↔lock root spec equality and installed tree checked, not CI. |
| 16 Artifact provenance | `actions/upload-artifact@v4` for reports/logs/coverage, `if: always()` | Evidence collection configured; no immutable source/image/model/wheel SBOM, signing/attestation or current run. |
| 17 Release approvals | None | No environment approval, release-owner decision or verified branch protection. TASK-035 remains NO-GO. |
| 18 Deployment rollback | None | No CD or rollback execution/verification gate; documented limitation, not approved deferral. |

Other configured checks: PostgreSQL pgvector creation/verification, Redis PONG, custom security script, backend Docker build, three Compose config variants. `EMBEDDING_LOCAL_FILES_ONLY=false` and broad online installs make CI dependent on mutable external resolution. `logs/`, JUnit and `coverage.xml` are configured uploads, but workflow configuration is **not proof of execution**. This checkpoint ran only local safe quality checks; exact commands/results are in the qualification summary. Branch required-status configuration and current remote run evidence remain unknown.
