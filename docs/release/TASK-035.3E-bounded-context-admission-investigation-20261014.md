# TASK-035.3E — bounded context-admission investigation

Date: 2026-10-14 (Asia/Saigon). **COMPLETED as investigation and test design.**
Decision: **NO DEFENSIBLE CONTEXT ADMISSION CORRECTION IDENTIFIED.** No
production correction, image build, service recreation, database/Redis write,
corpus change, model/dependency download, or RC sign-off was performed.

## Protected evidence and scope

The authoritative 035.3B qualification and permission capture remain at
`docs/release/TASK-035.3B-isolated-candidate-qualification-20261013.md`,
`artifacts/task-035-3b-20261013/security-repeatability.md`, and
`artifacts/task-035-3b-20261013/permission-safety.json`. The 035.3C diagnostic,
035.3C.1 runtime report, 035.3C.2 design stop, 035.3C.2E/2F decisions, 035.3D
decision/next-action charter, 035.2 traceability matrix, and H5.2 V2 final
qualification were inspected. Those documents distinguish a historical V2
98/98 supported-case result from the **failed** 035.3B candidate permission
safety gate. The 035.3C.2E/2F model/obligation prototypes selected no safe
replacement; this investigation did not reopen or retune them.

The repository is on `main` with extensive pre-existing uncommitted H5.2,
release-documentation and experimental changes. Nothing was reset or committed.
The existing `AGENTS.md` was absent. Read-only `docker ps -a` shows accepted V2
API `9d510d8b8027`, worker `2afc4af27fe5`, PostgreSQL `1a5a658a2ef2`, and
Redis `db2961fc9413` **up/healthy**; the four 035.3B candidate containers
`39b1a6632ee5`, `dc3d812bafc6`, `b1fdda3a7a0a`, and `50fbede718ce` remain
exited 255. `docker volume ls` still lists all four candidate volumes and the
accepted V2 volumes. Neither container state nor volume listing proves candidate
DB integrity; no database query or live replay was made. Historical Celery
accounting remains UNKNOWN.

SHA-256 checks at this checkpoint match the previously recorded evidence:
`permission-safety.json` `b6e0f415dee409be55786fb4788cf9888d06890e0cfe684444013a5a1196714f`,
`broad-v2-candidate.json` `4e117caf65281168d01b71822bf686398a2e1cb4fb03a170b46aa7ff740b5c58`,
and `h5-2-qualification-20261013.md` `4ebd7d1eef42d8154aebf440e4ad469f32a01d1d580821bedaa2a3a9fdb36e0a`.
Shared production file hashes remain `4c9d4c64...` (grounded answer),
`26b2daaf...` (context builder), `4fa1e470...` (reranker), and `d7e11c25...`
(claim validator), matching the prior manifest. This is source/evidence identity,
not a fresh full V2 acceptance or data-integrity verification.

## Exact failed evidence flow

**Verified from preserved capture:** STAFF asked, “What approval must staff
obtain before booking travel?” The sole V2 answering policy clause was in
private `UAT-GROUNDING-001`, available to its owner and VIEW-granted manager,
not STAFF. Manager document detail and cited answer succeeded; STAFF private
document detail and cross-user chat detail returned 404. STAFF's response was
`ANSWERED` HTTP 201, citing one permission-visible `ND-HR-003` page-8 chunk
`59403786-a55a-4f4e-a4d2-dab07671a61e` about post-incident rest rather
than travel approval. The saved diagnostics show two selected visible chunks:
`UAT-SHARED-001` `e1708875-821e-48d0-b542-460a5623a0ec` (hybrid 0.01739,
reranker 0.0), and that ND-HR-003 chunk (hybrid 0.01713, reranker 0.0).
Neither contains the requested approval. The private answer chunk was not
selected for STAFF. The citation supports the *quoted sentence* but not the
question. Expected STAFF behavior was NO_ANSWER with zero citations.

**Inferred from source and observation:** permission-filtered retrieval found
visible but insufficient candidates; `_prepare_prompt_retrieval_hits` retained
ranked and candidate pools, and `select_context_for_prompt` admitted hits that
fit the token budget. Source registry creation made them available as citation
sources. This is the **first observed unsafe progression**, not proof that
retrieval itself violated its documented similarity/keyword contracts.

