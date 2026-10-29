# Project Status

## TASK-035.3M dependency exposure and remediation decision -- 2026-10-14

**COMPLETED for read-only triage; dependency remediation and CI implementation NOT AUTHORIZED; RC NO-GO.** Six 035.3M reports identify seven version-matching frontend advisories across five dev-tool lock entries, trace actual ESLint/PostCSS/Vite/Vitest call paths, separate assessed production-static-bundle absence from build/development exposure, and propose package-specific fixes plus CI gates. Four brace advisories and Vite are recommended for pre-candidate remediation; nanoid/Vitest current paths have scoped not-applicable recommendations requiring security-owner acceptance. OSV and PyPI public-only backend audit attempts both failed DNS, so full backend and image advisory coverage remain **NOT VERIFIED**. No production code, manifest, lock, workflow, Docker/V2 resource, Git index or historical evidence was changed. Source versioning approval **NOT GRANTED**; current RAG B19/B21/R18 safety **OPEN/FAIL**, API/worker R05 skew **UNRESOLVED**, full-tree Ruff and eight-path staging whitespace FAIL, TASK-035 **IN PROGRESS**, RC **NO-GO**, approved deferrals **0**. Historical H5.2 V2 98/98 and failed 035.3B candidate remain distinct.

## TASK-035.3L dependency security and CI qualification -- 2026-10-14

**COMPLETED as bounded evidence and remediation proposal; RC NO-GO.** Seven current reports are in `docs/release/TASK-035.3L-*20261014.md`. Targeted official advisory review found five affected frontend dev-tool lock entries across seven distinct advisories, while the checked React Router RSC-CSRF issue does not affect locked 7.18.2. Their deployed exploitability is unproven. Fresh full frontend/backend and container scans are **NOT VERIFIED**; host Python 3.11 differs from required >=3.12, pip-audit public-pin query failed DNS, and no image scanner/SBOM was available. Local app-only Ruff/format/compile/narrow security scan and frontend type/lint/Vitest 40/40/mocked Chromium 15/15/isolated build passed in limited scope; no current CI run or live candidate qualification was shown. Full-tree Ruff and eight-path staging whitespace failures persist. RAG unsupported-answer safety B19/B21/R18 **OPEN/FAIL**, active API/worker skew R05 **UNRESOLVED**, source versioning approval **NOT GRANTED**, TASK-035 **IN PROGRESS**, RC **NO-GO**. Historical H5.2 V2 acceptance is not promoted to this source state. No production source, dependency/lock, CI, Docker image, active V2 or original Git index was modified.

## TASK-035.3K source versioning approval gate -- 2026-10-14

**COMPLETED for bounded review; READY_FOR_VERSIONING_APPROVAL NO, RC NO-GO.** At entry all 035.3J 666-path identities, 495-file source archive and key historical captures matched; the subsequent authorized `TASKS.md` and `PROJECT_STATUS.md` updates are the two expected documentation hash differences from the frozen manifest. Its self-path is not hashed within the list. All 103 review-required paths await owners; the locally present Gitlink still lacks a documented/reachable fetch path and verified license. In an independent 497-file simulation, exact staged membership and copy hashes passed, but `git diff --cached --check` failed with 15 findings in eight paths. Original `.git/index` SHA-256 remained unchanged. Selected Ruff and 49 focused units passed; full-tree Ruff remains failed. See `docs/release/TASK-035.3K-*20261014.*`. No owner approval, commit, tag, push, source/runtime change, off-host backup or independent reproducible build was established. H5.2 historical 98/98 and frozen 035.3B failure remain separate; RAG answer safety **OPEN/FAIL**, active API/worker skew **UNRESOLVED**, TASK-035 **IN PROGRESS**, RC **NO-GO**.

## TASK-035.3J reviewed source selection/versioning readiness -- 2026-10-14

**COMPLETED as a bounded decision package; source selection READY_FOR_REVIEW,
versioning approval NOT READY, RC NO-GO.** The 035.3I 495-file archive and
all selected original hashes remain intact. An exact per-path proposed Git
staging manifest and five companion decisions classify production source,
tests/tooling, docs, experiments, private evidence, generated output and
owner-review paths. The locally available `vite-monorepo` Gitlink lacks a
parent `.gitmodules` fetch mapping and nested origin, so fresh-clone
recoverability is not established. Full original repository Ruff failures
remain visible. No Git add/commit/tag/push, source edit, image/service or
database action occurred. See `docs/release/TASK-035.3J-*20261014.*`.
Historical H5.2 V2 98/98 remains scoped PASS; frozen 035.3B candidate remains
FAILED; 035.3H frontend mock correction remains PASS in its scope. RAG
unsupported-answer safety **OPEN/FAIL**, B19/B21/R18 open, active API/worker
skew **UNRESOLVED**, approved deferrals **0**, TASK-035 **IN PROGRESS**, RC
**NO-GO**.

## TASK-035.3I source hygiene/reproducible baseline preparation -- 2026-10-14

**COMPLETED for bounded local inventory/preservation; RC NO-GO.** Full
working-tree classification and a unique 495-file reviewed source tar were
created with per-file SHA-256 and independently verified extraction. Shared
035.3A source paths show zero hash drift; the 035.3H frontend correction is
included, but the frozen 035.3B candidate remains FAILED. Full repository
Ruff check/format still FAIL on preserved scratch/research files; the
filtered source copy passes both. Focused extracted units 49/49 and current
frontend type/lint/Vitest 40/40/mocked Chromium 15/15/isolated build passed
in their scopes; one broader unit attempt was interrupted without result.
No production source, service, database, Git history or historical evidence was changed;
one release-inventory script and the checkpoint documents were added.
See the six `docs/release/TASK-035.3I-*20261014.md` reports. Source archive is
local, not independent build or off-host DR proof. RAG answer safety
**OPEN/FAIL**, B19/B21/R18 open, API/worker skew **UNRESOLVED**, deferrals
**0**, TASK-035 **IN PROGRESS**, RC **NO-GO**.

## TASK-035.3H confirmation-dialog keyboard remediation -- 2026-10-14

**COMPLETED in local frontend scope; RC NO-GO.** Both 035.3G dialog failures
were reproduced and corrected in the shared frontend component. Focused
component tests passed 4/4; focused mocked Chromium accessibility passed
6/6; full frontend typecheck and isolated build passed; lint passed with
seven unchanged warnings; Vitest passed 40/40 and mocked Chromium passed
15/15. The [035.3H report](docs/release/TASK-035.3H-confirmation-dialog-remediation-20261014.md)
records root cause, source/test hashes, before/after focus behavior and
remaining gaps. P14's dialog sub-check is closed; P14/R19 live/broader
accessibility criteria are not fully accepted. No backend, active V2 runtime,
failed candidate, dependency, origin or source-map configuration was changed.
RAG unsupported-answer safety **OPEN/FAIL**, API/worker skew **UNRESOLVED**,
approved deferrals **0**, TASK-035 **IN PROGRESS**, RC **NO-GO**.

## TASK-035.3G frontend delivery/accessibility verification -- 2026-10-14

**COMPLETED for its local static/mock scope with newly verified keyboard
FAILURES; RC NO-GO.** Typecheck/build and 36/36 Vitest passed; lint had seven
warnings. Mocked Chromium 11/13 passed; both failures concern confirmation
dialog focus and Escape. The previously existing nine mocked tests passed.
The build-time localhost fallback and referenced source-content map are
verified local configuration/exposure risks, not proof of a production
misconfiguration or public secret leak. Static frontend/backend contract
comparison found no established live compatibility result. Source-hygiene
Ruff failures remain; no file was discarded. See five
`docs/release/TASK-035.3G-*20261014.md` reports and the 035.2 matrix
addendum. Active V2 service identities remained unchanged and healthy; no
live E2E or protected data operation ran. RAG answer safety remains
**OPEN/FAIL**, API/worker skew **UNRESOLVED**, deferrals **0**, TASK-035 **IN
PROGRESS**, RC **NO-GO**.

## TASK-035.3F independent qualification -- 2026-10-14

