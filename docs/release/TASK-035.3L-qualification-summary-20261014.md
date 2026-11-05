# TASK-035.3L — dependency security and CI qualification summary

Date: 2026-10-14 (Asia/Saigon). **TASK-035.3L COMPLETED as bounded evidence/plan; security, CI and RC qualification are NOT PASS.** HEAD `04ebd73aae737414fb591fe2e8b2c286134cdcd8`, dirty `main`, source selection READY_FOR_REVIEW only, versioning approval NOT GRANTED. Seven 035.3L reports were created; the original Git index, source, dependencies, lock, workflows, images and V2 services/data were not intentionally modified. Prior 035.3I/J/K source/historical evidence was not rewritten. The proposed source manifest now necessarily needs a future post-3L refresh and owner review; it is not silently extended.

## Results and commands

| Check | Actual local result and limit |
| --- | --- |
| Backend app lint/format | `.venv/Scripts/python.exe -m ruff check --no-cache app` PASS; `ruff format --check --no-cache app` PASS, 216 files. Full-tree Ruff remains historical **FAIL** (24 lint errors; three format files) and isolated 3K staging whitespace **FAIL** (15 findings/eight paths). |
| Backend compilation/integrity | In-memory `compile()` over 216 `app/*.py` files PASS on host Python 3.11.0; `python -m pip check` PASS; `python .github/scripts/security_scan.py` PASS narrowly. Not Python 3.12 candidate or a comprehensive security scan. No full pytest/API/DB integration suite run. Existing 035.3E six and multilingual eight red safety contract failures preserved, not excluded by proposed CI. |
| Frontend installed tree | Node 24.14.0/npm 11.9.0; `npm ls --all --json` zero problems; root `package.json` versus lock specs zero differences. Not an advisory result. |
| Frontend quality | `npm run typecheck` PASS; `npm run lint` PASS with 0 errors/7 warnings; Vitest `npm run test` PASS 8 files/40 tests after redirecting `TMP`/`TEMP` into ignored writable 035.3L artifacts. First attempt failed before collection on sandbox EPERM temp rename; not a test failure. |
| Mocked browser | `npm run test:e2e` PASS 15/15 Chromium on bounded retry, with `VITE_API_BASE_URL=http://127.0.0.1:9` (unused loopback port). Initial sandbox attempt never passed local server readiness and was stopped before tests. No protected V2 API targeted; no live integration conclusion. |
| Isolated frontend build | `npm run build -- --outDir ../artifacts/task-035-3l-20261014/frontend-dist` PASS, 1,978 modules, isolated output. Not a Docker image or release bundle approval. |
| Frontend advisories | Targeted fresh official checks: Router 7.18.2 not affected by checked RSC-CSRF advisory; five dev-only lock entries match seven distinct advisories across `brace-expansion@5.0.8`, `nanoid@3.3.16`, `vite@8.1.5`, `vitest@4.1.10` and `@vitest/mocker@4.1.10`. Production exploitability not established. Full 350-entry fresh audit **NOT VERIFIED**. Cached `npm audit --offline` zero is not clearance. |
| Backend advisories | `pip-audit 2.10.1` import/path issue mitigated by `PYTHONIOENCODING=utf-8` for version invocation; public-only 20-direct-pin query with `--no-deps --disable-pip` failed on `pypi.org` DNS. Full/partial report **NOT VERIFIED**. Pillow 12.3.0 is outside one checked affected range; PyMuPDF potential applicability unresolved. |
| Image advisories | No installed safe scanner or full image bytes/SBOM; **NOT VERIFIED**. Read-only protected-container status/identity only. |
| CI | One backend workflow statically reviewed; no current remote run or branch required-status evidence. Backend commands configured, frontend/advisory/image gates absent; custom security script is narrow. |

## TASK-035 acceptance traceability

“Prior” distinguishes the 2026-10-13 035.2 matrix from later 3F–3K effective qualifications; no historical row was rewritten. All checks here were local/static, not an accepted same-source RC runtime gate.

| Criterion | Prior effective status | 3L check/environment/evidence | Current justified status; remaining work/approval |
| --- | --- | --- | --- |
| B19 | Historical V2 PASS; current RC FAIL in 3F–3K | No RAG runtime; red safety coverage inspected in CI YAML and unit file paths | **OPEN/FAIL**; generic safety fix, red contracts and new candidate runtime gate, no deferral. |
| B21 | Historical V2 PASS; current RC materiality FAIL in 3F–3K | No citation runtime check | **OPEN/FAIL** for current RC; same-source citation/safety requalification. |
| B26 | 035.2 EVIDENCE_GAP | `.github/workflows/ci.yml` static map; safe local subset above | **EVIDENCE_GAP**; frontend/security jobs, actual CI run and owner required-status review. |
| P14 | 035.2 NOT_RUN; 3G/3H local qualified in scope | Local TS/lint/Vitest 40/40/mocked Chromium 15/15/build PASS | **PARTIALLY_VERIFIED locally**; no current CI or live frontend candidate/V2 evidence. |
| R03 | 035.2 CONFLICT | Narrow scan PASS; 3K owner-review 103 paths and manual privacy/rights not resolved | **OPEN/CONFLICT**; publication and secrets review/owner decision. |
| R05 | 035.2 FAIL; 3K UNRESOLVED | Read-only API/worker image ID comparison; different IDs, prior 8 source/22 package version differences | **UNRESOLVED/FAIL**; approved same-source rebuild/deploy qualification. |
| R06 | 035.2 EVIDENCE_GAP; 3K approval NO | HEAD/status and 3J/3K manifest review | **EVIDENCE_GAP**; owner source/Gitlink decision, explicit versioning approval; no staging. |
| R07 | 035.2 EVIDENCE_GAP | Local report/artifact creation only | **EVIDENCE_GAP**; off-host access-controlled evidence backup and restore verification. |
| R09 | 035.2 EVIDENCE_GAP | Lock/base/CI provenance inventory | **EVIDENCE_GAP**; exact backend lock/wheel/model/base bytes, SBOM, clean independent build. |
| R18 | 035.2 EVIDENCE_GAP; later 3F–3K safety OPEN/FAIL | Narrow scan and targeted advisories, no full secret/image/backend audit or current security runtime | **OPEN/FAIL for current RC**; safety remediation plus security evidence/owner review. |
| R19 | 035.2 NOT_RUN; 3G/3H local partial | Local mock frontend suite and isolated build PASS | **EVIDENCE_GAP for candidate/live**; CI and approved live role-flow/accessibility gate. |

## Decision

Current confirmed locked vulnerable package versions warrant review, but their dev-only paths and exploit preconditions must not be conflated with deployed exposure. Backend and image packages remain largely unverified, not secure by omission. New 3L findings do **not** override the independently mandatory RAG safety and API/worker skew blockers. No release deferral is approved; TASK-035 remains **IN PROGRESS**, RC **NO-GO**. Next: owner/security triage of exact advisory exposure and proposed audits/CI, resolve source/versioning and Gitlink gate, remediate safety and image skew in a separately authorized candidate, then execute required current gates.

Companion reports: `TASK-035.3L-dependency-inventory-provenance-20261014.md`, `TASK-035.3L-frontend-dependency-advisories-20261014.md`, `TASK-035.3L-backend-dependency-advisories-20261014.md`, `TASK-035.3L-container-base-image-security-20261014.md`, `TASK-035.3L-ci-gate-coverage-matrix-20261014.md`, and `TASK-035.3L-prioritized-security-ci-remediation-plan-20261014.md`.
