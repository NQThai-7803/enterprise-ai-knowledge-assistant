# TASK-035.3C.2 — multilingual answer responsiveness, test-first design stop

Date: 2026-10-14 (Asia/Saigon). **Status: PARTIAL / BLOCKED at the explicit Phase 4 design gate.** No production correction was implemented. The frozen TASK-035.3B candidate remains FAILED; TASK-035 remains IN PROGRESS and RC sign-off is NOT GRANTED. This checkpoint adds a synthetic test-only contract and records why none of the currently evidenced mechanisms meets the requested multilingual safety and false-abstention requirements.

## Protected baseline and pre-correction manifest

Branch `main`, HEAD `04ebd73aae737414fb591fe2e8b2c286134cdcd8`; the completed H5.2 source remains in the pre-existing dirty working tree. No reset, commit, volume operation, migration, build, deployment, candidate restart, active V2 recreation, or corpus/Redis/PostgreSQL write was performed. The original accepted V2 and failed candidate retained these container/image identities in read-only Docker inspection:

| Project/service | Container prefix | Image prefix | State |
| --- | --- | --- | --- |
| V2 API | `9d510d8b8027` | `sha256:1f057785bd8c` | running, healthy, restart 0, OOM false |
| V2 worker | `2afc4af27fe5` | `sha256:1e19725cdd89` | running, healthy, restart 0, OOM false |
| V2 PostgreSQL | `1a5a658a2ef2` | `sha256:cf134a767f47` | running, healthy, restart 0, OOM false |
| V2 Redis | `db2961fc9413` | `sha256:858f009f9709` | running, healthy, restart 0, OOM false |
| Failed candidate API | `39b1a6632ee5` | `sha256:97cf3222e128` | exited 255, unchanged |
| Failed candidate worker | `dc3d812bafc6` | `sha256:ccf26439f4ca` | exited 255, unchanged |
| Failed candidate PostgreSQL | `b1fdda3a7a0a` | `sha256:cf134a767f47` | exited 255, unchanged |
| Failed candidate Redis | `50fbede718ce` | `sha256:858f009f9709` | exited 255, unchanged |

The accepted V2 corpus/data rebaseline remains the completed TASK-035.3C.1 read-only result, not a new database scan here. Historical H5.2 qualification and frozen candidate evidence remained byte-identical: H5.2 qualification SHA-256 `4ebd7d1eef42d8154aebf440e4ad469f32a01d1d580821bedaa2a3a9fdb36e0a`; candidate broad capture `4e117caf65281168d01b71822bf686398a2e1cb4fb03a170b46aa7ff740b5c58`; permission-safety capture `b6e0f415dee409be55786fb4788cf9888d06890e0cfe684444013a5a1196714f`. The failed candidate database is still NOT VERIFIED after exit 255.

Pre-correction host source SHA-256 manifest (no production source changed after recording it):

| Path | SHA-256 |
| --- | --- |
| `app/services/claim_evidence_validation_service.py` | `d7e11c25b42d710b1a2ba4d325244adecb371c723dda9b3148b27bdc4f65b6e1` |
| `app/services/grounded_answer_service.py` | `4c9d4c648bbcef30a35c4e2ca01fad0093ed0e7a8aebb777dc78b478b345c919` |
| `app/retrieval/question_analysis.py` | `ed8cdd729b7e2c1285d14e33056193c13fbd550d425b7237744a973681c40c8e` |
| `app/chat/context_builder.py` | `26b2daafcc7da2448ba8933e6702e12cd58d880edb92b054edefb7dfe8884ab8` |
| `app/retrieval/reranker.py` | `4fa1e470dfa097f3b881f9dfdaef3fb7771cd4953bfe99031c8b77dd882da8d0` |
| `app/citations/evidence.py` | `f46189b9b3f09d8bb2f87efa5fef1518aa1de2a522763c9dda01476d41e59bdf` |

There is no root `requirements.lock`; the frozen candidate's dependency lock and source manifest remain in its separate TASK-035.3B artifacts. No dependency manifest or schema file was changed.

