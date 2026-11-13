# Architecture Decisions

This file lists accepted project-level decisions. Detailed records may be added under `adr/`.

## DEC-001 — Backend framework

Use FastAPI for the Python backend.

## DEC-002 — Primary database

Use PostgreSQL with pgvector.

## DEC-003 — Async document processing

Use Celery with Redis for background processing.

## DEC-004 — MVP document type

Support text-based PDF first. OCR and other formats come later.

## DEC-005 — Authorization model

Use role plus document access scope and optional direct grants.

## DEC-006 — RAG safety

Permission filtering occurs before context is sent to the LLM. Citations are validated by backend.

## DEC-007 — Provider abstraction

Embedding, LLM and storage providers must be replaceable through interfaces.

## DEC-008 — Held-out v1 is used for diagnosis

Since the official score (2026-11-05, `docs/eval/runs/heldout-v1-f3cdbf3/score.md`), held-out v1 is used for diagnosis and is no longer a test set. A new held-out v2 is required before release. Dev stays Q001-Q100.

## DEC-009 — Reranker deferred; RAM limits for eval

Stay on the lexical fallback for now. PROMPT 6 comes after the fixes to the deterministic route, the alignment filter and the validator. The 1000 MB Available limit applies only when loading or measuring a model alone, with Ollama not loaded. During eval runs the held-out validity rules apply: no INFRA_ERROR, no Ollama restart, no item above 120 s.

## DEC-010 — Rule for choosing RAG_DETERMINISTIC_ROUTE_MODE

Written before any measurement of `legacy`, `strict` or `off` (FIX 1, 2026-11-05).

The route is `_structured_condition_value_answer`. The other deterministic branches are not part of this choice.

Compare each mode with `legacy`, on the RBAC dev set:

1. `false_answer` must not increase.
2. The number of correct answers must increase. A correct answer is a control that passes `control_passed` (right status, right document cited, fact present).

Then:

3. Q001-Q100 only detects regressions and never picks a mode. A regression beyond the guard's tolerance of 1 question, a change of `false_answer_rate` beyond it, or any permission leak blocks the default change under `eaka-rag-change-guard`, and the owner is told.
4. Held-out v1 runs once at the end, as a diagnostic, and does not influence the choice or any further change.

**Addition by the owner, written before measuring `strict` or `off`.** The branch `_structured_condition_value_answer` answers 0 of the dev questions, so dev cannot show its value. A branch not used on dev but with evidence of harm (held-out v1: 6/6 FAIL) takes `off`, provided UAT and RBAC show no regression. This addition replaces rule 2 for this branch: `off` does not need more correct answers than `legacy`. A regression means more than the guard's tolerance of 1 question on UAT, more false answers or fewer correct answers on RBAC, or any permission leak.

If both `strict` and `off` pass, take the one with more correct answers, then fewer false answers, then `strict` because it keeps the route. (The owner set rules 1 to 4; this tie-break was added by the implementer before measuring.) If neither passes, the default stays `legacy`.

**Second addition by the owner, written before measuring `strict` or `off`.** It is based on the branch breakdown of `legacy` (`condition_value`: 2 correct, 13 wrong on RBAC plus held-out v1), not on any `strict` or `off` result. Reason: the old rule 2 stood level with rule 1, against the priority that a wrong answer is worse than a refusal.

This replaces every comparison above, including the first addition and the tie-break:

- Required: `permission_leak_count = 0` and no regression on Q001-Q100 (tolerance of 1 question under `eaka-rag-change-guard`).
- Among the modes that meet both, compare in order: (a) lowest `false_answer` on RBAC, then (b) most correct answers on RBAC.
- Modes still equal after (b) are not decided by this rule. The owner decides.

**Result (2026-11-06): `strict` is the default.** `legacy` stays available through `RAG_DETERMINISTIC_ROUTE_MODE` for rollback. Scores: `docs/eval/runs/fix1-route-mode/score.md`.

| Mode | `permission_leak_count` | Q001-Q100 proxy match | RBAC false answers | RBAC correct answers |
|---|---:|---:|---:|---:|
| `legacy` | 0 | 99/100 | 5/18 | 4/18 |
| `strict` | 0 | 99/100 | 0/18 | 5/18 |
| `off` | 0 | 99/100 | 1/18 | 3/18 |

