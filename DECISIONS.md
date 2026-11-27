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

## DEC-024 — Phase 2 model: keep qwen2.5:3b

Recorded on 2026-11-14 at the owner's instruction. Full record: `adr/0003-phase-2-llm-model.md`.

- qwen2.5:7b was measured against 3B on 6 dev sets, with gold context and with real retrieval, on CPU. It removes some false answers (5 of 6 sets with real retrieval, one more on relevance) but adds almost no correct answers, at 1.9-2.8x the latency and 11-13 GB peak RAM on a 16 GB runner.
- **Keep qwen2.5:3b. Revisit when a GPU with at least 8 GB VRAM is available,** with the same 6 sets in one batch.
- Limit recorded: the responsiveness threshold t = 0.81 was calibrated on 18 LLM-route UAT answers with 3B; a model change needs a new calibration.

## DEC-025 — No cross-encoder in the pipeline (ADR 0004 option b)

Set by the owner on 2026-11-15.

- `RERANKER_PROVIDER` defaults to `heuristic`: candidates are ranked by lexical alignment, which is what every measurement used (`reranker_mode=lexical_fallback`). The lexical ranking itself is not changed.
- The `sentence_transformers` cross-encoder stays in the code behind `RERANKER_PROVIDER` for option (a) of ADR 0004, once a GPU is available. The eval workflow no longer downloads or mounts cross-encoder models.
- Accepted only if one batch on the 6 dev sets (same job, 2 runs) changes no answer; a stable change stops the merge.

## DEC-026 — New selection rule; UAT is monitored, not a gate

Set by the owner on 2026-11-15, before the simple answer mode is coded.

- **UAT Q001-Q100 is no longer a hard gate.** It overfits the deterministic route (75-76 of 100 answers are server-built, `docs/design/pipeline-loss-fix-plan.md` section 7). UAT is still run and reported for monitoring, split by route (`by_route`).
- **Since DEC-041 (2026-11-20), UAT is a regression suite only:** it is run to watch for changes, and is not a criterion for choosing a configuration, not even as a tie-break.
- **Selection rule for a configuration, in this order:**
  1. permission leaks = 0 on every set;
  2. the **total** of false answers (answered when it must refuse, plus a wrong value) summed over the dev sets does not increase;
  3. then prefer fewer false refusals on `natural_dev_v1` (once it exists), then on the other dev sets.
- Supersedes the per-set "not worse anywhere" comparison of DEC-013 for decisions from now on. Same-job baselines, 2 runs and rules written before measuring (DEC-011) still apply.
- **`natural_dev_v1` and held-out v3** are collected by the owner from the team. Intake follows the held-out v2 procedure (`docs/design/natural-dev-heldout-v3-intake.md`): freeze with a lock, fingerprints, overlap check, gold written from the PDFs only and approved by the owner. `natural_dev_v1` may be used for design; held-out v3 may not (as DEC-012).
- Recorded reason: on new questions the false-refusal rate is about 53%, caused by the stack of hand-written checks; only this overall conclusion is used, never held-out v1/v2 items, for design.

## DEC-027 — Variation between runners: decisions need two separate jobs

Set by the owner on 2026-11-16, before s4 and s5 are measured.

- Two runs inside one Actions job are identical (same runner, same Ollama), so they do not measure the variation between runners. On s1-s3 the same configuration differed on 10-14 UAT questions between two jobs, and legacy on 2 (`docs/design/simple-answer-mode.md`, "Results of s1-s3").
- **A default-flip decision rests on at least 2 separate jobs, each with its own `legacy`** (1 run per configuration per job is enough).
- **A difference smaller than the variation between the jobs counts as a tie.** Applied per count (false refusals, false answers + wrong, ...): the difference between two configurations is taken in each job; it counts only when it has the same sign in both jobs and its smaller size is larger than the largest change of either configuration between the two jobs on that count.
- DEC-011/016 (baseline in the same job) and DEC-026 (selection order) still apply inside each job.
- Recorded with it, at the owner's instruction: s5 uses a cross-encoder (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) as a per-claim relevance check behind its flag, for measurement. DEC-025 (no cross-encoder reranker) is unchanged; the eval workflow downloads that model only for a configuration that turns the check on.
- **Observed variation between jobs (recorded 2026-11-27, DEC-042):**
  - the same image and the `base` configuration gave 69, 71 and 68 right answers on UAT, in the PR #59 jobs and confirmation rounds 1 and 2;
  - the items whose category changed: Q028, Q029, Q033, Q036, Q046, Q048, Q063;
  - so a UAT difference of 2-3 items between configurations is within that variation.

## DEC-028 — Model comparison: candidates and rule, fixed before measuring

Set by the owner on 2026-11-17, after s3 did not win on `natural_dev_v1`. Hypothesis: the 3B model is the main bottleneck (with oracle context it is still wrong on about 44% of UAT; the wrong-subject answers of s3 on ND-002/003/011/014/019 are reading errors; some answers mix in another language).

**Eligibility** (all must hold): (1) in the Ollama library and runs on the pinned Ollama 0.40.15; (2) at most 8B parameters; (3) a licence that allows commercial use without a user-count threshold (Apache 2.0 or MIT); (4) the developer's model card names Vietnamese, or a language list known to include it; (5) the Q4 download is at most about 5.5 GB, so it fits next to the eval stack (6-7 GB peak) on the 15.7 GB runner; (6) a chat model that answers without a thinking block under the app's `reasoning_effort=none`. Ranking among the eligible: explicit Vietnamese training first, then the newest generation, then the smaller model (CPU latency).

**Models measured** (all Q4_K_M, used with `num_ctx` 8192 as before):

| Model | Why | Parameters | Download | Native context | Licence |
|---|---|---|---|---|---|
| `qwen2.5:3b` | baseline (ADR 0003) | 3.1B | 1.9 GB | 32K | **Qwen Research: non-commercial only**; commercial use needs a licence from Alibaba Cloud (LICENSE §2) |
| `qwen2.5:7b` | the owner's addition; same family, measured before in ADR 0003 | 7.6B | 4.7 GB | 32K | Apache 2.0 |
| `sailor2:8b` (= `8b-chat-q4_K_M`) | explicit Vietnamese: Qwen2.5-7B continued on 500B tokens of 15 South-East Asian languages, chat-tuned | 8B (9B on its card) | 5.2 GB | 32K | Apache 2.0 |
| `qwen3.5:4b` | newest generation (201 languages; Qwen3 lists Vietnamese among its 119), smallest candidate; vision encoder unused | 4.2B | 3.4 GB | 256K | Apache 2.0 |

Checked locally before measuring: with the app's payload `qwen3.5:4b` answers directly (no reasoning field).

**Not eligible:** `gemma4:e4b` (Apache 2.0, 140+ languages, but a 6.6-9.5 GB download with its audio and vision encoders: rule 5); `qwen3.5:9b`, `gemma4:12b` (rule 2); `granite4.x`, `ministral-3`, `phi4-mini` (their language lists have no Vietnamese: rule 4); `aya-expanse:8b` (CC-BY-NC: rule 3); `llama3.1:8b` (licence with a user threshold, and Vietnamese is not among its supported languages: rules 3, 4); `qwen3:8b` (same family as `qwen3.5`, older generation; ranking).

**Measurement:**

- Sets: `natural_dev_v1` and the 5 dev sets (RBAC, relevance, false refusal v1 and v2, compound). **UAT is not run.**
- Configurations: {`legacy`, `s3`} × {3B, 7B, `qwen3.5:4b`, `sailor2:8b`} (`EVAL_LLM_MODEL`). So that a job stays under the 340-minute limit and the runner disk, each set and round has two jobs, each with its own `legacy` + 3B and `s3` + 3B: job A adds 7B and `qwen3.5:4b`, job B adds `sailor2:8b`. Two rounds (a, b) on separate jobs, 1 run per configuration (DEC-027).
- Every configuration in these jobs runs with an LLM timeout of 600 s per call (`eval.yml` `llm_timeout`; the runners wait 4 × that), so that a slower model is judged on its answers, not cut off; latency is reported separately. Ollama keeps one model in memory (`OLLAMA_MAX_LOADED_MODELS=1`). Seed, temperature, prompts and every threshold stay as they are.
- Per set and configuration: correct – false refusal – false answer – wrong, leaks; `natural_dev_v1` also near UAT / rest; right number, wrong subject (a wrong answer whose numbers are all in its cited sources, as for s1-s5); answers in the wrong language (an answered case with a CJK character, or a sentence of at least 5 ASCII words with 2 English stopwords); latency median and p95 per question; runner peak memory while the configuration ran. s3 drafts are saved (`simple_trace`).
- For ND-002, 003, 011, 014 and 019: every model's answer, read against the gold.
- **Rule:** each combination against `legacy` + 3B of its own job, DEC-026 (leaks = 0; dev false answers + wrong, `natural_dev_v1` included, not above; then fewer false refusals on `natural_dev_v1`, then on the other dev sets) and DEC-027 across the two rounds. **The default is not changed in this step.**
- **Known limits:** the prompts and the thresholds (s3's e5 relevance check at 0.78, legacy's responsiveness check at 0.80) were calibrated with 3B and are not recalibrated per model; a model can lose answers to a threshold, not to its reading. Hardware figures are CPU-only (4 vCPU); VRAM needs are estimated from the model size, not measured.
- **Result (2026-11-17):**
  - Leaks 0 everywhere.
  - **Win against `legacy` + 3B under DEC-026/027:** `s3` + `qwen3.5:4b`, `s3` + 7B, and `legacy` + `qwen3.5:4b`.
    - Compared directly, `s3` + `qwen3.5:4b` and `s3` + 7B tie on every count.
  - **Do not win:** `legacy` + 7B and `legacy` + `sailor2:8b` (more false refusals), and `s3` + `sailor2:8b` (more natural false refusals).
  - Default unchanged.
  - Oracle (5 dev sets, 1 run): `s3` + `qwen3.5:4b` gets 104 of 117 correct with gold context, against 106 / 107 with real retrieval.
  - Details: `docs/design/model-comparison.md`; hardware per model: ADR 0003.