## Actual validation architecture

The original resolved user question reaches `GroundedAnswerService._draft_from_generation`, is passed to `ClaimEvidenceValidationService.validate`, and is available to `_validate_answer_against_evidence`. Citation validation maps/revalidates cited permitted sources before claim validation; `SUPPORTED` then leads to `GroundingStatus.ANSWERED`. Invalid claim status enters existing repair/NO_ANSWER handling, rather than persisting an accepted citation. A replacement generation in the ordinary retry/quality-repair paths is passed through `_draft_from_generation` again. Compound claims are validated individually against their information needs in `_validated_structured_claims`; their combined output is then passed to `_draft_from_generation` with `claims_already_validated=True`, so it does not receive another combined-claim validation. This bypass is an architecture observation, **not** proof of an additional live failure. The exact failed request's original draft and repair stage remain UNKNOWN.

The independent verified gap is in `_validate_answer_against_evidence`: a copied clause for a generic non-yes/no, non-value, non-person question can return `SUPPORTED` before generic question-to-answer responsiveness is established. Question-specific relation guards and `require_subject_attribute_alignment=True` cover selected cases but do not provide a general bilingual entailment contract. Current context selection admitted the two irrelevant yet permitted sources in the failed case; per-channel retrieval scores and raw reranker scores were not saved. A normalized/floored reranker `0.0` is not calibrated irrelevance and is not a safe global gate.

## Test-first multilingual result (before correction)

Added `tests/unit/test_multilingual_answer_responsiveness_contract.py`, an unmarked fake-only unit module using synthetic documents and permission-filtered source registries. It has no protected database, Docker, network, or model target. Each case asserts the final *claim-validation status* for a question, proposed final answer, and cited authorized evidence. It does **not** by itself prove API-level ANSWERED/NO_ANSWER, citation materiality, RBAC enforcement, or persistence. In B and O, the private or unsupported source is absent from the registry; the claim service correctly returns INSUFFICIENT. Existing citation and permission unit tests remain separate.

| Cases | Intended controls | Before-correction result |
| --- | --- | --- |
| A, F, H, I, J | Relevant English answer, English paraphrase, two-source material answer, false-premise correction, obligation reversal | 5 PASS |
| B, O | No cited authorized evidence | 2 PASS at claim service |
| C, D, L, M, N | Unrelated English/Vietnamese source, shared irrelevant number, changed final claim, missing material condition | 5 FAIL: false acceptance (`SUPPORTED`) |
| E, G, K | Vietnamese paraphrase, English/Vietnamese cross-language support, valid conditional clause | 3 FAIL: false abstention (`INSUFFICIENT`) |

Thus the new A–O test-first contract is **7 passed, 8 failed**. The prior 035.3C.1 diagnostic suite remains **4 passed, 3 strict expected failures**. Combined completed run: **11 passed, 8 failed, 3 xfailed**. No newly failing case was skipped, xfailed, or weakened. The synthetic matrix is a regression design and exposes current behavior; no after-correction result exists.

## Why the approved implementation stops at Phase 4

The narrow *boundary* is known—question-aware claim validation before final ANSWERED—but a defensible *decision mechanism* is not established. Applying existing subject/attribute alignment or a new keyword/phrase overlap gate to every copied clause would likely reject legitimate low-overlap Vietnamese, paraphrased, and cross-language positives; E/G/K already demonstrate false abstention in the current heuristics. A fixed score on the existing reranker or multilingual embedding would conflate relevance with entailment and ignore that reranker normalization is relative. Adding a few bilingual synonym mappings for these synthetic examples would be an unvalidated, domain-limited shortcut rather than a generic correction. None can guarantee that conditions, negation, multi-source relations and relevant paraphrases survive while unrelated copied clauses are rejected.

