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