**Unknown:** original per-channel hit lists and raw scores, the full reranker
candidate set and raw model logits, exact excerpt transformations and all
draft/retry/repair outputs for this request. The preserved final capture cannot
identify which generation attempt first emitted the unrelated sentence. A
previous isolated diagnostic independently demonstrated a generic validator
verbatim-support gap; it does not reconstruct this request's missing trace.

## Actual boundary and score contracts

| Boundary | Actual function and inputs → outputs | Existing guard/fallback and limit |
| --- | --- | --- |
| Question interpretation | `app/retrieval/question_analysis.py:166` `analyze_question(question)` → answer-shape flags; `question_terms`/normalization and `information_need_queries` derive retrieval forms. | Extracts types such as person, value, yes/no and condition; not a general requested-action/actor/relation entailment record. |
| Vector candidates | `app/retrieval/semantic_repository.py:~50` `search_permitted_chunks` with query embedding, user, top-k, minimum → `RetrievalRow`. | `READY`, `build_accessible_document_filter`, cosine-distance minimum. `relevance_score = 1 - cosine_distance`, bounded 0–1 by model; similarity is not material answer support. Embedding failure becomes `RetrievalError`. |
| Keyword candidates | `app/retrieval/keyword_repository.py:~105` `search_permitted_chunks_by_keyword` → ranked rows. | `READY`, same permission filter, `@@` match, `ts_rank_cd` minimum. Diacritic/identifier/fallback query variants may recover valid hits; rank is nonnegative lexical relevance, not a probability or cross-channel comparable score. |
| Hybrid | `app/retrieval/fusion.py:~25` `fuse_retrieval_hits`; `app/retrieval/hybrid_service.py:~200` `_merge_variant_fusions` → ranked hybrid hits. | RRF sums channel weight / (`rrf_k` + one-based rank); keyword-only and vector-only hits are valid. Variant merge adds a small original-form precedence offset. A positive RRF is evidence of a candidate rank, not an answer probability. Service failure raises retrieval error rather than silently granting access. |
| Reranking | `app/retrieval/reranker.py:235,294,~405,~692` heuristic or local cross-encoder → ordered hits with `reranker_score`. | Cross-encoder raw scores are min-max normalized **within that candidate set** to 0–100; singleton/tied sets become 50. Heuristic alignment is added and floored at 0. Model load/timeout falls back to heuristic; `_prepare_prompt_retrieval_hits` catches rerank failure and uses prompt ranking. `0.0` is not calibrated irrelevance; unreranked/adjacent hits can have `None`. |
| Prompt pool | `app/services/grounded_answer_service.py:1607` `_prepare_prompt_retrieval_hits` → candidate/reranked/adjacent merged hits; `:4691` `_rank_hits_for_prompt`. | Permission-filtered supplements and adjacent expansion, question-specific prioritizers, non-answer *reference/question-list* guard, and **relative** low-alignment-document filtering. `_merge_retrieval_hits(reranked_hits, candidate_hits)` and final merge retain fallback candidates. No generic proof of query-material answer coverage. |
| Actual admission | `app/chat/context_builder.py:137` `select_context_for_prompt(hits, question, information_needs, max_tokens)` → `SelectedContext.items`; `:221` `query_focused_excerpt`. | Excerpt focus and token budget, not a materiality predicate. A short unrelated hit can pass unchanged if it fits. The first source registry at `app/citations/registry.py:10` maps selected items (up to `max_sources`) to SOURCE markers; identity/score fields are carried, not reclassified. |
| Generation/NO_ANSWER | `app/services/grounded_answer_service.py:~690` `_answer` builds source registry/prompt and calls provider; `:3114` `_reason_evidence_is_missing`, `:4554` `_should_retry_no_answer`. | Zero sources and certain named-entity/reason/leave gaps abstain; no universal missing-relation rule. A no-answer draft can be retried for lexical/number overlap. Generation/repair stage for failed STAFF request is UNKNOWN. |
| Citation/claim/final | `app/services/grounded_answer_service.py:2083` `_draft_from_generation`; `app/services/claim_evidence_validation_service.py:1288` `_validate_answer_against_evidence`. | Citation mapping checks source identity/permissions; condition/value/topic guards are selective. Generic non-yes/no, non-value, non-person verbatim evidence can return `SUPPORTED` before question responsiveness (`~1360`). This independent final-answer gap remains open. |