The configured Qwen-compatible provider can generate and repair answers, but it has no existing calibrated, deterministic answer-responsiveness/entailment verdict contract. An additional LLM judgment would require a new prompt, call and failure path; it could hallucinate relevance, add latency/tokens and timeouts, and send another copy of permission-filtered question/evidence to the configured model provider. A timeout would require an explicit fail-safe policy that risks false abstention. Mocked unit tests would verify wiring, not real multilingual reliability. The repository's existing cross-encoder is a retrieval reranker, not a validated entailment model. No isolated reliability/latency/privacy evaluation or authority for a material architecture change was supplied. Automatically adding another model call or dependency would violate the stated gate.

Accordingly, the Phase 4 instruction **“If no defensible correction can be established, STOP”** applies. A partial lexical fix would improve selected negatives while leaving the requested multilingual positive contract unproved and risking the historical 98/98 H5.2 baseline. No production source edit, threshold change, retry increase, prompt change or candidate build was made. TASK-035.3C.2 is PARTIAL / BLOCKED, not falsely completed.

The exact next evidence/decision needed is a separately scoped, isolated evaluation of candidate multilingual responsiveness/entailment mechanisms on this A–O contract plus a substantially wider positive/negative policy corpus (including false-premise, condition, number-binding, permission, citation and low-overlap paraphrases), with measured false-accept/false-abstention rates, latency, timeout, determinism and provider/privacy behavior. The user must approve any extra LLM call, new model/dependency, or explicitly narrower deterministic safety contract before production integration. The test contract can then drive a small implementation at the existing claim/final-answer boundary, followed by all affected unit and safety gates, a **new** reviewed source snapshot and same-source API/worker images, and isolated requalification. Required later candidate gates include STAFF unsupported-answer safety, manager positive access, multilingual controls, ingestion/Celery smoke, citation/RBAC, the full frozen V2 Q001–Q100, independent semantic grading, high-risk repeatability and post-run integrity. The old failed candidate is never promoted; historical 98/98 does not transfer to changed images.

## Checkpoint gates and final status

Ruff check and Ruff format check passed for both synthetic test files after formatting; Python compilation passed; `git diff --check` exited 0 (pre-existing CRLF warnings, no whitespace errors). The before-correction pytest run intentionally exits nonzero due to 8 real contract failures. Broader unit and runtime qualification gates were **NOT RUN** because Phase 4 stopped before any correction; no PASS is claimed for them.

| Required field | Result |
| --- | --- |
| TASK-035.3C.2 | **PARTIAL / BLOCKED** at the explicit design gate |
| ROOT CAUSE ADDRESSED | **NO**; origin boundary verified, safe generic mechanism unresolved |
| PRODUCTION MODULES CHANGED | **NONE** |
| QUESTION RESPONSIVENESS CONTRACT | Grounding and authorized citation are necessary but not sufficient; final answer must satisfy the original information need |
| MULTILINGUAL POSITIVE TESTS | A/F/H/I pass as scoped; E/G/K false abstain; see matrix |
| MULTILINGUAL NEGATIVE TESTS | B/J/O pass as scoped; C/D/L/M/N false accept; see matrix |
| EXPECTED FAILURE TESTS BEFORE / AFTER | 3 existing strict xfails before; 8 new unmasked failures before; **no after** (no correction) |
| FALSE ACCEPTANCE | 5 of the new synthetic claim-status controls |
| FALSE ABSTENTION | 3 of the new synthetic claim-status controls |
| UNIT REGRESSION | New test-first run 7 pass / 8 fail; broader unit gates NOT RUN after Phase 4 stop |
| RUFF / FORMATTING / COMPILATION | PASS for the two test-only modules |
| SOURCE HASHES | Pre-correction table above; no production after-change hash because no edit |
| ORIGINAL H5.2 RUNTIME | **PRESERVED** at checked container/image identity; data integrity relies on completed 035.3C.1 rebaseline |
| FROZEN FAILED CANDIDATE | **PRESERVED**, still exited 255; DB integrity NOT VERIFIED |
| NEW CANDIDATE IMAGES | **NOT BUILT** |
| RUNTIME CORRECTION | **NOT VERIFIED** |
| READY FOR NEW CANDIDATE BUILD | **NO** |
| TASK-035 | **IN PROGRESS** |
| RC SIGN-OFF | **NOT GRANTED** |
