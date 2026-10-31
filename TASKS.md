
# Implementation Tasks

## PROMPT 3e evidence scan, leave labels, eval warm-up, exact KNN flag, Q071 -- 2026-10-31

**COMPLETED except the 100k benchmark cell; default flip of the exact-KNN flag awaits the owner.**

Open follow-ups:
- **Owner decision: `RAG_SEMANTIC_EXACT_PERMITTED_KNN_ENABLED` default.** Implemented in `5e40bfa`, default `false`. Unit and integration pass with both values (image: unit 1692 pass / 17 xfail; integration 404 pass / 3 xfail). Benchmark on pgvector 0.8.6 with synthetic clustered vectors:
  - 1k/10k/50k chunks: exact recall@k = 1.0 in every cell. The default statement used HNSW in every cell, with recall_min 0.0 in most cells, also at 100 % permitted.
  - Wall p95, including the connection: exact 47-59 ms at 1k, 56-155 ms at 10k, 165-259 ms at 50k. Default: 45-84, 59-138 and 110-154 ms.
  - EXPLAIN execution time at 50k: exact 63-91 ms, default 8-25 ms.
  - The proposed budget (p95 <= 150 ms at 50k) fails on wall time.
  - The **100k cell did not finish**: the background run was stopped by Claude Code for low system memory. NOT_VERIFIED.
  - The semantic/hybrid model lanes were not run with the flag on.
- **Medium: evidence_text after an off-language answer.** Only Q073 lost `evidence_text` (1 of 98-100 citations). Cause: `extract_exact_evidence` (`app/citations/evidence.py:65-126`, called at `app/citations/mapper.py:77`) scores source sentences by word overlap with the answer; an English answer to a Vietnamese source scores below `4.0` (`evidence.py:115`) and returns `None`. Why the answer became English is unexplained: segmenting, validation, prompt excerpt and the deterministic repair are identical before and after `4534430`. Decision pending.
- **Medium: Ollama state changes answers.** With the warm-up, 2 runs from a cold start differ only on Q096 (PROMPT 3d without warm-up: 3 cases). Compared with PROMPT 3d, 6 answers changed (Q034, Q055, Q071, Q073, Q094, Q097), and several now match the 035.3B reference verbatim; none is an annual-leave question touched by `e14f217`. Before/after comparisons must use the same warm-up protocol (`scripts/eval/run_uat.sh`).
- **High (RAG, not fixed): Q071 contradiction not reproducible in isolation.** A traced cold single-question run and both warm-up runs answer correctly (SUPPORTED); the `claim_validation_contradicted` verdict needs the long PROMPT 3d run order. Method to capture it: `artifacts/prompt3e/item5-q071.md`. NOT_VERIFIED.
- **Low: background runs are stopped on low memory.** Two long runs (UAT run 2 post-processing, 100k benchmark) were stopped by Claude Code. Run long jobs in smaller foreground steps, or with `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1` if the owner agrees.

## PROMPT 3d CI green, mojibake repair and before/after UAT -- 2026-10-31

**COMPLETED except the deferred leave-category labels; Q073 label pending owner decision.** Items 1-6 done. Before/after Q001-Q100: 96 identical, Q002/Q033/Q096 vary by run order (already in the baseline), Q073 changed answer language only. See `PROJECT_STATUS.md`.

Open follow-ups:
- **Medium (not fixed): pin the pgvector image by tag or digest.** `pgvector/pgvector:pg17` floats in `.github/workflows/ci.yml:26`, `compose.yaml:35`, `compose.prod.yaml:61` and `scripts/test/compose.integration.yaml:48`. CI pulled pgvector 0.8.7 (`sha256:ac08538c...a75d`) while the local image is 0.8.6 (`sha256:cf134a76...8e6f`), so CI and local runs do not use the same extension.
- **High (RAG; implemented behind a flag, default off, in PROMPT 3e `5e40bfa`): HNSW post-filter recall.** `search_permitted_chunks` filters permission and status after the HNSW index returns `hnsw.ef_search` (40) candidates. More than 40 nearer index elements that the user cannot see, or that belong to deleted but unvacuumed chunks, hide every permitted chunk. No unauthorized chunk is returned. Reproduced locally with the default planner. Two `xfail(strict)` tests in `tests/integration/test_semantic_retrieval_hnsw_recall.py` (integration lane) capture it: they force the index plan (`enable_seqscan`/`enable_sort` off) and fail with `RuntimeError` if the plan does not use HNSW. Proposed design: `docs/design/hnsw-permission-recall.md` (exact KNN over permitted chunks behind an `OFFSET 0` fence, flag `RAG_SEMANTIC_EXACT_PERMITTED_KNN_ENABLED` default off, benchmark 1k-100k chunks x 5/50/100 % permitted, recall@k = 100 % vs brute force). Not implemented; implementation must go through `eaka-rag-change-guard`.
- **FIXED in PROMPT 3e (`e14f217`): two garbled leave-category labels in `_structured_grouped_duration_answer`** (`app/services/grounded_answer_service.py`). These are the `category = "..."` literals for the branch where the line itself contains "dieu kien binh thuong" and the branch where only the neighbor window contains "dac biet". They are still mojibake and reach users in grouped annual-leave answers (for example "12 ngay cho" followed by the garbled "cong viec trong dieu kien binh thuong"). Why deferred: categories are keys of `entries.setdefault(...)`. With the correct text, the neighbor-window branch produces the same key as the real "dac biet" line, so for the layout in `test_structured_grouped_duration_repair_preserves_all_policy_categories` and `..._accepts_plain_annual_leave_wording` the 16-day row is dropped and the 14-day row (minors/disabled/heavy work) is labeled as special work. The garbled key had kept all three values only by accident. The root cause is branch order: `elif "dac biet" in local` runs before the minors/disabled check, and the same condition repeats later where it can never be reached. Removing that early branch fixes those two tests but breaks `test_structured_grouped_duration_repair_handles_value_then_condition_wrap`, so the row-to-category binding needs a general redesign through `eaka-rag-change-guard`. Held by the strict xfail `test_grouped_annual_leave_answer_names_categories_in_vietnamese` and by the explicit two-line allowance in `tests/unit/test_no_mojibake_in_app.py`.
- **Medium: `check_no_question_leak.py` checks nothing today.** It reads questions from `tests/acceptance`, `uat`, `eval`, but Q001-Q100 live in the git-ignored `artifacts/rag-h5-1-stress-uat.py`, so it reports "no questions found" and exits 0. Point it at the real question source. For `4534430` a manual 4-gram check of the added lines against all 100 questions found 0 hits.
- **Low: `eaka-rag-change-guard` assumes a held-out dev split (`run_heldout.py`, `n_dev`) that the repo does not have.** PROMPT 3d used only Q001-Q100, the tuning set, so generalization stays NOT_VERIFIED. A held-out set written independently of the tuning set is still needed.
- **Q073 labeled FAIL by the owner (PROMPT 3e).** After the fix the answer keeps status ANSWERED and citation ND-HR-005 p.11 but is in English ("The policy does not prohibit..."); the cited chunk is Vietnamese only, so the model translated. The 035.3B reference answer was also English.
- **High (RAG, not fixed; not reproducible in isolation, see PROMPT 3e): Q071 false abstention.** ND-HR-005 p.7 (chunk with the salary-review cycle table) reaches the prompt as SOURCE_2, but claim validation returns `claim_validation_contradicted` three times and the fixed no-answer is returned in every run, before and after the fix. Investigate excerpt selection (240 chars, no reranker score) and the contradiction check generically; no question-specific logic.
- **Medium (partly resolved by the PROMPT 3e warm-up; Q096 still varies): run-order variance of Q002/Q033/Q096.** Each first run after the Ollama model was unloaded differs from the warm second run, identically before and after the fix. Main hypothesis: cold vs warm Ollama state (`keep_alive=10m`, no `seed` sent). Test by forcing cold/warm before each run (`artifacts/prompt3d/followup/README.md`).
- **Low (worked around by `scripts/eval/bootstrap_corpus_v2.py`): `scripts/uat/bootstrap_corpus_v2.ps1` always writes `artifacts/uat-corpus-v2/runtime-manifest.json`.** Running it against any other stack overwrites the V2 evidence file. PROMPT 3d used an equivalent Python bootstrap with its own output path (`artifacts/prompt3d/scripts/bootstrap_p3d.py`). Add an output-path parameter.

## PROMPT 3c small fixes before PROMPT 4 -- 2026-10-30

**COMPLETED.** Anonymous volume `7365c1dd...` removed. API test clients get a unique client address so the Redis login/refresh limiter never shares counters; new tests cover 429 on the over-limit login with real Redis and fail-open/fail-closed with Redis unreachable. Image and host: api-unit 51, api-integration 245 passed.

Open follow-ups:
- **ADR (merge into PROMPT 7): login rate limiter fails open when Redis errors.** Outside production the login/refresh rules use `fail_closed=False`, so a Redis outage disables brute-force protection there. Decide the policy per environment.
- **High:** CI has never reached the test step on this branch. Backend CI fails at Lint (24 errors in `tmp_*_trace.py`, 1 E501 in `tests/containment_runtime.py`). Frontend CI fails at parse time ("workflow file issue"), likely `${{ runner.temp }}` in job-level `env` (`frontend-ci.yml:23`).
- **High (RAG, report only):** mojibake in runtime matching/output code: `app/retrieval/structured.py:48` (list bullet regex), `:766` (dong sign unit), `app/services/claim_evidence_validation_service.py:879-881` (segment split set breaks words at "â", e.g. "Nhân"), `app/services/grounded_answer_service.py:7661, 8745, 9174, 9181` (strip sets), `:9025, 9027` (garbled user-facing leave category text).
- **Low:** `ruff format` on the 4 `tests/containment*` files and the E501 at `tests/containment_runtime.py:272`.

## PROMPT 3b reference test environment completion and cleanup -- 2026-10-30

**COMPLETED except volume removal.** `repo_layout` marker, scripts/ in the test image, `TESTING.md`, throwaway integration compose stack, `.venv*/` ignore, SYSTEM-memory test + `RAG_DESIGN.md`, `CITATION_VALIDATION_FAILED` warning log, safe Ruff fixes.

Open follow-ups:
- **High:** API auth tests are not isolated from the Redis rate limiter (14 HTTP 429 failures with real Redis). CI also provides Redis, so the CI api-integration lane is likely affected (NOT_VERIFIED). Reset or disable the limiter per test.
- Awaiting approval: remove anonymous volume `7365c1dd...` (67.06 MB, PostgreSQL 17 data dir from the step-D `eaka-test-pg`, no container uses it).
- `tests/containment_runtime.py:272` E501 and `ruff format` on the 4 containment files; `RAG_DESIGN.md` has pre-existing double-encoded Vietnamese text (e.g. line 105).

## PROMPT 3 follow-up: image built from the approved lock -- 2026-10-30

**COMPLETED.** Build context trimmed, Dockerfile installs from `requirements.lock`, test tools pinned, frontend dev-tool audit fixes applied, runtime/test images verified offline. Reference test environment: `eaka-backend:prompt3-lock-test`.

