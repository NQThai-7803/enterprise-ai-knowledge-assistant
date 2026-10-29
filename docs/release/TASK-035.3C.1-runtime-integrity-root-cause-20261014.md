# TASK-035.3C.1 — runtime integrity rebaseline and root-cause verification

Date: 2026-10-14 (Asia/Saigon). **Diagnostic authorization completed; no correction implemented.** TASK-035 remains IN PROGRESS. The frozen TASK-035.3B candidate remains FAILED and RC sign-off is NOT GRANTED. This report uses read-only runtime and archived-data checks plus synthetic, database-free unit tests. It does not qualify a new release candidate.

## Preservation and source identity

Branch `main`, HEAD `04ebd73aae737414fb591fe2e8b2c286134cdcd8`; the H5.2 implementation and release artifacts remain uncommitted in the pre-existing dirty worktree. No pre-existing change was discarded. This checkpoint adds only `tests/unit/test_answer_responsiveness_diagnostic.py` and this report. No production source, frozen benchmark, image, container, database, Redis state or volume was changed by this checkpoint.

The four inspected production-file SHA-256 values remained equal to the TASK-035.3C checkpoint: `claim_evidence_validation_service.py` `d7e11c25b42d710b1a2ba4d325244adecb371c723dda9b3148b27bdc4f65b6e1`; `grounded_answer_service.py` `4c9d4c648bbcef30a35c4e2ca01fad0093ed0e7a8aebb777dc78b478b345c919`; `reranker.py` `4fa1e470dfa097f3b881f9dfdaef3fb7771cd4953bfe99031c8b77dd882da8d0`; `context_builder.py` `26b2daafcc7da2448ba8933e6702e12cd58d880edb92b054edefb7dfe8884ab8`. The selected hashes in the running V2 API `/app` match the host. The active worker still has the already documented older grounded-answer-service hash `7ad6dc69fa39a55b13dd3ed0141feed8e67d12a592d8148420f4bcf01ad04548`; this pre-existing API/worker skew is not resolved here.

## Accepted V2 post-restart rebaseline

The same four accepted V2 container identities were observed running and healthy after the host restart, with restart count zero and OOM false:

| Service | Container ID prefix | Image ID prefix | Observed state |
| --- | --- | --- | --- |
| API | `9d510d8b8027` | `sha256:1f057785bd8c` | healthy; live 200, ready 200 |
| Worker | `2afc4af27fe5` | `sha256:1e19725cdd89` | healthy |
| PostgreSQL | `1a5a658a2ef2` | `sha256:cf134a767f47` | healthy |
| Redis | `db2961fc9413` | `sha256:858f009f9709` | healthy; PONG |

Their post-boot start timestamps are approximately `2026-10-14T05:01:32Z`; none was recreated. Redis `/data` remains mapped to `enterprise-ai-uat-v2_redis_recovered_cutover_20261010`. This is a point-in-time runtime check, not a future availability guarantee.

Read-only PostgreSQL transactions found **9 documents, all READY; 143 chunks; 3 users; one manager VIEW grant; migration `20260822_0011`**. Document ID, status, owner, visibility, storage key, SHA-256, chunk count and maximum page matched the saved V2 runtime and structural manifests. The three accounts retained ADMIN/MANAGER/STAFF roles; the sole checked document grant remained manager VIEW on the private grounding document. All 143 current chunk `content_sha256` values equal SHA-256 of their current text, and all have 384-dimensional stored vectors and matching metadata for `intfloat/multilingual-e5-small`/`sentence_transformers`.

Counts alone were not used as identity proof. `pg_restore --data-only --table=document_chunks --file=-` read the archived `20260930-010258` V2 PostgreSQL dump to stdout **without connecting to a database or restoring it**. The 143 archived chunk `(id, document_id, chunk_index, content_sha256, embedding provider/model/dimensions)` tuples exactly equal the 143 read-only live tuples: archive-only 0, live-only 0, canonical digest on each side `252ac7e644b8478436752d9163d17c7ef70b165381885247a25c8802bc1b2451`. All nine local source PDF hashes matched `uat/corpus-v2/manifest.json`; all nine mounted upload PDF hashes matched the database SHA-256. Previously recorded H5.2 qualification, final broad, safety smoke, repeatability, runtime-manifest and corpus-manifest file hashes also matched. The final broad artifact remains the historical **98/98 supported PASS**, with Q018/Q100 safe abstentions; no new broad test was run.

**Decision:** the checked original H5.2 corpus/source/artifact baseline is INTACT and post-restart data integrity is PASS for the enumerated identities, content hashes, metadata and grants. This does not prove full database byte equivalence, current semantic acceptance, complete historical Celery accounting, or removal of active API/worker skew. No unexpected replay was observed in the inspected logs/window; historical Celery accounting remains UNKNOWN.

## Stopped candidate forensics

All four original `enterprise-ai-task0353b` candidate containers remain **exited 255**, restart policy `no`, OOM false, with finish timestamps within milliseconds of `2026-10-14T05:01:21.38Z`:

| Service | Container ID prefix | Image ID prefix | Preserved mount |
| --- | --- | --- | --- |
| API | `39b1a6632ee5` | `sha256:97cf3222e128` | candidate uploads and model cache |
| Worker | `dc3d812bafc6` | `sha256:ccf26439f4ca` | candidate uploads and model cache |
| PostgreSQL | `b1fdda3a7a0a` | `sha256:cf134a767f47` | candidate PG data |
| Redis | `50fbede718ce` | `sha256:858f009f9709` | candidate Redis data |

The four candidate-only volumes `enterprise-ai-task0353b_task0353b_{pg_data,redis_data,uploads,model_cache}` still exist with original 2026-10-13 creation timestamps. Their mounts still resolve to the candidate project, and all containers retain network configuration for `enterprise-ai-task0353b_candidate` (network ID prefix `365f7ddec467`); the bridge network itself still exists with zero currently attached containers because the candidates are stopped. Candidate image IDs are still inspectable. Frozen source tar, source manifest, dependency lock, permission-safety capture and broad capture hashes match TASK-035.3B. All 401 staged source-manifest files independently matched their recorded SHA-256 values.

Read-only log tails showed normal PostgreSQL checkpoint/Redis save activity and API health responses before termination, without a captured application exception explaining exit 255. Bounded Docker event history for the restart interval returned no retained events. Windows uptime reported a host boot at `2026-10-14T04:54:24Z`; System event-log access was denied. The four near-simultaneous exits and V2 `unless-stopped` resumption are **consistent with** a host/Docker runtime transition; the precise exit-255 mechanism is **not verified**. No candidate service was started. Volume existence, historical pre-stop integrity and intact images do **not** verify the candidate PostgreSQL database after the event. Candidate database integrity is NOT VERIFIED; a separately authorized, isolated startup and read-only verification is required if that old database must be assessed. No observed evidence justifies deleting or repairing any candidate resource.

## Question responsiveness diagnosis

The failing TASK-035.3B STAFF request asked about approval for travel. Direct private-document and cross-user session access were denied; the final answer instead quoted a permitted but unrelated post-incident-rest clause. This is a **nonresponsive-answer safety failure**, not observed private-content leakage. The saved trace showed two permission-visible, irrelevant hits admitted into the prompt registry as SOURCE_1/SOURCE_2, with no answering clause. This is the **first observed incorrect progression**. Per-channel retrieval scores, the full reranker candidate set and raw model scores were not saved, so a specific earlier discovery or ranking defect is not established. A normalized reranker score of zero is relative to the current candidate set and may be a heuristic floor; it cannot serve as a global irrelevance threshold.

The independent final acceptance defect is verified at `app/services/claim_evidence_validation_service.py`'s `_validate_answer_against_evidence`: for generic non-yes/no, non-value, non-person questions, a verbatim copied clause can return `SUPPORTED` before generic question/answer responsiveness is established. The existing topic/relationship checks protect some specialized questions but not this general case. `app/services/grounded_answer_service.py` maps permitted citations, accepts `SUPPORTED`, then returns `GroundingStatus.ANSWERED`. Thus authorization, citation validity and sentence-level evidence grounding can all hold while the answer fails to address the question. A citation to an accessible source is necessary but not sufficient for a responsive answer.

The test-only synthetic module reproduces this without fixture names or benchmark IDs: an unrelated English printer-fault sentence and an unrelated Vietnamese printer-fault sentence both receive `SUPPORTED` for an English microscope-shipping approval question (two strict expected failures). Responsive English and mixed English/Vietnamese copied clauses receive `SUPPORTED` (two positive controls). A Vietnamese conditional-policy question with an unrelated Vietnamese clause is correctly rejected, but a responsive Vietnamese copied clause is also rejected (one strict expected failure), demonstrating a **false-abstention risk** for any broad lexical rule. Relative score normalization controls confirm `(2,9) -> (0,100)` and singleton/tied scores -> `50`, so zero is not calibrated irrelevance. These are validator/scoring controls, not a rebuilt end-to-end candidate or permission-fixture run.

The exact failed request's raw model draft, retry/repair sequence and original per-channel retrieval values were not persisted. Its final answer and logged `SUPPORTED` status are known, but whether generation or a repair first produced that wording remains UNKNOWN. Do not ascribe it to a particular repair branch or claim the gap is candidate-only; the active V2 was deliberately not asked the new question.

## Synthetic multilingual regression contract for an authorized fix

