# TASK-035.3B — isolated candidate broad V2 requalification

Date: 2026-10-13. **Workflow status: COMPLETED. Candidate qualification: FAIL.** The authorized restore, frozen broad run, case-level source/citation review, safety/repeatability checks, performance observation and post-run integrity review were completed. The candidate is **not** eligible for promotion because an independent permission-aware unsupported-answer safety gate failed. TASK-035 remains **IN PROGRESS**; no RC sign-off, cutover, tag, release deferral or active V2 replacement is authorized or claimed.

## Frozen candidate and isolated restore

The exact 035.3A images were reused without rebuild: API `sha256:97cf3222e128467fb77d8bf5b4a8c90da321be5008632f10601bd881c7a71eba`; worker `sha256:ccf26439f4cabe7e6282e15b3aa671edabe46a189ec192c2f559d28a557ed44e`. Their 217 shared application files, 92 installed package versions and Python 3.12.15 identity remain the 035.3A accepted candidate configuration. Source tar SHA-256 `3ae9c41fadb0a4c7193aac9828b4fd4ef52b669f1003f16753e251cd76b52e86`, source manifest `10bdab98da72058f16b0c115e7f1dfd2eee95c3ec11cdd41b7815a7e29d6b5a4`, and exact dependency lock `104750a454d695f395b24cd583f1c5ba1de0e1bbc18f041a2a5f56967df2c797` rehashed unchanged. The 401 source-stage manifest entries matched. Benchmark runner, original Q001–Q100 inventory, classification file and expected answers were not edited. Full frozen input identities are in `artifacts/task-035-3b-20261013/frozen-inputs.md`.

The new `enterprise-ai-task0353b` project has separate PostgreSQL, Redis, API, worker, network, uploads and model-cache volumes and localhost ports 15436/16386/18036. The original V2, earlier restore-check and 035.3A synthetic projects were not used as restore targets. The local V2 recovery package passed all 13 listed checksums. Its dump was restored into a **confirmed empty** new candidate database with `pg_restore --exit-on-error`; its upload archive was extracted into an empty new candidate volume. Nine source PDFs matched their stored SHA-256. Model cache was copied from the 035.3A cache mounted read-only and compared. No reingestion or account reseeding occurred.

Restored state: 9 documents/9 READY, 143 chunks, 3 fixture users, one manager VIEW grant on the private handbook, all 143 embeddings 384-dimensional with `intfloat/multilingual-e5-small`, migration `20260822_0011`. All 143 chunk ID/document/content-hash/model/dimension rows matched protected V2 read-only. A pre-run candidate dump (`0a5b61638fd6fc1c9c8cd449528891badb9d98695dc1283b007c4bf7c128feb1`) was **actually restored** into a second new candidate-only logical database; its 9/9/143/3/1/migration invariants matched. This demonstrates local logical restoratability on the same host, **not** off-host DR or separate-node rollback. See `artifacts/task-035-3b-20261013/restored-corpus-integrity.md`.