Open follow-ups:
- **Medium:** upgrade production dependency `zod` 3.25.76 -> 4.x (GHSA-mrhx-c7xc-m3w5, client-side memory exhaustion). Breaking major; migrate the 5 form schemas using `zodResolver` and re-run frontend checks.
- Add `--require-hashes` (`uv pip compile --generate-hashes`) to the lock install.
- Test image lacks `scripts/`, `deploy/` and repo config files: 2 eval-harness collection errors, 7 config-file failures, 11 compose skips. Decide whether to copy them into the test stage or mark those tests host-only.
- Still not done from the takeover cleanup: `.venv*/` in `.gitignore`; SYSTEM-memory test plus `RAG_DESIGN.md`; citation-failure code in logs/audit; Ruff for `tests/containment*` and `tmp_*.py`; remove anonymous volume `7365c1dd...`.

## PROMPT 3 tiktoken offline bundle and backend dependency lock -- 2026-10-30

**COMPLETED for source/doc changes; image build and `npm audit fix` await approval.** Tiktoken `cl100k_base` is bundled in the image under `/opt/tiktoken`; docs corrected; `requirements.lock` reproduces the accepted 92-package versions (91 runtime pins, no upgrade).

Open follow-ups:
- Approve a tagged image build to verify the bundled encoding loads with networking disabled.
- Proposal: install from `requirements.lock` in the Dockerfile with `--no-deps` and the PyTorch CPU index, add hashes (`--generate-hashes`), and add a dev lock for CI.
- Decide `npm audit fix` (dev-tool findings) and the `zod` 3 -> 4 major upgrade separately.
- Exclude `.venv*/` in `.dockerignore` and `.gitignore`.

## Takeover test realignment (PROMPT 1, PROMPT 2, pre-PROMPT 3) -- 2026-10-30

**COMPLETED; application code unchanged.** AUTH-02 local backup verified (27,299/27,299 SHA-256). Stale fixtures realigned (`283cb91`); invalid-citation tests and API docs aligned to fail-safe NO_ANSWER (`fc0d63e`). Default suite 1692 pass / 0 fail / 17 xfail on both Python 3.11.0 and 3.12.10. DB-backed CI lanes on Python 3.12: 696 pass / 1 fail / 1 xfail.

Open follow-ups:
- Decide `test_internal_system_messages_are_not_grounding_prompt_memory` (stale assertion) and update `RAG_DESIGN.md` history section to the query-rewrite-only behaviour.
- Fix follow-up topic loss (Travel Approval -> "Are there exceptions?", strict xfail).
- Add a citation failure code to structured logs/audit for fail-safe NO_ANSWER downgrades.
- Ignore `.venv*/` in `.gitignore`; clear the 33 Ruff lint and 7 format findings.
- Off-host copy of the AUTH-02 backup; run Celery/model lanes.

## TASK-035.3M dependency vulnerability exposure triage -- 2026-10-14

**COMPLETED as bounded read-only applicability/remediation decision package; no implementation authorization.** Six reports in `docs/release/TASK-035.3M-*20261014.md` recheck seven official frontend advisories against five unchanged dev-tool lock entries. Four brace advisories (`eslint → minimatch → brace-expansion`) and Vite are recommended **REMEDIATE_BEFORE_CANDIDATE**; nanoid's current PostCSS `non-secure(6)` path and Vitest's current jsdom/no-public-plugin path are recommended **VERIFIED_NOT_APPLICABLE only to those assessed configurations**, pending security-owner sign-off. No production frontend runtime exposure was verified in the inspected isolated build; build/test/dev-tool exposure and future Linux CI uncertainty remain. A second public-only pip-audit attempt via OSV failed DNS; backend and image advisory coverage remain **NOT VERIFIED**. CI/security and exact-version plans are proposals only. No source, dependency/lock, CI, image, V2, database/Redis or original Git index change. H5.2 historical V2 98/98 remains scoped; frozen 035.3B FAILED; full-tree Ruff and staging whitespace FAIL; source versioning approval NOT GRANTED; RAG B19/B21/R18 **OPEN/FAIL**; API/worker R05 skew **UNRESOLVED**; TASK-035 **IN PROGRESS**, RC **NO-GO**, deferrals **0**.

## TASK-035.3L dependency security advisory and CI gate qualification -- 2026-10-14

**COMPLETED for bounded verification/reporting; security/CI release qualification NOT PASS.** Seven reports in `docs/release/TASK-035.3L-*20261014.md` inventory distinct host, frozen candidate, active V2 and frontend dependencies. Official targeted checks found five affected frontend dev-tool lock entries across seven distinct advisories; React Router 7.18.2 is outside the checked RSC-CSRF affected range. Fresh comprehensive frontend/backend and final-image advisory scans remain **NOT VERIFIED** (backend pip-audit query failed DNS; no safe installed image scanner). App-only Ruff/format/compile and narrow scan PASS; frontend type/lint/Vitest 40/40/mocked Chromium 15/15/isolated build PASS locally. Current CI has backend gates but no frontend/advisory/image scan jobs or verified current run; full-tree Ruff and eight-path staging whitespace FAIL remain. RAG safety B19/B21/R18 **OPEN/FAIL**, active API/worker skew R05 **UNRESOLVED**, source versioning approval **NOT GRANTED**, TASK-035 **IN PROGRESS**, RC **NO-GO**. No source/lock/workflow/image/V2 modification or original Git staging occurred.

## TASK-035.3K source versioning approval gate and Gitlink resolution -- 2026-10-14

**COMPLETED as an analysis/isolated-simulation package; versioning approval NOT GRANTED.** At entry all 666 listed 035.3J identities and 495 archived-source originals matched; this checkpoint's `TASKS.md` and `PROJECT_STATUS.md` edits now intentionally differ from the frozen manifest. Its self-path remains outside its own hashed list. All 103 owner-review paths remain `REVIEW_REQUIRED`; the Gitlink has no proven fresh-clone source. An independent 497-file source/test Git index simulation matched the selected paths without changing the original index, but its staged whitespace check **FAILED** on eight paths. Selected-copy Ruff and focused units 49/49 PASS; full-tree Ruff FAIL remains. See `docs/release/TASK-035.3K-*20261014.*`. Manual privacy/licensing, off-host backup, reproducible build and owner decisions remain open. RAG safety **OPEN/FAIL**, active API/worker skew **UNRESOLVED**, TASK-035 **IN PROGRESS**, RC **NO-GO**. No original Git add/commit/tag/push or runtime change occurred.

## TASK-035.3J reviewed source selection and versioning readiness -- 2026-10-14

**COMPLETED for the authorized source-selection/governance scope; no versioning
approval.** Exact proposed Git staging decisions and hashes, scratch/research
dispositions, Gitlink/legacy reproducibility, offline publication preflight
and logical commit/evidence sequence are in six
`docs/release/TASK-035.3J-*20261014.*` files. The 035.3I snapshot remains
unchanged; source selection is READY_FOR_REVIEW but Gitlink/legacy, privacy
and research-harness owner decisions remain. No Git index/history write or
application/runtime change occurred. Full-repository Ruff remains FAIL;
RAG safety B19/B21/R18 **OPEN/FAIL**, active API/worker skew **UNRESOLVED**,
approved deferrals **0**, TASK-035 **IN PROGRESS**, RC **NO-GO**.

## TASK-035.3I source hygiene and reproducible baseline -- 2026-10-14

**COMPLETED for the authorized inventory/preservation scope; RC NO-GO.**
The working-tree source/evidence inventory, hygiene disposition matrix,
future-source manifest, 495-file local tar plus verified independent
extraction, versioning proposal and remaining-risk register are recorded in
six `docs/release/TASK-035.3I-*20261014.md` reports. Full repository Ruff
lint/format FAIL on retained scratch/research files; filtered source copy
PASS. Source remains uncommitted and no candidate was built, promoted or
qualified. 035.3B safety failure, B19/B21/R18, active API/worker skew and
owner decisions remain open; approved deferrals **0**, TASK-035 **IN
PROGRESS**, RC **NO-GO**.

## TASK-035.3H confirmation-dialog keyboard remediation -- 2026-10-14

**COMPLETED for the narrowly authorized local frontend fix; RC NO-GO.**
The two 035.3G dialog focus/Escape failures reproduced before code changes.
The shared `ConfirmDialog` now initializes and contains focus, handles
Escape only when dismissable, locks pending actions, associates its message,
and restores focus to a live control. Focused component 4/4 and Chromium
accessibility 6/6 passed; full frontend typecheck/build passed, lint retained
the same seven warnings, Vitest 40/40 passed, and mocked Chromium 15/15
passed. See
`docs/release/TASK-035.3H-confirmation-dialog-remediation-20261014.md`
and the dated 035.2 matrix addendum. Historical 035.3G failures remain
recorded; broader accessibility/live E2E gaps remain. No backend, V2 service,
candidate, dependency, API origin or source-map policy was changed.
Unsupported-answer safety **OPEN/FAIL**, API/worker skew **UNRESOLVED**,
approved deferrals **0**, TASK-035 **IN PROGRESS**, RC **NO-GO**.

## TASK-035.3G frontend delivery/accessibility/build-output verification -- 2026-10-14

**COMPLETED as a bounded independent verification checkpoint; RC NO-GO.**
Frontend typecheck, isolated build and 36/36 Vitest passed; lint passed with
seven warnings. Mocked Chromium ran 13 tests: 11 passed, **two failed** on
confirmation-dialog initial focus and Escape dismissal. The existing 9/9
mocked tests passed. The local build embeds the documented loopback API
fallback and a source-content map; external frontend serving and production
API origin remain unverified. Static API contract review found an incomplete
frontend Web-citation type but no proven live break. Repository-wide Ruff
still fails on preserved scratch/evaluation files. See the five
`docs/release/TASK-035.3G-*20261014.md` reports and dated 035.2 matrix
addendum. No production code, service, database, candidate or lockfile was
changed. Unsupported-answer safety is **OPEN/FAIL**, API/worker skew
**UNRESOLVED**, approved deferrals **0**, TASK-035 **IN PROGRESS**, RC **NO-GO**.

## TASK-035.3F independent frontend, build and security qualification -- 2026-10-14

**Status: COMPLETED for the authorized static/mock/host-unit verification
scope; RC NO-GO.** Frontend typecheck and isolated production build passed;
ESLint passed with seven warnings; Vitest passed 36/36; mocked Chromium E2E
passed 9/9. App-only Ruff lint/format, host Python 3.11 compilation and
`pip check`, bounded security scan, and 1423 non-red host unit tests passed
(three expected failures). Repo-wide Ruff/format failed on pre-existing
scratch/experimental files. Development/production Compose config parses;
no image build, service recreation, V2 database test, candidate restart, live
frontend flow, production TLS verification or fresh vulnerability scan was
performed. See `docs/release/TASK-035.3F-frontend-qualification-20261014.md`,
`docs/release/TASK-035.3F-backend-build-security-verification-20261014.md`,
`docs/release/TASK-035.3F-ci-observability-review-20261014.md`,
`docs/release/TASK-035.3F-acceptance-matrix-evidence-mapping-20261014.md`,
and `docs/release/TASK-035.3F-prioritized-remaining-rc-plan-20261014.md`.
The mandatory unsupported-answer safety defect, current B19/B21 RC failure,
active API/worker skew and owner decisions remain OPEN. Approved deferrals 0;
TASK-035 IN PROGRESS; frozen 035.3B candidate FAILED/preserved; RC NO-GO.

## TASK-035.3E bounded context-admission investigation -- 2026-10-14