All three modes meet both requirements, and `strict` has the fewest false answers on RBAC, so (a) decides. (b) points the same way. Correction (2026-11-06): RBD-03 also answered falsely under `strict` in the FIX 2 trace, so read its count as 0 to 1. The choice stands, because a tie on (a) goes to (b). The `off` UAT run was interrupted after Q092 and resumed from Q093, which the owner accepted; its metadata records this.

## DEC-011 — Baseline and candidate run in one batch; rule for the FIX 2 defaults

Written before measuring groups 1 + 2 together (2026-11-06).

**Batch rule, for every flag measurement from now on.** A baseline and a candidate are compared only when they ran in the same batch: same image, same session, Ollama not restarted, the API recreated only to switch flags, runs interleaved (baseline, candidate, baseline, candidate). A baseline from another batch does not count. Reason: UAT runs in one session were identical on all 100 questions, while runs on different days matched on 90 (`docs/eval/runs/fix2-results.md`).

**Rule for turning on groups 1 + 2** (`RAG_REPAIR_AFTER_LLM_REFUSAL_ENABLED=false` with `RAG_ANSWER_UNIT_GUARD_ENABLED=true`), 2 runs per side on `answer_relevance_dev_v1`, RBAC dev and UAT. Only changes seen in both runs count (`scripts/eval/compare_flag_runs.py`).

- Required: no permission leak, in the RBAC API runs and in the retrieval check, and no regression on Q001-Q100 (tolerance of 1 question under `eaka-rag-change-guard`).
- If both are met, compare in order: (a) fewer false answers, then (b) more correct answers, each as the sum over `answer_relevance_dev_v1` and RBAC dev.
- The defaults change only if the combination wins on (a), or ties on (a) and wins on (b). Otherwise they stay and the owner is told. The flags stay available for rollback.
- A case that gets worse on either set is reported by id, even when the sum improves.

`RAG_RESELECT_REQUIRES_STRONG_SUPPORT_ENABLED` is not part of this choice and stays off.

**Result (2026-11-07): groups 1 + 2 are the default.** `RAG_REPAIR_AFTER_LLM_REFUSAL_ENABLED=false` and `RAG_ANSWER_UNIT_GUARD_ENABLED=true`; both flags stay available for rollback. Scores: `docs/eval/runs/fix2a-defaults.md`.

| Side | Leak (API + retrieval) | Q001-Q100 proxy match | False answers (relevance + RBAC) | Correct answers (relevance + RBAC) |
|---|---:|---:|---:|---:|
| Baseline | 0 | 99/100 | 8 + 1 = 9 | 13 + 22 = 35 |
| Groups 1 + 2 | 0 | 99/100 | 4 + 1 = 5 | 18 + 22 = 40 |

Both requirements are met and (a) decides. No case got worse on either set.

## DEC-012 — Held-out v2 rules

Set by the owner on 2026-11-07, for batch 1 (`docs/eval/heldout-v2-questions.yaml`, 20 questions from team members, kept word for word, frozen by hash and lock before any other work).

- The system does not run on this set until the owner says so. That covers the API, the trace tools and the eval runners. Comparing question text and embedding similarity to other question sets is allowed.
- This set does not inform any fix: no change to code, thresholds, cues, prompts or dev sets may be based on its questions or gold.
- Gold comes only from the source PDFs of `uat/corpus-v2/manifest.json`, and every excerpt is checked against its PDF page. A compound question has one required point per asked point. A false premise must be corrected in the gold.
- Gold is frozen only after the owner approves `docs/eval/heldout-v2-review.md`. Any edit after that needs a new version and a new lock.
- `scripts/eval/question_fingerprints.json` includes these questions, so `check_no_question_leak.py` blocks them in `app/`.

Known limit: the implementer wrote this gold and also works on fixes in the same session. The fixes approved next (REL-103, REL-303, REL-402) were set by the owner from the relevance dev traces before this set existed.

## DEC-013 — Choose per set, not on a sum

Set by the owner on 2026-11-08, written before the next measurement. Replaces the sum rule of DEC-011; the batch rule of DEC-011 stays.

- Required: no permission leak, in the RBAC API runs and in the retrieval check; no regression on Q001-Q100 (tolerance of 1 question under `eaka-rag-change-guard`); and **false answers do not increase on any single set** (`answer_relevance_dev_v1`, RBAC dev).
- Then compare set by set, in order: (a) fewer false answers, then (b) more correct answers. A candidate wins only if, on every set, it is not worse under that order, and on at least one set it is better.
- Only changes seen in both runs count, and every case that gets worse is reported by id.

