# TASK-035.3F — prioritized remaining RC verification plan

Date: 2026-10-14. **RC NO-GO**. This plan does not approve a deferral, narrow
the product, authorize a source change/build/restart, or mark TASK-035 complete.
The failed 035.3B candidate and accepted H5.2 V2 baseline remain preserved.

## Independent gate classification

| Group | Safely executable in 035.3F and result | Still requires another scope/authorization |
| --- | --- | --- |
| A. Frontend build/static | Typecheck, ESLint and isolated bundle build PASS (lint warnings retained). | Production API origin, served bundle/TLS and same-source deployment verification. |
| B. Frontend tests/accessibility | Vitest 36/36 and mocked Chromium 9/9 PASS. Limited role/mobile/reduced-motion assertions. | Current live frontend↔backend E2E, upload→READY, auth refresh/logout, feedback/audit, accessibility/keyboard/screen-reader audit. |
| C. Backend static/dependencies | App-only Ruff/format, host 3.11 compile, `pip check`, 1423 non-red host units PASS; broad Ruff/format FAIL on pre-existing scratch/experimental files. | Candidate 3.12/full red-contract regression, package advisory freshness and exact source/lock qualification. |
| D. Security/secrets | Limited repository security scan PASS; server-side RBAC/config/log redaction inspected. | Full current isolated security/RBAC/privacy smoke, comprehensive secret/advisory/image scan, data-class/retention owner decision. |
| E. Docker/image | Development/production/observability Compose syntax PASS; Dockerfile, privileges, volumes, network and healthchecks reviewed. | Same-source image build/repro, production-like startup, image scan, rollback and active API/worker skew resolution. |
| F. CI/CD | Backend workflow configuration reviewed. | Current versioned candidate CI run; frontend/security/advisory/image gates and release approval/CD design. |
| G. Logging/metrics | Source/unit/config reviewed; private scrape and dashboard defined. | Live redaction/non-disclosure, Prometheus scrape, alerts, worker monitoring and retention evidence. |
| H. Deployment docs/env | Contradictions identified, not rewritten; example Compose interpolation passes. | Current head/version/TLS/freeze documentation reconciliation and production secret/origin review. |
| I. Integration/runtime | **NOT_RUN** against protected V2 or failed candidate. | Isolated auth/RBAC/ingestion/SSE/frontend/security, candidate TLS, performance, restore/rollback and broad acceptance after explicit runtime authorization. |
| J. Release decisions | Seven pending deferral proposals, Q018 authority, original TASK-034.1 matrix, privacy and off-host DR identified. | Product/security/operations/release-owner decisions; no automatic approval or weakening of mandatory RAG safety. |

## Prioritized blockers and risks

1. **P0 — mandatory application safety FAIL.** 035.3B STAFF request returned
   an irrelevant cited ANSWERED instead of NO_ANSWER. 035.3E found no
   defensible generic context-admission correction and the separate final
   responsiveness gap remains. B19 and current question-materiality B21 are
   open. Requires a separately authorized evidence-backed mechanism, then
   source correction and a *new* candidate with negative/positive multilingual,
   permission, condition, polarity, multi-document and citation gates. The
   frozen failed candidate cannot be promoted.
2. **P0 — candidate identity/reproducibility FAIL/GAP.** Active V2 API/worker
   images differ, with documented source/package skew; accepted source is
   uncommitted and key artifacts remain local/ignored. 035.3A's same-source
   isolated candidate later failed safety. A reviewed versioned source/lock,
   exact image/model provenance and separate build/promotion authorization are
   required *after* the safety design gate.
3. **P0 — production security/owner decisions.** Real TLS is NOT VERIFIED;
   production secrets, external-provider residency, plaintext data, PII
   masking/retention, malware scanning and off-host DR have no current owner
   disposition. Seven deferral proposals remain PENDING_REVIEW; approved
   deferrals **0**. No mandatory RAG safety deferral is proposed.
4. **P1 — verified local quality gate failures, not newly proven app defects.**
   `ruff check .` reports 24 errors in pre-existing untracked `tmp_*_trace.py`;
   repo-wide format check flags those and an existing 3C.2F harness. App-only
   lint/format passes. The exact files to version, exclude or repair need a
   reviewed source hygiene decision; this task did not alter them.
5. **P1 — frontend operational evidence gap.** Source/unit/mocked browser/build
   checks pass, but no real backend E2E, comprehensive accessibility audit or
   production-origin check. The locally built bundle embeds loopback API URL;
   source maps are generated. These are deployment/configuration review risks,
   not proof of an exposed secret or a failed live flow.
6. **P1 — dependency/CI security evidence gap.** Offline npm audit reports
   zero from local cache but does not settle the prior React Router advisory;
   host `pip-audit` failed before scanning due Windows path decoding. No fresh
   backend advisory feed, image vulnerability scan or comprehensive secret
   scan. CI covers backend only and no current dirty-tree workflow result was
   inspected. No release CD/approval pipeline exists.
7. **P1 — integration, recovery and performance gaps.** Full RBAC, upload and
   worker lifecycle, SSE, candidate frontend, rate limits, safe errors, TLS,
   backup/restore/rollback and stated CRUD/retrieval component targets remain
   unverified on a new qualified candidate. Historical Celery task accounting
   remains UNKNOWN; Q018 policy authority unresolved but safe abstention is
   preserved. Do not use end-to-end chat p95 as the documented component SLO.
8. **P2 — observability and documentation.** Configured metrics/health/logging
   are not live alert/retention/incident evidence. README, SECURITY and release
   checklist have stale task/freeze/migration/TLS statements; reconcile with
   release owners without rewriting the contract to match convenience.

## Safe next independent work, without touching V2

- Review the current static frontend bundle/API-origin/source-map policy and
  perform local mocked keyboard/accessibility checks using existing tools;
  do not assert WCAG compliance without a documented method.
- Review/version or explicitly exclude scratch files so a *reviewed* source
  snapshot can run `ruff check .` and format checks cleanly. Any cleanup or
  source mutation requires its own request; preserve the present dirty tree.
- Prepare a fresh, privacy-safe dependency advisory plan and CI frontend gate
  proposal. Network advisory queries, dependency installation and workflow
  edits are not authorized by this report.

After an approved safety correction and new same-source candidate exist, run
the isolated live/frontend/security/TLS/recovery/performance and broad V2
acceptance gates in the documented release order. Those are **not** part of
this 035.3F static/mock checkpoint. TASK-035 remains IN PROGRESS; RC NO-GO.