**COMPLETED in static/mock/host-unit scope; RC NO-GO.** Frontend typecheck,
build, 36 Vitest units and nine mocked Chromium E2E tests passed; lint passed
with seven warnings. Backend app-only Ruff/format, host Python 3.11 compile,
`pip check`, limited security scan and 1423 non-red unit tests passed (three
expected failures). Repo-wide Ruff/format are not green because pre-existing
scratch/experimental files fail; red 035.3C.2 and 035.3E safety contracts
were excluded from the non-red unit run and remain open. Compose config syntax
passed; no image or service changed. Live frontend, current vulnerability
data, production TLS, full security/observability and rollback remain gaps.
Five evidence/plan documents are linked from `TASKS.md` and the 035.2 matrix
addendum. Accepted H5.2 V2 scope is preserved; frozen 035.3B candidate still
FAILED. Unsupported-answer safety and current B19/B21 RC materiality are
OPEN, active API/worker skew UNRESOLVED, approved deferrals 0, TASK-035 IN
PROGRESS, RC NO-GO.

## TASK-035.3E context-admission investigation -- 2026-10-14

**COMPLETED as bounded investigation; NO DEFENSIBLE CORRECTION IDENTIFIED.**
The first observed unsafe progression in 035.3B was admission of two
permission-visible but question-irrelevant sources into answer context.
Synthetic A–O context tests completed 11 pass / 4 fail (all four intended
irrelevant-hit exclusions failed); 0/8 material-answer positive controls were
lost by the current permissive boundary. Two separate final-claim controls
both returned unsafe `SUPPORTED`. A zero-reranker-score or lexical
cutoff lacks defensible semantics and would risk multilingual false abstention.
Contradictory/incomplete context can be useful for correction or abstention,
so selection is not final-answer support. The independent final responsiveness
defect remains OPEN. Report:
`docs/release/TASK-035.3E-bounded-context-admission-investigation-20261014.md`.
Accepted V2 and frozen failed candidate identities/evidence were checked
read-only; no production source, service, database, model or corpus was changed.
TASK-035 remains **IN PROGRESS**, RC **NO-GO**, candidate **FAIL/preserved**,
source-level fix **NOT READY**, new candidate build **NOT READY**.

## TASK-035.3D release safety decision -- 2026-10-14

**COMPLETED as a bounded documentation/decision checkpoint; RC NO-GO.** The
known 035.3B permission-aware unsupported-answer defect is an open mandatory
safety blocker, despite historically valid H5.2 V2 and candidate broad 98/98
supported-case results. Direct RBAC denial passed, but unrelated accessible
evidence was admitted and its grounded yet nonresponsive answer returned
ANSWERED instead of NO_ANSWER with zero citations. Context admission and final
responsiveness show verified problems; exact generation/repair origin remains
UNKNOWN. The 80-criterion matrix has a dated current-status addendum for
B19/B21 and other affected rows; no unrelated historical PASS was erased.
Both 2E and 2F selected **NO SAFE MECHANISM**. Current release strategy is
explicit NO-GO; a bounded context-admission investigation is recommended only
under separate authorization. Narrowed scope is **UNPROVEN**, not approved.
See `docs/release/TASK-035.3D-release-safety-decision-20261014.md` and its
linked affected-criteria, blocker, owner-decision and next-action documents.
No production code, active V2 runtime, failed candidate, database, Redis,
model, corpus or release policy changed. TASK-035 **IN PROGRESS**, approved
deferrals **0**, RC sign-off **NOT GRANTED**.

## TASK-035.3C.2F obligation analysis -- 2026-10-14

**COMPLETED for bounded synthetic/offline research; NO SAFE MECHANISM
SELECTED.** A new independent 12-development/24-final-test manifest was frozen
before one-shot evaluation. Existing validation falsely accepted 11/14
non-ACCEPT final cases and rejected 3/10 valid answers. Automatic
question/evidence-only obligation extraction plus per-obligation E5 coverage
reduced unsafe accepts to 2/14 but rejected all 10 valid answers; the
intersection retained one unsafe accept and also rejected all 10. The
extractor missed all three genuine development/final authority conflicts.
The oracle-obligation cosine diagnostic also rejected all 10 final positives.
No final-test tuning occurred. Synthetic authorization scoping is not a
production RBAC or release-gate proof. Experimental artifacts and decision:
`docs/release/TASK-035.3C.2F-feasibility-decision-20261014.md` and
`artifacts/task-035-3c2f-20261014/`. Production source hashes and accepted
V2 container identities stayed unchanged in read-only checks; broad V2 and
database integrity were not rerun. TASK-035.3C.2 source correction remains
**PARTIAL / BLOCKED**, TASK-035 **IN PROGRESS**, frozen candidate
**FAIL/preserved**, and RC sign-off **NOT GRANTED**.

## TASK-035.3C.2E isolated multilingual entailment evaluation -- 2026-10-14

**COMPLETED for bounded synthetic/offline research; NO SAFE MECHANISM
SELECTED.** A new 36-case English/Vietnamese/mixed manifest (12 development,
24 held-out pilot) compared the existing claim validator, locally cached E5
similarity, and a constrained localhost Qwen judge. The existing validator
had 7/14 unsafe held-out acceptances and 5/10 false abstentions; E5 had 2/14
and 10/10; the initial judge had 0 and 10/10, with 2/36 malformed outputs.
A revised schema judge recovered development positives but falsely accepted
an omitted condition, negation reversal, and unresolved authority conflict;
its 12/12 repeated decisions repeated those errors. No new production source,
model dependency, image or deployment changed. Active V2 remained healthy;
the frozen failed candidate remains preserved and stopped. See
`docs/release/TASK-035.3C.2E-evaluation-design-20261014.md` and
`docs/release/TASK-035.3C.2E-decision-20261014.md`. TASK-035.3C.2 stays
**PARTIAL / BLOCKED**, TASK-035 **IN PROGRESS**, and RC sign-off **NOT GRANTED**.

## TASK-035.3C.2 multilingual responsiveness correction -- 2026-10-14

**PARTIAL / BLOCKED at the authorized design gate; no production correction.**
The synthetic A-O claim-validation contract completed 7 PASS / 8 FAIL: five
grounded-but-nonresponsive or incomplete claims falsely pass, while three
valid Vietnamese/mixed-language/conditional controls falsely abstain. Existing
035.3C.1 tests remain 4 PASS / 3 expected failures. No evidence-backed
generic deterministic or model-based decision rule yet preserves both sides;
a lexical gate or relative reranker cutoff would be unsafe. The approved
instruction to stop if no defensible correction is established was applied.
Only test and documentation files changed. V2 and the frozen failed candidate
retain their recorded container/image identities; neither was restarted or
rebuilt. See
`docs/release/TASK-035.3C.2-multilingual-responsiveness-design-stop-20261014.md`.
TASK-035 is **IN PROGRESS**, candidate qualification **FAIL**, and RC sign-off
**NOT GRANTED**.

## TASK-035.3C.1 runtime rebaseline and root-cause verification -- 2026-10-14

**COMPLETED for the authorized diagnostic scope; no production correction.**
Read-only accepted V2 verification passed for the documented 9 READY documents,
143 chunk identities/content hashes, 3 users, migration `20260822_0011`,
grants, source PDFs and H5.2 artifact hashes after the host restart. The
stopped 035.3B candidate, images and four volumes remain preserved; its
database integrity is **NOT VERIFIED** without separately authorized startup.
A host reboot is verified, but the precise exit-255 mechanism is unknown.
Synthetic controls reproduced the generic answer-responsiveness gap and a
Vietnamese false-abstention risk (4 passed, 3 expected failures); no code or
image was changed. The older 035.3C status below is historical and its V2
rebaseline uncertainty is superseded by this checkpoint. See
`docs/release/TASK-035.3C.1-runtime-integrity-root-cause-20261014.md`.
The failed candidate remains **FAIL**, TASK-035 **IN PROGRESS**, and RC sign-off
**NOT GRANTED**.

## TASK-035.3C permission-aware answer-relevance diagnostic -- 2026-10-14