Runtime matched the V2 comparison settings: Ollama `qwen2.5:3b` (local digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b` before and after), `intfloat/multilingual-e5-small`/384, 500/75 chunking, retrieval top-k 10, reranker top-k 6, 8192 context, temperature 0, 512 output cap and 180-second LLM timeout. Embedding cache bytes were compared with the local 035.3A cache but no independent model-revision digest or off-host copy was certified.

## Broad Q001–Q100 and case-level grading

The **original frozen 100-question V2 inventory** ran against only candidate port 18036. Classification stayed 98 `SUPPORTED_BY_V2`, Q018 `INTENTIONALLY_CONFLICTING`, Q100 `UNSUPPORTED_BY_V2`, zero `STALE_FIXTURE_DEPENDENT`. No supported question was excluded or reclassified. Capture `artifacts/task-035-3b-20261013/broad-v2-candidate.json` SHA-256 `4e117caf65281168d01b71822bf686398a2e1cb4fb03a170b46aa7ff740b5c58`: 100/100 requests HTTP 201, zero transport errors, 98 `ANSWERED`, two `NO_ANSWER`.

The reviewer inspected every candidate question/answer/cited evidence across the nine semantic categories, with additional full-chunk checks on high-risk compensation/own-salary and the failing safety case. Each broad answer and ordered cited document/chunk identity exactly matches the independently, manually reviewed accepted-H5.2 final capture; all 143 restored chunk identities/content hashes match protected V2. The 101 candidate citations resolve to the exact persisted document/chunk/page identity. On this combined source and proposition review, the broad result is **98/98 supported semantic PASS and 101/101 material citation PASS**. Q018 safely abstained on unresolved policy authority; Q100 safely abstained on unsupported AWS scope; both had zero citations. Automated HTTP status alone was not used to assign semantic PASS. `broad-evidence-audit.json` (SHA-256 `b4bd3537e86cc0b959cf94e980253ab038673125a4121d25cd489a8343752944`) and `case-level-semantic-citation-grade.json` (SHA-256 `f6b95fbbafd1ae57ab2ba6026fd3645acdfcb1848c115a30e1ccc0bb7a8e5ed7`) contain the per-case answer, source identity, checks and decisions. Generated answer/claim-focused excerpts are not always literal substrings of raw chunks, so simple excerpt substring matching was not treated as a materiality verdict.

Historical high-risk categories inspected include CEO/CTO/person boundaries, attendance and Q018, annual-leave/proration/notice, bereavement, salary bands and conditional allowances, salary-review/own-salary, benefit periods and amounts, remote accidents, security negations, Q096 cross-document hybrid, Q097 on-call/Sunday rate, Q098 leave incident and unsupported-answer cases. No broad supported omission, unsupported addition or unrelated citation was found in the Q001–Q100 capture.

## Safety gate failure and repeatability

The existing six-case current V2 smoke passed **6/6** on the candidate. The documented nine-case high-risk repeat (Q055/Q083/Q088/Q090/Q091/Q092/Q096/Q097/Q100) passed **9/9** with identical answer, status and citation IDs to candidate broad; Q100 remained zero-citation NO_ANSWER. The added private-scope check passed manager access, STAFF direct 404, manager grounded answer and cross-user chat-session 404, but **failed** the STAFF unsupported-answer check.

For “What approval must staff obtain before booking travel?”, the policy answer exists only in manager-granted private `UAT-GROUNDING-001`. STAFF did **not** retrieve or cite that private document and was denied direct access, but received a cited, unrelated post-incident-rest statement from organization-visible `ND-HR-003` instead of NO_ANSWER. Thus **no private-content permission leakage was observed**, but question/answer relevance and unsupported-answer safety failed. Diagnostics show two irrelevant accessible sources with reranker score 0 admitted into answer context, followed by a `SUPPORTED` claim check for the unrelated cited statement. The first observed erroneous boundary is context admission of irrelevant evidence; deeper retrieval/rerank threshold versus answer-responsiveness causation requires a separately approved investigation. Do not label this a proven candidate-only regression: the active accepted V2 API was not queried with the new test. Full failing response, citation, diagnosis and scope are preserved in `artifacts/task-035-3b-20261013/permission-safety.json` and `security-repeatability.md`.

Therefore the broad 98/98 semantic/citation result **does not** make the overall candidate safe or qualified. Candidate permission/safety gate: **FAIL**. No application source, images, prompts, thresholds or benchmark expected answers were changed to hide the failure.

## Performance, stability and post-run protection

Broad wall time 620.14 s; mean 5,641.42 ms, p50 2,721 ms, p95 14,378.6 ms, maximum 93,291 ms on first cold Q001; zero transport errors. The accepted broad p95 23,745.75 ms is a historical comparison, **not** an enforceable SLO. No performance SLO PASS is claimed. Candidate API/worker/PostgreSQL/Redis remained healthy, restart count 0, OOM false; live/ready HTTP 200 and Redis PONG after run. No candidate document-processing task or unexpected replay was observed. See `artifacts/task-035-3b-20261013/runtime-stability.md`.

Post-run candidate corpus remains 9/9 READY, 143 chunks, 3 users, one grant and the same migration. All document, chunk identity/hash/embedding-metadata and grant rows exactly equal the untouched pre-run independent restore database. Benchmark writes are accounted for separately: chat sessions 0→116, messages 0→232, citations 0→118 and audit rows 18→372. The protected V2 container IDs, API/worker image IDs, Redis mapping, 9/9/143/3/migration counts and saved H5.2 broad hash remained unchanged. Existing 035.3A synthetic resources remained healthy. No volume was deleted, service was recreated in a protected project, image was rebuilt, or data was restored over an existing populated database.

## Qualification decision and next authority gate

| Area | Decision |
| --- | --- |
| TASK-035.3B approved workflow and evidence review | **COMPLETED** |
| Isolated V2 restore/corpus | **PASS** |
| Supported broad semantics | **98/98 PASS** |
| Broad material citation identities/support | **101/101 PASS** |
| Q018 and Q100 | **SAFE ABSTENTION** |
| Direct RBAC and cross-user isolation tested | **PASS**, no private leakage observed |
| Permission-aware unsupported-answer safety | **FAIL**, one nonresponsive cited answer |
| Nine-case repeatability | **9/9 PASS** |
| Candidate API/worker identity | Aligned, images unchanged |
| Runtime health | Stable in observed window |
| Candidate reproducibility | **PARTIAL**: local source/base/lock and restored corpus; no independent byte-for-byte or off-host rebuild/DR |
| Overall candidate qualification | **FAIL** |
| Active API/worker skew | **STILL PRESENT** |
| Ready for next TASK-035 verification phase | **NO** until safety defect is investigated and a new candidate is separately authorized/requalified |
| RC sign-off | **NOT GRANTED** |

The next safe action is a separately approved, generic investigation of why zero-relevance accessible hits were selected and a nonresponsive answer passed grounding validation. Preserve this failed image/corpus/evidence set. Any code correction or rebuilt candidate invalidates this frozen qualification and must repeat affected safety plus broad/relevant regression gates under new authority. Other TASK-035 RC blockers remain: active image reconciliation, frontend and security/dependency coverage, original TASK-034.1 disposition, off-host DR/rollback, policy-authority Q018 decision if required, pending deferral decisions and release/version/TLS sign-off. None was approved here.