**Status: COMPLETED as diagnostic/test design; NO DEFENSIBLE CONTEXT ADMISSION
CORRECTION IDENTIFIED.** Preserved 035.3B evidence and exact source tracing
confirm irrelevant, permission-visible hits can enter selected context through
the current budget/excerpt boundary. A fresh, invented-policy A–O offline
contract records 11/15 context expectations passing and four intended
irrelevant-hit exclusions failing; eight material-answer positive controls
remain admitted, including Vietnamese/mixed and two-document evidence. Two
separate prohibition/incomplete-claim controls both return unsafe `SUPPORTED`
from the existing validator. Existing
scores and topic-specific guards do not establish a safe general admissibility
signal; the separate final-answer responsiveness gap remains open. See
`docs/release/TASK-035.3E-bounded-context-admission-investigation-20261014.md`.
No production code, candidate image, service, database, corpus, model or
release policy changed. TASK-035 remains **IN PROGRESS**, frozen 035.3B
candidate **FAIL/preserved**, and RC sign-off **NOT GRANTED**.

## TASK-035.3D release safety scope and remediation decision -- 2026-10-14

**Status: COMPLETED as decision preparation; RC NO-GO.** The independent
035.3B STAFF private-policy check remains a permission-aware unsupported-answer
safety **FAIL**: direct RBAC denial worked, but unrelated accessible context
produced a cited ANSWERED response instead of zero-citation NO_ANSWER.
TASK-035.2 matrix B19/B21 now carry explicit current-RC qualifications while
the dated H5.2 98/98 and candidate broad 98/98 remain historical scoped PASS.
Neither 035.3C.2E nor 035.3C.2F selected a safe semantic mechanism. The
recommended current strategy is explicit RC NO-GO with a separately approved,
bounded context-admission investigation as the next engineering action; no
scope reduction, safety deferral, production correction or build is approved.
Decision package: `docs/release/TASK-035.3D-release-safety-decision-20261014.md`,
`docs/release/TASK-035.3D-affected-criteria-analysis-20261014.md`,
`docs/release/TASK-035.3D-rc-blocker-remediation-register-20261014.md`,
`docs/release/TASK-035.3D-product-release-owner-decision-request-20261014.md`,
and `docs/release/TASK-035.3D-next-engineering-action-20261014.md`.
TASK-035 remains **IN PROGRESS**, 035.3B candidate **FAILED/preserved**,
approved deferrals **0**, and RC sign-off **NOT GRANTED**.

## TASK-035.3C.2F question–answer obligation analysis -- 2026-10-14

**Status: COMPLETED as bounded offline research; NO SAFE MECHANISM SELECTED.**
A fresh 36-case invented-policy manifest (12 development/24 one-shot final test,
eight final cases per EN/VI/MIXED group) compared the existing validator with
question/evidence-only local Qwen obligation extraction plus cached E5
per-obligation coverage and their intersection. On the final set, existing
validation had 11/14 unsafe acceptances and 3/10 false abstentions; automatic
obligation evaluation had 2/14 and 10/10; the intersection had 1/14 and
10/10. The extractor missed all 3/3 genuine source-authority conflicts across
both splits and invented unsupported obligations. The oracle-obligation
diagnostic also rejected 10/10 valid final answers at its development-selected
cutoff. See `docs/release/TASK-035.3C.2F-question-obligation-spec-20261014.md`,
`docs/release/TASK-035.3C.2F-gold-label-review-20261014.md`,
`docs/release/TASK-035.3C.2F-experimental-results-20261014.md`, and
`docs/release/TASK-035.3C.2F-feasibility-decision-20261014.md`.
No production code, model/dependency, image, or service changed. Source
correction and new candidate remain NOT READY; TASK-035 remains IN PROGRESS,
the frozen 035.3B candidate FAIL/preserved, and RC sign-off NOT GRANTED.

## TASK-035.3C.2E isolated multilingual responsiveness evaluation -- 2026-10-14

**Status: COMPLETED as bounded research; NO SAFE MECHANISM SELECTED.**
The synthetic 36-case, 12-development/24-held-out pilot compared existing
claim validation, locally cached E5 similarity, and localhost Qwen judgment.
None met both safety and multilingual usefulness: held-out false acceptance /
false abstention was 7/14 and 5/10 for the validator, 2/14 and 10/10 for E5,
and 0 and 10/10 for the initial judge. A revised constrained judge repeated
three unsafe development acceptances involving condition omission, negation
and policy conflict, so it was not taken to a new held-out set. See
`docs/release/TASK-035.3C.2E-evaluation-design-20261014.md`,
`docs/release/TASK-035.3C.2E-decision-20261014.md`, and the synthetic manifest
and metrics under `artifacts/task-035-3c2e-20261014/`. No production code,
dependency, Docker image, database or active V2 service was changed. Source-
level correction and new candidate build remain NOT READY. TASK-035 is IN
PROGRESS; frozen 035.3B candidate remains FAIL; RC sign-off NOT GRANTED.

## TASK-035.3C.2 multilingual answer responsiveness correction -- 2026-10-14

**Status: PARTIAL / BLOCKED at Phase 4 design gate.** Test-first A-O
synthetic claim controls show 7 PASS / 8 FAIL before correction, including
five false acceptances and three false abstentions. The existing test suite
has 4 PASS / 3 expected failures. No safe generic rule was established from
the current deterministic heuristics, relative reranker scores or an
uncalibrated extra model call. Per the explicit stop condition, no production
source or image was changed and no runtime test or broad benchmark was run.
See
`docs/release/TASK-035.3C.2-multilingual-responsiveness-design-stop-20261014.md`.
An isolated multilingual entailment/responsiveness evaluation and explicit
architecture choice are needed before code correction and a new candidate.
The frozen candidate remains FAIL; TASK-035 is IN PROGRESS; RC sign-off is
NOT GRANTED.

## TASK-035.3C.1 runtime integrity and root-cause verification -- 2026-10-14

**Status: COMPLETED for diagnostic authorization; remediation NOT STARTED.**
Accepted V2 post-restart corpus/source/artifact integrity passed the documented
read-only identity and hash checks. The stopped failed candidate and its four
volumes remain preserved, but candidate database integrity is NOT VERIFIED.
The host reboot is confirmed; the exact exit-255 mechanism is not. Test-only
synthetic controls showed 4 passes and 3 strict expected failures, including
both nonresponsive grounded answers and a responsive Vietnamese clause that
currently abstains. The existing candidate remains FAIL. Production code and
images were not changed; the authorized next step is a separately approved
generic correction and new isolated qualification, with separate authority
for starting the stopped candidate if its database must be inspected. See
`docs/release/TASK-035.3C.1-runtime-integrity-root-cause-20261014.md`.
TASK-035 remains IN PROGRESS; RC sign-off is NOT GRANTED. The 035.3C entry
below describes the earlier checkpoint and is superseded only on V2 rebaseline.

## TASK-035.3C permission-aware answer-relevance remediation -- 2026-10-14

**Status: PARTIAL / BLOCKED.** Read-only evidence and a non-benchmark synthetic
probe verified that source-grounded verbatim text can be accepted without
question responsiveness. No score cutoff or safe multilingual generic remedy
was established. All isolated 035.3B containers were unexpectedly found exited
with code 255 during inspection; images and volumes remain, but candidate DB
integrity cannot currently be rechecked without starting a service. Accepted
V2 containers were up/healthy after a recent restart; data baseline was not
reverified. No application change, service action, broad benchmark or
requalification occurred. The diagnostic and synthetic A-J test plan are in
`docs/release/TASK-035.3C-permission-answer-relevance-diagnostic-20261014.md`.
The frozen 035.3B candidate remains **FAIL**; TASK-035 remains **IN PROGRESS**;
RC sign-off is **NOT GRANTED**. Resume only after an authorized integrity
rebaseline and defensible generic correction design.

## TASK-035.3B isolated candidate broad V2 requalification -- 2026-10-13

**Status:** Authorized qualification workflow COMPLETED; candidate
qualification **FAIL**. A fresh isolated V2 restore and verified pre-run
second-database restore passed. Frozen candidate Q001-Q100 achieved 98/98
supported semantic/material answers, 101/101 persisted citation identities,
Q018/Q100 safe abstentions, and 9/9 documented repeatability; existing six-case
safety smoke passed. A new STAFF question about a manager-granted private travel
policy returned an unrelated, cited organization-document answer instead of
NO_ANSWER. No private document or cross-user chat access leaked, but the
permission-aware unsupported-answer gate failed. Candidate images, source,
benchmark and protected V2/035.3A stacks were preserved. See
`docs/release/TASK-035.3B-isolated-candidate-qualification-20261013.md`.
TASK-035 remains **IN PROGRESS**; active image skew remains, promotion is
blocked, and RC sign-off is **NOT GRANTED**. A generic fix and rebuilt/retested
candidate require separate approval.

## TASK-035.3A isolated candidate build and compatibility qualification -- 2026-10-13

**Status:** Completed within the approved isolated scope. Same-source,
same-dependency API and worker candidate images were built under unique tags;
their shared source and 92 package versions match. A separate candidate
Compose project passed static/security checks, 506 focused unit tests, 70
isolated-database integration tests, a Celery broker ping, normal synthetic
document READY ingestion, grounded material citation, private-document RBAC,
and safe unsupported-answer smoke. The accepted H5.2 V2 baseline stayed intact.
The active API/worker skew remains and the candidate has not undergone broad
V2 requalification. See
`docs/release/TASK-035.3A-isolated-candidate-qualification-20261013.md`.
TASK-035 remains **IN PROGRESS**; no TASK-035.3 completion, candidate promotion,
RC sign-off, or production cutover is claimed.

## TASK-035.2A RC candidate readiness planning -- 2026-10-13

**Status:** Bounded planning checkpoint completed; TASK-035 remains IN PROGRESS.
The accepted H5.2 V2 baseline remains intact in the verified scope. API/worker
source and dependency skew remains an unresolved RC blocker; a jointly built,
frozen-source/dependency candidate is recommended for separately approved
isolated qualification, not authorized or built here. Historical Celery
accounting and TASK-034.1 disposition remain unresolved. See
`docs/release/TASK-035.2A-rc-candidate-readiness-20261013.md`. TASK-035.3
has not started; no RC sign-off was granted.

## TASK-035.2 acceptance traceability and deferral review -- 2026-10-13

**Status:** Documentation checkpoint completed. TASK-035 remains IN PROGRESS;
TASK-035.3 through TASK-035.6 have not started. The current 80-criterion matrix
records 9 scoped PASS, 1 proven FAIL, 17 NOT_RUN, 43 EVIDENCE_GAP, 7 CONFLICT,
and 3 DEFERRAL_PROPOSED; no deferral is approved. The API/worker candidate
identity skew remains an RC blocker. TASK-034.1's original strict matrix is
still IN_PROGRESS and is not silently superseded by H5.2 V2. Evidence and
decisions are documented in `docs/release/TASK-035.2-acceptance-traceability-matrix-20261013.md`,
`docs/release/TASK-035.2-release-deferral-register-20261013.md`, and
`docs/release/TASK-035.2-verification-coverage-summary-20261013.md`.
No TASK-035.3 gate or RC sign-off was performed.

## TASK-035.1 baseline protection and release-contract reconciliation -- 2026-10-13