**PARTIAL / BLOCKED; no generic correction implemented.** The failed 035.3B
capture and a synthetic probe establish that a verbatim cited clause can pass
claim validation while not answering the user's question. Reranker score zero
is not a calibrated irrelevance flag, and the complete generation/retrieval
causal chain is not preserved. During read-only inspection, all four isolated
035.3B containers were found exited with code 255; their images and volumes
remain. The accepted V2 containers were up/healthy but had recently restarted.
No services, databases, volumes or application source were modified in this
checkpoint. Current candidate DB integrity and post-restart V2 data baseline
are unverified, so remediation stopped under the integrity hard-stop rule.
See `docs/release/TASK-035.3C-permission-answer-relevance-diagnostic-20261014.md`
for boundary analysis and synthetic A-J regression design. The old candidate
remains **FAIL**; TASK-035 is **IN PROGRESS** and RC sign-off is **NOT GRANTED**.

## TASK-035.3B isolated candidate broad V2 requalification -- 2026-10-13

TASK-035.3B's authorized restore, frozen broad run, source/citation review,
safety/repeatability gates and post-run integrity assessment are **COMPLETED**.
The isolated candidate restored 9 READY documents/143 chunks/3 users with
verified grants and a successful second-database pre-run restore. Original
Q001-Q100 completed with 98/98 supported semantic/material answers, 101/101
persisted citation identities, and safe Q018/Q100 abstentions. The documented
nine-case repeat was 9/9 and existing six-case safety smoke was 6/6. However,
an independent STAFF private-policy question received an unrelated, cited
organization-document answer instead of NO_ANSWER. Direct private-document and
cross-user access were denied; no private-content leak was observed, but the
unsupported-answer safety gate **FAILED**. Overall candidate qualification is
**FAIL**, despite broad PASS. Active V2 and 035.3A synthetic resources stayed
intact. See
`docs/release/TASK-035.3B-isolated-candidate-qualification-20261013.md`.
TASK-035 remains **IN PROGRESS**; active API/worker skew remains, next release
verification is not ready, and RC sign-off is **NOT GRANTED**. No code change,
image rebuild or candidate promotion is authorized by this result.

## TASK-035.3A isolated candidate qualification -- 2026-10-13

TASK-035.3A is **COMPLETED for its authorized isolated build/compatibility scope**.
Two uniquely tagged candidate images share the same 217 application-file hashes,
92 exact installed package versions, and Python 3.12.15 runtime. Focused checks
passed (506 unit, 70 isolated-DB integration, static/security, Celery ping,
synthetic READY ingestion, materially supported citation, private-document RBAC
and safe NO_ANSWER). The accepted H5.2 V2 API/worker containers, images, Redis
mapping, and 9 READY/143 chunks/3 users/migration baseline stayed intact. The
active API/worker skew **still exists**; only the isolated candidate pair is
aligned. Candidate reproducibility is partial, and broad V2 acceptance on the
candidate has **NOT RUN**. See
`docs/release/TASK-035.3A-isolated-candidate-qualification-20261013.md`.
TASK-035 remains **IN PROGRESS**; TASK-035.3 overall and subsequent phases are
not complete. RC sign-off is **NOT GRANTED** and no deployment is authorized.

## TASK-035.2A RC candidate readiness planning -- 2026-10-13

TASK-035.2A is **COMPLETED as a planning-only checkpoint**. Read-only source,
corpus, evidence, image-identity and database checks found no material H5.2 V2
baseline drift. The eight-file API/worker source difference and 22 installed
package-version differences persist; no direct document-task source-path
regression was demonstrated, but single-candidate identity remains an RC
blocker. The conditional recommendation is to prepare one reviewed,
dependency-frozen API/worker candidate in isolation under separate approval
and then requalify it. See
`docs/release/TASK-035.2A-rc-candidate-readiness-20261013.md`. TASK-035 is
**IN PROGRESS**; TASK-035.3 has not started; RC sign-off is **NOT GRANTED**.

## TASK-035.2 acceptance traceability and deferral review -- 2026-10-13

TASK-035.2 is **COMPLETED as a read-only documentation checkpoint**. The
80-criterion acceptance matrix has 9 scoped PASS, 1 FAIL (API/worker candidate
identity skew), 17 NOT_RUN, 43 EVIDENCE_GAP, 7 CONFLICT, and 3
DEFERRAL_PROPOSED. The seven reviewed deferral proposals remain
`PENDING_REVIEW`; **zero are approved**. The original TASK-034.1 real-LLM
report remains IN_PROGRESS with empty case results and is not automatically
superseded by the passing H5.2 V2 qualification. Evidence:
`docs/release/TASK-035.2-acceptance-traceability-matrix-20261013.md`,
`docs/release/TASK-035.2-release-deferral-register-20261013.md`, and
`docs/release/TASK-035.2-verification-coverage-summary-20261013.md`.
TASK-035 remains **IN PROGRESS**; TASK-035.3 onward have not started. No current
frontend, production/security, isolated integration, or DR gate was executed
by this checkpoint. No RC sign-off is granted.

## TASK-035.1 baseline protection and contract reconciliation -- 2026-10-13

TASK-035 is **IN PROGRESS**, limited so far to the authorized 035.1 evidence
checkpoint. The accepted H5.2 V2 API image matches all 216 current application
Python files, while the older worker differs in eight RAG/chat/citation files
and 22 installed package versions. No direct Celery task/pipeline source
contract difference was found, but the version skew blocks an unqualified RC
candidate identity. Current source, image, corpus, evidence and Redis recovery
identities, along with unresolved release-authority decisions, are documented
in `docs/release/TASK-035.1-baseline-manifest-20261013.md` and
`docs/release/TASK-035.1-release-contract-reconciliation-20261013.md`.
TASK-035.2 onward are not started. **No RC sign-off**, commit, tag, external
backup, runtime rebuild, database write, or corpus change occurred.

## RAG-H5.2 V2 final qualification -- 2026-10-13

**RAG-H5.2 COMPLETED for isolated UAT Corpus v2; TASK-035 ELIGIBLE / NOT STARTED.**
The frozen final API image `sha256:1f057785bd8cacb68aa8573e3aa12e29a23c37692e0ad045997770d4adf2648e`
passed the broad Q001-Q100 run: 100/100 transport, 98/98 supported answers
manually checked against material source evidence, 101/101 valid persisted
citation identities, Q018 safe conflict abstention, Q100 safe unsupported
abstention, and zero infrastructure errors. Final-image safety/permission smoke
passed 6/6; high-risk repeatability passed 9/9. The previously independent
restored corpus passed corrected current-image smoke 6/6 and retained 9 READY
documents, 143 chunks, 3 users and migration `20260822_0011`. Active V2
services remain healthy with zero restarts/OOM. The 13-file backup package and
all nine source PDFs match SHA-256. Performance was measured (broad p95
23.75 s) without a repository-defined p95 ceiling.

This qualifies RAG-H5.2, **not** TASK-035 release-candidate sign-off. No
verified off-host backup is claimed; historical Celery accounting remains
UNKNOWN; Q018 policy precedence remains unresolved. The independent
restore-check API had a Docker stop anomaly after its passing smoke but is now
exited, and the active V2 stack was unaffected. Full evidence and limits:
`artifacts/uat-corpus-v2/h5-2-qualification-20261013.md` and the superseding
supported-failure ledger of the same date. Earlier checkpoints below are
historical and are superseded for current RAG-H5.2 status.

## RAG-H5.2 V2 qualification checkpoint -- 2026-10-12

**RAG-H5.2 remains IN PROGRESS; TASK-035 remains BLOCKED / NOT STARTED.**
Redis infrastructure recovery remains completed. The isolated V2 broad frozen
Q001-Q100 run completed 100/100 requests with zero transport errors, but this is
not a semantic pass. The applicability denominator remains 98 supported cases;
Q018 is an unresolved authority conflict and Q100 is unsupported safe NO_ANSWER.
Targeted generic RAG fixes closed Q042/Q043/Q045/Q047/Q048/Q050 and preserved
the current CEO/CTO, Q096, Q097, representative, and six-case smoke gates.
Supported Q055/Q080/Q084/Q088/Q089/Q091 remain confirmed failures; Q090 is
cross-run inconsistent, and several truncated/partial answers need adjudication.
The broad run predates the targeted fixes and has not been repeated on the final
image, so its current 98-case pass rate is not certified. Citation registry
identity is 95/95 in that broad capture, but material support has failures.
See `artifacts/uat-corpus-v2/h5-2-qualification-20261012.md` for case-level
evidence, performance, reproducibility limits, and the next checkpoint.

