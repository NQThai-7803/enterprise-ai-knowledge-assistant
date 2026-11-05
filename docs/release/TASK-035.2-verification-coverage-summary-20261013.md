# TASK-035.2 verification coverage summary

Version 1.0, 2026-10-13. This document accompanies the [acceptance traceability matrix](TASK-035.2-acceptance-traceability-matrix-20261013.md) and [deferral register](TASK-035.2-release-deferral-register-20261013.md). No acceptance, integration, frontend, security, Docker-recreation or recovery drill was executed for TASK-035.2. The current H5.2 V2 artifacts were inspected, not rerun.

## Matrix quality-control result

- **80 criteria** mapped across every TASK-001–034 parent plus TASK-035 release gates. TASK-030 is included despite conflicting completion statements; TASK-034.1 is reviewed separately because its original strict report is incomplete, not a completed task. TASK-028.1 localization is historically deferred, not silently counted completed.
- Status counts: **PASS 9; FAIL 1; NOT_RUN 17; EVIDENCE_GAP 43; CONFLICT 7; DEFERRAL_PROPOSED 3.** No aggregate pass percentage is used. Approved deferrals: **0**.
- All 80 matrix rows have unique IDs and all 15 requested fields. Every TASK-001–034 ID occurs. No row is promoted to PASS solely from a “Completed” label, HTTP 200, existing source/test files, or old unit results.
- The nine PASS rows are scoped: isolated backend/config health and persistence (B01/B02/B25/P32), V2 embeddings and grounded/cited answers (B14/B19/B21), local guarded backup/restore evidence (P31), and the fact that TASK-035 is not prematurely marked complete (R04). P31 does **not** satisfy off-host DR (R08) or RC rollback (R16).
- The **FAIL** is R05, the proven API/worker candidate source/dependency skew. **CONFLICT** includes TASK-030 status, unsupported freeze/version claims, stale migration documentation, Q018 authority and the unresolved relation of the original TASK-034.1 track to V2. `DEFERRAL_PROPOSED` entries are review requests, not approval.
- Source and evidence references were checked against current repository paths where available. Git-ignored artifacts are local. Historical TASKS/PROJECT_STATUS verification statements predate the final V2 API image and remain labeled `old` in the matrix. Criterion bundles for TASK-001–025 reflect their documented deliverables, not invented per-task acceptance thresholds.

## TASK-034.1 strict lane versus RAG-H5.2 V2 — criterion by criterion

The original `artifacts/task-034-1/real-llm-acceptance-report.json` is `IN_PROGRESS`, with 20 named cases and empty result fields, using `qwen3:4b` and two unseen synthetic documents. The H5.2 V2 report uses `qwen2.5:3b`, nine permanent V2 documents, 98/98 supported manually reviewed material answers, and a different acceptance runner/corpus. “Overlaps” means relevant evidence exists for the V2 scope, **not** equivalence or completion of the original strict lane. Contract: `TESTING_STRATEGY.md:489-525` and `README.md:275-314`.

| Original strict criterion | V2 comparison | Classification | Remaining action/decision |
| --- | --- | --- | --- |
| Authentic real local LLM, not deterministic fake provider | V2 ran Ollama `qwen2.5:3b`; original report specifies Ollama `qwen3:4b`. | Identical principle; different model | Decide whether provider/model substitution is acceptable. |
| Newly uploaded unseen documents processed READY | Original two Atlas/Beacon synthetic PDFs were reported READY; V2's nine recovered/selected permanent documents were separately ingested READY. | Different corpus/protocol | Do not claim unseen-document matrix complete from V2. |
| Exact fact, number, date and named entity with material citations | V2 broad manually checked all supported propositions and citations, including people, dates, amounts and policy scope. | Overlapping, V2 PASS | Map individual original cases if substituting; original result cells are blank. |
| Conditional rule and exception | V2 review checked conditions, exceptions, units and negative obligations. | Overlapping, V2 PASS | Map case IDs/claims; no blanket strict-lane PASS. |
| Multi-source synthesis and paraphrase | V2 broad and six-case smoke cover cross-document claims. | Overlapping, V2 PASS | Confirm exact original scenarios if substitution proposed. |
| Unsupported fact, hallucination trap and false premise | Q100 unsupported abstention and Q018 conflict abstention passed; final broad reported no unsupported additions. Specific original traps are not enumerated as run. | Partially overlapping | Run or map each trap/false-premise case. |
| Cross-document contamination | V2 material-source audit found no unrelated citation in final broad capture. | Partially overlapping | Check original contamination scenarios separately. |
| Existing work/leave/Nova regressions | V2 covers organization, schedule, leave and related corpus questions. | Overlapping but dataset/version differs | Source/case mapping by product owner. |
| Same-session memory without other-session leakage | V2 qualification does not document an equivalent live same-session/cross-session gate. | Different/unverified | Isolated conversation-memory API/live test. |
| Non-streaming versus SSE streaming parity | V2 broad is not an SSE parity acceptance run. | Different/unverified | Current-candidate streaming parity and timeout gate. |
| Organization, department, private, direct and revoked grant isolation | V2 safety smoke covered manager private grant and staff private 404; not full department/revoked matrix. | Partially overlapping | Isolated full permission matrix. |
| Provider unavailable, timeout, malformed response and invalid markers | V2 broad reports zero timeouts, not injected failure cases. | Different/unverified | Isolated fault-path tests. |
| Content-free logging and safe metrics | Historical TASK-034 tests exist; V2 semantic qualification did not rerun this strict lane. | Different/unverified | Current security/observability review. |
| Manual claim-by-claim support | V2 final 98 supported answers were manually checked against material citations; original 20 case claim entries remain empty. | Overlapping principle, different report | Product/release owner decides criterion-level equivalence; no automatic supersession. |