**Status:** TASK-035 is IN PROGRESS; TASK-035.1 documentation checkpoint
completed. TASK-035.2 through TASK-035.6 have not started. No release candidate
or production sign-off is granted. The exact accepted H5.2 V2 working-tree,
image, corpus and evidence identities, API/worker skew, unresolved release
contract contradictions, and evidence-protection proposal are recorded in
`docs/release/TASK-035.1-baseline-manifest-20261013.md` and
`docs/release/TASK-035.1-release-contract-reconciliation-20261013.md`.
No source commit, tag, external backup, service recreation or corpus change was
performed in this checkpoint.

## RAG-H5.2 V2 final qualification -- 2026-10-13

**Status:** RAG-H5.2 COMPLETED for the isolated UAT Corpus v2 scope. TASK-035
is ELIGIBLE / NOT STARTED; Document Creator is NOT STARTED. The exact final
image passed 98/98 supported broad semantic/material cases, with Q018 safe
authority-conflict abstention and Q100 unsupported abstention; 101/101
citations match persisted chunk/document identities. Six-case safety/permission
smoke, nine-case repeat, 467 focused unit tests, quality checks, source/package
checksums and current-image semantic smoke on the previously independent
restored corpus passed. No off-host DR claim or historical Celery consistency
claim is made. Review the restore-check API stop anomaly and off-host backup
expectation during TASK-035; do not infer TASK-035 release-candidate approval.
Evidence: `artifacts/uat-corpus-v2/h5-2-qualification-20261013.md` and
`artifacts/uat-corpus-v2/h5-2-supported-failure-ledger-20261013.md`.

## RAG-H5.2 V2 final qualification checkpoint -- 2026-10-12

**Status:** IN PROGRESS. TASK-035 is BLOCKED / NOT STARTED; Document Creator is
NOT STARTED. The broad V2 Q001-Q100 transport run completed, but supported
semantic/material failures remain and final 98-case acceptance is not certified.
Targeted leave, security-polarity, and citation-record fixes passed focused
runtime gates; current representative and six-case safety smoke are green.
Next: resolve Q055/Q080/Q084/Q088/Q089/Q091 and Q090 inconsistency without
benchmark-specific logic; adjudicate partial answers; rerun affected gates and
then the full V2 acceptance/reproducibility gates. Q018 remains a separate
corpus-authority conflict. Evidence:
`artifacts/uat-corpus-v2/h5-2-qualification-20261012.md`.

## Isolated UAT Corpus v2 Redis recovery -- 2026-10-12

**Status:** Redis infrastructure recovery completed; backend source unchanged;
monitored PostgreSQL integrity gates and runtime health pass. Current inspected
Celery broker/worker/document state is consistent; historical Celery accounting
remains **UNKNOWN**. The initial Redis autosave dirty-counter origin remains
unresolved, with no observed task replay or material PostgreSQL transition.

The approved Redis-only cutover is complete and must not be repeated. See
`artifacts/uat-corpus-v2/redis-recovery-20261010/postreboot-cutover-integrity-20261011.md`.
RAG-H5.2 is **IN PROGRESS**; TASK-035 is **BLOCKED / NOT STARTED**. The next
workstream is targeted CEO/CTO regression, representative cross-cluster
regression, hardcoding audit, release gates, broad V2 acceptance, reproducibility
verification, and then the final H5.2 decision. None of those gates was run as
part of Redis recovery finalization. The September corpus provenance status
below is historical and distinct from isolated V2.

## RAG-H5.2 September corpus source recovery -- 2026-09-29

**Status:** source recovery partial; isolated reconstruction not authorized by
provenance; RAG-H5.2 in progress; TASK-035 blocked/not started.

- Created `artifacts/rag-h5-2-september-corpus-recovery/manifest.json` with exactly 12
  expected document slots and per-entry identity, title, candidate, hashes, metadata,
  permissions, READY evidence, provenance sources, and conservative classification.
- Preserved nine `VERIFIED_SOURCE` binaries under the recovery artifact: all six Nova
  policy PDFs, the checksum-matched generic leave policy, and both deterministic UAT
  seed PDFs.
- Recorded one `PROBABLE_SOURCE`: private document
  `0c490a2a-e1a9-40a6-82d4-19042e10c596`, `UAT Live Upload 1786697622220`. The
  repository has its deterministic generator and artifacts establish content/access,
  but the exact generated binary and checksum are unavailable.
- Recorded one `PARTIAL_SOURCE`, `UAT Live Upload 1786698102732`. Its exact generated
  PDF and passed live-test output survive, but its historical database ID does not.
- Recorded one `MISSING` document slot. The aggregate proves another active READY
  document existed, but no surviving artifact safely establishes its ID, title, file,
  checksum, or permissions.
- Git branches, tags, reflog, deleted paths, reachable object paths, and unreachable
  trees/blobs contain no policy corpus. Targeted host and OneDrive searches found no
  further September candidates.
- Do not reconstruct from benchmark excerpts. Request manual OneDrive
  recycle-bin/version-history recovery for the known `1786697622220` live-upload file,
  the `1786698102732` database identity, and the final unidentified document.
- Do not start an isolated Compose reconstruction until all 12 authoritative sources
  and their required access metadata are established. Benefits and all later H5.2
  clusters remain deferred; Exact-100 remains deferred.

## RAG-H5.2 runtime recovery forensic hard stop -- 2026-09-28

**Status:** RAG-H5.2 in progress; TASK-035 blocked/not started; Exact-100 not ready.

- Targeted benefits execution could not begin because the previously verified
  September project runtime and its volumes are no longer present.
- Both Docker contexts reach the same current engine. Docker Desktop logged a missing
  data disk followed by `detected no file system. Formatting` before Compose created
  the only four visible project volumes at `2026-09-28T14:24:15Z`/`16Z`; this is not
  a context, backend, or project-prefix discovery issue.
- Read-only database counts are `users=0`, `documents=0`, and `chunks=0`;
  health/readiness are `200/200`; Alembic current/head is `20260822_0011`.
- The two PostgreSQL custom dumps and upload archives are from 2026-08-09. Their
  schemas include users/documents/chunks/vector data, but the upload files are older
  fixture/July-August assets with different storage IDs. Classify them as
  `STALE_PRE_SEPTEMBER_BACKUP`; do not restore them as the September runtime.
- Repository artifacts preserve partial provenance (12 active READY documents, 153
  chunks, 384-dimensional embeddings, and seven cited document IDs/titles), but the
  repository and Codex attachments do not contain all authoritative policy binaries
  or a complete ingestion manifest. Exact deterministic reconstruction is currently
  `PARTIAL`, not verified.
- No seed, restore, reingestion, user creation, volume deletion, or persistent-state
  overwrite was performed.
- Required next action: obtain explicit authorization and authoritative September
  corpus files/manifests, then reconstruct in a separate Compose project/new volumes,
  verify accounts/checksums/READY documents/chunks/embedding dimensions, and only then
  reconnect acceptance execution. Preserve the current empty volumes until that
  isolated state is verified.
- Closed compensation and cross-document results remain authoritative; all four
  active application clusters remain unexecuted/open in this checkpoint.

## RAG-H5.2 remaining release-gate checkpoint -- 2026-09-28

**Status:** RAG-H5.2 in progress; TASK-035 blocked/not started; compensation closed;
Exact-100 not rerun.

- Current unresolved inventory: `23` cases (`22` application defects and Q018 as one
  corpus conflict); infra and expected-no-answer blockers: `0`.
- Open application clusters: person/organization fact binding
  (Q006/Q008/Q010/Q011/Q012/Q015), schedule/attendance value binding
  (Q016/Q017/Q020/Q021/Q022/Q024/Q032/Q038), annual-leave allocation (Q039/Q040),
  and benefit value/condition binding (Q075/Q079/Q083/Q085/Q086/Q087).
- Q018 requires policy-authority metadata or a human supersession decision; do not
  treat its overlapping working-hour windows as a retrieval defect.
- Cross-document synthesis Q096/Q097/Q098 is closed on production `qwen2.5:3b`.
  The generic fix addressed decomposition, retrieval intent, multi-source value
  binding, and leave-incident clause selection at their first origin boundaries.
- Verification: selected runtime gate `3/3 PASS`, final focused gate `8 passed`,
  subclaim suite `13 passed`, Ruff/format/compile/import pass, citation materiality
  `100%`, hallucinations/permission leakage/infra errors `0`, API `200/200`.
- Next checkpoint: benefit value/condition binding only. Exact-100 remains a later
  release gate.

## RAG-H5.2 compensation hardening checkpoint -- 2026-09-24

**Status:** Q059 closed; salary-band hardening fixed (`5/5`); compensation hardening
fixed (`12/12`). RAG-H5.2 remains in progress and TASK-035 remains blocked/not started.

- Root cause: exact role/range evidence ranked below generic salary and unrelated
  monetary prose before the production top-two prompt cutoff.
- Generic fix: prioritize an atomically bound, query-matched structured salary row;
  run salary-band extraction before generic value extraction; preserve compound money
  units. No production Q059/role/grade/range/source hardcoding was added.
- Safety: citation inference `NO`; validation weakening `NO`; RBAC and READY-state
  filters unchanged.
- Focused verification: `20 passed, 276 deselected`; Ruff, format, and compileall pass.
- Runtime: Q059 `PASS`; Q056-Q060 `5/5 PASS`; required compensation set `12/12 PASS`;
  citation/material support `100%`; hallucination, permission leakage, timeout `0`.
- Runtime update: only the API image/service was rebuilt and recreated; persistent
  database, Redis, uploads, and volumes were preserved; health/readiness `200/200`.
- Not executed: Exact-100 and broader RAG-H5.2 release gates.

## CURRENT COMPLETION SNAPSHOT -- 2026-08-21

### TASK-034.1.2 -- Multi-Document Reliability & RAG Accuracy Hardening

**Status:** Complete for the seven-case runtime UAT set after restoring the intended UAT leave-policy evidence through the real ingestion pipeline. TASK-035 remains not started.

#### Non-negotiable runtime constraint

The 12 / 14 / 16 annual-leave values were not hard-coded into runtime logic and no regression/UAT question was converted into a lookup rule. Runtime answers still flow through RBAC-filtered retrieval, normal ingestion/indexing, reranking/fallback reranking, grounded generation, citation validation, and citation persistence.

#### Four RAG root causes fixed

1. Retrieval/source quality allowed sample-question, appendix, and reference chunks to compete with direct answer-bearing policy clauses. The new evidence/source-quality path ranks clause/table evidence ahead of question-list or sample text.
2. YES/NO validation was not subject/object aware enough. It could accept the wrong actor/object or reject supported answers when the leading polarity token was missing. Validation now anchors polarity to the asked subject/object.
3. Relation entailment was missing for replacement/supplemental relationships such as NovaCare versus mandatory BHYT. Validation now recognizes source-supported relation cues instead of treating the answer as unsupported.
4. Citation repair was too weak. It could leave redundant markers or map final citations to non-answer evidence. Citation selection now uses answer-bearing evidence, focused evidence text, source-quality scoring, and marker repair before public citation numbering.

#### Answer-bearing evidence architecture completed

- Added/used answer-bearing evidence scoring in `app/retrieval/evidence_quality.py`.
- Added focused citation evidence extraction in `app/citations/evidence.py`.
- Added evidence-aware citation pruning and marker repair in `app/citations/pruning.py`.
- Extended citation mapping/persistence/API history with nullable `message_citations.evidence_text`.
- Strengthened `app/services/claim_evidence_validation_service.py` for subject/object-aware YES/NO validation and relation entailment.
- Preserved RBAC and permission revalidation; citations remain tied to authorized retrieved chunks.