## Isolated UAT Corpus v2 Redis recovery -- 2026-10-12

**REDIS RECOVERY COMPLETED** after the approved Redis-only cutover and a further
read-only post-cutover verification. The active V2 Redis service is healthy on
`enterprise-ai-uat-v2_redis_recovered_cutover_20261010`; API live/ready are HTTP
200, worker and PostgreSQL are healthy, and Redis has zero restarts/OOM. The
monitored PostgreSQL baseline remains 9 READY documents, 143 chunks, 3 users,
and Alembic `20260822_0011`; backend source hash is unchanged. No Celery task
execution was observed, but historical Celery accounting is **UNKNOWN**. The
initial Redis autosave dirty-counter origin is unresolved although the saves
match configured thresholds and completed successfully.

The evidence and limitations are recorded in
`artifacts/uat-corpus-v2/redis-recovery-20261010/postreboot-cutover-integrity-20261011.md`.
This isolated V2 recovery does not resolve the separate historical September
corpus provenance gaps documented below. RAG-H5.2 remains **IN PROGRESS**;
TASK-035 remains **BLOCKED / NOT STARTED**. Resume RAG release work separately;
no broad benchmark was executed in this infrastructure finalization.

## RAG-H5.2 September corpus source recovery -- 2026-09-29

Authoritative-source forensics recovered and preserved nine verified source binaries
without changing any runtime or persistent volume:

- Six Nova Digital PDFs were found in the locally synchronized OneDrive folder
  `Máy tính/Chính sách ct`. Their filenames, exact byte sizes, document IDs,
  READY states, organization scope, page layout, and policy content agree with the
  retained UAT document-library screenshot and September RAG artifacts. The
  organization binary also matches the SHA-256 stored in the August database and the
  September artifact facts (`2021`, approximately `180` staff), excluding the later
  editable variant that contains different values.
- The exact generic leave-policy binary was recovered from the August upload archive.
  Its SHA-256 is
  `24178db420422e474326986672b6c15cc67373ee6adbe1489ba5e8addf95f4f4`, matching the
  September restoration ledger.
- The exact deterministic UAT grounding and shared-policy PDFs were recovered from the
  same archive. Their hashes match the stale database, while the seed path, screenshot,
  and September artifacts establish their logical metadata and access behavior.

The diagnostic manifest is
`artifacts/rag-h5-2-september-corpus-recovery/manifest.json`; recovered binaries are
copied under its `sources/` directory. Current classification is `9 VERIFIED_SOURCE`,
`1 PROBABLE_SOURCE`, `1 PARTIAL_SOURCE`, and `1 MISSING`. The probable entry is the private
`UAT Live Upload 1786697622220`: its ID, logical content, permission behavior, and
deterministic generator survive, but its original generated PDF/checksum do not. The
partial entry is retained successful-run binary `uat-live-1786698102732.pdf`; its
title, content, READY contract, and access behavior are recoverable, but its historical
database ID is not. One additional active READY record implied by the verified
12-document aggregate remains wholly unidentified.

Git history contains no tracked/deleted corpus files, and unreachable Git objects are
source/test/documentation snapshots rather than policy binaries. Targeted host,
OneDrive, Documents, Desktop, Downloads, and `E:` searches found no other September
source or database backup. Manual OneDrive recycle-bin/version-history recovery is now
required for the original `1786697622220` live-upload binary, the historical row for
`1786698102732`, and the final unidentified record.

Automatic isolated reconstruction is **NOT SAFE** because authoritative documents,
complete document metadata, and the permission manifest remain incomplete. No users,
documents, chunks, or embeddings were created; no H5.2 cluster or Exact-100 case was
run. RAG-H5.2 remains **IN PROGRESS** and TASK-035 remains **BLOCKED / NOT STARTED**.

## RAG-H5.2 runtime recovery forensic hard stop -- 2026-09-28

RAG-H5.2 remains **IN PROGRESS** and TASK-035 remains **BLOCKED / NOT STARTED**.
Compensation and cross-document synthesis retain their latest verified closed status.
No semantic cluster or Exact-100 case was executed in this checkpoint.

Read-only Docker and host forensics found no recoverable September runtime:

- Both visible Docker contexts target the same current Docker Desktop engine. The only
  Compose project is `enterprise-ai-knowledge-assistant`, and the only named volumes
  are its four fresh volumes created at `2026-09-28T14:24:15Z` or one second later.
- Docker Desktop logs show the former data disk could not be found by its disk ID and
  then report `detected no file system. Formatting` at `2026-09-28T14:05:15.514Z`.
  Older UI logs had shown 14 volumes before that restart. The current VHDX contains
  only the four new volume directories, so this is storage reinitialization rather
  than a CLI context or Compose-prefix mismatch.
- Read-only database counts remain `users=0`, `documents=0`, and `chunks=0`. API
  live/readiness are `200/200`, migration current/head is `20260822_0011`, restart
  count is `0`, and OOM killed is `false`; infrastructure health does not establish
  semantic-runtime readiness.
- The only database/upload backups are two 2026-08-09 PostgreSQL 17 custom dumps and
  their upload archives. They contain the expected tables, including users,
  documents, chunks, citations, and vector extension, but predate the September
  corpus. One upload archive contains only four synthetic UAT fixtures; the other
  contains older July/August uploads with different storage IDs. They are classified
  `STALE_PRE_SEPTEMBER_BACKUP`, not recovery candidates.
- The repository and Codex attachment directories contain no authoritative PDF/DOCX
  copies of the September policy corpus. Runtime artifacts preserve partial evidence
  and seven cited document IDs/titles, but not all 12 source binaries or complete
  document metadata. The documentation ZIP is documentation-only.

Expected September provenance remains: three UAT roles/accounts, 12 active READY
documents, 153 active chunks, 384-dimensional embeddings, and the recorded acceptance
document IDs. The restored leave document provenance is still documented below, but
its source PDF is not presently available. Exact recovery is therefore unavailable,
and deterministic reconstruction is only partial from current repository artifacts.

No seed, restore, document ingestion, user creation, embedding rebuild, volume
deletion, or persistent-state overwrite was performed. Resuming requires explicit
authorization plus authoritative copies/manifests for all September documents. The
recommended procedure is to preserve the current empty volumes, create an isolated
reconstruction project and new volumes, restore/recreate the three UAT accounts,
ingest checksum-verified authoritative documents through the normal pipeline, verify
12 READY documents / 153 chunks / 384-dimensional embeddings and representative IDs,
then switch acceptance execution only after provenance is demonstrated.

Hard stop: **no verified old state exists; reconstruction/reingestion and persistent
writes require user authorization and missing authoritative corpus assets**. The
active application queue remains benefits, person/organization, schedule/attendance
excluding Q018, and annual-leave allocation. Q018 remains a separate corpus-authority
conflict.

## RAG-H5.2 remaining release-gate checkpoint -- 2026-09-28

RAG-H5.2 remains **IN PROGRESS**. TASK-035 remains **BLOCKED / NOT STARTED**.
Compensation hardening is closed (`12/12 PASS`) and was not reopened. Exact-100 was
not rerun in this checkpoint.

The current repository ledgers and the latest per-cluster artifacts supersede stale
failures in the 2026-09-10 Exact-100 transport capture. Newer authoritative closure
artifacts are:

- `artifacts/rag-h5-2-compensation-gate-post-q059.json`
- `artifacts/rag-h5-2-security-cluster-final-closure.json`
- `artifacts/rag-h5-2-attendance-work-schedule-final-closure.json`
- `artifacts/rag-h5-2-leave-condition-binding-final-closure.json`
- `artifacts/rag-h5-2-cross-document-synthesis-final.json`
- `artifacts/rag-h5-2-cross-document-final-closure.json`