Existing unit coverage includes context budget/excerpt behavior,
semantic/keyword/hybrid retrieval service contracts, and permissions. The
035.3C.2 A–O claim test documents final-responsiveness failures. These tests
do **not** establish a general context-admission sufficiency contract.

## Synthetic test-first result and alternative assessment

New test-only file:
`tests/unit/test_task0353e_context_admission_contract.py`. It calls the
actual `select_context_for_prompt` with invented archive/specimen/field-kit
evidence; it does not load V2 data, DB fixtures, Docker, a model, or a network
service. The input hits represent the *post-permission-filter candidate pool*;
case B deliberately excludes its private source and therefore does not by
itself prove the upstream RBAC query. High token budget isolates admission
from truncation. Cases L/M correctly retain contradiction/partial text as
context useful for correcting a premise or abstaining; neither is asserted to
be complete support for a final positive answer. The A–O design includes eight
answer-bearing positive controls (A/D/E/F/G/H/I/O) and seven safety-negative
controls (B/C/J/K/L/M/N); L/M are negative at the final-claim sufficiency
boundary, not at the context-presence boundary.

| Case | Required control | Current context outcome |
| --- | --- | --- |
| A | Relevant accessible policy | PASS; material hit admitted |
| B | Answer only in inaccessible private source | PASS at post-filter boundary; no input source admitted (upstream RBAC separately tested) |
| C | Only irrelevant accessible policy | **FAIL**; irrelevant hit admitted |
| D | Relevant plus irrelevant | **FAIL**; relevant preserved but irrelevant also admitted |
| E | Vietnamese paraphrase, synthetic reranker 0 | PASS; relevant hit retained |
| F | English paraphrase | PASS |
| G | Mixed terminology | PASS |
| H | Conditional policy | PASS; full condition-bearing text retained |
| I | Complementary two documents | PASS; both retained |
| J | Same topic, wrong action/relation | **FAIL**; insufficient hit admitted |
| K | Same unit/number in unrelated policy | **FAIL**; unrelated hit admitted |
| L | Reversed prohibition | PASS **for context retention only**; contradicts any permissive answer, which must be checked downstream |
| M | Incomplete approval rules | PASS **for context retention only**; complete-answer sufficiency remains unproved |
| N | No authorized hit | PASS; empty context enables NO_ANSWER |
| O | Valid keyword-only hybrid fallback | PASS; evidence retained |