## DEC-029 — Candidate `s3` + `qwen3.5:4b`: conditions before the default changes

Set by the owner on 2026-11-17, after DEC-028.

**Candidate:** `s3` + `qwen3.5:4b`.

- It is lighter than 7B, can run on a 4 GB GPU, and is Apache 2.0.
- `qwen2.5:3b` does not allow commercial use.
- The default (`legacy` + `qwen2.5:3b`) stays until (a), (b) and (c) all hold.

**Conditions to change the default:**

- **(a) Variation.** Add a third job per set (round c) on `natural_dev_v1` and the 5 dev sets, each with its own `legacy` + 3B.
  - Over the three jobs (aA, bA, cA), `s3` + `qwen3.5:4b` must still win against `legacy` + 3B under DEC-026.
  - DEC-027 extended to three jobs: a difference counts only if it has the same sign in all three. The smallest of the three must also exceed the largest between-job change of either side. Otherwise it is a tie.
- **(b) UAT read by hand.** Run UAT Q001-Q100 in two rounds on separate jobs, each with `legacy` + 3B. UAT stays monitoring only (DEC-026).
  - List every item that `s3` + `qwen3.5:4b` answers wrongly (false answer or wrong value) in either round, with the question, answer, citations and reference answer.
  - The owner reads the list and accepts it.
- **(c) Target hardware:** a host with 16 GB RAM, either CPU-only (4 vCPU) or with an NVIDIA GPU of at least 4 GB VRAM.
  - CPU-only, measured on the Actions runner (4 vCPU, 15.6 GiB): no `INFRA_ERROR`, at least 1.5 GB RAM free at the stack's peak, and every answer within the deployment's LLM timeout.
  - GPU, measured on the owner's GTX 1650 (4 GB): the model fully on the GPU (`ollama ps` 100% GPU).
  - The owner names which of the two is the deployment target.

**When the default changes, the same change must update:**

- **Settings:** `RAG_ANSWER_MODE=simple` with s1-s3 on, and `LLM_OLLAMA_MODEL`.
- **Timeout:** `LLM_TIMEOUT_SECONDS`, set from the latency measured on the target. It is 30 s today in `compose.yaml` and `.env.example`.
- **Configuration files:** `compose.yaml`, `compose.prod.yaml`, `compose.uat-corpus-v2.yaml`, `.env.example`.
- **Documentation:** `ENVIRONMENT_VARIABLES.md`, `DEPLOYMENT.md`, `README.md`, `SETUP.md`.
- **Eval baselines:** `eval.yml`, `heldout-v2.yml`, `scripts/eval/compose.uat-eval.yaml`.
- **ADR:** a new ADR replaces ADR 0003.

**Measurement, fixed before running:**

- **Round c:** one job per set, configurations `legacy` + 3B, `s3` + `qwen3.5:4b` and `s3` + `qwen3.5-text:4b`. LLM timeout 600 s, 1 run.
- **`qwen3.5-text:4b`:**
  - The Ollama library has no text-only tag: every `qwen3.5:4b` tag lists text and image input.
  - The vision encoder is a separate projector layer. So `eval.yml` builds a text-only copy from the same model layer, template, renderer, parser and parameters, without the projector.
  - It is measured for memory. It is a deployment option for the same candidate only if its answers differ from `qwen3.5:4b`'s by no more than the between-job change.
- **UAT:** two rounds, each split into two jobs (Q001-Q050 and Q051-Q100) so no job reaches the 340-minute limit. Each job has its own `legacy` + 3B.
- **Local GPU** (the owner's GTX 1650 4 GB, 7.8 GiB RAM, Windows, Ollama 0.40.15):
  - Placement from `ollama ps` for both builds, once with Ollama's own placement and once with all layers forced to the GPU (`num_gpu` 99).
  - Latency: the s3 LLM calls of ND-001 to ND-010 (the first 10 `natural_dev_v1` items), replayed from the `simple_trace` of CI run 44018356568 (round a, job A). Same prompts, temperature 0, seed, `num_ctx` 8192. The figure is LLM time per question; retrieval and validation are not included.
  - No eval runs locally: the local Docker VM has 4 GB and runs the protected stacks.

**Results, 2026-11-17** (`docs/design/s3-q35-candidate.md`). **The default is not changed.**

- **(a) holds.** Over aA, bA and cA, with the three-job rule:
  - leaks 0;
  - false answers + wrong on the six sets: 15 / 10 / 12 against 28 / 27 / 28, real;
  - false refusals on `natural_dev_v1`: 4 / 9 / 5 against 7 / 7 / 7, a tie;
  - false refusals on the other five sets: 1 / 2 / 1 against 27 / 28 / 27, real.
- **`qwen3.5-text:4b` is a valid option.** In round c it gives the same answer and status as `qwen3.5:4b` on 137 of 137 items, with a runner peak 0.5-0.7 GB lower.
- **(b) waits for the owner.** The list of 19 items is in `docs/review/uat-s3-q35-2026-11-17.md`.
  - Proxy counts: round A / B, 67-23-1-9 / 69-22-1-8 against `legacy` 98-1-0-1 / 99-0-0-1.
  - Claude's first reading: 9 real errors in both rounds (1 false answer, 8 wrong or incomplete values; 6 of them a wrong table row or column), 1 right value with an unsupporting citation, and 7 right values from another document.
- **(c) CPU is not met with Ollama's defaults.**
  - Ollama 0.40's llama-server keeps a prompt cache of up to 8192 MiB in host RAM. With `qwen3.5:4b` it reached 6.6-8.0 GiB on each UAT half.
  - One UAT job lost its runner, and two halves had only 1240 and 1249 MB free.
  - With `LLAMA_ARG_CACHE_RAM=2048` on the Ollama server (new `eval.yml` input `ollama_cache_ram`), one half kept 6.8 GB free at the same speed. That cap was not in the plan above; relying on it needs a capped re-measurement.
  - The cache is not specific to the candidate: any model on a long-running Ollama 0.40 server can grow by up to 8 GiB.
- **(c) GPU (GTX 1650):** the model is fully on the GPU only when forced (`num_gpu` 99). Ollama's own placement keeps a reserve and puts 52% (`qwen3.5:4b`) or 36% (text copy) on the CPU.
- **Still open:** the owner's reading of the UAT list, and which hardware is the target.

**Owner decisions, 2026-11-18** (the default is still not changed):

- **(c) Target hardware: an NVIDIA GPU with at least 4 GB VRAM, model `qwen3.5-text:4b`** built from a Modelfile with `PARAMETER num_gpu 99`.
  - Built with `scripts/deploy/ollama_text_model.py`; setup in `DEPLOYMENT.md` 3.3.
  - Checked on the GTX 1650 on 2026-11-18: 100% GPU through the app's `/v1` endpoint with no options, 2971 MiB. The GPU part of (c) holds.
- **A CPU-only host with 16 GB is supported, but slow.**
- **The prompt cache is capped at 2048 MiB** in eval (`eval.yml` default, `heldout-v2.yml`) and in the deployment documentation, for the current configuration too (DEC-031).
- **Still open:** (b), the owner's reading of the UAT list.

## DEC-030 — Held-out v3: a team member's 20 questions with gold, frozen

Set by the owner on 2026-11-18.

**What it is.**

- 20 questions with expected answers and expected sources, written by a member of the project team (not the owner, not Claude).
- Source: workbook `Held-out_20_cau_Nova_Digital.xlsx`, sheet "Held-out". Its SHA256 is recorded in the YAML.

**How it is kept.**

- `scripts/eval/heldout_v3.py import` copied the six gold columns word for word into `docs/eval/heldout-v3.yaml`, as items HO3-01 to HO3-20. It reloads the YAML and refuses if any cell changed.
- Questions and gold are frozen together by `docs/eval/heldout-v3.lock` (SHA256 of the YAML). Any edit needs v3.1 with a new lock.
- The questions are in `scripts/eval/question_fingerprints.json` (source `heldout_v3`), so the leak check covers them.

**Rules, as DEC-012 for held-out v2:**

- Never used to design or tune a fix.
- Not run during development. Run only at the measurement milestone, with the owner's approval.
- The workbook and the YAML are not opened again until then.
- The import and check scripts print only ids, counts and flags. The details for the owner are in `docs/eval/heldout-v3-check.json`.

**Checks on 2026-11-18** (`heldout_v3.py check`): report only; the gold was not changed.

- **(1) Documents.** HO3-09, HO3-13 and HO3-20 cite ND-HR-007, which is not in corpus V2. The answer numbers of these three are also absent from the corpus.
- **(2) Accounts.**
  - "Bất kỳ" (17 items) maps to any seeded account.
  - "Tài khoản Phòng Nhân sự" (HO3-09, HO3-13) and "Tài khoản phòng Kỹ thuật (ngoài HR)" (HO3-20) have no seeded account: the seeded manager and staff are in "UAT Knowledge Operations", admin in none.
- **(3) Sources in the PDFs.**
  - The source column gives a document code and a section name or article, not a passage.
  - Not found as written: HO3-16, HO3-17, HO3-18. Found only as separate words: HO3-03, HO3-05, HO3-07, HO3-10.
  - Answer numbers missing from the cited documents: HO3-08 (2 of 4), HO3-11 (1 of 4).
- **(4) Overlap with the other sets.**
  - At the v1 review threshold (0.60 on character trigram or difflib): HO3-02, HO3-03 and HO3-19 against UAT Q001-Q100; HO3-06 against rbac.
  - Word 4-gram Jaccard is at most 0.273 (HO3-05 against held-out v1).
- **The owner decides** on these items before the milestone: for example, add ND-HR-007 and an HR and an engineering account to the eval corpus, or set the three items aside.

## DEC-031 — Table rows behind a flag, prompt cache capped: how they are measured

Set on 2026-11-18, from the owner's items C and D, before any run.

**Table rows (D).** Flag `DOCUMENT_TABLE_ROW_CHUNKING_ENABLED`, default off (`app/document_processing/extractors/table_rows.py`). At extraction, each data table of a native PDF page becomes one paragraph per row:

```
<table title> | <column>: <cell>; <column>: <cell>; ...
```

- **Data table:** PyMuPDF `find_tables()`, at least 2 columns and 3 rows. A page without one keeps its text byte for byte.
- **Column names:** the first row, when it has at least two distinct short labels (≤ 60 characters, no final full stop), every cell is bold, and the next row is not all bold. Otherwise every row is data, written `<first cell>: <other cells>`.
- **Title:** the nearest line above the table, outside every table region, within 60 points.
- **Merged cells:** a cell merged from above takes its text; one merged from the left is written once.
- **A table that ends low on its page** carries its title and columns to a first table on the next page that has no title, the same number of columns, and either no header or the same header.
- **The chunker is unchanged.** Rows are separate paragraphs, so a chunk boundary falls between rows.

**Offline, before any run** (corpus V2 with the app's extractor and chunker; the 5 dev sets' generated PDFs):

- The 18 dev-set documents are unchanged with the flag on, so the 5 dev sets are a no-change control.
- Corpus V2: 143 chunks without the flag, 167 with it. Every row line sits whole in one chunk.
- The organisation chart (ND-CORP-001 page 6) is still read as a table and stays garbled, as it is today (risk 1 of the design).

**Measurement (D):**

- **Two rounds**, dA and dB, each in its own jobs: `natural_dev_v1`, the 5 dev sets, and UAT in two halves (Q001-Q050, Q051-Q100).
- **Three configurations per job, in this order:**
  1. `legacy` + `qwen2.5:3b`;
  2. `s3` + `qwen3.5-text:4b` (the target model, DEC-029 B);
  3. the same with `EVAL_TABLE_ROWS=true`.
- **The third configuration** runs after `ci_batch.sh` has rebuilt the job's database and redis, started the worker with the flag, and loaded the corpus again (corpus V2, or the dev set's documents). One run per configuration.
- **Settings:** LLM timeout 600 s for `natural_dev_v1` and the dev sets, 180 s for UAT, as in DEC-028/029. Prompt cache capped at 2048 MiB (the new eval default).
- **Rule:**
  - DEC-026 with DEC-027 over the two jobs, comparing `s3` + text + rows against `s3` + text: leaks 0; false answers + wrong on the 6 sets not up; then false refusals on `natural_dev_v1`, then the other sets.
  - UAT is monitoring only, reported by route, with the 9 UAT errors of DEC-029 and ND-002/ND-003 reported item by item.
  - On the 5 dev sets any difference is job variation, since their chunks are unchanged.