### Remaining inventory

There are **23 unresolved cases**: **22 application defects**, **1 corpus conflict**,
and no current infra, expected-no-answer, or insufficient-metadata blockers. The 36
case records covered by newer compensation, security, targeted attendance,
leave-condition, and cross-document closure gates are stale/superseded rather than
open failures.

| Cluster | Cases | Classification | Newer generic fix may cover | Runtime rerun |
| --- | --- | --- | --- | --- |
| Person/organization fact binding | Q006, Q008, Q010, Q011, Q012, Q015 | APPLICATION_DEFECT | Yes | Required |
| Schedule/attendance value binding | Q016, Q017, Q020, Q021, Q022, Q024, Q032, Q038 | APPLICATION_DEFECT | Yes | Required |
| Working-hours policy authority | Q018 | CORPUS_CONFLICT | No | Human authority required before adjudication |
| Annual-leave allocation | Q039, Q040 | APPLICATION_DEFECT | Yes | Required |
| Benefit value/condition binding | Q075, Q079, Q083, Q085, Q086, Q087 | APPLICATION_DEFECT | Yes | Required |

Q018 is not classified as a retrieval defect. The indexed policies contain overlapping
morning-start windows, and current metadata does not establish which document
supersedes the other. No policy authority was invented.

### Selected cluster result: cross-document synthesis

Q096, Q097, and Q098 were selected because all three required multiple independently
supported claims and exposed a shared interpretation/evidence-composition boundary.
The first failure origin was query decomposition and retrieval intent formation, before
generation or validation. Generic changes now decompose paired/coordinated clauses,
normalize incident wording for retrieval, preserve the original user-facing question,
bind allowance descriptors and OT day types to values, and select the direct
leave-incident rights/time clauses.

Production `qwen2.5:3b` results: Q096 `PASS`, Q097 `PASS`, Q098 `PASS`; all returned
HTTP `201`, material registered citations, and no infra errors. The cluster is
**CLOSED**. Focused tests passed (`13` subclaim tests and a final `8`-test shared RAG
gate), Ruff check/format check passed, source compilation/import passed, and API
live/readiness is `200/200` with restart count `0` and OOM killed `false`.

No benchmark ID, expected answer, document ID, or source ordinal was added to
production logic. Persistent volumes were not changed. Compensation was not rerun;
focused shared-component safeguards for salary bands, conditional allowances, OT
day-type/rate binding, review timeline, and locale decimal ranges remained green.

Next checkpoint: run only the open benefit value/condition-binding cases
Q075/Q079/Q083/Q085/Q086/Q087. Exact-100 remains deferred until known semantic
clusters and safety gates are green.

## RAG-H5.2 Q059 / compensation closure checkpoint -- 2026-09-24

Q059 is closed. The current production failure originated before generation: the
query-matched salary-table row survived retrieval and structured rescue but ranked
third, while the production path retained only the top two hits for the prompt.
Generic compensation principles and an unrelated benefit amount therefore displaced
the answer-bearing row. Qwen cited the generic salary source, strict claim validation
returned `CONTRADICTED`, and the safe user-visible result was `NO_ANSWER`.

The generic fix prioritizes candidates that atomically bind the requested role to a
salary range before the per-query prompt cutoff. It also runs the narrowly gated
salary-band extractor before generic structured value extractors and preserves compound
currency units such as `triệu đồng`. No role, grade, amount, case ID, or source ordinal
is encoded in production logic. Citation inference and validator weakening were not
introduced.

Verification completed against production `qwen2.5:3b`, temperature `0`:

- Focused salary/structured/citation tests: `20 passed, 276 deselected`.
- Q059 post-fix: HTTP `201`, `ANSWERED`, authoritative salary-table chunk on page 4,
  same-row role/range binding, material citation, claim validation `SUPPORTED`.
- Salary-band gate Q056-Q060: `5/5 PASS`.
- Compensation gate Q056, Q057, Q058, Q059, Q060, Q063, Q064, Q067, Q068,
  Q071, Q072, Q073: `12/12 PASS`.
- Citation registry validity and material support: `100%`; hallucinations,
  permission leakage, and application timeouts: `0`.
- Ruff check and Ruff format check passed for all currently changed Python files;
  compileall passed.
- API was rebuilt/recreated without touching persistent volumes. Final live/readiness
  checks returned `200/200`, restart count `0`, OOM killed `false`, and the running
  service file hash matched the workspace source.

Artifacts: `artifacts/rag-h5-2-q059-production-contract-before-fix.json`,
`artifacts/rag-h5-2-q059-post-fix.json`,
`artifacts/rag-h5-2-salary-gate-post-q059.json`, and
`artifacts/rag-h5-2-compensation-gate-post-q059.json`.

RAG-H5.2 remains **IN PROGRESS** because broader release gates were not executed in
this checkpoint. Exact-100 was intentionally not run. TASK-035 remains blocked/not
started under the existing roadmap.

## CURRENT STATUS -- 2026-08-21

> This block supersedes older 2026-08-19 RAG handoffs. TASK-034.1.2 runtime RAG acceptance is complete for the agreed seven-case set. TASK-035 is still not started.

### Completed

- Restored the intended UAT leave-policy evidence through the normal ingestion/indexing pipeline instead of changing runtime RAG logic or inserting direct chunk answers.
- Verified active non-deleted indexed evidence for the 12 / 14 / 16 annual-leave distinctions before runtime UAT.
- Completed answer-bearing source-quality, subject/object-aware YES/NO validation, relation entailment, and citation repair work.
- Passed all seven runtime UAT cases in new chats against the local real LLM runtime.
- Re-ran focused RAG suites, full unit tests, Ruff lint, and Ruff format check with actual counts.

### Corpus action

Restored document `43cb2c93-52bc-44f6-8e03-1b1f075e1d89`, `Chính sách nghỉ của người lao động`, checksum `24178db420422e474326986672b6c15cc67373ee6adbe1489ba5e8addf95f4f4`, storage key `documents/2026/08/951776f4-88c3-4c98-8401-c8ce5edad268.pdf`, uploaded by `admin.uat@example.test`, `ORGANIZATION` scope.

The document was restored from soft delete by setting `is_deleted=false`, reset to `UPLOADED`, and processed by normal worker task `274fe326-9d28-421c-9c11-253ec7b74bc2`. Final ingestion result: `READY`, `page_count=6`, `chunk_count=12`, `total_tokens=6458`, embeddings `384` dimensions. Active corpus verification after processing: `12` active ready documents, `153` active chunks, and authoritative active leave clause chunk `4b341201-f0df-4102-b9f2-5ad7091781a6` on page `3`.

Provenance is clear enough for UAT restoration because the file was UAT-admin uploaded, organization scoped, HR-policy themed, and contained the exact authoritative annual-leave table. Remaining corpus limitation: it is generic/template-branded; no Nova-branded PDF with the 12 / 14 / 16 table was found, and the active Nova-branded leave policy only had the 12-day normal-work clause.

### Runtime UAT

| Case | Result |
| --- | --- |
| Own salary | PASS -- `Có`; salary policy pages 10-11; `SUPPORTED`. |
| EAP | PASS -- `Không`; benefits policy page 8; `SUPPORTED`. |
| NovaCare vs BHYT | PASS -- `Không`; benefits policy page 4; `SUPPORTED`. |
| Engineering Manager | PASS -- `N5`, `42 - 70 triệu đồng`; salary table page 4; `SUPPORTED`. |
| Head / Director | PASS -- `N6`, `65 - 110 triệu đồng`; salary table page 4; `SUPPORTED`. |
| Annual leave | PASS -- starts `Không`, distinguishes `12 / 14 / 16`, cites real active leave clause/table page 3, no sample-question citation, `SUPPORTED`. |
| CEO false premise | PASS -- starts `Không`, identifies `Nguyễn Anh Khoa`; organization source page 6; `SUPPORTED`. |

### Verification