Note on the RBAC score: RBD-04 and RBD-05 are correct at baseline only because, without diacritics, "giám" (in "Phó giám đốc") matches the outcome cue for "giảm", so the condition route answers them. A fix that removes that match can lose these two controls without being worse in substance (`docs/eval/runs/fix2b-cues.md`).

## DEC-014 — Ollama version and backend are part of a run

Set by the owner on 2026-11-08, after `docs/eval/runs/nondeterminism.md` found that results change when Ollama changes GPU backend, not when it restarts.

- **Baselines before 2026-11-06 18:26 ran on Vulkan and are not comparable with later runs.** That covers FIX 1, FIX 2 except its second UAT baseline run, and held-out v1 `f3cdbf3`. Later runs use CUDA.
- Pinned for local measurements: Ollama **0.40.15**, backend **CUDA** (GTX 1650, driver 13.3). Auto-update of the Windows app is off (`auto_update_enabled = 0` in `%LOCALAPPDATA%\Ollama\db.sqlite`, the "Auto update" switch in the app settings) while measurements run.
- Every eval runner refuses to start when the Ollama version or backend differs from the expected one (`scripts/eval/ollama_check.py`, called from `reranker_check.guard`). The defaults are the pinned values above; `EVAL_OLLAMA_EXPECTED_VERSION` and `EVAL_OLLAMA_EXPECTED_BACKEND` override them for another host (CI runs on CPU).
- Every run records `ollama_version`, `ollama_backend` and `ollama_auto_update` at the start and the version and backend at the end. A change during the run invalidates it.
- Changing the pinned version or backend is a new baseline: re-run the baseline in the same batch as the candidate (DEC-011) before comparing anything.

## DEC-016 — Temporary: CI replaces local verification and measurement

Set by the owner on 2026-11-08, because the local host stays below the 1000 MB start gate. Temporary; it ends when the repository moves out of OneDrive and local runs are possible again. **Verification part ended by DEC-018 (2026-11-09); measurement stays on Actions.**

- **Verification:** a branch is pushed and the 4 GitHub CI checks replace `eaka-verify` before review. No PR is merged until all 4 checks are green.
- **Measurement:** every batch runs on GitHub Actions (`eval.yml`, `workflow_dispatch`) through `scripts/eval/ci_batch.sh`. The baseline and every candidate configuration run in the same job, interleaved (run 1 of each, then run 2), on one image and one Ollama (0.40.15, CPU). DEC-011 and DEC-013 apply unchanged.
- **Metadata:** each batch records the Ollama version and backend (`batch.json`), and every runner records them per run (DEC-014).
- **No comparison with local runs:** CPU and CUDA runs are not comparable. A decision uses only runs from one Actions job.

## DEC-018 — Local eaka-verify is back before every push