#### Annual-leave corpus issue and restoration

Annual-leave UAT exposed a corpus issue, not a runtime-code issue. The active Nova-branded leave policy only contained the 12-day normal-work clause, while the authoritative 12 / 14 / 16-day distinction existed in a soft-deleted UAT-admin, organization-scope leave policy document.

Restored existing document rather than reseeding:

- Document ID: `43cb2c93-52bc-44f6-8e03-1b1f075e1d89`
- Title: `Chính sách nghỉ của người lao động`
- Filename: `Chinh_sach_nghi_cua_nguoi_lao_dong.pdf`
- Storage key: `documents/2026/08/951776f4-88c3-4c98-8401-c8ce5edad268.pdf`
- Checksum: `24178db420422e474326986672b6c15cc67373ee6adbe1489ba5e8addf95f4f4`
- Uploaded by: `admin.uat@example.test`
- Access scope: `ORGANIZATION`
- Restore action: set `is_deleted=false`, reset status to `UPLOADED`, and enqueued normal processing task `274fe326-9d28-421c-9c11-253ec7b74bc2`.
- Worker result: `READY`, `page_count=6`, `chunk_count=12`, `total_tokens=6458`, `embedding_dimensions=384`.
- Active indexed verification: active ready corpus became `12` documents and `153` chunks; active authoritative 12 / 14 / 16 clause chunk count is `1`.
- Active evidence chunk: `4b341201-f0df-4102-b9f2-5ad7091781a6`, page `3`, containing the table rows for `12 ngày`, `14 ngày`, and `16 ngày`.

Provenance conclusion: the restored file is part of the local Nova Digital UAT corpus by uploader, scope, timing, and HR-policy purpose. Remaining corpus debt is that this authoritative 12 / 14 / 16 source is generic/template-branded, while the active Nova-branded leave policy is incomplete for those distinctions.

#### Seven-case runtime UAT result

All cases were run as new staff chat sessions against the real local runtime (`qwen2.5:7b-instruct-8k`). All seven passed.

| Case | Result | Required evidence behavior |
| --- | --- | --- |
| Own salary | PASS | Answer `Có`; cites salary policy pages 10-11; claim validation `SUPPORTED`. |
| EAP | PASS | Answer `Không`; cites benefits policy page 8; claim validation `SUPPORTED`. |
| NovaCare vs BHYT | PASS | Answer `Không`; cites benefits policy page 4; claim validation `SUPPORTED`. |
| Engineering Manager | PASS | Returns `N5`, `42 - 70 triệu đồng`; cites salary table page 4; claim validation `SUPPORTED`. |
| Head / Director | PASS | Returns `N6`, `65 - 110 triệu đồng`; cites salary table page 4; claim validation `SUPPORTED`. |
| Annual leave | PASS | Starts `Không`; distinguishes `12`, `14`, and `16` days; cites the restored active leave clause/table on page 3 and no sample-question/test-question section; claim validation `SUPPORTED`. |
| CEO false premise | PASS | Starts `Không`; corrects CEO to `Nguyễn Anh Khoa`; cites organization source page 6; claim validation `SUPPORTED`. |

Annual-leave answer observed:

```text
Không. 12 ngày Công việc trong điều kiện bình thường; 14 ngày Người chưa thành niên, người khuyết tật hoặc công việc nặng nhọc, độc hại, nguy hiểm theo danh mục pháp luật; 16 ngày Công việc đặc biệt nặng nhọc, độc hại, nguy hiểm theo danh mục pháp luật; 12 ngày làm việc/năm khi đủ [1] [2]
```

#### Verification

```text
python -m pytest tests\unit\test_grounded_answer_service.py -q
75 passed in 1.33s

python -m pytest tests\unit\test_grounded_answer_service.py tests\unit\test_rag_accuracy_components.py tests\unit\test_citation_mapping.py -q
132 passed in 1.56s

python -m pytest tests\unit\test_grounded_answer_service.py tests\unit\test_rag_accuracy_components.py tests\unit\test_citation_mapping.py tests\unit\test_citation_validation_service.py tests\unit\test_grounded_output.py -q
157 passed in 1.71s

python -m pytest tests\unit -q
1061 passed in 8.22s

python -m ruff check <21 touched Python files>
All checks passed!

python -m ruff format --check <21 touched Python files>
21 files already formatted
```

#### Remaining technical debt

- Replace the restored generic/template leave policy with a Nova-branded leave policy containing the same source-defined 12 / 14 / 16 distinctions through the normal upload pipeline when the canonical file is available.
- The configured CrossEncoder reranker is unavailable in the current runtime and falls back to alignment reranking; hydrate/cache the intended reranker model or explicitly bless the fallback for local UAT.
- Runtime UAT latency remains high, with observed case elapsed times from about 94s to 186s.
- Annual-leave `evidence_text` is currently too narrow (`12 ngày`) even though the citation excerpt contains the full 12 / 14 / 16 table; multi-value/table evidence highlighting should capture the full supporting clause.
- The active Nova-branded leave policy still contains sample-question/test-question chunks; source-quality scoring prevents them from factual citation use, but corpus curation should move test material out of production knowledge documents.
- The seven-case runtime UAT runner is still manual; add an automated acceptance harness that records prompt, citations, claim-validation diagnostics, and latency.

## CURRENT MANUAL WORK — 2026-08-19

### TASK-034.1.2 — Multi-Document Reliability & RAG Accuracy Hardening

**Status:** In Progress (manual work; Codex not used).

This work is not TASK-035 and does not mark a Release Candidate.

#### Runtime constraint

The regression/UAT question set exists only to measure system behavior. It must never be converted into:

- question-to-answer dictionaries;
- special-case runtime branches;
- prompt rules containing expected answers for individual UAT questions;
- source-specific hard-coded answer templates.

#### Completed in current manual work

- Added exact evidence extraction from answer + backend source text.
- Added optional `ValidatedCitation.evidence_text`.
- Persisted nullable `message_citations.evidence_text`.
- Added DB check constraint preventing blank non-null evidence text.
- Added migration `cd124fa71c86_add_citation_evidence_text.py`.
- Added repository read/write propagation.
- Added `CitationRead.evidence_text` API propagation.
- Verified DB persistence and GET session reload with a live citation containing `evidence_text = "180 người"`.
- Added frontend exact-evidence rendering so only the evidence substring is emphasized instead of the whole excerpt.
- Preserved compatibility for historical citations without evidence metadata.
- Started Minimal Citation Selection with evidence-aware pruning.

#### Current verification

Exact evidence focused suite checkpoint:

```text
15 passed
```

Minimal Citation Selection is **IMPLEMENTED + UNIT VERIFIED; LIVE RUNTIME VERIFICATION PENDING**.

Final focused citation-mapping verification:

```text
17 passed in 0.19s
```

The punctuation-whitespace regression after removing redundant markers is fixed:

```text
Before: Quy mô nhân sự là 180 người [1] .
After:  Quy mô nhân sự là 180 người [1].
```

#### Current acceptance intent for citation pruning

- Same `document_id` + same normalized `evidence_text`: keep one strongest citation.
- Same document + different supporting evidence: preserve multiple citations when required.
- Never deduplicate only by `document_id`.
- Pruning occurs before public marker renumbering.
- Frontend must not hide backend citation errors.

#### RAG accuracy hardening scope after pruning

1. Query understanding / bilingual alias support where useful.
2. Retrieval recall for existing document facts.
3. Reranking precision.
4. Table/row discrimination for nearby values and conditions.
5. Claim contradiction validation (`Có/Không`, allowed/prohibited, numeric conditions).
6. Multi-document contamination prevention.
7. Regression/UAT coverage with paraphrased questions, not runtime answer lookup.

#### UI-04B status

- B1 Exact Evidence Extraction: Completed.
- B2 Persistence + API: Completed.
- B3 React exact evidence highlighting: Implemented and manually visible; rerun frontend quality gates after citation-pruning work stabilizes.
- B4 Document Viewer: Pending. Target behavior remains citation click -> correct document -> correct page -> locate `evidence_text` -> scroll/highlight without mutating source files.

#### Next action

Before final completion, run one live runtime check with a newly generated answer that previously produced duplicate citations:

```text
Quy mô nhân sự của Nova Digital là bao nhiêu?
```

Expected behavior: one public citation for the repeated `180 người` evidence, not two same-document/same-evidence citations.

After the live runtime check passes, mark Minimal Citation Selection completed and start RAG Accuracy Hardening.

First investigation target:

```text
Query Understanding
-> Hybrid Retrieval recall
-> Reranking precision
```

Inspect the real retrieval/reranking implementation before changing code. Do not add question-specific runtime answers.


## Summary

TASK-001 -> TASK-034: Completed. TASK-035 is not started.

Phase 1: Completed.
Phase 2 backend roadmap: Completed through TASK-034.
Current task: UAT FIX -- UX Selectors + LLM_NOT_CONFIGURED completed. TASK-035 not started.
Next roadmap task: TASK-035 -- Final Acceptance Test & Release Candidate is pending and not started.
TASK-028 live acceptance: COMPLETED_AND_VERIFIED.
READY FOR USER EXPERIENCE: YES.
TASK-029 implementation completed: Yes.
TASK-030 implementation completed: Yes. TASK-031 status: Completed. TASK-032 status: Completed. TASK-033 status: Completed. TASK-034 status: Completed. TASK-035 status: Not started.

## Rules

- Implement tasks in order unless there is a clear technical reason.
- Each task must include tests or a documented verification path.
- After each task, update `PROJECT_STATUS.md` and `CHANGELOG.md`.

## TASK-001 â€” Initialize backend project

**Status:** Completed.

### Deliverables

- Python project configuration.
- `app/main.py`.
- `app/core/config.py`.
- Health live endpoint.
- First test.
- `.gitignore`.
- `.env.example`.

---

## TASK-002 â€” Docker infrastructure

**Status:** Completed.

### Deliverables

- Docker Compose with PostgreSQL pgvector and Redis.
- Volume persistence.
- Health checks.

---

## TASK-003 â€” Database foundation

**Status:** Completed.

### Deliverables

- Async SQLAlchemy session.
- Declarative base.
- Alembic config.
- Database readiness check.

---

## TASK-004 â€” User and department models

**Status:** Completed.

### Deliverables

- Department model.
- User model.
- Role enum.
- Initial migration.
- Development Admin seed command.

---

## TASK-005 â€” Authentication

**Status:** Completed.

### Deliverables

- Login.
- Access token.
- Refresh token persisted as hash.
- Refresh.
- Logout.
- Current user endpoint.

---

## TASK-006 â€” RBAC dependencies and policies

**Status:** Completed.

### Deliverables

- Role guards.
- Permission policy helpers.
- Tests for Admin, Manager, and Staff.

---

## TASK-007 â€” User and department APIs

**Status:** Completed.

### Deliverables

- Admin CRUD.
- Pagination.
- Validation.
- Basic audit log events.

---

## TASK-008 â€” Document data model

**Status:** Completed.

### Deliverables

- Document model.
- Access scope.
- Status enum.
- Document permission model.
- Migration.

---

## TASK-009 â€” Local file storage and upload

**Status:** Completed.

### Deliverables