```text
tests/unit/test_grounded_answer_service.py: 75 passed in 1.33s
focused RAG/citation suite: 132 passed in 1.56s
combined RAG/citation/validation/output suite: 157 passed in 1.71s
tests/unit: 1061 passed in 8.22s
ruff check on 21 touched Python files: All checks passed
ruff format --check on 21 touched Python files: 21 files already formatted
```

### Remaining technical debt

- Replace the restored generic/template leave policy with canonical Nova-branded content once available.
- Hydrate/cache the configured CrossEncoder reranker or formally accept alignment fallback for local UAT.
- Profile runtime UAT latency; observed wall-clock case times were about 94s-186s.
- Improve table evidence highlighting so annual leave captures the full 12 / 14 / 16 support span, not only a narrow value.
- Remove sample-question/test-question sections from production knowledge documents through corpus curation.
- Convert the manual seven-case runtime UAT runner into an automated acceptance artifact.

## CURRENT MANUAL STATUS — 2026-08-19

> This block is the latest project handoff and should be read before older status snapshots below.

### Current phase

Manual RAG Accuracy Hardening + UI-04B Exact Evidence / citation quality.

### Current task

Minimal Citation Selection is **IMPLEMENTED + UNIT VERIFIED; LIVE RUNTIME VERIFICATION PENDING** after Exact Evidence persistence/API work was verified.

Current checkpoint:

- Exact evidence extraction: implemented and focused tests passed (`15 passed` at completion checkpoint).
- `message_citations.evidence_text`: implemented and persisted.
- API/session history exposes optional `evidence_text`.
- Frontend exact-evidence rendering is visibly active in citation cards.
- Original source PDF/DOCX files remain unchanged.
- Minimal citation pruning: focused citation-mapping suite passed `17 passed in 0.19s`; one live new-message runtime check is still required before final completion.
- Document Viewer navigation to exact document/page/evidence is still pending.
- RAG answer-quality hardening is the next active work based on manual Vietnamese multi-document UAT.

### Mandatory runtime principle

Regression/UAT questions are not a runtime knowledge base. No hard-coded question-to-answer mappings are allowed. Answers must be generated from currently authorized retrieved document evidence.

### Accuracy findings requiring general fixes

Manual UAT showed recurring classes of errors:

- retrieval misses even when the source contains direct answers;
- wrong row selection in tables with neighboring percentages/conditions;
- contradictions such as `Có` vs `Không`;
- semantic intent confusion between related HR concepts;
- role/workflow confusion;
- redundant citations that support the same factual evidence.

The remediation path is capability-level:

```text
Query Understanding
-> Hybrid Retrieval
-> Reranking
-> Table/Row Discrimination
-> Minimal Evidence Selection
-> Claim/Evidence Validation
-> Grounded Answer
```

### Documentation policy during manual work

After each completed change, update:

- `TASKS.md`
- `PROJECT_STATUS.md`
- `CHANGELOG.md`

Also update the affected spec/design docs (`RAG_DESIGN.md`, `API_SPEC.md`, `DATABASE_DESIGN.md`, `TESTING_STRATEGY.md`, `FRONTEND_SPEC.md`) when their contracts/designs change.


## Current phase

UAT UX + LLM configuration fix

## Overall progress

```text
Documentation: Active for UAT fix only
Backend foundation: Completed
Database foundation: Completed
Authentication and RBAC: Completed
Administration APIs: Completed
Document management: Completed
Document processing pipeline: Completed
Semantic retrieval: Completed
Keyword retrieval: Completed
Hybrid retrieval: Completed
Chat data model: Completed
Chat session APIs: Completed
Grounded Chat: Completed
LLM provider: Completed
Grounded answer generation: Completed
Citation validation: Completed
Citation persistence: Completed
Permission revalidation: Completed
Feedback model/API: Completed
Feedback reporting: Completed
Audit log expansion: Completed
Web Search Integration: Completed
Backend Docker stack: Completed
CI pipeline: Completed
MVP hardening: Completed
Backend MVP: Completed
Frontend: Completed through TASK-028 live UI acceptance; UAT selector fix applied
Production deployment and observability: Completed in TASK-034
Final acceptance and release candidate: TASK-035 not started
```

## Completed

- TASK-001 through TASK-034 completed.
- TASK-023 completed the Docker full backend stack with PostgreSQL/pgvector, Redis, one-shot Alembic migration, FastAPI API, Celery worker, shared upload volume, shared model-cache volume, non-root application containers, and Python 3.12 runtime.
- TASK-024 completed a GitHub Actions CI pipeline for the backend with Python 3.12, pip caching, `pyproject.toml` dependency installation, PostgreSQL/pgvector and Redis service containers, Alembic verification, Ruff checks, pytest coverage across unit/API/integration/marker suites, security scanning, Docker build verification, Compose config validation, and artifact upload.
- TASK-025 completed Docker recovery, Docker runtime verification, database-backed verification, marker suites, end-to-end release smoke, persistence, failure/recovery, and final quality gates.
- TASK-026 completed Multi-LLM Provider Support and Docker runtime verification.
- TASK-027 completed backend SSE streaming chat with buffer-after-validation grounding, citation, persistence, cancellation, and safe-error tests.
- TASK-028 frontend implementation adds a React/TypeScript/Vite console in `frontend/` with authentication, role-aware shell, typed API integration, POST SSE chat, document workflows, admin screens, feedback, audit, system status, frontend tests, UI docs, and optional Docker frontend profile.
- TASK-028 live acceptance recovery verified the real Docker stack with PostgreSQL, Redis, API, worker, frontend, Alembic current/head `20260722_0009`, UAT seed idempotency, live Admin/Manager/Staff login, upload-to-READY, permissions grant/revoke, live SSE chat, citations, feedback, audit, responsive/accessibility smoke, mock E2E, live E2E, frontend quality gates, and backend regression suites.
- TASK-029 completed bounded same-session Conversation Memory with `ConversationContextBuilder`, message and token limits, retrieval-query augmentation, prompt-history formatting, non-streaming and streaming parity, no migration, and no prompt persistence.
- TASK-030 completed OCR and Image Understanding with OCR routing, Tesseract runtime support, extraction quality checks, image upload validation, and retrieval/citation compatibility.
- TASK-031 completed Web Search Integration with backend-only internal-only, hybrid, and web-only modes, provider registry/manager, mock/Bing/DuckDuckGo/Google Custom Search providers, web citation persistence, admin provider endpoints, security normalization, Docker runtime, migration, API, streaming, integration, regression, quality, and security verification.
- TASK-032 completed backend-only Admin Dashboard & System Monitoring with safe Admin-only health, provider, worker, queue, statistics, version, and system endpoints.
- TASK-033 completed backend-only Analytics & Reporting with Admin-only overview, chat, user, search, OCR, LLM, feedback, audit, and CSV/JSON export endpoints.
- TASK-034 completed backend-only Production Deployment & Observability with production Compose, reverse proxy, Prometheus/Grafana provisioning, safe metrics/logging, runtime validation, backup/restore helpers, and Docker runtime verification.
- UAT UX + LLM configuration fix completed the upload Department selector, permission User/Department selectors, safe validation errors, deterministic local UAT LLM coverage, Docker UAT config verification, live chat verification, streaming verification, and focused regressions.

## Current task

UAT FIX -- UX Selectors + LLM_NOT_CONFIGURED remediation is completed and verified locally.

This is not TASK-035. TASK-035 -- Final Acceptance Test & Release Candidate is not started. No backend Release Candidate version is marked.

Roadmap status: TASK-001 through TASK-034 completed for the backend roadmap. TASK-028.1 Localization is deferred. Frontend UI Foundation exists. TASK-035 is pending and not started.

## Phase 2 roadmap initialized

- TASK-026 -- Multi-LLM Provider Support: Completed.
- TASK-027 -- Streaming Chat with Server-Sent Events: Completed.
- TASK-028 -- Frontend UI Foundation & Test Console: Completed.
- TASK-029 -- Conversation Memory: Completed.
- TASK-030 -- OCR and Image Understanding: Completed.
- TASK-031 -- Web Search Integration: Completed.
- TASK-032 -- Admin Dashboard & System Monitoring: Completed.
- TASK-033 -- Analytics & Reporting: Completed.
- TASK-034 -- Production Deployment & Observability: Completed.
- TASK-035 -- Final Acceptance Test & Release Candidate: Not started.
- TASK-036 -- Enterprise Release v2.0: Pending.