Set by the owner on 2026-11-09, after the repository moved to `C:\dev\eaka`. Ends the verification part of DEC-016; its measurement part stays, now under DEC-017 (embedding fine-tune, PR #14).

- **Rule restored: eaka-verify green locally, then push.** The image is built from `git archive` of the commit, the lanes of `ci.yml` run in it against the throwaway stack of `scripts/test/compose.integration.yaml`, and the 4 GitHub CI checks stay required before a merge.
- **Evidence (2026-11-09, `315efd6`):** unit 1698 passed, api 51 + 245, integration 404, llm-provider 3; 0 failed, 0 regressed against `6a2c72f`. Available RAM was 1100-1380 MB at the start, 296 MB at the lowest during the run (Docker VM peak 1816 MB), with no out-of-memory error; the whole run took about 5.5 minutes.
- **The 1000 MB Available gate applies at stack start.** Below it, wait; if it stays below, verify on CI as under DEC-016 and say so in the report.
- **Measurement stays on GitHub Actions (CPU)** for end-to-end, flag and model comparisons (DEC-016, DEC-017). Local and Actions numbers are never compared.

## DEC-019 — CI replaces local eaka-verify when the RAM gate stays closed

Set by the owner on 2026-11-09. Amends DEC-018.

- **Fallback:** if Available RAM stays below the 1000 MB gate for 15 minutes, the branch may be pushed and the 4 GitHub CI checks stand in for local eaka-verify.
- **No merge without the 4 checks green**, as under DEC-016 and DEC-018.
- **The PR says so:** a PR verified this way states "verified by CI (DEC-019), local eaka-verify not run" and gives the RAM readings that kept the gate closed.
- Local eaka-verify stays the default whenever the gate opens.

## DEC-020 — PROMPT 6 findings; what stays as it is until the owner decides

Recorded on 2026-11-12 from the ablation batches on GitHub Actions (`docs/design/pipeline-loss-fix-plan.md`). This entry fixes what the measurements settle; the owner's choices are in DEC-021.

- **F (`RAG_NUMBER_NORMALIZATION_ENABLED`) does not meet DEC-013:** 0 cases changed on all 5 dev sets. The flag stays off; its code is merged flag-off (DEC-021) so the completeness checks can reuse the number normalization.
- **No default changes from the ablations.** Removing the low-alignment document filter, widening `group_hits[:2]` to 5, or passing whole chunks instead of query-focused excerpts each regress UAT (−2, −6, −8) and help no set on balance. They are not to be shipped as fixes with `qwen2.5:3b`.
- **A real cross-encoder changes no answer** (bge-reranker-v2-m3 and mMiniLMv2-L12, `reranker_mode=cross_encoder` verified) because prompt ranking puts the lexical alignment order first. Earlier `lexical_fallback` measurements therefore stand. bge adds about 100 s per UAT question on a CPU runner.
- **Oracle context (gold chunks straight to the prompt) barely improves any dev set.** The loss is after the context: the 3B model, the validator, and the retry forced by the completeness checks. Retrieval and embeddings are not the bottleneck on dev, so the embedding fine-tune is not required before held-out v2.
- **Diagnostic tooling** (`scripts/diagnostics/ablation_patches.py`, `EVAL_ABLATION`) lives on branch `feat/prompt6-ablation`; it patches the eval API process only and is not part of `app/`.

## DEC-021 — Owner decisions after PROMPT 6

Set by the owner on 2026-11-12.

- **Two-part questions get a partial answer.** The validated parts are answered; each other part gets a fixed server-side sentence saying it **could not be verified** from the documents the user may access ("chưa xác minh được…"). The wording "the documents do not mention" is not used: on the diagnostic traces the documents did state those parts. Nothing is made up for a missing part. A dev set of half-answerable two-part questions (overlap check, fingerprints, frozen) comes before any code for this.
- **Order of work:** (i) the retry after the completeness checks, (ii) a responsiveness check calibrated on UAT, (iii) a fallback for query-focused excerpts, (iv) two-part questions. The low-alignment filter (A) and `group_hits[:2]` (B) are left as they are.
- **F is merged flag-off;** its number normalization is reused in the completeness checks.
- **No cross-encoder for now,** on Actions or in production. The docs say that prompt ranking puts the lexical alignment order before the cross-encoder score, so the reranker does not affect results today.
- **No embedding fine-tune before held-out v2.** PR #14 stays open.

## DEC-022 — Held-out v2 was run once by hand outside DEC-012

Recorded on 2026-11-12 at the owner's instruction.

- On 2026-11-11 the owner ran the 20 held-out v2 questions by hand on the system, outside the procedure of DEC-012.
- **The record of that run is not in the repository** and is not used to design any fix. The implementer (Claude Code) does not read it and does not ask for it.
- Only three general display defects were taken from that run, and nothing else: the fixed no-answer sentence is written without Vietnamese diacritics; answer templates print unaccented Vietnamese (units such as "trieu/thang"); an answer can repeat one sentence twice.
- **Any report of held-out v2 results must state this event.**

## DEC-023 — Wording-only fixes may ship with their flag on

Recorded on 2026-11-14 at the owner's instruction, after D2 (PR #23).

- **Exception to the change guard's "a new flag keeps the old behaviour by default":** a fix that changes only the wording of answers may be on by default when one batch on the 5 dev sets (UAT, RBAC, relevance, FR v1, FR v2; 2 runs, same job as the baseline) shows no change of status and no change of cited documents for any question.
- **The flag stays** so a later batch can run the old wording as its baseline.
- First use: `RAG_RESTORE_SOURCE_DIACRITICS_ENABLED` and `RAG_DEDUPE_CLAIM_ANSWERS_ENABLED`.
- Any change that can alter status, citations or which facts an answer states still follows the guard and DEC-013.