Result: **11/15 context-selection expectations pass, 4/15 fail**. All four
intended irrelevant-hit exclusions (C, D's extra hit, J, K) fail: **4/4 unsafe
context admissions** in this deliberately diagnostic set. Among the eight
clearly material answer-evidence controls A/D/E/F/G/H/I/O, **0/8 false
abstentions** at this admission boundary; D still fails because of the extra
irrelevant hit. These are *fixture-conditioned counts*, not runtime rates or
release acceptance. L/M are not included in that eight-case complete-answer
denominator. Case B's absent private input is not a fresh permission proof.
Two additional *final-claim* controls, explicitly separate from the 15
admission cases, pass that admitted L/M context to the existing claim
validator. Both fail the desired safety status: an affirmative answer to the
prohibition returns `SUPPORTED` rather than `CONTRADICTED`, and a copied
partial approval sentence returns `SUPPORTED` rather than `INSUFFICIENT`.
Thus **2/2 final-claim negative controls are unsafely accepted** in these
invented fixtures. This is a unit-level observation, not proof that the live
generation path would emit those exact answers.

Only three bounded options were considered:

1. Reuse `READY`/RBAC and `is_non_answer_context`/structured question-specific
   guards. These remain essential but classify ordinary irrelevant policy
   sentences as answer-like. They cannot reject the preserved ND-HR-003 clause
   or synthetic C/J/K. The relative alignment-document filter also keeps
   low-scoring-only candidate sets by design, while fallback merges can retain
   candidates. **Not sufficient.**
2. Exclude `reranker_score == 0` or impose a global vector/RRF/keyword cutoff.
   The observed two sources would be removed by the zero rule, but the score is
   relative/floored and the synthetic relevant Vietnamese E is also 0: at
   least **1/8 false abstentions** on the answer-evidence controls in that
   test-only counterexample. Raw score calibration and retrieval-mode
   comparability are absent. **Rejected, not implemented.**
3. Require ordinary lexical/number overlap or a currently exposed structured
   match. Lexical overlap misses E/F/G-style paraphrase/cross-language cases;
   overlap itself admits J/K, where topic or value matches the wrong relation.
   Existing structured guards are strong for selected value, salary, leave,
   attendance, role and policy shapes but do not expose a general matched
   proposition/action/actor/condition object for this OTHER approval query.
   No measured reliable general rule follows. **Not sufficient.**

No arbitrary threshold, new ontology, embedding model, LLM judge, score
calibration claim, or benchmark-specific rule is proposed. The failed context
admission is verified, but *which generic signal should decide sufficiency*
is not. Even a later bounded admission fix would address only the evidence
pool; the separate copied-clause final-responsiveness defect would still
require its own proven correction and end-to-end permission/no-answer gate.

## Quality and decision

Focused isolated run: `python -m pytest -q` on this contract plus context
builder, hybrid, vector, keyword service and permission unit files completed
**135 passed / 6 intentional new contract failures** (four admission, two
final-claim). It did not use
`tests/integration` or its destructive DB cleaner. Ruff check, Ruff format
check, Python compilation and `git diff --check` pass for the new test and
working diff (the latter emits only pre-existing CRLF normalization warnings).
No after-correction test exists. No broad V2/candidate benchmark was run.

| Required decision field | Result |
| --- | --- |
| TASK-035.3E | **COMPLETED** as bounded investigation |
| FIRST VERIFIED ADMISSION FAILURE | Permission-visible, question-irrelevant chunks selected into answer context in 035.3B; synthetic reproduction at context builder |
| ACTUAL CONTEXT-SELECTION BOUNDARY | `_prepare_prompt_retrieval_hits` → `select_context_for_prompt` → source registry; budget/excerpt, no generic materiality proof |
| SCORE SEMANTICS | Vector cosine similarity; keyword `ts_rank_cd`; rank-based RRF; relative/floored reranker; none calibrated answer-support probability |
| EXISTING ADMISSION INVARIANTS | READY/RBAC; channel minima; topic-specific filters, reference/scaffolding exclusion, budget/source limit; no general proposition-coverage gate |
| SYNTHETIC TEST RESULTS | Admission 11/15 pass, 4/15 fail; final-claim L/M 0/2 pass; isolated unit aggregate 135 pass / 6 fail |
| UNSAFE ADMISSION CASES | C, D extra hit, J, K = 4/4 intended exclusions |
| FALSE ABSTENTION CASES | Current boundary 0/8 complete-answer positive controls; zero-score proposal at least 1/8 in test-only E counterexample |
| MULTILINGUAL POSITIVE CONTROLS | E, F, G retained by current permissive boundary; no new rule proven to preserve them |
| MULTI-DOCUMENT CONTROLS | I retained; D retained relevant hit but also unrelated one |
| RECOMMENDED CORRECTION | **NONE** |
| CORRECTION EVIDENCE | **INSUFFICIENT** |
| FINAL ANSWER RESPONSIVENESS GAP | **OPEN** |
| READY FOR SOURCE-LEVEL FIX | **NO** |
| READY FOR NEW CANDIDATE BUILD | **NO** |
| ORIGINAL H5.2 BASELINE | **INTACT for checked identities/source/evidence; no fresh data-integrity or broad requalification claimed** |
| FROZEN FAILED CANDIDATE | **PRESERVED** (containers exited 255; volumes and evidence present; DB integrity UNKNOWN) |
| PRODUCTION CODE MODIFIED | **NO** |
| RC STATUS | **NO-GO** |
| TASK-035 | **IN PROGRESS** |

**Next required authorization:** a separately scoped design/evidence plan
that establishes an independently reviewed multilingual, relation/condition/
polarity-sensitive admissibility signal (or an explicitly narrower safety
contract), with matched positives and negatives and an independent fresh test
set. Any model/dependency/LLM call, production edit, image build, service
restart or candidate requalification requires its own authorization. Do not
promote the failed candidate or mark B19/B21/current RC safe from historical
98/98 or these offline observations.