**Decision reserved:** the product/release owner must decide whether each overlapping criterion may adopt V2 evidence, whether model/corpus differences matter, and which distinct cases must run. The original report cannot currently be marked complete. The final V2 result remains valid within its own scope.

## Test and evidence coverage by execution lane

| Lane / source | Already verified | Needed next; safe environment | Gate type |
| --- | --- | --- | --- |
| V2 RAG: `artifacts/uat-corpus-v2/h5-2-qualification-20261013.md`, broad/safety/repeat/restore captures | Exact final API image: 98/98 supported material answers, 101/101 citation identities, Q018/Q100 safe abstentions, 6/6 safety, 9/9 repeat, prior restored-corpus smoke 6/6. | Preserve evidence; do not rerun to substitute for unrelated gates. | Existing scoped PASS |
| Backend unit/API: `tests/unit/`, `tests/api/`, `.github/workflows/ci.yml` | 467 relevant unit tests and Ruff/compile reported in final H5.2; historical TASK-024/034 broader suites. | Current candidate unit/API contract/security suites; no active V2 DB writes. | Focused retest |
| Isolated DB/integration: `tests/integration/`, `tests/api/*` integration markers | Historical auth/document/chat/citation/feedback/audit/worker suites and V2 corpus behavior. | Separate disposable test DB; verify target before any `pytest`, because `tests/conftest.py:45-107` runs Alembic and deletes data. | Isolated integration |
| Worker/ingestion: `test_document_worker_transitions.py`, `test_end_to_end_document_processing_pipeline.py`, `test_processing_pipeline_celery.py` | Nine V2 docs READY and worker healthy; task source matches. | Reconcile image/package skew first; run READY/FAILED/retry/reprocess and enqueue failure on isolated stack. | Blocked by candidate identity |
| Frontend: `frontend/package.json`, `frontend/src/**/*.test.*`, `frontend/src/test/e2e/`, `frontend/tests/e2e-live/` | TASK-028 historical lint/typecheck/Vitest/build/mock/live E2E claims. | Current lint/typecheck/Vitest/build; role-aware auth/doc/chat/citation/feedback/admin E2E on isolated backend. Active V2 stack has no frontend service. | Frontend validation |
| Security: `RELEASE_CHECKLIST.md`, `SECURITY.md`, `.github/scripts/security_scan.py`, RBAC/citation tests | Historical hardening, TASK-034 metrics/log tests; V2 grant/denial smoke. | Current secret/content log scan, dependency audit, RBAC/cross-user/citation, upload/rate-limit/CORS, production TLS/proxy/container review. | Security review |
| Operations: `compose.prod.yaml`, `deploy/nginx/`, `scripts/backup/`, `TESTING_STRATEGY.md:450-485` | TASK-034 historical prod stack/failure-recovery; local V2 backup package and independent restore smoke; Redis cutover integrity. | Candidate prod-like config/build/health, guarded fresh restore, failure/recovery and rollback drill under separately authorized operational scope. | Deployment/DR drill |
| Performance: `NON_FUNCTIONAL_REQUIREMENTS.md:16-22` | V2 end-to-end chat latency measured, zero app timeouts. | Separate CRUD p95 and retrieval-only local/demo timing; do not compare chat p95 to these targets. | Performance measurement |
| Release authority: deferral register | No deferrals approved; Q018 safely abstains; historic Celery unknown. | Decide TASK-034.1 equivalence, off-host DR, privacy/TLS, Q018 precedence/abstention and residual operations risks. | Human approval |

## Gaps and handoff

Critical unresolved items are the proven API/worker skew, current RBAC/citation/security breadth, production TLS, candidate rollback, source/evidence/build reproducibility and explicit privacy/data-protection decisions. The documented local backup/restore and Redis recovery evidence should be reused without claiming off-host or historical Celery proof. Stale `v1.0.0-rc1`, migration and roadmap/checklist assertions need later authorized reconciliation; they were not edited in TASK-035.2.

The contracts themselves leave some acceptance detail unspecified: TASK-001–025 provide deliverables rather than atomic pass/fail thresholds; TASK-030's task block and later project summary disagree on completion; the target RC deployment environment and off-host backup retention/RTO/RPO are not specified; and the V2 report explicitly found no repository-defined end-to-end chat p95 ceiling. These are specification gaps or owner choices, not permission to invent new mandatory thresholds. The documented non-functional CRUD/retrieval targets remain mapped as R17.

TASK-035.2 is a completed **mapping/review** checkpoint, not final acceptance. The next authorized phase may plan/run current candidate quality and security gates only after its scope protects the active V2 corpus. TASK-035 remains IN PROGRESS; RC sign-off is NOT GRANTED.