- Storage abstraction.
- Local implementation.
- PDF validation.
- Upload endpoint.
- Checksum.
- 202 response.

---

## TASK-010 â€” Document listing and access control

**Status:** Completed.

### Deliverables

- List/detail/download/update/delete.
- Permission-aware filters.
- Direct User and Department grants.

---

## TASK-011 â€” Celery and Redis worker

**Status:** Completed.

### Deliverables

- Celery app.
- Redis broker and result backend configuration.
- Document queue.
- Worker ping task.
- Document task skeleton.
- Worker-specific database session.

---

## TASK-012 â€” PDF extraction

**Status:** Completed.

### Deliverables

- TextExtractor abstraction.
- PyMuPDF extractor.
- Page-level text.
- Unicode and whitespace normalization.
- Extraction result models.

---

## TASK-013 â€” Chunking

**Status:** Completed.

### Deliverables

- Token-aware chunker.
- Overlap.
- Metadata.
- Unit tests.

---

## TASK-014 â€” pgvector and embeddings

**Status:** Completed.

### Deliverables

- Extension migration.
- Chunk model with vector.
- Embedding provider interface.
- Batch embedding.

---

## TASK-015 â€” Document processing pipeline

**Status:** Completed.

### Deliverables

- End-to-end worker.
- Idempotent reprocess.
- READY/FAILED state.

---

## TASK-016 â€” Retrieval service

**Status:** Completed.

### Deliverables

- Semantic search.
- Permission filtering.
- Top-k and threshold.
- Leakage tests.

---

## TASK-017 â€” Keyword and hybrid search

**Status:** Completed.

### Deliverables

- PostgreSQL full-text search.
- Hybrid score merge.
- Permission-aware hybrid retrieval.

---

## TASK-018 â€” Chat data model and APIs

**Status:** Completed.

### Deliverables

- Session and message models.
- Create/list/read session.
- Ownership checks.
- Visible message history.

---

## TASK-019 â€” LLM provider and grounded answer

**Status:** Completed.

### Deliverables

- LLM provider interface.
- OpenAI-compatible provider.
- Grounded prompt builder.
- Context token budget.
- No-answer behavior.
- Atomic USER/ASSISTANT persistence.
- POST Chat message endpoint.

---

## TASK-020 â€” Citation validation

**Status:** Completed.

### Deliverables

- Source markers.
- Citation mapping.
- Permission revalidation.
- Excerpt response.
- MessageCitation model and migration.
- Citation-enriched Chat responses and history.

---

## TASK-021 â€” Feedback

**Status:** Completed.

### Deliverables

- Upsert feedback.
- Manager/Admin reporting scope.

---

## TASK-022 â€” Audit log expansion

**Status:** Completed.

### Deliverables

- Audit service.
- Admin filters.
- Events for documents and chat.

---

## TASK-023 â€” Docker full backend stack

**Status:** Completed.

### Deliverables

- Backend container.
- Worker container.
- Startup/migration flow.

---

## TASK-024 â€” CI pipeline

**Status:** Completed.

### Deliverables

- GitHub Actions workflow in `.github/workflows/ci.yml`.
- Python 3.12 setup with pip cache.
- Dependency installation from `pyproject.toml`.
- PostgreSQL service container with pgvector extension verification.
- Redis service container with health verification.
- Alembic `upgrade head` with single-head and current-equals-head checks.
- Ruff lint and format checks.
- Unit, API, integration, and marker pytest suites.
- Combined coverage XML report.
- Security scan for forbidden schema creation, pickle serialization, raw SQL interpolation, hardcoded secrets, production debug, and unsafe logging.
- Docker runtime build verification.
- Docker Compose config validation.
- Artifact upload for `coverage.xml`, pytest reports, and logs.

---

## TASK-025 â€” MVP hardening

**Status:** Completed.

### Deliverables

- Rate limiting.
- CORS config.
- Upload edge cases.
- Retrieval evaluation set.
- Security regression tests.
- Static retrieval evaluation fixture.

### TASK-025 verification

- Production configuration validation.
- CORS and trusted-host enforcement.
- Security headers and request-size limiting.
- Upload edge-case hardening and error-code coverage.
- Redis-backed rate limiting.
- Database/Redis timeout and pool configuration.
- Celery JSON-only and bounded time-limit configuration.
- Safe generic exception responses and logging redaction.
- Docker `no-new-privileges` runtime hardening.
- Backup/restore and release checklist documentation.

### Final recovery verification

- Docker Desktop API recovered; `docker version`, `docker info`, `docker ps`, and Compose v5.2.0 worked.
- Compose config passed with PostgreSQL, Redis, migration, API, worker, and test profile services.
- PostgreSQL and Redis were healthy; migration exited 0; Alembic current/head stayed at `20260722_0009`.
- API and worker ran Python 3.12.13 as non-root UID 10001.
- DB-backed auth, administration, document, chat, citation, feedback, and audit tests passed with no zero-match suite counted.
- Celery, embedding, processing, semantic, hybrid, and LLM provider marker suites passed.
- End-to-end Docker API smoke passed with login, department/user creation, PDF upload, worker processing to READY, permission grant, chat session, expected `LLM_NOT_CONFIGURED` grounded path with runtime LLM disabled, feedback, feedback report, audit report, RBAC checks, and rate-limit checks.
- Persistence survived `docker compose down` / `docker compose up -d` without `-v`; database rows, upload file, READY status, chat session, feedback, audit rows, and model cache were retained.
- PostgreSQL and Redis failure/recovery checks passed.
- Security scan, Ruff, format check, compile, Docker `pip check`, and host `pip-audit` passed.
---

## Phase 2 Roadmap

Phase 2 extends the completed backend MVP with multi-provider LLM support, streaming UX readiness, a working frontend console, conversation memory, multimodal and web inputs, operational analytics, observability, production deployment, enterprise authentication, and the v2.0 release.

---

## TASK-026 â€” Multi-LLM Provider Support

**Status:** Completed.

### Goal

Extend the current LLM abstraction to support multiple safely configurable providers without changing grounded-answer or citation-validation contracts.

### Provider scope

- OpenAI-compatible providers, including OpenAI, OpenRouter, Ollama OpenAI endpoint, LM Studio OpenAI endpoint, and custom enterprise gateways.
- Azure OpenAI.
- Google Gemini.
- Anthropic Claude.

### Acceptance criteria

- Provider registry/factory validates supported provider names and creates providers lazily.
- LLM disabled requires no provider keys.
- Only the selected enabled provider requires its provider-specific configuration.
- Provider secrets are hidden from repr, logs, and validation errors.
- No provider network call happens during import or application startup.
- Provider calls use bounded timeout, bounded retry, backoff, and safe error normalization.
- Raw provider request/response bodies, prompts, retrieved context, answers, document text, citation excerpts, API keys, and authorization headers are not logged or returned.
- OpenAI-compatible, Azure OpenAI, Gemini, and Anthropic adapters normalize content, finish reason, usage, provider name, model, and safe request id when available.
- Ollama, LM Studio, and OpenRouter are supported through the shared OpenAI-compatible adapter.
- Grounded-answer, selected-context, citation-validation, no-answer, and rollback behavior remain provider-independent.
- Existing Chat API request/response compatibility is preserved.
- Docker startup works with `LLM_ENABLED=false` and no LLM container is added.
- No database migration is introduced unless provider/model metadata storage becomes strictly required.
- Unit, API, integration, LLM provider marker, security scan, Ruff, format, and compile checks pass.

### TASK-026 verification

- Completed Docker/Python 3.12 runtime verification after safe storage cleanup and Docker Desktop/WSL backend recovery.
- Verified default Docker stack starts with `LLM_ENABLED=false`, no external provider container, no provider credentials required, and no LLM provider network call on import.
- Verified Alembic head/current remained `20260722_0009` with a single source head and no migration created.
- Verified Multi-LLM provider marker, provider unit, Chat API, grounded-answer, citation, rollback, privacy, Docker `pip check`, security scan, Ruff, format, and compile checks.

---

## TASK-027 â€” Streaming Chat with Server-Sent Events

**Status:** Completed.

### Goal

Add controlled streaming chat responses using Server-Sent Events while preserving grounded-answer, citation validation, audit, feedback, and persistence guarantees.

### Acceptance criteria

- Streaming endpoint or mode is designed without breaking the existing non-streaming Chat API.
- Partial tokens are never persisted as final answers before citation validation succeeds.
- Provider streaming errors return safe standardized errors and do not leak raw provider content.
- Client disconnect, timeout, retry, and cancellation behavior are bounded and tested.
- Citation markers are validated before final answer persistence and public citation display.
- Rate limiting and authentication apply to streaming requests.

### TASK-027 completion notes

- Added `POST /api/v1/chat/sessions/{session_id}/messages/stream` using `text/event-stream`.
- SSE event ordering is centralized and tested for started, delta, citations, completed, error, cancelled, and heartbeat events.
- Strategy is buffer-after-validation: no provisional provider tokens are public or persisted before grounding and citation validation pass.
- Provider streaming capability is represented as safe fallback metadata; native provider stream parsing is deferred until incremental grounding is designed.
- Docker runtime verification passed with Python 3.12.13, streaming marker, LLM provider marker, chat regression, citation regression, and provider unit tests.
- No schema migration was created; Alembic head remains `20260722_0009`.

---

## TASK-028 â€” Frontend UI Foundation & Test Console

**Status:** Completed.

### Goal

Create a professional, usable frontend interface for operating and testing the Enterprise AI Knowledge Assistant.

### Required frontend capabilities

- Authentication.
- Current-user profile.
- Department management.
- User management.
- Document upload.
- Upload progress.
- Document processing status.
- Document list and detail.
- Document permissions.
- Chat sessions.
- Chat messages.
- Streaming response UI.
- Citation display.
- Feedback submission.
- Feedback report access.
- Audit-log access.
- LLM provider/model selection when permitted.
- Health/readiness status.
- Rate-limit feedback.
- Standard loading, empty, and error states.

### Interface requirements

- Professional enterprise visual design.
- Responsive desktop-first layout.
- Accessible controls.
- Clear navigation.
- Consistent design system.
- Dark/light theme readiness.
- Reusable components.
- Typed API client.
- Authentication state management.
- Error boundary.
- Loading skeletons.
- Empty states.
- Toast/notification system.
- Form validation.
- Permission-aware navigation.
- No fake production data.

### Scope boundary

TASK-028 is the working and testing interface for the existing system. TASK-032 is the advanced analytics dashboard and must not duplicate TASK-028 scope.

### TASK-028 verification notes

- React/TypeScript/Vite frontend implemented in `frontend/` with typed API client, auth state, protected routes, role-aware navigation, documents, chat with POST SSE, citations, users, departments, feedback, audit logs, system status, profile, reusable states, and controlled motion primitives.
- Stitch workflow, screen prompts, design system, screen inventory, React Bits inventory, frontend architecture, and frontend testing docs created in `docs/ui/`.
- Frontend lint, typecheck, Vitest, Playwright smoke E2E, production build, and Docker frontend build passed.
- Docker backend regression passed for streaming chat marker, LLM provider marker, auth/RBAC, documents, chat, citations, feedback, audit logs, rate limiting, security scan, Ruff, format, compile, host pip check, and Docker pip check.
- TASK-028 live UI acceptance recovery passed with the real Docker frontend/backend stack, idempotent UAT seed, verified Admin/Manager/Staff accounts, upload-to-READY, permissions grant/revoke, live SSE chat, citations, feedback, audit, responsive and keyboard smoke, frontend quality gates, mock E2E, live E2E, and backend regression suites.
- UAT account stability fix keeps Development Admin separate from fixed UAT Admin/Manager/Staff accounts and makes `compose.uat.yaml` run an idempotent one-shot `uat-seed` without resetting volumes or deleting unrelated users.
- TASK-029 Conversation Memory is completed. TASK-030 OCR and Image Understanding recovery is in progress and is not completed until Docker/API/integration acceptance passes. TASK-032 analytics was not implemented.