- **The default stays off** whatever the result. Turning it on in a deployment needs the corpus processed again.

**Prompt cache (C).**

- `LLAMA_ARG_CACHE_RAM=2048` is the default of `eval.yml` and is set in `heldout-v2.yml`, matching the deployment documentation.
- **Measurement:** one more UAT job on Q051-Q100 with `s3` + `qwen3.5:4b` and the cap (uC2m, run 44144537645), the same configuration as uB2m.
- **Rule:** an item's change counts as an effect of the cap only if uB2m and uC2m agree on it and both differ from the two uncapped jobs (uA2, uB2), which agree. Anything else is job variation.

**Results (2026-11-18, graded value-aware, DEC-032).** Details per item: `docs/design/table-chunking.md` ("Measurement").

- **Runs:**
  - `natural_dev_v1`: 44148260972, 44148409028.
  - The 5 dev sets: 44148286143-44148384526 and 44148432685-44148534878.
  - UAT: 44148578890, 44148605005, 44148631493, 44148657545.
  - Every job reloaded its corpus with the flag (`batch.log`, `reingest.log`: 9 documents READY).
- **D, rows vs no rows** (both `s3` + `qwen3.5-text:4b`, two jobs):
  - Leaks 0.
  - False answers + wrong on the 6 sets are tied: 13/12 vs 12/13.
  - On `natural_dev_v1`, false refusals rise by 2 in both jobs (7 vs 5) and correct falls by 2 (9 vs 11).
  - By DEC-026 the flag is **not adopted**.
  - UAT (monitoring), with rows:
    - correct 53/55 vs 62/60, false refusals 35/33 vs 23/24;
    - false answers + wrong 12/12 vs 15/16. With the proxy grading this last count was 11/11 vs 8/9.
  - Mechanism, with the fix proposed but not coded:
    - Repeated titles and column names make table chunks crowd out the passage with the answer: 8 of the 11 correct answers that became refusals lost their evidence from the context.
    - The template UAT-LEAVE-AUTHORITY-001 gains slots.
  - ND-003 is fixed. ND-002 stays a false answer (a subject error, not the table text).
- **C, prompt cache cap** (`s3` + `qwen3.5:4b`, Q051-Q100):
  - Totals are 36-11-0-3 in all four jobs.
  - 4 items change in both capped jobs against both uncapped ones: Q063 and Q064 correct → refusal, Q076 and Q090 refusal → correct.
  - By the rule above that is an effect of the cache, with no net change. Every configuration in a job runs under the same cap, so comparisons within a job stay fair.
  - Comparisons across jobs with a different cap must not count those 4 items.

## DEC-032 — Value-aware grading for every set

Set on 2026-11-18 by the owner. The UAT proxy (status and cited document codes) does not read the values of an answer. It graded as correct answers with the wrong number:

| Item | Expected | Answered |
|---|---|---|
| Q048 | 02 days | 10 days |
| Q079 | 1,2 million | 12 million |
| Q077 | 150 million | 1,2 million |
| Q019 | 18:00 | 17:00 |
| Q054 | the 10th | no date |

**Rule.** An answered case counts as correct only when it states every value of its reference and gives no other value in the same unit. Otherwise it is wrong. Implementation: `scripts/eval/value_grading.py`.

- **Values:** numbers with their unit, money, clock times and dates, written one way.
  - Numbers go through `canonical_number_unit_pairs` of the claim validator (FIX 3c F): "02 ngày" = "2 ngày", "1.200.000 đ" = "1,2 triệu đồng".
  - Times: "9h30" = "09:30". A number word before a unit is a digit ("ba ngày" = "3 ngày").
- **Required:** every value of the reference, including one the question holds ("nghỉ 2 ngày báo trước mấy ngày" → 02 days).
- **Conflicting:** a value in a reference unit that is neither a reference value nor a question value. A threshold ("từ 05 ngày trở lên") is not a conflict.
- **Not values:** citation markers, codes (ND-HR-004, N3), article and section numbers, list numbering.

**Per set:**

- **UAT** (`grade_proxy.py`): `value_match` = `proxy_match` + both checks. The categories use `value_match` when a result has it.
- **The dev sets already checked values**, by their fact forms with no digit touching (`natural_dev_v1` also by its `wrong` forms). They keep that check and add the conflict check:
  - `run_answer_relevance_dev.py`: relevance, false refusal v1/v2, compound;
  - `run_natural_dev.py`;
  - `run_rbac_dev.py`. RBAC controls used a plain substring ("1 lần" matched "11 lần") and now use the digit boundary.
- **Old runs are regraded, not rerun:** `python scripts/eval/value_grading.py regrade <set> <results.json> <out.json>`. The old flag is kept as `<flag>_before_values`.

**Calibration.** On 1,200 UAT answers of `legacy` + 3B, `s3` + `qwen3.5:4b`, `s3` + `qwen3.5-text:4b` and the rows configuration:

- No `legacy` answer is flagged.
- `s3` + `qwen3.5-text:4b` and `s3` + `qwen3.5:4b`: exactly the 7 value errors of the 2026-11-17 reading (Q019, Q041, Q048, Q049, Q054, Q077, Q079).
- One false conflict, with rows: Q069 adds a separate 20 % rule to a right 30 %.

**Regrade of the existing runs** (D, the model comparison of DEC-028/029, the UAT runs of DEC-029, uB2m, uC2m):

- **Dev sets:** no case changes. Every conflict found was already in a failed case (ND-001 16 days, CP1-P02).
- **UAT**, correct - false refusal - false answer - wrong, proxy → value-aware:

  | Configuration | Round A | Round B |
  |---|---|---|
  | `legacy` + 3B | unchanged | unchanged |
  | `s3` + `qwen3.5-text:4b` | 69-23-1-7 → 62-23-1-14 | 67-24-1-8 → 60-24-1-15 |
  | `s3` + `qwen3.5:4b` (2026-11-17) | 67-23-1-9 → 60-23-1-16 | 69-22-1-8 → 63-22-1-14 |
  | rows | 54-35-1-10 → 53-35-1-11 | 56-33-1-10 → 55-33-1-11 |

- **DEC-026/027 conclusions:** unchanged. They rest on the dev sets, which do not move: `s3` + `qwen3.5(-text):4b` beats `legacy` + 3B, and rows are not adopted.
- **What changes is the UAT monitoring:**
  - `s3` + `qwen3.5-text:4b` gives 14-15 wrong answers per round instead of 7-8.
  - Rows show fewer false answers + wrong than no rows (12 vs 15/16), where the proxy showed more.
  - The UAT list for the owner is `docs/review/uat-s3-q35-text-2026-11-18.md`.

**From now on** every set is graded this way. Any figure taken from results graded before 2026-11-18 is regraded first.

## DEC-033 — Template and draft documents are excluded from answers; gold moved to the company document

Set on 2026-11-18 by the owner, from `docs/design/document-authority.md`. "A company document wins over a template."