## Current blockers

- None for the scoped UAT UX + LLM configuration fix.

## Files changed in latest task

UAT fix relevant files:

- `frontend/src/features/documents/DocumentUploadPage.tsx`
- `frontend/src/features/documents/DocumentUploadPage.test.tsx`
- `frontend/src/features/documents/DocumentPermissionsPage.tsx`
- `frontend/src/features/documents/DocumentPermissionsPage.test.tsx`
- `frontend/tests/e2e-live/fake-openai-provider.mjs`
- `tests/integration/test_docker_stack_config.py`
- `README.md`
- `SETUP.md`
- `ENVIRONMENT_VARIABLES.md`
- `TESTING_STRATEGY.md`
- `PROJECT_STATUS.md`
- `TASKS.md`
- `CHANGELOG.md`

## UAT UX + LLM configuration snapshot

- Document upload no longer exposes a raw Department ID input. `DEPARTMENT` scope loads `GET /api/v1/departments`, displays department names/codes, validates a required selection, and sends the selected `department.id`.
- Document permission grants no longer expose a raw Grantee ID input. `USER` loads `GET /api/v1/users`; `DEPARTMENT` loads `GET /api/v1/departments`; changing grantee type clears stale selections.
- Default `compose.yaml` keeps `LLM_ENABLED=false` and does not start a local LLM container.
- UAT mode uses `docker compose -f compose.yaml -f compose.uat.yaml up -d` and enables the local deterministic OpenAI-compatible provider at `http://uat-llm:18080/v1` with `LLM_MODEL=uat-deterministic-model`.
- UAT chat verification uses the local deterministic provider only; no real provider API key or external LLM call is required.
- UAT account lifecycle fix: `compose.uat.yaml` runs one-shot `uat-seed` before API/worker startup. The seed updates known UAT users in place, including password hash, full name, role, department, active flag, and lowercase email normalization, while preserving unrelated users.

## Known limitations

- TASK-035 is not started and the backend is not marked Release Candidate in this UAT fix.
- The default Docker stack is for local development and binds API, PostgreSQL, and Redis to `127.0.0.1` host ports.
- LLM is disabled by default. UAT LLM behavior requires `compose.uat.yaml`; host or production LLM providers require explicit operator configuration.
- Web search is disabled by default; external provider calls require explicit configuration and `WEB_SEARCH_ALLOW_EXTERNAL=true`.
- Feedback reason, Chat content, citation excerpts, chunk text, and selected fields are still stored plaintext in PostgreSQL.
- Frontend `npm audit --audit-level=high` reports a React Router RSC/action advisory for `react-router-dom@7.18.2`; TASK-028 uses SPA-only routing and does not enable RSC/actions. Reassess when a clean upstream release is available.
- No malware scanning, PII masking, automatic chat retention, audit retention, or feedback deletion workflow is implemented.
- Broker enqueue is not backed by a transactional outbox; broker failure can leave a committed Document in `UPLOADED` until manually enqueued.
- Worker crash can leave a Document in `PROCESSING` until recovery logic is added.
- Current local UAT data may include documents from earlier verification runs. The UAT fix did not delete documents, reset the database, or remove Docker volumes.
## TASK-031 verification snapshot

Final verification passed:

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
- Docker runtime verified PostgreSQL, Redis, API, worker, and migration service; migration exited 0.
- API `/health/live` and `/health/ready` passed.
- `alembic current`, `alembic heads`, and `alembic upgrade head` passed in the API container; current/head is `20260803_0010`.
- Runtime smoke verified default disabled/internal-only provider status, no-answer chat, SSE streaming, UAT internal citation, mock-provider `internal_only`, `web_only`, `hybrid`, no-internal-hit intent, and web citation source typing.

## TASK-032 verification snapshot

TASK-032 completed backend-only Admin Dashboard & System Monitoring:

- Added Admin-only `/api/v1/admin/system`, `/api/v1/admin/health`, `/api/v1/admin/providers`, `/api/v1/admin/workers`, `/api/v1/admin/statistics`, `/api/v1/admin/queues`, and `/api/v1/admin/version`.
- Added `AdminMonitoringService` with safe read-only health/status aggregation for API uptime, PostgreSQL, Redis, Celery worker, OCR, embedding configuration, LLM provider configuration, Web Search provider configuration, streaming registration, conversation memory configuration, queues, statistics, and version.
- Added safe schemas for admin health, providers, workers, queues, statistics, version, and system dashboard responses.
- Added unit and API integration tests for Admin RBAC, health subsystem coverage, provider safety, queue reporting, worker status, aggregate statistics, version, and secret/content non-disclosure.
- No frontend, React, Stitch, Localization, Chat API, Streaming behavior, Conversation Memory behavior, Citation behavior, OCR processing behavior, Web Search behavior, Celery architecture, or database schema migration was changed.
- Alembic source/current/head remained `20260803_0010`; no migration was created.

Verification completed:

- `python -m pytest tests/unit/test_admin_monitoring_service.py -v`: 4 passed.
- `python -m pytest tests/api/test_admin_monitoring.py -m integration -v`: 4 passed.
- `python -m pytest tests/api/test_admin_monitoring.py tests/api/test_web_search_admin.py tests/api/test_rbac_dependencies.py -m integration -v`: 10 passed, 11 deselected.
- `python -m pytest -q`: 1001 passed, 654 deselected.
- Docker test profile TASK-032 unit/API suites passed on Python 3.12.13.
- `python -m ruff check .`, `python -m ruff format --check .`, `python -m compileall app tests`, and `python .github/scripts/security_scan.py` passed.
- `alembic heads`, `alembic current`, and `alembic upgrade head` passed with `20260803_0010`.
- `docker version`, `docker info`, `docker compose config`, `docker compose build`, `docker compose up -d`, and `docker compose ps` passed.
- Docker runtime verified API health, worker health, PostgreSQL health, Redis health, migration service exited 0, pgvector extension, Tesseract OCR binary, Celery worker ping, and live Admin monitoring endpoints.

Note: broad all-file `tests/api -m integration` commands were attempted but timed out and are not counted; focused TASK-032/RBAC/provider integration and default backend regression passed.
## TASK-033 verification snapshot

TASK-033 completed backend-only Analytics & Reporting:

- Added Admin-only `/api/v1/admin/analytics/overview`, `/api/v1/admin/analytics/chat`, `/api/v1/admin/analytics/users`, `/api/v1/admin/analytics/search`, `/api/v1/admin/analytics/ocr`, `/api/v1/admin/analytics/llm`, `/api/v1/admin/analytics/feedback`, `/api/v1/admin/analytics/audit`, and `/api/v1/admin/reports/export`.
- Added `AdminAnalyticsService` with read-only PostgreSQL aggregates for chat, users, citation-inferred search, image-document OCR status, LLM token/latency/failure metrics, feedback ratings, audit categories, and overview summaries.
- Added safe analytics schemas and CSV/JSON export helpers. PDF export returns `422 VALIDATION_ERROR` because no backend PDF export infrastructure exists.
- Added unit and API integration tests for filters, RBAC, aggregate correctness, security non-disclosure, export behavior, regression coverage, and performance smoke.
- No frontend, React, charts, Localization, Chat API, Streaming behavior, Conversation Memory behavior, Citation behavior, OCR processing behavior, Web Search behavior, Celery architecture, or database schema migration was changed.
- Alembic source/current/head remained `20260803_0010`; no migration was created.

Verification completed:

- `python -m pytest tests/unit/test_admin_analytics_service.py -q`: 5 passed.
- `python -m pytest tests/api/test_admin_analytics.py -m integration -q`: 6 passed.
- `python -m pytest tests/api/test_admin_analytics.py tests/api/test_admin_monitoring.py tests/api/test_web_search_admin.py tests/api/test_rbac_dependencies.py -m integration -q`: 16 passed, 11 deselected.
- `python -m pytest -q`: 1006 passed, 660 deselected.
- `python -m ruff check .`, `python -m ruff format --check .`, `python -m compileall app tests`, and `python .github/scripts/security_scan.py` passed.
- `python -m alembic heads`, `python -m alembic current`, and `python -m alembic upgrade head` passed with `20260803_0010`.
- `docker compose config`, `docker compose build`, `docker compose up -d`, and `docker compose ps` passed.
- Docker runtime verified API health, PostgreSQL health, Redis health, migration service exit 0, Celery worker ping, container Alembic heads/current/upgrade, and live Admin analytics route RBAC (`401 ACCESS_TOKEN_INVALID` without bearer token).

Known data limitations: retrieval duration, per-message streaming usage, OCR duration, exact scanned-PDF OCR page attribution, and historical per-message LLM provider/model attribution are not persisted and are reported as unavailable or partially inferred.
## TASK-034 verification snapshot

TASK-034 completed backend-only Production Deployment & Observability:

- Added standalone production Compose with PostgreSQL, Redis, one-shot migration, API, worker, reverse proxy, volume initialization, restart policies, healthchecks, CPU/RAM/PID limits, log-size limits, and Docker secret-file compatibility.
- Added Nginx reverse proxy config for forward headers, request/upload limits, SSE compatibility, security headers, HTTPS readiness without committed certificates, and external `/metrics` blocking.
- Added request ID context, traceparent capture hooks, structured content-free request logging, in-process HTTP metrics, and Prometheus runtime metrics for API, worker, Redis, PostgreSQL, OCR, embedding, LLM, Web Search, Streaming, Conversation, queues, version, and uptime.
- Added Prometheus scrape config and Grafana provisioning/dashboard files.
- Added PostgreSQL and uploads backup/restore helpers with verification and guarded restore behavior.
- No frontend/UI/React/Stitch/Localization/Chat/RAG/Citation/Conversation/Streaming/OCR/Web Search behavior was changed.
- No database migration was created; Alembic source/current/head remains `20260803_0010`.

Verification completed:

- `python -m pytest tests/unit/test_admin_monitoring_service.py tests/unit/test_observability_metrics.py tests/unit/test_runtime_validation.py tests/api/test_observability.py tests/integration/test_production_deployment_config.py -q`: 21 passed, 2 deselected.
- `python -m pytest tests/unit -k "ocr or image or document_processing or extractor" -q`: 91 passed, 843 deselected.
- `python -m pytest -q`: 1023 passed, 662 deselected.
- `python -m pytest -m "integration or not integration" tests/api/test_observability.py tests/api/test_admin_monitoring.py tests/api/test_admin_analytics.py tests/api/test_rbac_dependencies.py tests/api/test_chat_streaming.py tests/integration/test_production_deployment_config.py tests/integration/test_docker_stack_config.py -q`: 55 passed.
- `python -m ruff check .`, `python -m ruff format --check .`, `python -m compileall app tests .github\scripts`, `python .github\scripts\security_scan.py`, `python -m pip check`, and `python -m pip_audit` passed.
- `python -m alembic heads`, `python -m alembic current`, and `python -m alembic upgrade head` passed with `20260803_0010`.
- `docker compose config`, `docker compose build`, `docker compose up -d`, and `docker compose ps` passed for the development stack.
- `docker compose --env-file <production env> -f compose.prod.yaml config`, `build`, `up -d`, and `ps` passed for the production stack.
- Production runtime verified API, worker, Redis, PostgreSQL, migration, and reverse proxy health; API `/health/ready` returned ready through Nginx; worker Celery ping returned `pong`; API container Alembic current remained `20260803_0010`; final image contains `Pillow 12.3.0`.
- Internal `/metrics` returned safe Prometheus text and did not contain the sensitive `context` marker; production reverse proxy returned `404` for external `/metrics`.
- Backup/restore verification created and validated a PostgreSQL dump, restored it into an isolated check database, created and validated an uploads archive, restored it into an isolated check volume, and confirmed restore guardrails refuse production overwrite without explicit switches.
- Failure recovery verified API restart, worker restart, Redis unavailable/readiness degradation/recovery, PostgreSQL unavailable/readiness degradation/recovery, and safe degraded responses without secrets.

Known TASK-034 limitations: real TLS certificates, cloud secret manager integration, SIEM/log shipping, alert rules, distributed tracing backend, Kubernetes, Terraform, cloud resources, CD automation, WAF, malware scanning, automatic retention deletion, and cloud backup are not included. In-process HTTP metrics reset on API restart.

## TASK-034.1 status snapshot

TASK-034.1 -- Real / Local LLM Strict Grounded Runtime Acceptance is current and in progress. TASK-034.2 is not started. TASK-035 is not started.

Completed in the repository for TASK-034.1:

- Audited LLM provider architecture, grounded answer service, citation validation, retrieval, web search, streaming, frontend chat integration, Compose, and environment documentation.
- Strengthened the grounded system prompt for strict evidence-only behavior, preservation of numbers/dates/names/conditions/exceptions, conflict handling, and no unsupported inference.
- Added a runtime invariant that `ANSWERED` results must include validated citations.
- Added focused unit coverage for strict prompt text and answered-without-citations rejection.
- Added disabled-by-default `real_llm_acceptance` report validator.
- Created local ignored synthetic acceptance PDFs and a report template under `artifacts/task-034-1/`.
- TASK-034.1 local Ollama streaming timeout fix verified `qwen3:4b` through buffer-after-validation SSE for Nova Digital CEO, CTO, and NovaAssist questions twice each with no `STREAM_TIMEOUT`.

Current remaining completion requirements:

- Full strict real-LLM matrix must be rerun and recorded in the manual acceptance report.
- Manual claim-level support remains required for every factual claim; automated claim-level entailment is deferred.
- Permission, failure, no-answer, and cross-document acceptance cases must remain green after the local streaming timeout fix.

TASK-034.1 cannot be marked completed until real/local or explicitly configured external provider acceptance passes against the new unseen document set with manual claim verification.


### RAG-H2.1 checkpoint — 2026-08-19

- Post-reranker ordering bug fixed: reranked hits are now preserved before prompt-ranked supplemental hits.
- Regression coverage added.
- Focused verification passed: `61`, `27`, and combined `147` tests.
- Runtime cross-encoder is currently unavailable and falls back to `HeuristicRetrievalReranker`.
- `RAG_DIAGNOSTICS_ENABLED` is not present in the API container; `Settings().rag_diagnostics_enabled` remains `False`.
- Runtime H2 acceptance is pending after diagnostics injection and real query verification.


### Runtime recovery checkpoint — 2026-08-19

- `LLM_GENERATION_FAILED` incident resolved.
- Ollama/provider path verified healthy; 8K model alias runs with context 8192.
- Actual backend root cause was `NameError` from a partially applied `question=grounding_question` claim-validation call inside `_draft_from_generation()`.
- Restored current claim-validator call contract.
- Tests passed: `61` focused grounded-answer tests and `147` combined RAG/retrieval tests.
- Live `Head` salary query now fails as NO_ANSWER rather than generation failure; accuracy investigation continues.
- `RAG_DIAGNOSTICS_ENABLED=True`, but INFO diagnostic events are not appearing in `docker compose logs`; logging visibility investigation is next.

### RAG accuracy checkpoint — salary amount PASS

Salary-band runtime probes are now passing:
- Head / Director: 65 - 110 triệu đồng.
- Engineering Manager / N5: 42 - 70 triệu đồng/tháng.

Regression verification:
- grounded-answer unit suite: 63 passed.
- combined focused RAG/retrieval suite: 149 passed.

Current open issue:
`Nhân viên có được nói về mức lương của chính mình không?` still returns NO_ANSWER. Diagnostics show correct YES_NO retrieval and three `SUPPORTED` claim validations, followed each time by `reason=yes_no_missing_leading_polarity`. This is a presentation/quality-gate failure, not a retrieval miss.

Citation UX decision pending implementation: evidence highlighting should represent the source passage(s) that materially support the answer/inference.