### Acceptance criteria

- Frontend foundation runs locally and communicates with the backend through a typed API client.
- Authenticated and permission-aware navigation is implemented.
- Core backend workflows can be operated from the UI without fake production data.
- Chat UI can display standard and streaming answer states, citations, provider/model status when allowed, and safe error/rate-limit feedback.
- Reusable design-system components cover forms, tables, navigation, skeletons, empty states, errors, notifications, and theme readiness.
- Frontend tests or documented verification cover primary workflows and permission-aware states.

---

## TASK-029 -- Conversation Memory

**Status:** Completed.

### Goal

Add configurable same-session conversation memory that improves follow-up questions without allowing old chat content to bypass document permissions or grounded-answer policy.

### Implemented

- Added `ConversationContextBuilder` in `app/chat/conversation_context_builder.py`.
- Loads USER, ASSISTANT, and internal SYSTEM messages from the current owned ChatSession only.
- Orders memory by `created_at ASC, id ASC` and removes duplicate message IDs.
- Trims the memory window by `CHAT_HISTORY_MAX_MESSAGES` and `CHAT_HISTORY_MAX_TOKENS`.
- Formats prompt history as a bounded `<conversation_history>` block.
- Builds a bounded retrieval query that includes selected recent history plus the current question.
- Keeps Hybrid Retrieval mandatory and preserves grounded no-answer behavior.
- Keeps citations tied only to retrieved context source markers.
- Applies the same behavior to non-streaming `/messages` and streaming `/messages/stream` because both use `GroundedAnswerService.answer_question()`.
- Adds no migration, schema, memory table, cache, vector memory, summary memory, or LLM summarization.
- Does not persist formatted prompts or formatted conversation history.

### Verification

- Unit tests cover builder formatting, ordering, de-duplication, message limit, token budget, retrieval-query bounding, prompt format, citation-source separation, and service behavior.
- Integration tests cover leave-policy and working-policy follow-ups, no-answer follow-ups, repository filtering, internal SYSTEM memory handling, and citation mapping with source-like markers in history.
- API tests cover non-streaming same-session isolation.
- Streaming tests cover `/messages/stream` memory parity.

### Acceptance criteria

- AI remembers conversation within the same session.
- AI does not remember other sessions.
- ConversationContextBuilder owns memory load, trim, token budget, and format.
- Message and token limits are configurable.
- No migration or schema change is introduced.
- Prompts are not persisted.
- Streaming, non-streaming, citation, grounding, no-answer, Docker, regression, and documentation checks are required for completion.

---
## TASK-030 -- OCR and Image Understanding

**Status:** In Progress.

### Goal

Extend ingestion and retrieval to support OCR and image-based document understanding with safe processing limits.

### Implemented during recovery

- Upload validation accepts `application/pdf`, `image/png`, and `image/jpeg` with matching extensions and signatures.
- Storage keys use the server-selected primary extension (`.pdf`, `.png`, `.jpg`) and never trust client paths.
- `ExtractionRouter` keeps native PDF text when usable, OCRs low-quality/scanned PDF pages, and OCRs standalone PNG/JPEG documents.
- OCR runs through an `OCRProvider` abstraction backed by Tesseract; no OCR subprocess runs at import/startup.
- Image safety validation uses Pillow verify/reopen, EXIF transpose, RGB conversion, PNG normalization, and bounded width/height/pixel limits.
- Extracted pages preserve `page_number`, `extraction_method`, `source_type`, optional confidence, width, height, and warnings for downstream chunk/retrieval/citation metadata.
- The existing Celery document-processing pipeline passes stored MIME metadata to the extractor without changing the upload or Chat API contracts.
- Dockerfile runtime installs `tesseract-ocr`, `tesseract-ocr-eng`, and `tesseract-ocr-vie`.
- No schema migration was added; Alembic source head remains `20260722_0009`.

### Recovery verification completed

- `python -m pytest tests/unit -q` passed: 876 passed.
- TASK-030 focused OCR suite passed: 152 passed.
- Conversation/grounding/citation/OCR-source unit compatibility passed: 65 passed.
- Default non-integration suite passed: 957 passed, 643 deselected by configured integration marker filtering.
- Default API directory passed: 46 passed, 226 deselected.
- Default integration directory non-integration selection passed: 26 passed, 417 deselected.
- `python -m ruff check .` passed.
- `python -m ruff format --check .` passed.
- `python .github/scripts/security_scan.py` passed.
- `python -m compileall app tests` passed.
- `alembic heads` reports `20260722_0009 (head)`.

### Current blocker

Docker runtime acceptance is blocked in the local environment. Docker Desktop Service is stopped; `Start-Service com.docker.service` is denied even with escalation; `docker compose ps`, `docker version`, `docker info`, and `docker desktop restart` time out. Local Postgres port `55432` is open, but asyncpg connection startup times out, so Alembic `upgrade head/current` and Docker-backed API/integration suites cannot be counted as passing.

### Acceptance criteria

- OCR/image processing is asynchronous and bounded: implemented locally, Docker worker runtime not verified.
- Extracted text keeps page/source metadata for retrieval and citations: implemented and unit verified.
- Unsupported, encrypted, oversized, or low-quality files fail safely: implemented and unit verified.
- No OCR model download or external call occurs during import/startup: implemented by subprocess-only Tesseract provider and unit verified.
- Docker/API/worker/Postgres/Redis/migration verification: blocked by Docker runtime availability.

---

## TASK-031 -- Web Search Integration

**Status:** Completed.

### Goal

Add controlled web search as an optional source with clear provenance and policy separation from internal enterprise documents.

### Implemented

- Added `app/web_search/` with provider protocol, provider registry, provider manager, mock provider, Bing provider, DuckDuckGo provider, and Google Custom Search provider.
- Added backend-only `WEB_SEARCH_MODE` values: `internal_only`, `hybrid`, and `web_only`.
- Added config for enabled state, provider, max results, timeout, max content length, external-call allow flag, user agent, retry, provider endpoints, and provider credentials.
- Added `WebSearchIntentClassifier` so hybrid mode keeps internal retrieval first and adds web search only for current/web intent or empty internal hits.
- Integrated web search into `GroundedAnswerService` without changing non-streaming or streaming Chat API request bodies.
- Added web content and URL normalization that strips HTML/script/style/hidden/comment/control data, bounds content, rejects unsafe URLs, and does not fetch raw webpages.
- Added `CitationSourceType` with `INTERNAL` and `WEB`.
- Added web citation persistence fields and migration `20260803_0010_add_web_search_citations.py`.
- Internal citations keep document/chunk permission revalidation; web citations use backend provider title and URL and no internal document IDs.
- Added Admin-only `/api/v1/web-search/provider-status` and `/api/v1/web-search/test` endpoints.
- Added unit, API, streaming, and migration tests for web search behavior.

### Final verification completed

- Focused TASK-031 unit suite: 137 passed.
- Web Search unit suite: 25 passed.
- Web Search admin API integration suite: 3 passed.
- Chat/citation/streaming API integration acceptance suite: 8 passed.
- Web citation migration integration suite: 2 passed.
- Conversation Memory integration suite: 4 passed.
- Grounded answer citation/persistence integration suites: 8 passed.
- Hybrid retrieval integration suite: 19 passed.
- Citation revalidation and message citation migration integration suites: 17 passed.
- Default non-integration regression suite: 997 passed, 650 deselected.
- `python -m ruff check .` passed.
- `python -m ruff format --check .` passed.
- `python -m compileall app tests` passed.
- `python .github/scripts/security_scan.py` passed.
- `docker version`, `docker info`, `docker compose config`, `docker compose build --quiet`, `docker compose up -d`, and `docker compose ps` passed.
- PostgreSQL, Redis, API, worker, migration, API health, and Alembic current/head/upgrade checks passed in Docker.
- Runtime smoke verified default disabled/internal-only provider status, no-answer chat, SSE streaming, UAT internal citation, mock-provider `internal_only`, `web_only`, `hybrid`, no-internal-hit intent, and web citation source typing.

### Acceptance criteria
- Web search is disabled by default and configured explicitly: implemented and unit tested.
- Search results are marked separately from internal document sources: implemented through `source_type` and schema/migration.
- Data residency and external transfer warnings are documented: implemented in README, SECURITY, SETUP, ENVIRONMENT_VARIABLES, RAG_DESIGN, and API_SPEC.
- Citations distinguish web sources from internal document citations: implemented and verified by unit, API, streaming, DB-backed migration, and runtime smoke checks.

---

## TASK-032 -- Admin Dashboard & System Monitoring

**Status:** Completed.

### Goal

Provide backend-only administrative monitoring for system health, providers, workers, queues, version, uptime, and safe aggregate statistics.

### Acceptance criteria

- Dashboard scope is analytics/reporting, not the core operating console from TASK-028.
- Aggregations avoid exposing chat content, prompts, retrieved context, citation excerpts, feedback reasons, or secrets.
- Role-based access is enforced server-side.
- Metrics are documented and tested for safe filtering/pagination.

---


### TASK-032 completion notes

Implemented backend-only Admin Monitoring APIs under `/api/v1/admin`:

- `GET /api/v1/admin/system`
- `GET /api/v1/admin/health`
- `GET /api/v1/admin/providers`
- `GET /api/v1/admin/workers`
- `GET /api/v1/admin/statistics`
- `GET /api/v1/admin/queues`
- `GET /api/v1/admin/version`

The APIs reuse existing Admin RBAC, return safe aggregate/status data only, and do not expose secrets, prompts, retrieved context, chat content, citation excerpts, feedback reasons, storage keys, database URLs, Redis URLs, or API keys.

Monitoring covers API uptime, PostgreSQL, Redis, Celery worker, OCR, embedding configuration, LLM provider configuration, Web Search provider configuration, streaming registration, conversation memory configuration, queue state, statistics, and version/Alembic metadata.

No migration was created; Alembic head remains `20260803_0010`. No frontend/UI/Localization/Chat/Streaming/Conversation/Citation/OCR/Web Search behavior was changed.

Verification: focused unit/API integration, RBAC/provider API regression, default backend regression, Ruff, format check, compile, security scan, Alembic, Docker Compose, API/worker/PostgreSQL/Redis/migration/OCR runtime checks, Celery worker ping, and live Docker Admin monitoring endpoint smoke passed.

## TASK-033 -- Analytics & Reporting

**Status:** Completed.

### Goal

Add analytics and reporting for usage, feedback trends, document processing, retrieval quality, and safe operational reporting.

### Acceptance criteria

- Structured metrics cover safe request, dependency, retrieval, LLM, worker, and queue metadata.
- Logs remain redacted and content-free.
- Health/readiness and alerting guidance are documented.
- Trace/span data does not contain prompts, document text, answers, or secrets.


### TASK-033 completion notes