- **Metadata:** a new lifecycle value `DRAFT` (not an issued document).
  - It is set by a person: the uploader or an admin, through the existing `lifecycle_status` field. It is never inferred from the text.
  - Corpus V2's manifest marks UAT-LEAVE-AUTHORITY-001 (`Tài liệu mẫu - chưa phải văn bản ban hành`) as DRAFT. `bootstrap_corpus_v2.py` uploads it with that value as the admin.
  - The V2 volume is not touched.
- **Flag `RAG_DRAFT_DOCUMENT_POLICY`:** `off` (default) or `exclude`.
  - `off`: a DRAFT document ranks and answers exactly like an ACTIVE one, as today.
  - `exclude`: no DRAFT chunk enters any answer path. That covers semantic and keyword retrieval, the explicit-document, topic and policy supplements, and the citation source lookup.
  - Document management, listing and permissions are unchanged. The filter is added to the permission filter, never in place of it.
  - `demote` from the design is not implemented: the owner chose `exclude`.
- **Gold, edited with the owner's approval of 2026-11-18** (the reason is written in each file; new locks):
  - UAT Q044 (`eval-data/uat/reference-grade.json`, `retrieval-gold.json`): the expected citation becomes ND-HR-004 page 6 ("Con đẻ hoặc con nuôi kết hôn 01 ngày") instead of the template's page 3. The answer is unchanged.
  - `natural_dev_v1` ND-001: the gold citation becomes ND-HR-004 page 5. "11 ngày" is the sum of its holiday table (01 + 05 + 01 + 01 + 02 + 01). The template is no longer acceptable.
  - `natural_dev_v1` ND-004, ND-012, ND-019: the template is removed from the acceptable citations and the excerpts.
  - Held-out v2 and v3 are not opened (DEC-012, DEC-030).

## DEC-034 — Table rows, version 2, and a retrieval gate before any LLM job

Set on 2026-11-18 by the owner: all four adjustments of `docs/design/table-chunking.md`. Measured as below, fixed before measuring.

**Version 2** replaces version 1 under the same flag `DOCUMENT_TABLE_ROW_CHUNKING_ENABLED` (default off). Version 1 was measured and not adopted (DEC-031).

1. **Both representations.**
   - The page text is extracted and chunked exactly as with the flag off.
   - Each row of a data table becomes one extra chunk of kind `TABLE_ROW`, holding `<title> | <column>: <cell>; …` (the text the prompt and the embedding see). It carries the page of its table.
2. **One slot per table.**
   - A row chunk has a parent: the page's text chunk that holds most of its table's cells.
   - Hybrid retrieval keeps one hit per group (a text chunk with its rows), the best-ranked.
   - The retrieval supplements read text chunks only.
3. **Labels indexed once.**
   - A row chunk's keyword text (`search_text`) is its cells only.
   - Keyword retrieval reads `coalesce(search_text, text)`. Text chunks keep their text, which already holds the title and header once.
4. **At least 3 columns** (and 3 rows). Two-column key-value tables stay as page text only.

**Retrieval gate (no LLM).**

- Ablation `retrieval_oracle`: in the simple answer mode, it records the 5 chunks selected for the prompt (at most 2 per document) and whether one is gold, then returns no answer without calling the LLM.
- **Gold:** the oracle map of `build_oracle.py`, with the gold of DEC-033:
  - UAT: the reviewed citation's document and page;
  - dev sets: the item's document and a form of its fact;
  - `natural_dev_v1`: the document and pages of its gold and acceptable citations.
- **Configurations:**
  - `s3` + `qwen3.5-text:4b` + `exclude`;
  - the same with rows, after re-ingestion.
- **Jobs:** one job per set (UAT, natural, the 5 dev sets). Retrieval has no sampling.
- **Pass:** on every set, the rows configuration has at least as many items with a gold chunk in the 5 as without rows. Items lost and gained are listed.
- If it fails on any set, the rows configuration is dropped from the LLM measurement.

**LLM measurement (two rounds, value-aware grading, DEC-032).**

- **Jobs:**
  - `natural_dev_v1` and the 5 dev sets: one job per round each.
  - UAT: 4 jobs per round, Q001-Q025, Q026-Q050, Q051-Q075 and Q076-Q100, so that every job stays under the 340-minute limit.
- **Configurations, in this order, each job:**
  1. `legacy` + 3B;
  2. `s3` + `qwen3.5-text:4b`;
  3. the same with `RAG_DRAFT_DOCUMENT_POLICY=exclude`;
  4. the same with rows version 2, only if the gate passed. It runs last, after the job reloads its corpus with the flag.
- Every configuration is graded on the DEC-033 gold. Prompt cache 2048 MiB, LLM timeout 600 s (180 s for UAT).
- **Rule (DEC-026, DEC-027 over the two jobs):**
  - 3 against 2, then 4 against 3: leaks 0; false answers + wrong on the 6 sets not up; then fewer false refusals on `natural_dev_v1`, then on the other sets.
  - The best configuration is the last one of this chain that the rule accepts.
  - UAT is monitored. Its list for the owner is written for the best configuration.
- **The defaults stay unchanged.**

## DEC-035 — Held-out v3: how it is run and what it decides (written before any run)

Set on 2026-11-18 by the owner, before held-out v3 is run or opened.

- **When:** after the DEC-034 round, once its best configuration is known. Not before, and not for design.
- **What:** held-out v3 (DEC-030, locked) is run for `legacy` + `qwen2.5:3b` and for the best candidate.
  - Both run in the same job, interleaved, over two rounds (two jobs, DEC-027).
  - Graded value-aware (DEC-032) against its locked gold.
- **Rule:**
  - Leaks must be 0, or the configuration is rejected.
  - The default becomes the configuration with the lower total of false answers + wrong (wrong values included), counted over both rounds and applying DEC-027 to the two jobs.
  - If equal, the one with fewer false refusals. If still equal, the current default stays.
- **Reporting:**
  - The report says plainly that held-out v3 was used both to choose between the two configurations and to measure them, so its figures are not an unbiased estimate of the chosen one.
  - The open findings of DEC-030 are decided by the owner before the run: references to ND-HR-007, test accounts without a seeded user, and references not found.
- **Who runs it:** the owner starts the run. Changing the default after it needs the owner's approval.

**Results of DEC-033 and DEC-034 (2026-11-18, value-aware grading on the DEC-033 gold):**