Use fake user-scoped retrieval and a citation registry, no protected database, to exercise positive and negative controls in both English and Vietnamese. Assertions must cover: (1) accessible relevant evidence gives a material cited answer; (2) private relevant evidence without a grant never enters retrieval/context and yields NO_ANSWER; (3) only irrelevant accessible evidence yields NO_ANSWER with zero citations; (4) a grounded but nonresponsive answer is rejected despite a valid source/citation; (5) two authorized documents jointly support a multi-condition answer and both material citations survive; (6) synonym/paraphrase wording remains answerable; (7) negation and obligation reversals are rejected; (8) conditional approvals, exceptions and prerequisites stay bound to the correct subject; (9) shared numbers with unrelated meanings do not manufacture support; (10) unsupported questions abstain; (11) mixed English/Vietnamese question and policy terminology works in both directions; and (12) low keyword overlap with genuinely relevant semantic evidence is not blindly rejected. Include matched irrelevant and relevant controls at zero/near-zero normalized score. Parameterize invented subjects, actions, roles, quantities and document IDs so production logic cannot learn fixture literals.

## Focused execution and correction decision

`tests/conftest.py`'s database-cleaning fixture is scoped to integration-marked tests; the new synthetic tests and selected existing unit modules are unmarked, fake-only, and did not target V2 or candidate DB. Windows asyncio socketpair setup hung in the sandbox; those interrupted attempts are **not** counted as PASS. An isolated retry with the sandbox exception needed for local loopback completed the selected fake-only modules:

- New synthetic module: **4 passed, 3 strict xfailed** (known gaps), 0 unexpected pass/fail.
- `test_permissions.py`: **39 passed**; `test_chat_context_builder.py`: **35 passed**.
- Selected semantic/keyword/hybrid retrieval and citation-validation/mapping modules: **81 passed**.
- Selected claim/rerank accuracy-component cases: **5 passed**, 289 deselected.
- Selected grounded-answer NO_ANSWER/hybrid/rerank-order cases: **6 passed**, 94 deselected.
- Ruff check and Ruff format check on the new test file: PASS; `py_compile` on it: PASS; `git diff --check`: exit 0 (pre-existing CRLF conversion warnings, no whitespace error).

**Recommended minimal generic correction, not implemented:** establish a separate *question-to-answer responsiveness* decision at the claim-validation/final-answer boundary, after authorization and source-grounding checks and before `ANSWERED` is returned. `SUPPORTED` must mean both that cited authorized evidence entails the claim **and** that the answer satisfies the actual information need. Apply the rule to all answer paths, including deterministic/structured repair, without treating citation mapping, lexical overlap, normalized reranker zero or a model's uncalibrated multilingual relevance score as proof. On demonstrated nonresponsiveness, perform only existing bounded repair/NO_ANSWER behavior; preserve zero-citation abstention. Build the above positive and negative English/Vietnamese controls first, particularly paraphrases and the observed responsive-Vietnamese false rejection. The narrow candidate implementation area is `claim_evidence_validation_service.py` with the existing final decision in `grounded_answer_service.py`; context admission should be investigated separately with raw retrieval/rerank traces. Avoid a new global score threshold, retry increase, context expansion or benchmark-specific branch.

This is a **strategy, not yet a safe algorithm specification**: multilingual semantic equivalence and the false-abstention tradeoff require synthetic proof before production changes. A code change could regress the previously accepted 98/98 V2 broad result, compensation grounding, permission safety or citation materiality; historical 98/98 cannot qualify changed source. Any implementation needs separate authorization, focused multilingual/permission/NO_ANSWER/citation and shared RAG regression gates, new source hashes and **new isolated candidate image identities**, then targeted safety, representative repeatability, performance observation and broad V2 requalification. The failed candidate and active V2 baseline must remain preserved. Separately authorize a candidate-only startup if its stopped database integrity must be proved.

## Final decision

| Required field | Result |
| --- | --- |
| TASK-035.3C.1 | **COMPLETED** as authorized diagnostic; remediation not started |
| ORIGINAL H5.2 BASELINE | **INTACT** for checked corpus/source/artifact identities; no current broad rerun |
| POST-RESTART DATA INTEGRITY | **PASS** for documented read-only identities/hashes/grants, not full bytewise DB equivalence |
| STOPPED CANDIDATE | **PRESERVED** |
| CANDIDATE DATABASE INTEGRITY | **NOT VERIFIED** |
| EXIT CODE 255 ROOT CAUSE | **PARTIALLY VERIFIED**: host reboot verified; precise Docker exit mechanism unknown |
| FIRST OBSERVED INCORRECT BOUNDARY | Irrelevant permitted hits admitted to prompt context; separate deterministic failure at final claim responsiveness validation |
| ANSWER RESPONSIVENESS GAP | Verbatim evidence support can bypass generic question responsiveness |
| GENERATION/REPAIR CAUSALITY | **UNKNOWN** for the exact failed request |
| MULTILINGUAL SYNTHETIC TESTS | 4 passed, 3 strict expected failures; positive/negative contract above not yet full implementation |
| PRODUCTION SOURCE MODIFIED | **NO** |
| CANDIDATE IMAGES REBUILT | **NO** |
| NEXT REQUIRED APPROVAL | Separate production-code remediation/new candidate qualification; separate isolated startup if stopped candidate DB integrity is required |
| TASK-035 | **IN PROGRESS** |
| RC SIGN-OFF | **NOT GRANTED** |