Implemented backend-only Admin Analytics APIs under `/api/v1/admin`:

- `GET /api/v1/admin/analytics/overview`
- `GET /api/v1/admin/analytics/chat`
- `GET /api/v1/admin/analytics/users`
- `GET /api/v1/admin/analytics/search`
- `GET /api/v1/admin/analytics/ocr`
- `GET /api/v1/admin/analytics/llm`
- `GET /api/v1/admin/analytics/feedback`
- `GET /api/v1/admin/analytics/audit`
- `GET /api/v1/admin/reports/export`

The APIs reuse existing Admin RBAC, support today/7d/30d/90d/custom UTC date filters, return safe aggregate analytics only, and export sanitized JSON/CSV reports. PDF export is intentionally rejected until safe backend PDF report infrastructure exists.

Analytics cover chat questions, sessions, average response time, token usage, active users, top users, top departments, new users, citation-inferred internal/hybrid/web searches, hashed top queries, top cited documents, image-document OCR success/failure, LLM latency/failures/token usage, feedback percentages/trends, and audit categories.

No migration was created; Alembic head remains `20260803_0010`. No frontend/UI/React/charts/Localization/Chat/Streaming/Conversation/Citation/OCR/Web Search/Celery behavior was changed.

Verification: unit analytics, API integration analytics, Admin/RBAC/Web Search monitoring regression, default backend regression, Ruff, format check, compile, security scan, Alembic, Docker Compose, API/worker/PostgreSQL/Redis/migration runtime checks, Celery worker ping, and live Docker Admin analytics route smoke passed.
---

## TASK-034 -- Production Deployment & Observability

**Status:** Completed.

### Goal

Prepare backend production deployment and observability without adding AI features, frontend UI, charting, localization, or changes to Chat/RAG/Citation/Conversation/Streaming/OCR/Web Search behavior.

### Acceptance criteria

- Production Compose provides PostgreSQL, Redis, one-shot migration, API, worker, reverse proxy, runtime validation, startup validation, restart policy, healthchecks, resource limits, and log limits.
- Reverse proxy supports forward headers, request/upload limits, SSE compatibility, security headers, and HTTPS-ready example configuration without committed certificates.
- Observability exposes safe Prometheus metrics for API, worker, Redis, PostgreSQL, OCR, embedding, LLM, Web Search, Streaming, Conversation, queues, version, and uptime.
- Request IDs, trace hooks, latency metrics, and structured request logging avoid prompts, context, OCR text, citation excerpts, secrets, credentials, tokens, Redis URLs, and database passwords.
- PostgreSQL and uploads backup/restore helpers include verification and guarded restore behavior.
- Development Docker Compose remains supported.

### TASK-034 completion notes

Implemented backend-only production deployment and observability:

- Added `compose.prod.yaml`, `.env.production.example`, runtime validation, Docker secret-file compatibility, resource limits, restart policies, healthchecks, log-size limits, and volume ownership initialization.
- Added Nginx reverse proxy config with forward headers, security headers, upload/request limits, SSE buffering disabled for streaming routes, HTTPS example config, and external `/metrics` blocking.
- Added in-process Prometheus metrics, request ID context, traceparent capture hooks, request latency/status logging, and `/metrics` for internal scrape use.
- Added Prometheus scrape config and Grafana provisioning/dashboard files under `deploy/`.
- Added PostgreSQL and uploads backup/restore PowerShell helpers with verification and guarded overwrite switches.
- Added unit, API, and integration tests for metrics, logging safety, runtime validation, production compose, reverse proxy, Prometheus/Grafana provisioning, backup/restore guardrails, RBAC/security regression, and Docker config.
- No database migration was created; Alembic head remains `20260803_0010`.
- Verification passed: Ruff, format check, compileall, security scan, pip dependency audit, pip check, Alembic heads/current/upgrade, default regression, focused integration/API suites, production Compose config/build/up/ps, development Compose config/build/up/ps, API/worker/PostgreSQL/Redis/migration health, reverse proxy health, internal metrics safety, external metrics blocking, Celery ping, backup/restore checks, Redis/PostgreSQL degraded readiness and recovery, API restart, and worker restart.

---

## TASK-035 -- Final Acceptance Test & Release Candidate

**Status:** IN_PROGRESS — documentation, diagnostic,
local/mock verification, source-governance, and dependency
triage checkpoints are recorded through TASK-035.3M
(as of 2026-10-14), each within its documented scope.

Final release acceptance has NOT PASSED.
The TASK-035.3B candidate qualification FAILED its
independent unsupported-answer safety gate.
B19/B21/R18 remain OPEN/FAIL for current RC safety;
R05 API/worker skew remains UNRESOLVED.

Current RC identity: NOT_ESTABLISHED.
Approved deferrals: 0.
RC decision: NO-GO.

### Goal

Run final acceptance, release-candidate verification, and release-readiness documentation without starting post-release feature work.

### Acceptance criteria

- All completed-task acceptance criteria are verified or explicitly documented as deferred.
- Release candidate checks cover backend, frontend status, security, Docker, deployment, observability, data protection, backup/restore, failure recovery, and rollback.
- Documentation is current and does not include real secrets or fake production data.
- TASK-035 status is marked completed only after final acceptance verification passes.

### Notes

- The UAT UX + LLM configuration fix is not TASK-035.
- TASK-035 must not be marked completed by selector UX changes, fake UAT LLM verification, or focused UAT regressions alone.

---
## TASK-036 â€” Enterprise Release v2.0

**Status:** Pending.

### Goal

Prepare, verify, and document the Enterprise AI Knowledge Assistant v2.0 release.

### Acceptance criteria

- Release checklist covers backend, frontend, security, deployment, observability, data protection, and rollback.
- All Phase 2 acceptance criteria are verified or explicitly deferred.
- Documentation is current and does not include real secrets or fake production data.
- TASK-027 through TASK-035 statuses are accurate before release sign-off.

## TASK-034.1 -- Real / Local LLM Strict Grounded Runtime Acceptance

**Status:** In Progress.

TASK-034.1 stream timeout follow-up: local Ollama `qwen3:4b` SSE was verified for Nova Digital CEO, CTO, and NovaAssist twice each with no `STREAM_TIMEOUT`; full strict matrix acceptance remains required before completion.

### Goal

Verify the system as a real Enterprise RAG Assistant using a real/local LLM, newly uploaded unseen documents, permission-aware retrieval, strict grounded prompting, citation validation, no-answer behavior, streaming parity, failure safety, and content-free logging.

### Implemented so far

- Completed audit before coding.
- Kept deterministic UAT fake provider unchanged and excluded from real answer-quality acceptance.
- Reused existing TASK-026 provider architecture; no new provider was added.
- Selected Ollama as the recommended local acceptance provider path, with LM Studio as an alternative.
- Strengthened grounded prompt policy for strict evidence-only behavior.
- Added post-validation guard so `ANSWERED` cannot persist with zero validated citations.
- Added focused unit tests for strict prompt and invalid answered/no-citation behavior.
- Added skipped-by-default `real_llm_acceptance` report validator.
- Created ignored local acceptance artifacts under `artifacts/task-034-1/`.

### Remaining acceptance work

- Start Docker Desktop and verify PostgreSQL, Redis, API, worker, and migration health.
- Install/start a real local provider or configure an explicitly approved external provider.
- Upload/process the new unseen acceptance documents to READY.
- Run all required real-LLM question cases and existing regressions through non-streaming and streaming chat.
- Verify permissions and provider failures.
- Manually verify every factual claim against cited source excerpts.
- Validate the completed acceptance report with the `real_llm_acceptance` marker.

TASK-034.2 implementation started: No.
TASK-035 implementation started: No.


### RAG-H2.1 — Reranker Authority

**Status:** Implemented + unit verified; runtime verification pending.

#### Change

Corrected the post-reranker merge order in `app/services/grounded_answer_service.py`.

The previous implementation of `_preserve_reranked_hit_order()` iterated:

```python
for hit in (*ranked_hits, *reranked_hits):
```

which allowed the later prompt heuristic ranking to override the reranker's selected order.

It now iterates:

```python
for hit in (*reranked_hits, *ranked_hits):
```

so the reranker/fallback reranker remains authoritative and prompt ranking only appends remaining candidates.

A regression test was added to `tests/unit/test_grounded_answer_service.py` to enforce this contract.

#### Verification

```text
tests/unit/test_grounded_answer_service.py
61 passed in 2.46s

tests/unit/test_rag_accuracy_components.py
27 passed in 0.68s

Focused combined retrieval/RAG suite
147 passed in 2.38s
```

#### Runtime finding

The configured SentenceTransformer cross-encoder is currently unavailable at runtime and the application logs:

```text
Retrieval reranker unavailable; falling back to alignment reranking.
```

Therefore current runtime ranking uses the existing `HeuristicRetrievalReranker` fallback.

`RAG_DIAGNOSTICS_ENABLED` is not currently injected into the API container:

```text
Settings().rag_diagnostics_enabled = False
printenv RAG_DIAGNOSTICS_ENABLED = <empty>
```

Do not claim RAG-H2 runtime acceptance until the container receives the diagnostics setting and the real chat flow is retested.


### Runtime incident — LLM_GENERATION_FAILED (2026-08-19)

**Status:** Resolved.

Root cause was not Ollama. The provider stack and `/v1/chat/completions` endpoint were verified working with `qwen2.5:7b-instruct-8k`.

The application failure was a Python `NameError` in `GroundedAnswerService._draft_from_generation()`: a partially applied H5.1 change attempted to call claim validation with `question=grounding_question`, but `grounding_question` was not in that method's scope and the current validator signature did not accept `question`.

The invalid argument was removed to restore the previously supported validator contract.

Verification:

```text
pytest tests/unit/test_grounded_answer_service.py -q
61 passed in 1.34s

focused combined RAG/retrieval suite
147 passed in 2.41s

container source verification:
"question=grounding_question" in _draft_from_generation -> False
```

Live chat no longer returns `LLM_GENERATION_FAILED`. Accuracy work remains open: the `Head` salary query currently returns NO_ANSWER even though the source document contains the answer.

Diagnostics setting is `True`, but the expected INFO-level RAG diagnostic messages are not visible in current Docker logs. Logging visibility must be investigated before changing retrieval logic.

### RAG salary amount quality-gate fix — 2026-08-19

**Status:** PASS (unit + runtime).

Root cause: generic quantity completeness logic treated salary `AMOUNT` questions as generic quantity questions and could misread grade labels such as `N6 Head` as number/unit evidence. This caused already-supported salary answers to be retried repeatedly and converted to NO_ANSWER.

Fix:
- gate generic quantity completeness by analyzed answer type rather than raw `bao nhieu` / `how many` wording;
- preserve DURATION/COUNT/NUMBER protections;
- prefer exact question value units before normalized-family fallback.

Verification:
- `tests/unit/test_grounded_answer_service.py`: 63 passed.
- focused combined RAG/retrieval suite: 149 passed.
- runtime: `Head` -> `65 - 110 triệu đồng`.
- runtime: `Engineering Manager` -> `42 - 70 triệu đồng/tháng`.

Next:
- YES/NO presentation/quality issue is confirmed separately. Retrieval and claim validation pass, but three supported drafts are rejected by `yes_no_missing_leading_polarity`.
- Citation evidence UX refinement remains pending: highlight the minimal supporting evidence used to derive the answer, not merely text copied verbatim into the final answer.