- **Retrieval gate** (no LLM; the simple mode's 5 chosen chunks), items whose gold chunk is among them:
  - The first run was void: the extraction router dropped the rows, so no row chunk was written. Fixed in b637d76.
  - Second run: UAT 76/98 (`s3t`), 78/98 (exclude), **77/98** (exclude + rows). natural 18/20 in all three; the 5 dev sets reach every item in all three.
  - **Rows fail the gate** (77 < 78). They lose Q027 and Q063 and gain Q017; none of the three involves a row chunk in the 5. Row chunks fill 4 of 500 slots.
  - Between the two gate jobs, Q096 flips with nothing changed (ties are ordered by document id, drawn anew at every load), so a one-item difference is within one job's variation.
  - **Every table of ND-HR-004 has 2 columns**, so under the 3-column rule none of them gets rows. That includes the tables behind Q041, ND-001, Q048 and Q049.
  - The rows configuration was dropped from the LLM measurement, as the rule says.
- **LLM measurement:**
  - Jobs:
    - `natural_dev_v1`: 44254283048 (fA), 44254365338 (gA);
    - the 5 dev sets: 44254296297-44254352830 (fA), 44254379416-44254431753 (gA);
    - UAT in quarters: 44254446663-44254485549 (A), 44254500045-44254541309 (B).
  - Leaks 0 everywhere.

  | Comparison (DEC-026/027, jobs f/g) | false answers + wrong, 6 sets | natural false refusals | natural correct |
  |---|---|---|---|
  | `s3t` vs `legacy` + 3B | 12/13 vs 28/29 (real) | 5/5 vs 7/7 (real) | 10/10 vs 2/2 |
  | exclude vs `s3t` | 13/13 vs 12/13 (tie) | **7/7 vs 5/5 (+2, real)** | 7/8 vs 10/10 |

  - **Exclude is not adopted.** Its false answers + wrong tie, and its natural false refusals rise by 2 in both jobs.
    - ND-018 and ND-015 become refusals and ND-012 wrong. In all three the evidence is in the context with and without the flag (gate: natural 18/20 both).
    - Without the template chunks the sources are renumbered and partly replaced. The model words its answer differently and the validator rejects it, or it drops "phải được công ty chấp thuận".
  - **UAT** (monitoring), correct - false refusal - false answer - wrong:

    | Configuration | Round A | Round B |
    |---|---|---|
    | `legacy` | 99-0-0-1 | 98-1-0-1 |
    | `s3t` | 61-21-1-17 | 59-24-1-16 |
    | exclude | 69-20-1-10 | 65-23-1-11 |

    - With exclude, 7 items improve in both rounds (Q040, Q043, Q044, Q052, Q055 correct; Q039, Q042 wrong → refusal) and 1 gets worse (Q066).
    - `legacy`'s one wrong answer is Q044: it still cites the template, which the new gold no longer accepts.
- **Best configuration of this round:** `s3` + `qwen3.5-text:4b`, without exclude and without rows. Its UAT list is `docs/review/uat-s3-q35-text-2026-11-18.md`.
- **No default changed.**
- **Owner's decisions:**
  - whether UAT's gain justifies exclude despite natural's +2 refusals;
  - whether to gate rows over two jobs, or with a load-independent tie-break;
  - whether the 3-column rule should admit the 2-column tables behind Q041, Q048 and Q049.

## DEC-036 — Documents that are not issued do not answer: `exclude` is the data policy

Set on 2026-11-18 by the owner. This is a decision about the data, not a measured choice.

- **Rule:** a document that has not been issued (a template or a draft, `lifecycle_status=DRAFT`) is never used to answer.
  - `RAG_DRAFT_DOCUMENT_POLICY` defaults to `exclude` for every configuration, legacy and simple, in the app, `.env.example` and the eval stack.
  - `off` stays as the rollback.
- **It overrides DEC-026 for this one question.** By DEC-026, DEC-034 found exclude not adopted: false answers + wrong tied, and natural false refusals were +2 in both jobs. The owner takes that cost knowingly.
- **Measured cost and gain** (DEC-034 round, value-aware, DEC-033 gold, `s3` + `qwen3.5-text:4b`):
  - **`natural_dev_v1`: +2 false refusals in both jobs**, correct 7/8 vs 10/10.
    - ND-018 and ND-015 become refusals and ND-012 wrong. Their evidence stays in the context.
    - Without the template chunks the sources are renumbered and partly replaced. The model words its answer differently and the validator rejects it, or it drops a required part.
  - **UAT: +8 / +6 correct** (69/65 vs 61/59), false answers + wrong 11/12 vs 18/17.
    - 7 items get better in both rounds (Q040, Q043, Q044, Q052, Q055 correct; Q039, Q042 wrong → refusal), 1 gets worse (Q066).
  - **The 5 dev sets:** unchanged. They contain no DRAFT document.
- **Scope:**
  - The policy acts only on documents marked DRAFT. Documents uploaded before DEC-033 stay ACTIVE until an admin marks them.
  - The protected V2 stack is not changed. The eval stacks mark UAT-LEAVE-AUTHORITY-001 at upload (corpus V2 manifest).
- **DEC-035 is updated accordingly** (below): held-out v3 compares the two configurations with exclude.

**DEC-035, update of 2026-11-18 (owner):**

- **Configurations:** `legacy` + `qwen2.5:3b` + exclude against `s3` + `qwen3.5-text:4b` + exclude. Exclude is now the default of both.
- **Runs:**
  - One gated job (`.github/workflows/heldout-v3.yml`) with two interleaved runs (legacy, s3, legacy, s3), as for held-out v2.
  - DEC-027's rule is applied to the two runs: a difference counts only with the same sign in both and larger than the spread between the runs.
  - The two runs share one runner, so runner variation is not separated. The owner may dispatch the workflow a second time for that.
- **Items:**
  - An item whose test account maps to no seeded user is not asked, and is listed. The same holds for any item set aside by the owner's decisions on the DEC-030 findings.
  - An item expects a refusal when its expected sources name no document code; otherwise it expects an answer that cites one of those documents and states the expected answer's values (DEC-032).
- **Rule:** unchanged. Leaks must be 0; the lower false answers + wrong wins; on a tie, fewer false refusals; still tied, the current default stays.

## DEC-037 — The owner's grading policy

Set on 2026-11-18 by the owner, after reading the UAT list of 2026-11-17 (`docs/review/uat-s3-q35-2026-11-17.md`, the owner's notes committed as written).

**Registered before held-out v3.1 is dispatched.** It applies to every automatic grade from now on, and to the owner's own grading of held-out v3.1 (grading.csv).

1. **Same value, either source.** When ND-HR-002 and ND-HR-003 state the same value, a citation of either passes.
2. **On a conflict, ND-HR-003 wins.**
3. **A template or draft is never a valid source.** A citation of a document with `lifecycle_status=DRAFT` fails the item.
4. **A question about a rule passes when the rule is stated correctly.** A worked example is not required. Owner grading only; the automatic grader still asks for every value of the reference.
5. **A computed calendar date** (for example "ngày 10 tháng 12" for "this month") is a feature request, not a grading criterion.

**How it is applied:**

- **UAT gold** (`eval-data/uat/reference-grade.json`, `retrieval-gold.json`, re-locked in `gold.lock`; each change carries "owner review 2026-11-18"):
  - Q018: NO_ANSWER → ANSWERED from ND-HR-003 p4 (start 08:00-09:00, end 17:00-18:00), accepted source ND-HR-003 only (policy 2). `uat/corpus-v2/manifest.json` records how the Q018 conflict was resolved.
  - Q016, Q017, Q034: `accepted_sources` ND-HR-002 and ND-HR-003 (policy 1). A script checked that their values are in both documents. Q023, Q024, Q027 and Q031 matched by number only, outside working hours, and are not changed.
  - Q002: ND-CORP-001 added to the accepted sources.
  - Q054: the expected answer is "Ngày 10 tháng kế tiếp" (policy 5).
- **Grader** (`scripts/eval/grade_proxy.py`):
  - With `accepted_sources`, any non-empty set of cited codes inside the list matches.
  - A cited DRAFT code, read from the corpus manifest metadata and never named per question, fails the item.
  - Unit tests: `tests/unit/test_grade_proxy_owner_policy.py`.
- **Check on the existing 18/11 UAT artifacts** (no new run): the regraded `s3` + `qwen3.5-text:4b` matches the owner on every decided item.
  - The grader gives 64-21-0-15 (A) and 62-24-0-14 (B).
  - Owner pass rate: 126/200, with 5 item-rounds undecided (Q041 A/B, Q044 A/B, Q053 A), so 63.0-65.5 %.

## DEC-038 — Held-out v3 → v3.1

Set on 2026-11-19 from the owner's decisions on the DEC-030 findings. The gold is not edited; v3 and its lock stay for reference.

- **Removed (3):** HO3-09, HO3-13, HO3-20. Their source document is not in corpus V2, and no corpus is added.
  - This also removes the only items whose test account had no seeded user.
- **Value check** (`heldout_v3.py derive-v3.1`; ids and counts only): do the gold's values (numbers, times, dates, %) occur in the cited documents?
  - Kept: HO3-03 1/1, HO3-05 2/2, HO3-07 2/2, HO3-10 1/1, HO3-16 4/4, HO3-17 5/5, HO3-18 1/1.
  - **PENDING_AUTHOR_REVIEW:** HO3-08 2/4, HO3-11 3/4. Both were pending by default, and the script did not find all their values.
  - All the cited documents are in the corpus.
- **near_duplicate:** HO3-02, HO3-03, HO3-19 (near UAT) and HO3-06 (near RBAC dev). Reported as a separate group, as for held-out v2.
- **Result:** 17 items. **15 will be asked**; 2 are pending. All 15 use a seeded account.
- **PENDING items:**
  - The workflow does not ask them and lists them as `excluded_pending`.
  - The owner clears one in a commit of its own that changes its `status` and rewrites `heldout-v3.1.lock`. That commit lands before the dispatch.
- **Deadline (owner, 2026-11-19):** the author confirms HO3-08 and HO3-11 by the end of **2026-11-21**.
  - Confirmed: a commit of its own sets the item ACTIVE (`python scripts/eval/heldout_v3.py set-status ACTIVE <id>`, which rewrites the lock and the fingerprints).
  - Not confirmed by then: a commit of its own sets it **EXCLUDED** (`set-status EXCLUDED <id>`), and held-out v3.1 runs with the 15 items left. An EXCLUDED item is never asked and is listed under `not_run`.
  - There is no "run first, complete later": a real run (`gate --no-pending`, and `run`) refuses while any item is still PENDING_AUTHOR_REVIEW. Only `preflight_only` may run before.
- **Resolved (owner, 2026-11-19), before the deadline:**
  - **HO3-08: ACTIVE.** The owner confirmed it.
  - **HO3-11: EXCLUDED.** Its gold holds a value that is not in its source document.
  - Applied with `heldout_v3.py set-status` (both changes are recorded in the lock's `status_changes`). Lock sha256 d4481d56…; fingerprints rebuilt.
  - **Held-out v3.1 asks 16 items** (17 minus HO3-11); `gate --no-pending` passes.
- **Files:**
  - `docs/eval/heldout-v3.1.yaml` and `heldout-v3.1.lock`, sha256 047d0859….
  - `scripts/eval/question_fingerprints.json` rebuilt, with a `heldout_v3_1` source.
  - The gate and the run of `heldout_v3_release.py` read v3.1.
- **Owner's grading table:** each answer is flagged when it cites another document than the gold one with the gold's values, so the owner can apply DEC-037 policy 1. The automatic grade does not apply it.
- **Run 44559765410 (2026-11-19): infrastructure failure, not counted.**
  - In the step "Run held-out v3", `ci_batch.sh` printed `unknown set heldout_v3` and exited 2 at 16:02:28, before its first request. Its set whitelist lacked `heldout_v3`.
  - Evidence: the public log shows that line before any request. The batch had not started yet, so no held-out question was asked: 0 asked.
  - The run is not counted, and the owner may dispatch held-out v3.1 again.
  - The owner does not decrypt this run's artifact.
  - Preflight 44555016057 was green because it stops before `ci_batch.sh`. Since 2026-11-19, preflight and run both call `ci_batch.sh --validate-only` with the run's own arguments first.

## DEC-039 — Held-out results never public in plaintext; known exposure of the held-out sets

Set on 2026-11-19 by the owner, before the held-out v3.1 dispatch.

**What a held-out workflow may publish** (`heldout-v2.yml`, `heldout-v3.yml`):

- **The artifact** (`heldout-v*-public/`) holds only:
  - the lock;
  - the text-free `summary.md` and `verdict.json` (ids, counts, the DEC-035 verdict);
  - on a GitHub-hosted runner, the age ciphertext of everything else.
- **Everything else is private:** run results, the owner's `grading.md` / `grading.csv`, stack logs and Ollama logs. `scripts/eval/heldout_publish.sh` handles them according to the runner type:
  - **GitHub-hosted** (both workflows today, `ubuntu-latest`): `tar | age -r "$HELDOUT_AGE_RECIPIENT"`, and only the ciphertext is uploaded. Without a valid recipient in the repository variable, the job fails at its start and again at the split. There is no plaintext fallback.
  - **Self-hosted:** the results are copied to `HELDOUT_PRIVATE_DIR/<run id>` and not uploaded. The default is `C:/dev/eaka-private/<name>/<run id>`.
- **Scan before the upload:** `question_leak.py scan` checks every file of the public folder against all the question fingerprints. Any match fails the job. The upload runs only when the scan succeeded.
  - Until 2026-11-19 the upload also needed the split to succeed.
  - Now a failed split still uploads the public folder: it is filled before the private part, so it then holds the text-free files only. Nothing private is uploaded in plaintext, and the job still fails.
- **Run status (2026-11-19):** `summary.md` opens with the status block of `scripts/eval/heldout_status.py`, whether the job passed or failed. It gives:
  - the status and whether the run was a preflight;
  - the failing step and its exit code, recorded by an exit trap that every bash step sources through `BASH_ENV`;
  - the questions sent to the API and the other API requests, counted from the uvicorn access log in the stack log. When the log holds no access line, it says "unknown", never 0.
- **Job summary:** it gets `summary.md` only after the scan. The held-out v2 step that copied the first 40 lines of `grading.md` into it is removed.
- **Step logs:** they print ids and counts only. I checked this in the code of the gate, the runners, `ci_batch.sh` (its compare output is ids and counts) and the grading step.
- **Dry run** (2026-11-19, fake data, Linux container with age):
  - A missing or bad key fails.
  - An unknown runner and a bad public folder are refused.
  - The self-hosted copy works.
  - The ciphertext decrypts back to the private folder.
  - The scan passes the public folder. It fails once a sheet holding a dev question is planted there, and it names only the question id.
- **Environments:** `heldout-v2-release` and `heldout-v3-release` both need the owner's review and deploy from `main` only.

**Known exposure, accepted:**

- **Held-out text in the public repository.** The questions and gold of held-out v2, v3 and v3.1 are in plaintext in `docs/eval/` and in the git history. The fingerprint salt is also public (`question_leak.py`), so the hashes let anyone confirm a question they guessed.
  - Why it is accepted: the held-out sets guard against overfitting during development, and the development side keeps the no-read rule (DEC-012, DEC-030). The local models do not learn from GitHub.
  - No file is deleted, the history is not rewritten, and the repository visibility is not changed.
- **ND-001 and HO2-017:** the `gold_answer` of natural_dev_v1 ND-001 shares 75 % of the 4-grams of the HO2-017 question. This is not verified; it is probably wording shared with the source document. It is a known limit of held-out v2.
- **Past exposure:**
  - Three held-out v2 artifacts held the full results (runs 43697066034, 43701098015, 43701804785). They were deleted on 2026-11-19.
  - The public job summary of run 43701804785 still shows the first 40 lines of the v2 grading sheet. This is inferred from the code; the summary was not opened. Removing it means deleting that run, which is the owner's call.
- **Not scanned:**
  - the contents of `docs/eval/heldout-v2-check.json`, `docs/eval/heldout-v2-e5.json` and `docs/eval/runs/`;
  - gold text outside `docs/eval/`, because only the questions have fingerprints.

## DEC-040 — The default after held-out v3.1

Set on 2026-11-20 by the owner, after reading `grading.md` of held-out v3.1 run 44575927833.

**New default:** `s3t` = simple answer mode with s1-s3 (`EVAL_SIMPLE_LEVEL=3`) + `qwen3.5-text:4b` +
`RAG_DRAFT_DOCUMENT_POLICY=exclude`. **Rollback:** `legacy` + `qwen2.5:3b`
(`RAG_ANSWER_MODE=legacy`, `LLM_OLLAMA_MODEL=qwen2.5:3b`; `DEPLOYMENT.md` 3.3). ADR 0005 replaces
ADR 0003.

**Basis:**

- The DEC-035 rule, registered before the run. The automatic verdict is `s3t`: false answers +
  wrong are lower in every run.
  - Per run (correct / false refusal / false answer / wrong): `legacy` 0 / 8 / 0 / 8, `s3t`
    3 / 7 / 0 / 6.
- The owner's labels lean the same way (`s3t` / `legacy`): PASS 1 / 1, PARTIAL 4 / 1, refusals 6 / 7,
  wrong 5 / 7. Labels per item, ids and reason codes only:
  `docs/eval/heldout-v3.1-owner-grading.md`.
- The owner differs from the automatic grader on two items:
  - HO3-02 `legacy`: the grader asks for a derived value that the document does not state;
  - HO3-03 `s3t`: the value matches by chance and the citation does not support it.
- DEC-029: conditions (a) and (c) held; (b), the owner's reading of the UAT list, was still open
  when the owner decided.

**Limits, stated with the decision:**

- run1 = run2 for every item (deterministic), so there is one observation, not two.
- Both configurations gave the same answer on 5 items, so only 11 items tell them apart.
- Held-out v3.1 both chose the configuration and measured it: its figures are not an unbiased
  estimate.
- `s3t` is about 2.5 times slower on CPU (1994 s against 796 s for the 16 items of one run).
- The held-out questions and gold are in the public repository (DEC-039).
- **Held-out v3.1 is spent.** It is not used again to measure or to design a fix, and
  `heldout-v3.yml` refuses every dispatch. The next independent measurement needs held-out v4.

**Held-out v3.1 items not asked:** HO3-09, HO3-13 and HO3-20 were removed from v3 because their
source documents are not in corpus V2 (DEC-038); HO3-11 was excluded because its gold is wrong.

**What the change touches** (the DEC-029 list):

- Settings: `RAG_ANSWER_MODE=simple` and the five s1-s3 flags on in `app/core/config.py`;
  `.env.example` (also `LLM_OLLAMA_MODEL=qwen3.5-text:4b`, `LLM_TIMEOUT_SECONDS=90`).
- `compose.uat-corpus-v2.yaml` (model only). `compose.yaml` and `compose.prod.yaml` set neither
  the answer mode nor the Ollama model, so the application defaults apply there.
- Eval: `scripts/eval/compose.uat-eval.yaml` defaults, `eval.yml` (default model, LLM timeout
  600 s), `heldout-v2.yml` (measures the new default), `ci_batch.sh` (`EVAL_SIMPLE_LEVEL=n` now also
  turns the flags after n off).
- Documentation: `DEPLOYMENT.md` 3.3 (GPU, building `qwen3.5-text:4b`, rollback),
  `ENVIRONMENT_VARIABLES.md`, `README.md`, `SETUP.md`, ADR 0005.
- The unit tests of the legacy pipeline pin `rag_answer_mode="legacy"` in their settings helper.

**Diagnosis of run 44575927833 (2026-11-20):**

- `api_requests=35` counted only the last API container. `ci_batch.sh` recreates the API for every
  configuration and run, which drops the container's log. It now saves each container's log before
  the recreate, and the status step counts them all.
- The held-out summary now also lists the items removed before v3.1, with the reason.
- `scripts/eval/heldout_v3_diag.py` prints, for the owner, one text-free row per configuration, run
  and item.

**Baseline on the dev sets after the switch (2026-11-20):** `eval.yml` from the PR branch, CPU
runner, one job per set, `legacy` (the rollback,
`legacy:EVAL_ANSWER_MODE=legacy,EVAL_LLM_MODEL=qwen2.5:3b`) then `default` (DEC-040) on the same
image and Ollama, 1 run, LLM timeout 600 s. It is the reference for later dev work, not an input to
this decision.

- UAT Q001-Q100 (run 44669869629; monitoring only, DEC-026), `legacy` / `default`:
  - `value_match` 96 / 71 (`proxy_match` 96 / 77); false refusals 3 / 21; wrong 1 / 8; false
    answers 0 / 0; infra errors 0 / 0; time 1429 s / 5071 s.
  - By route: `legacy` answers 74 items on the deterministic route (73 match) and 26 on the LLM
    route (23); `default` answers all 100 on the LLM route (71). Simple mode has no deterministic
    route.
  - `default` gains no item and loses 25 (22 that `legacy` answered on the deterministic route,
    3 on the LLM route): 19 become refusals, 6 wrong.
  - `default` false refusals: Q001, Q003, Q006, Q007, Q026, Q030, Q031, Q036, Q037, Q039, Q041,
    Q042, Q046, Q048, Q071, Q075, Q080, Q086, Q093, Q096, Q097. Wrong: Q018, Q019, Q020, Q049,
    Q054, Q066, Q077, Q079.
  - The saved logs count 100 + 100 chat requests.

- `natural_dev_v1` (run 44669873227, 20 items), `legacy` / `default`:
  - correct 3 / 7; false answers 1 / 1 (ND-002 in both); refused (`NO_ANSWER`) 8 / 8; leaks 0 / 0;
    infra errors 0 / 0; time 1020 s / 2688 s.
  - `default` gains ND-010, ND-011, ND-013, ND-018, ND-020 and loses ND-017.
  - The saved logs count 20 + 20 chat requests, one per item and configuration.

## DEC-041 — Keep s3t; hybrid stays behind a flag, not recommended

**Owner decision, 2026-11-20: option 1.** The default stays s3t = simple with s1-s3 +
`qwen3.5-text:4b` + `RAG_DRAFT_DOCUMENT_POLICY=exclude` (DEC-040). `RAG_ANSWER_MODE=hybrid` stays
in the code behind its flag, off by default, and is **not recommended**.

**Basis:**

- (a) On the 6 dev sets, s3t and hybrid are tied within the noise (correct 114 / 112, false
  answers + wrong values 16 / 19), so the choice of the DEC-026 rule stands.
- (b) The route's false matches are systematic: outside UAT it answered 14 items and got 4 wrong,
  each a wrong value with a citation (ND-006, ND-019, ND-020, REL-103).
- (c) The owner puts accuracy before speed.
- No default changes, so the two-job rule of DEC-027 for a flip does not apply.

**Known limit:** UAT is 68 with s3t, against 92 with hybrid and 97 with legacy, mostly from false
refusals (22 with s3t). From now on **UAT is a regression suite to watch, not a criterion for
choosing a configuration** (DEC-026 updated). The 22 s3t false refusals on UAT and the 6 on
`natural_dev_v1` are the case set for diagnosing refusals in the shared layer (`TASKS.md`).

### GPU latency on the owner's machine (2026-11-22)

- **Conditions:**
  - GTX 1650 4 GB, 8 GB RAM (7.8 GiB visible), Windows, Ollama 0.40.15 with the CUDA backend,
    `qwen3.5-text:4b` with `PARAMETER num_gpu 99`, `num_ctx` 8192.
  - Only the `eaka-smoke` stack (main at 51c1767, the default configuration) and Ollama were
    running: the V2 and main stacks were stopped, Edge and the UI session closed. Still open:
    Docker Desktop, Defender and this Claude Code session.
  - VRAM free before: 3935 MiB.
- **End to end: not measured.** RAM available stayed at 425-500 MB, below the 2 GB the owner set
  for this run.
- **LLM time per question,** from `scripts/eval/gpu_latency_replay.py`:
  - Input: the s3t prompts of ND-001 to ND-010 from CI run 44694912116, sent through the app's
    own provider with the eval settings.
  - Result: p50 18.4 s, p95 25.5 s (the 10th value), mean 20.1 s, range 17.1-25.5 s, 13 calls.
    ND-003, ND-005 and ND-006 have a retry.
  - The first call, which loads the model, took 23.8 s.
  - These figures match the 18.7-28.6 s measured on 2026-11-18 (`DEPLOYMENT.md` 3.3).
- **No layer on the CPU:**
  - The Ollama log shows `offloaded 33/33 layers to GPU`, and `ollama ps` reads `100% GPU`,
    context 8192.
  - The host holds 525 MiB of the model (497 MiB weights, 28 MiB compute).
  - Ollama's fit step reported it could not keep its usual 1 GiB VRAM reserve. Because
    `num_gpu 99` is set, it loaded every layer on the GPU anyway, using 2903 MiB.
  - Under the memory pressure the log also shows a GPU-discovery watchdog warning; free memory
    was read from earlier values.
- **RAM available during the replay** (one sample every 5 s, 41 samples): lowest 99 MB, highest
  1017 MB.
- **Hardware recommendation (owner):**
  - an NVIDIA GPU with at least 4 GB VRAM;
  - at least 8 GB RAM with the system running alone, 16 GB recommended.
  - On 8 GB the system runs, but with almost no free memory: here as little as 99 MB during
    the LLM calls.

### The proposal and the measurement it rests on (2026-11-20)

The owner keeps DEC-040 and asked for a hybrid configuration measured on the dev sets only.
`RAG_ANSWER_MODE=hybrid` exists, off by default: the legacy pipeline up to its deterministic
route, under the existing conditions (no new route, no wider match); a question the route does
not answer (no source, missing reason evidence, no route, or a route draft that is not ANSWERED)
goes to the s3t path. Permission filtering and the DRAFT exclusion are in retrieval, the same
for both branches. The default stays s3t until the owner chooses.

**Measurement** (`docs/eval/runs/dec041-hybrid-dev.md`): the 7 dev sets, one job per set with
`legacy`, `s3t`, `hybrid` in the same job, same image and Ollama, 1 run on CPU. One run because a
run repeats itself within a job (DEC-040: run1 = run2 for every held-out item); the 7 sets do not
fit one job (UAT alone takes about 2.6 hours with three configurations, the job limit is
340 minutes).

| | legacy | s3t | hybrid |
|---|---:|---:|---:|
| 6 dev sets, 137 items: correct | 75 | 114 | 112 |
| false refusals | 36 | 7 | 6 |
| wrong values | 9 | 6 | 8 |
| false answers | 17 | 10 | 11 |
| false answers + wrong values | 26 | 16 | 19 |
| leaks | 0 | 0 | 0 |
| time, s | 5008 | 5142 | 4665 |
| UAT, 100 items (monitoring only, DEC-026): correct | 97 | 68 | 92 |
| UAT false refusals / wrong values | 2 / 1 | 22 / 10 | 6 / 2 |
| UAT time, s | 1575 | 5563 | 2198 |

The 6 dev sets: `natural_dev_v1` (20), rbac (36), relevance (25), false_refusal (20),
false_refusal_v2 (24), compound (12). On `natural_dev_v1`: correct 3 / 8 / 6, false refusals
8 / 6 / 5.

**Route matrix (the false-match measurement):**

- UAT: the route answers 74 of 100 items, 73 right.
- The 6 other sets: the route answers 14 of 137 items, 10 right. `natural_dev_v1` 4 (1 right),
  rbac 3 (3), relevance 2 (1), false_refusal 4 (4), false_refusal_v2 1 (1), compound 0.
- The 4 misfires: ND-006, ND-019 and ND-020 give a wrong value (s3t refused ND-006 and answered
  ND-019 and ND-020 right); REL-103 is a false answer in every configuration.
- legacy and hybrid take the same route decision on every item; no legacy answer came from a
  repair after the LLM.

**Where hybrid loses:**

- To s3t: ND-019, ND-020 (route misfires) and FR2-L06 (simple path, noise: FR2-L01 went the
  other way).
- To legacy: Q007, Q033, Q071, Q096, Q097 (UAT items no route answers, refused by the simple path
  and answered by legacy's LLM path), ND-017, REL-203, FR2-L05, CP1-R03.

**The three options:**

1. **Keep s3t (DEC-040).** It is what the DEC-026 rule picks: leaks 0 everywhere, and the fewest
   false answers + wrong values on the dev sets (16 against hybrid's 19). UAT stays at 68.
2. **Switch to hybrid.** UAT 92 instead of 68 and 2.5 times faster on UAT (the route skips the
   LLM). On the other dev sets it gives 2 fewer right answers and 3 more false answers + wrong
   values than s3t; 3 of those are route misfires on `natural_dev_v1`. Under DEC-026 it does
   not pass against s3t.
3. **Return to legacy.** UAT 97, but 39 fewer right answers than s3t on the other dev sets,
   36 false refusals and 26 false answers + wrong values.

**Limits:**

- Dev evidence only. The deterministic routes were written against UAT: they answer 74 % of
  UAT and 10 % of the other sets, and are right on 99 % of their UAT answers against 71 %
  elsewhere. Hybrid's UAT figure is therefore no estimate for questions the routes were not
  written for.
- An independent measurement needs held-out v4 (v3.1 is spent, DEC-040).
- One run on CPU runners. Within a job, the s3t path differs on 2 items between s3t and hybrid
  only because the request order differs; across jobs a configuration moves by a few items
  (s3t `natural_dev_v1` 7 → 8, UAT 71 → 68). Differences of 1-2 items are noise.
- The sets are small (`natural_dev_v1` has 20 items).
- **GPU latency not measured on 2026-11-20** (measured on 2026-11-22, LLM time only, see above).
  The owner's machine had about 640 MB of RAM available; the
  owner's rule is to stop and not close applications. Ready to run (`docs/eval/runs/dec041-hybrid-dev.md`):
  on ND-001 to ND-010, s3t makes 13 LLM calls and hybrid 10.

**What changed (no default changed):** `RAG_ANSWER_MODE=hybrid`; each answer counts
`answer_route_<route>` and each no-answer diagnostic `no_answer_<reason>`; every dev runner
records `answer_route`, `no_answer_reasons`, `retrieved`; `scripts/eval/route_matrix.py`,
`scripts/eval/gpu_latency_replay.py`.

## DEC-042 — Shared-layer refusal fixes: selection rule registered before measuring (2026-11-23)

The owner approved the PHA 2 diagnosis (`TASKS.md`, "Shared-layer refusals diagnosed") and asked
for directions 2 and 1, each behind its own flag, off by default; direction 3 is not attempted.
Dev sets only; no held-out set is run or read. **This rule is committed before any result.**

**Variants** (s3t = the default, DEC-040/041):

- `base`: s3t.
- `2a`: `RAG_PROMPT_CHUNK_SELECTION=per_document_3`: at most 3 chunks per document, 5 sources in
  total as before.
- `2b`: `RAG_PROMPT_CHUNK_SELECTION=lexical`: at most 2 chunks per document; within a document the
  chunks are ordered by their word overlap with the question instead of the RRF order.
- `1`: `RAG_VALIDATOR_V2_ENABLED=true`: the validator rules that rejected right drafts are
  corrected, and every amount of money, number of days and rate in a claim must be in the cited
  chunk, bound to what the claim attributes it to.
- `2a+1`, `2b+1`: both. Both combinations run, so that every comparison stays inside one job
  (DEC-011); "the best of 2 + 1" is the combination with the variant of 2 chosen below.

**Measurement:** the 7 dev sets (UAT, `natural_dev_v1`, rbac, relevance, false_refusal,
false_refusal_v2, compound), one job per set with all six configurations, 1 run (the LLM is seeded:
DEC-041 found the s3t path deterministic within a job). UAT runs as 3 jobs (Q001-Q034, Q035-Q067,
Q068-Q100), each with its own `base`, because six configurations of 100 items exceed the 340-minute
job limit; its counts are summed over the three. Categories are those of
`scripts/diagnostics/summarize_ablation.py` (`categories`, `leaks`): correct, false refusal, false
answer, wrong value, infra.

**A variant is accepted when, against `base` of the same job:**

1. leaks = 0 on every set;
2. on each of rbac, relevance, false_refusal, false_refusal_v2 and compound, false answers + wrong
   values do not increase. Tolerance 0 (the path is deterministic), except the items known to move
   with the order of the requests: **FR2-L01 and FR2-L06** (DEC-041). A change on those two is
   reported and not counted;
3. correct answers on `natural_dev_v1` + UAT together increase.

An item with an infra error in either configuration is left out of both and reported; more than 2
in one job, and the job is run again.

**The variant of 2 for the combination:** the one of 2a and 2b that is accepted; if both or
neither, the one with more correct answers on `natural_dev_v1` + UAT; a tie goes to fewer false
answers + wrong values on the five other sets, then to the smaller mean prompt.

**Also reported:** the mean prompt tokens per LLM call of each configuration (Ollama usage, from
`simple_trace`), and the items each variant fixes or breaks (IDs only).

**Known limitation:** the 28 diagnosed cases are UAT and `natural_dev_v1` items, and the fixes were
designed on them, so a gain on those two sets is biased upward. The five other sets are the guard
that matters. No default changes under this decision; the result is a proposal for the owner.

### Result (2026-11-24) and the proposal; no default changed

**Runs** (commit 4930af6, one run each, all six configurations in every job):

- `natural_dev_v1`: 45177644610.
- rbac: 45177651696.
- relevance: 45177658451.
- false_refusal: 45177665692.
- false_refusal_v2: 45177671410.
- compound: 45177676731.
- UAT, in three parts:
  - 45177685295, attempt 2. Attempt 1 failed: the runner's Ollama had no `llama-server` binary, so all 34 items were infra errors and the job was run again.
  - 45177692884.
  - 45177701483.

No infra error in the measured attempts.

| | base | 2a | 2b | 1 | 2a+1 | 2b+1 |
|---|---:|---:|---:|---:|---:|---:|
| `natural_dev_v1`: correct | 7 | 8 | 8 | 9 | 10 | 10 |
| false refusals | 8 | 7 | 6 | 5 | 3 | 4 |
| false answers + wrong values | 5 | 5 | 6 | 6 | 7 | 6 |
| UAT (100): correct | 69 | 72 | 66 | 71 | 74 | 67 |
| false refusals | 23 | 20 | 26 | 19 | 15 | 24 |
| wrong values | 8 | 8 | 8 | 10 | 11 | 9 |
| 5 guard sets (137 items): correct / false answers + wrong values | 106 / 10 | 106 / 10 | 106 / 10 | 106 / 10 | 106 / 10 | 106 / 10 |
| leaks, every set | 0 | 0 | 0 | 0 | 0 | 0 |
| mean prompt tokens per LLM call, natural / UAT | 2273 / 2273 | 2271 / 2273 | 2243 / 2269 | 2272 / 2269 | 2264 / 2267 | 2250 / 2267 |

**Verdicts under the rule:**

- 2a: accepted (+4).
- 2b: rejected (natural + UAT correct −2).
- 1: accepted (+4).
- 2a+1, the combination chosen since only 2a of 2a/2b is accepted: accepted (+8).
- 2b+1: +1, not the chosen combination.

**What the rule could not see:** no guard set moved under any configuration. Their documents are short, so 2a and 2b put the same chunks in the prompt (identical prompt sizes). Variant 1 changed one retry on compound, with the same outcome. The guard sets are therefore no evidence for or against either direction. The only signal comes from `natural_dev_v1` and UAT, the two sets the fixes were designed on.

**Items (IDs only):**

- **2a:**
  - fixed: ND-005; Q031, Q039, Q042, Q046, Q048;
  - broken: Q052, Q090;
  - newly wrong: ND-003, Q041 (as many wrong items were fixed, so the totals stay equal).
- **1:**
  - fixed: ND-006, ND-019; Q046, Q086;
  - newly wrong:
    - ND-015: a value of another row of the cited chunk (the known limit of the presence check);
    - ND-007: a partial answer, graded wrong;
    - Q030, Q037: content as the reference, but the cited document is ND-HR-005, not the reference ND-HR-003.
- **2a+1:**
  - fixed: ND-005, ND-006, ND-019; Q031, Q039, Q042, Q046, Q048, Q086;
  - broken: Q052;
  - newly wrong: ND-003, ND-007, ND-015, Q030, Q037, Q041, Q071.
- **2b:**
  - fixes 3 natural and 7 UAT items;
  - breaks 2 and 10.

**Validator v2, against the PHA 2 diagnosis:**

- **The 7 right drafts:**
  - All 7 pass the corrected rules when the recorded drafts are validated again.
  - In the measurement, only Q086 and ND-006 became correct.
  - Q030 and Q037 became answers that cite another document.
  - Q029, Q033 and ND-018 were refused again: the model wrote a new draft, which failed another check.
- **Correction to the PHA 2 table:** Q029 was rejected by `_answer_has_grounded_signal`, which counts only words of 4+ letters, not by `_yes_no_evidence_has_required_anchor`. The anchor rule is unchanged.
- **The value check is presence only.** A rule binding a value to the subject the claim gives it was tried, and rejected right claims each time: an answer normally repeats the question's words. The real Q097 (a right rate of another row, given for a day the source never names) is still rejected, but by another rule.

**Reranker (step 3, report only):** the demo stack `eaka-smoke` (main defaults) and the eval stack both run `RERANKER_PROVIDER=heuristic`, mode `lexical_fallback`. The simple path (s3t) does not rerank: the reranker only sets the candidate count (50), and the prompt takes the hybrid order. Only the legacy path calls `rerank()`.

**Proposal for the owner (no default changes until the owner chooses):**

1. **2a, `RAG_PROMPT_CHUNK_SELECTION=per_document_3`:**
   - The cleanest: +4 right answers on natural + UAT, no change in false answers + wrong values on any set, same prompt size.
   - Limit: the guard sets do not exercise it.
2. **1, `RAG_VALIDATOR_V2_ENABLED`, not as a default yet:**
   - It gives +4, but 3 more false answers + wrong values on natural + UAT.
   - Before it can be a default, it needs the value-of-another-row limit and the choice of cited document.
3. **2a+1:** the largest gain (+8), with 5 more false answers + wrong values on natural + UAT.

A default flip still follows DEC-026, and the two-job rule of DEC-027.

### Amendment after the result (2026-11-25, owner) and the DEC-027 confirmation of 2a

**Written after the result above was known.** The rule as registered and its verdicts stay above,
unchanged, for comparison.

- **The gap:**
  - Rule 2 blocked a rise in false answers + wrong values only on the five guard sets.
  - Those sets gave no signal: every configuration equals base there.
  - So a variant could add false answers + wrong values on `natural_dev_v1` and UAT and still be accepted.
- **Rule from now on:** false answers + wrong values must not increase on **any** set, `natural_dev_v1` and UAT included. Rules 1 and 3 are unchanged.
- **Verdicts under it:**

  | Variant | False answers + wrong values (base → variant) | Right answers | Verdict |
  |---|---|---|---|
  | 2a | natural 5 → 5, UAT 8 → 8 | +4 | **accepted** |
  | 1 | natural 5 → 6, UAT 8 → 10 | | **rejected** |
  | 2a+1 | natural 5 → 7, UAT 8 → 11 | | **rejected** |

  2b stays rejected.

**Confirmation of 2a before the flip (DEC-027), registered before its runs:**

- **Runs:**
  - Two rounds, separate from the PR #59 jobs.
  - Each round is one `natural_dev_v1` job and one UAT job (Q001-Q100).
  - Each job runs both `base` and `2a` on the same image (main 4ebf927; the branch adds only docs), 1 run each.
  - Round 2 sets `EVAL_LLM_SEED` to its default value only so that its jobs differ from round 1's in the concurrency group and run alongside it.
- **2a is accepted if, in both rounds:**
  - its right answers on `natural_dev_v1` + UAT together exceed base's;
  - its false answers + wrong values do not exceed base's, on `natural_dev_v1` and on UAT each.
  - Leaks stay 0.
- **Also reported:**
  - the DEC-027 tie test per count;
  - the items whose category differs between the two rounds, and from the PR #59 jobs (IDs only).
- **Outcome:**
  - If accepted, DEC-043 makes `per_document_3` the default and keeps the flag for rollback.
  - If not, base stays, and the result is written here.

### Confirmation result (2026-11-26): 2a not accepted, base stays

**Runs:**

| Round | `natural_dev_v1` | UAT |
|---|---|---|
| 1 | 45779822077 | 45779832197 |
| 2 | 45779827292 | 45779837610 |

Branch `eval/dec042-confirm` (main 4ebf927 plus docs), configurations `base` and `2a`.

**Round 1's UAT job ended at the job time limit both times** (attempts 1 and 2):

- each time `base` finished (12772 s and 12699 s, against 5700 s in round 2);
- `2a` stopped at Q058-Q059.

That job has no complete `2a`, and it was not run a third time: the rule needs both rounds to pass, and round 2 does not.

| | PR #59 jobs (UAT in 3 parts) | round 1 | round 2 |
|---|---|---|---|
| `natural_dev_v1` base: correct / false answers + wrong values | 7 / 5 | 7 / 5 | 7 / 5 |
| `natural_dev_v1` 2a | 8 / 5 | 8 / 5 | 8 / 5 |
| UAT base | 69 / 8 | 71 / 9 | 68 / 9 |
| UAT 2a | 72 / 8 | incomplete (time limit) | 70 / **10** |
| leaks | 0 | 0 | 0 |

**Verdict under the registered criteria: not accepted.**

- In round 2, 2a's false answers + wrong values on UAT exceed base's (10 > 9). The new one is Q057, right under base and wrong under 2a. Q041 is newly wrong under 2a, as it was in the PR #59 jobs.
- Right answers on natural + UAT were higher (+3), but that alone is not enough.
- **DEC-043 is not written:** `RAG_PROMPT_CHUNK_SELECTION` stays `rrf` by default, and `per_document_3` stays available behind the flag.

**The DEC-027 tie test** (PR #59 jobs against round 2, the two jobs with both configurations complete):

- `natural_dev_v1` +1 in both, with no change between jobs: a real but one-item difference.
- UAT right answers +3 and +2. Base moved by 1 between those jobs, 2a by 2; across all three jobs, base moved between 68 and 71. That is a tie.
- UAT false answers + wrong values: 0 and +1, so not the same sign: a tie.

**Items whose category differs between jobs** (IDs only):

- `natural_dev_v1`: none, for both configurations.
- UAT base, across the three jobs: Q028, Q029, Q033, Q036, Q046, Q048, Q063.
- UAT 2a, PR #59 jobs against round 2: Q003, Q020, Q031, Q057, Q074, Q076, Q080.

The UAT gain of 2a is no larger than the variation of base between jobs.
