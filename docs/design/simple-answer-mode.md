# Simple answer mode (`RAG_ANSWER_MODE`)

Started 2026-11-15, owner prompt "GIAI ĐOẠN MỚI — Simple answer mode, nhắm vào từ chối sai và trả lời lạc đề". Selection rule: DEC-026. Default stays `legacy`.

## Why

On new questions about 53% of the answers are false refusals, caused by the stack of hand-written checks. This is the only conclusion taken from held-out v1/v2; no held-out item was used to design this mode.

## What `simple` does

1. **Retrieval:** the same hybrid retrieval as legacy (semantic + keyword + fusion, with the permission filter in SQL). The first 5 chunks in hybrid order, at most 2 from one document. No subqueries, supplements, reranking cut, low-alignment filter or excerpt: each chunk goes in whole.
2. **One prompt** (`build_simple_grounded_prompt`). The system message holds only the rules, never retrieved text. The rules:
   - answer only from the sources and invent nothing;
   - end each sentence that uses a source with its `[SOURCE_n]` marker;
   - name a part the sources do not hold in one sentence: "Chưa xác minh được từ tài liệu bạn được phép truy cập: …" (or "Could not be verified from the documents you can access: …"). Until `716531f` the wording was "Tài liệu không đề cập …"; the owner replaced it on 2026-11-16 to match the compound grader (DEC PROMPT 6);
   - reply with the no-answer sentinel when no part is answered;
   - answer in the question's language.

   The answer is plain text, not JSON.
3. **Checks, and only these:**
   - the citation markers are valid and the cited chunks are still permitted (`CitationValidationService.validate_and_map`);
   - claim validation (`ClaimEvidenceValidationService.validate`) against the cited sources, with number/unit normalization forced on for this call (`number_normalization()`). A sentence with no marker that says the documents do not mention something states an absence, not a claim, so it is not validated: a partial answer is checked on its stated part. A sentence with a marker is always validated.
4. **One retry:** a missing marker, an unknown marker or an unsupported claim is retried once, with the specific reason and the rejected answer marked as not evidence. A second failure gives the fixed NO_ANSWER. The sentinel, an answer that only states absences, and a permission failure give NO_ANSWER at once, with no retry.
5. **Skipped in `simple`:** the deterministic route, the low-alignment filter, the completeness checks (c1/c3, D2), the responsiveness check, terminal blocks, compound partial and every repair after the LLM. Legacy code is unchanged.

`simple_det` is `simple` plus the strict deterministic route (`_structured_value_answer_draft`) as a fast path, tried before the LLM on the same 5 sources. **Removed in `716531f`** (owner decision, 2026-11-16); it appears below only as a measured configuration.

### Counters (`/metrics`, `enterprise_ai_rag_answer_branch_total`)

| Counter | Meaning |
|---|---|
| `simple_retry` | the one retry was used |
| `simple_deterministic` | removed with `simple_det` in `716531f` |
| `simple_no_answer_no_sources` | no permitted chunk, or the prompt guard stopped the call |
| `simple_no_answer_llm_refused` | the model replied with the sentinel |
| `simple_no_answer_refusal_text` | the answer only stated that the documents do not hold it |
| `simple_no_answer_citation_missing` | still no marker after the retry |
| `simple_no_answer_citation_invalid` | still an unknown marker after the retry |
| `simple_no_answer_claim_insufficient` / `_contradicted` | the cited sources still do not support the answer after the retry |
| `simple_no_answer_permission` | a cited chunk failed the permission re-check |

The UAT runner now records the run's branch counters (`branch_counters`), as the RBAC and relevance runners already did.

## Measurement plan (written before measuring, DEC-011)

- **Where:** Actions `eval.yml`, 2 runs, each configuration against a `legacy` baseline in the same job.
- **Configurations:** `legacy`, `simple`, `simple_det`, `oracle_legacy` (`EVAL_ABLATION=oracle`) and `oracle_simple` (`EVAL_ABLATION=oracle`, `EVAL_ANSWER_MODE=simple`).
- **Oracle:** the oracle gives the gold chunks in place of retrieval. For `simple` they still go through its 5-chunk, 2-per-document cut. The compound set has an oracle map from now on; its half-answerable items get the gold of their stated part.
- **Sets:** UAT (reported by route, monitoring only, DEC-026), RBAC, relevance, false refusal v1, false refusal v2, compound. UAT runs as two jobs: `legacy/simple/simple_det` and `legacy/oracle_legacy/oracle_simple`.
- **Per set and configuration:** correct, false refusal, false answer, wrong value or document, leaks and latency, plus the NO_ANSWER reasons of `simple`.
- **Rule (DEC-026):** leaks = 0 everywhere. The total of false answers plus wrong answers over the dev sets must not increase. Then fewer false refusals. The default is not changed in this task, whatever the result.

## Results

Measured 2026-11-15/16 on Actions (`eval.yml`, 2 runs, qwen2.5:3b on CPU, Ollama 0.40.15, `RERANKER_PROVIDER=heuristic`). Each cell is correct – false refusal – false answer – wrong value or document; a cell with two values is run 1 / run 2, otherwise both runs gave the same counts. Every configuration is compared with the `legacy` of its own job (DEC-016): legacy is stable inside a job but not always across jobs (compound legacy gave 4–5–2–1 in one job and 4–4–3–1 in another).

Code: `e9ad7ee` for RBAC and UAT, `c773dbb` for relevance, false refusal v1 and v2 and compound. The one change between them (see "The document-control bug" below) only affects a source the classifier marks REFERENCE; no document of those four sets is marked so, so their results stand.

Leaks: 0 in every configuration of every set. INFRA_ERROR: 0.

### Dev sets, answer modes

| Set (items, run) | legacy | simple | simple_det |
|---|---|---|---|
| RBAC (36, 43747646369) | 23–13–0–0 | 33–2–0–1 | 33–2–0–1 |
| relevance (25, 43734696442) | 18–3–4–0 | 19–2–4–0 | 18–2–5–0 |
| false refusal v1 (20, 43734705077) | 13–1–6–0 | 13–1–5–1 | 15–0–5–0 |
| false refusal v2 (24, 43734713503) | 14–6–4–0 | 17–4–3–0 | 17–4–3–0 |
| compound (12, 43734721769) | 4–5–2–1 | 5–2–5–0 | 5–1–6–0 |
| **Total (117)** | **72–28–16–1** | **87–11–17–2** | **88–9–19–1** |

Median latency per question (s):

| Set | legacy | simple | simple_det |
|---|---|---|---|
| RBAC | 31.6 | 4.2 | 3.9 |
| relevance | 19.8 | 12.3 | 10.1 |
| false refusal v1 | 31.6 | 3.4 | 2.9 |
| false refusal v2 | 42.5 | 16.3 | 10.5 |
| compound | 33.3 | 8.9 | 8.7 |

### DEC-026 on the dev sets

1. Leaks = 0: met on the dev sets (UAT below).
2. Total false answers (false answer + wrong value) must not increase: legacy **17**, simple **19** (+2), simple_det **20** (+3). **Not met by either mode, as measured.**
3. False refusals (only weighed once 2 holds): legacy 28, simple 11, simple_det 9. natural_dev_v1 does not exist yet.

Where simple's extra false answers come from, against the legacy of the same job:

| Set | legacy | simple | Δ | What changed |
|---|---|---|---|---|
| RBAC | 0 | 1 | +1 | one wrong value (`RBD-12control`); `oracle_simple` answers it correctly, so the wrong value comes from the chunks retrieval gave |
| relevance | 4 | 4 | 0 | |
| false refusal v1 | 6 | 6 | 0 | one false answer fewer, one wrong value more |
| false refusal v2 | 4 | 3 | −1 | |
| compound | 3 | 5 | +2 | see below |

**Compound wording.** The compound grader (`scripts/eval/run_answer_relevance_dev.py`) accepts a partial answer only when it holds "chưa xác minh được", the sentence chosen for legacy's compound partial answer (`pipeline-loss-fix-plan.md`: "không dùng 'tài liệu không đề cập'"). The phase prompt asked simple to say "tài liệu không đề cập" for a missing part, and its prompt does. Split of the compound false answers (counts only):

| | refuse item answered | partial, states the missing part | partial, does not state it |
|---|---|---|---|
| legacy | 1 | 0 | 1 |
| simple | 1 | 2 | 2 |
| simple_det | 1 | 1 | 4 |

So 2 of simple's 5 compound false answers (1 of simple_det's 6) are partial answers that name the missing part in the wording the phase prompt asked for, which the grader does not accept. They stay false answers here; this report does not re-grade them. Which wording counts is the owner's call (two decisions disagree). If "tài liệu không đề cập" is accepted, those items still need their stated part checked; at best simple would then total 17, equal to legacy, and simple_det 19.

### Oracle context × {legacy, simple}

The oracle puts the gold chunks of an answerable item in the prompt; items to refuse run unchanged. For `oracle_simple` the gold chunks still go through the 5-chunk, 2-per-document cut.

| Set (run) | legacy | oracle_legacy | oracle_simple |
|---|---|---|---|
| RBAC (43747646369) | 23–13–0–0 | 26–10–0–0 | 34–2–0–0 |
| relevance (43740828713) | 18–3–4–0 | 19–2–4–0 | 20–2–3–0 / 19–2–3–1 |
| false refusal v1 (43740838829) | 13–1–6–0 | 13–1–6–0 | 16–0–4–0 / 14–0–5–1 |
| false refusal v2 (43740848355) | 14–6–4–0 | 14–6–4–0 | 19–2–3–0 |
| compound (43740858097) | 4–4–3–1 | 4–4–3–1 | 5–3–4–0 |
| **Total (117)** | **72–27–17–1** | **76–23–17–1** | **94–9–14–0 / 91–9–15–2** |

- With the gold chunks, legacy still refuses 23 of 117: most of its false refusals come from its checks, not from retrieval.
- simple refuses 9 with the gold chunks and 11 with real retrieval: retrieval accounts for about 2 of its false refusals.
- False answers stay with the gold chunks (oracle_simple 14–17, oracle_legacy 18). They come from answering items that must be refused (which the oracle does not change) and from compound wording, not from missing context.

### NO_ANSWER reasons of simple

Counts per run (identical in both runs unless shown as run 1 / run 2). They include the correct refusals of items to refuse.

| Set | config | retries | refusal_text | claim_insufficient | claim_contradicted | citation_missing |
|---|---|---|---|---|---|---|
| RBAC | simple | 11 / 10 | 16 / 18 | 4 / 2 | 0 | 0 |
| RBAC | simple_det | 10 | 18 | 2 | 0 | 0 |
| RBAC | oracle_simple | 12 | 18 | 2 | 0 | 0 |
| relevance | simple | 9 | 5 | 5 | 0 | 0 |
| relevance | simple_det | 9 | 4 | 5 | 0 | 0 |
| relevance | oracle_simple | 10 / 11 | 6 | 4 | 0 | 1 |
| false refusal v1 | simple | 3 | 3 | 1 | 0 | 0 |
| false refusal v1 | simple_det | 1 | 3 | 0 | 0 | 0 |
| false refusal v1 | oracle_simple | 5 / 4 | 3 | 0 | 1 / 0 | 0 |
| false refusal v2 | simple | 15 | 6 | 2 | 1 | 0 |
| false refusal v2 | simple_det | 14 | 6 | 2 | 1 | 0 |
| false refusal v2 | oracle_simple | 16 | 5 | 1 / 2 | 1 / 0 | 0 |
| compound | simple | 5 | 3 | 1 | 0 | 0 |
| compound | simple_det | 6 | 2 | 1 | 0 | 0 |
| compound | oracle_simple | 6 | 4 | 0 | 1 | 0 |

- `llm_refused` (the sentinel), `citation_invalid`, `permission` and `no_sources` were 0 everywhere: the model never uses the sentinel and writes an absence sentence instead (`refusal_text`).
- `simple_det` took its deterministic fast path on 2 (relevance), 5 (false refusal v1), 1 (false refusal v2) and 2 (compound) questions, and on none of RBAC.
- The retry is used often (up to 15 of 24 questions on false refusal v2); latency stays well under legacy.

### The document-control bug (found and fixed during the measurement)

The first RBAC run of `simple` (43734687386, `c773dbb`) refused all 18 answerable items, with the oracle too. Cause: claim validation drops a source that `is_non_answer_context` classifies as a reference block. Legacy cuts an excerpt around the fact, but simple puts the whole chunk in, and a chunk holding a "Mã kiểm soát tài liệu" line matches the reference cue "kiem soat tai lieu", so every fact of that chunk was hidden. Fix (`e9ad7ee`, only under `simple_validation()`): a REFERENCE source counts by its segments the classifier marks ANSWER. The document-control line itself still is not evidence, and a QUESTION_LIST source is still dropped whole. Legacy is unchanged. The first RBAC and UAT jobs (43734687386, 43740818720, and the cancelled 43734670547, 43740809102) are superseded by the reruns above.

A process mistake: the first oracle dispatch set `EVAL_ABLATION=oracle` without `EVAL_ORACLE_FILE` and failed with "the oracle ablation needs EVAL_ORACLE_FILE"; it was rerun with the file.

### UAT, by route (monitoring only, DEC-026)

Q001-Q100; 2 of them expect a refusal. `simple` has no deterministic route, so its results are split by the route legacy took for the same question (legacy run 1 of the same job: 75 deterministic, 25 LLM).

| Config (run) | Total | legacy's 75 deterministic | legacy's 25 LLM | median latency (s): det / LLM |
|---|---|---|---|---|
| legacy (43747625613) | 98–1–0–1 / 99–1–0–0 | 75–0–0–0 | 23–1–0–1 / 24–1–0–0 | 0.8 / 25.2 |
| simple | 40–53–0–7 / 39–54–0–7 | 28–42–0–5 | 12–11–0–2 / 11–12–0–2 | 41.5 / 44.0 |
| simple_det | 59–32–1–8 | 49–21–0–5 | 10–11–1–3 | 0.4 / 31.5 |
| legacy (43747636163) | 98–1–0–1 / 99–1–0–0 | 75–0–0–0 | 23–1–0–1 / 24–1–0–0 | 0.6 / 15.5 |
| oracle_legacy | 95–4–1–0 | 74–1–0–0 | 21–3–1–0 | 0.3 / 17.7 |
| oracle_simple | 55–44–0–1 / 54–45–0–1 | 39–36–0–0 | 16–8–0–1 / 15–9–0–1 | 7.2 / 8.2 |

Leaks: 0 in every configuration.

- simple loses 58-60 UAT answers: 47 on the questions legacy answers with server-built values, and 12 even on the 25 questions legacy answers with the LLM.
- With the gold chunks (oracle_simple) it still refuses 44-45, so retrieval explains only about 9 of its refusals.
- `simple_det` takes its fast path on 50 questions (legacy's route takes 75), and on that path it gives 5 wrong values and 1 false answer. Legacy's route gives none. On 5 sources only, the strict route sometimes reads a value from the wrong chunk.
- simple is slower than legacy on UAT: 5 whole chunks of the real documents make a long prompt on CPU, and 76 of 100 questions use the retry.

NO_ANSWER reasons on UAT (run 1 / run 2; they include the 1-2 correct refusals):

| Config | retries | refusal_text | claim_insufficient | claim_contradicted | citation_missing |
|---|---|---|---|---|---|
| simple | 76 | 24 / 23 | 19 / 18 | 9 | 3 / 6 |
| simple_det | 35 / 34 | 15 / 16 | 10 / 9 | 4 | 4 |
| oracle_simple | 86 / 85 | 8 | 26 / 25 | 9 / 10 | 3 / 4 |

Two things the counters and the corpus show (page-level check of corpus V2 with `classify_evidence_context`; codes and counts only):

- **Claim validation is the main cause once the context is right.** With the gold chunks, `refusal_text` falls from 24 to 8, but claim_insufficient + claim_contradicted rise to 35. The validator compares the whole multi-sentence answer with the whole cited chunks. Legacy uses the same validator on shorter answers drawn from query-focused excerpts. The rejected drafts are not recorded, so whether the validator or the model is wrong in each case is not known yet.
- **Question-list pages:** the gold pages of 6 UAT questions (Q056-Q060, Q098) classify as QUESTION_LIST when taken whole. simple drops such a source whole, so those questions cannot pass in simple whatever the model writes. The gold pages of 8 more questions classify as REFERENCE; the `e9ad7ee` fix covers those.

### Summary

| | legacy | simple | simple_det |
|---|---|---|---|
| Leaks (all sets) | 0 | 0 | 0 |
| Dev false answers + wrong (DEC-026 rule 2) | 17 | 19 | 20 |
| Dev false refusals | 28 | 11 | 9 |
| UAT correct (monitoring) | 98-99 | 39-40 | 59 |

Neither mode meets DEC-026: the dev total of false answers rises. On UAT, which is monitoring only, simple loses more than half of the answers. The default stays `legacy`.

### Next step (for the owner to decide)

What the results say about the three options:

- **Prompt:** fixes two things. It can align the absence sentence with whatever compound wording the owner chooses. It can also ask for a short answer limited to what was asked: on UAT, long answers drawn from whole chunks are what claim validation rejects.
- **Claim normalization / validation:** the largest remaining cause on UAT, with the gold chunks too (35 of 46-47 NO_ANSWER). Two general changes are visible:
  - validate each marked sentence against its own cited sources, instead of the joined answer against every cited chunk;
  - treat a QUESTION_LIST chunk by segments, as `e9ad7ee` does for REFERENCE.

  Before choosing, a diagnostic run should record, for every rejected draft, which sentence failed and why (counts only, nothing in the repo), on the dev sets and UAT. The data so far cannot tell a strict validator from a wrong model answer.
- **Bigger model:** not indicated yet. The 3B ceiling in this mode is hidden behind the validator (oracle_simple refuses 44 of 100 UAT questions it has the gold for). The 7B measured on 2026-11-14 cut false answers but added almost no correct answers, at 1.9-2.8x the latency.

Proposed order:

1. The owner decides the compound wording ("chưa xác minh được" or "tài liệu không đề cập").
2. The diagnostic run above.
3. Per-sentence validation, QUESTION_LIST by segments and a short-answer prompt, each behind the mode and measured as here.
4. `simple_det` is not worth pursuing: its fast path on 5 sources adds wrong values on dev and on UAT.

## Diagnosis of the rejected drafts (2026-11-16)

Owner decisions before this step: a missing part is named "chưa xác minh được …" (the earlier "tài liệu không đề cập" prompt was wrong), `simple_det` is dropped, the LLM model stays. Both are in `716531f`. This step changes no behaviour: it records and classifies.

### How it was recorded

- Eval-only ablation `simple_trace` (`scripts/diagnostics/ablation_patches.py`, `3698da9`). It wraps `_simple_validate` and writes one line per LLM draft, rejected ones included, to the artifact `simple_trace.jsonl`: the draft, its outcome, each sentence with the `[SOURCE_n]` it cites and the validator status when judged alone, and the sources. The application code and the answers are unchanged.
- Jobs: `eval.yml`, 1 run, code `3698da9`, qwen2.5:3b on CPU, configurations `simple` (real retrieval) and `oracle_simple`. Runs: UAT 43786322434, RBAC 43786338347, relevance 43786354241, false refusal v1 43786368647, false refusal v2 43786382737, compound 43786397006. Leaks 0, INFRA_ERROR 0.
- The validator has two failing statuses, INSUFFICIENT and CONTRADICTED. INSUFFICIENT is what the owner's prompt calls UNSUPPORTED.
- The reason of each rejection comes from replaying the validator offline on every sentence of every rejected draft and noting which rule returned. The class of each sentence is a manual reading of the sentence against the text of the sources it cites. It was done once, by one reader, with no second opinion; about 6 of the 187 are borderline.
- Unit: one sentence of one draft that claim validation rejected. A retry that repeats the same sentence counts again, which is common: the seed is fixed, so the retry often returns the same text.

### What happens to a turn

Outcome of the first draft and of the retry, per question:

| Set | config | questions | answered at once | first draft has no marker at all | ends answered | ends rejected by claim validation | ends with no marker | absence only |
|---|---|---|---|---|---|---|---|---|
| UAT | simple | 100 | 3 | 79 | 43 | 42 | 8 | 7 |
| UAT | oracle_simple | 100 | 10 | 75 | 50 | 38 | 8 | 4 |
| RBAC | simple | 36 | 11 | 6 | 15 | 5 | 0 | 16 |
| RBAC | oracle_simple | 36 | 5 | 12 | 16 | 3 | 0 | 17 |
| relevance | simple | 25 | 13 | 6 | 18 | 6 | 0 | 1 |
| relevance | oracle_simple | 25 | 10 | 9 | 17 | 6 | 0 | 2 |
| false refusal v1 | simple | 20 | 12 | 2 | 14 | 4 | 0 | 2 |
| false refusal v1 | oracle_simple | 20 | 12 | 4 | 15 | 3 | 0 | 2 |
| false refusal v2 | simple | 24 | 5 | 15 | 18 | 4 | 0 | 2 |
| false refusal v2 | oracle_simple | 24 | 6 | 15 | 18 | 3 | 0 | 3 |
| compound | simple | 12 | 2 | 5 | 7 | 2 | 0 | 3 |
| compound | oracle_simple | 12 | 2 | 6 | 8 | 1 | 0 | 3 |

**The first draft usually has no marker.** On UAT 75-79 of 100 first drafts carry no `[SOURCE_n]` at all; on false refusal v2 15 of 24. The retry then returns the same sentence with a marker added. So most questions cost two LLM calls, and what is validated is in fact the second draft. This was not in the three classes the owner listed; it is a prompt matter.

### Classes of the rejected sentences

- **(a) validator too strict:** the sentence states what its cited source states, and answers the question.
- **(b) model wrong or off topic:** wrong value, a fact of another subject, a claim the cited source does not hold (right value but wrong source included), another language, or prompt text echoed back.
- **(c) question-list source:** every cited source is classified QUESTION_LIST, so the sentence has no evidence at all, right or wrong.
- **(d) absence sentence with a marker** (not in the owner's list): the model writes "Chưa xác minh được từ tài liệu bạn được phép truy cập: [SOURCE_1]". The marker makes it a claim, and it is validated as one.
- **(e) sentence with no marker** inside a draft that has markers elsewhere (not in the owner's list): long answers where only the last sentence is marked.

| Set | config | rejected sentences | (a) | (b) | (c) | (d) | (e) |
|---|---|---|---|---|---|---|---|
| UAT | simple | 62 | 13 | 27 | 10 | 4 | 8 |
| UAT | oracle_simple | 57 | 12 | 25 | 5 | 4 | 11 |
| RBAC | simple | 8 | 2 | 2 | 0 | 4 | 0 |
| RBAC | oracle_simple | 5 | 2 | 1 | 0 | 2 | 0 |
| relevance | simple | 13 | 2 | 3 | 0 | 6 | 2 |
| relevance | oracle_simple | 14 | 2 | 2 | 0 | 6 | 4 |
| false refusal v1 | simple | 8 | 6 | 0 | 0 | 2 | 0 |
| false refusal v1 | oracle_simple | 5 | 3 | 0 | 0 | 2 | 0 |
| false refusal v2 | simple | 6 | 3 | 3 | 0 | 0 | 0 |
| false refusal v2 | oracle_simple | 3 | 3 | 0 | 0 | 0 | 0 |
| compound | simple | 4 | 4 | 0 | 0 | 0 | 0 |
| compound | oracle_simple | 2 | 2 | 0 | 0 | 0 | 0 |
| **Dev sets** | simple | 39 | 17 (44%) | 8 (21%) | 0 | 12 (31%) | 2 (5%) |
| **Dev sets** | oracle_simple | 29 | 12 (41%) | 3 (10%) | 0 | 10 (34%) | 4 (14%) |
| **UAT** | simple | 62 | 13 (21%) | 27 (44%) | 10 (16%) | 4 (6%) | 8 (13%) |
| **UAT** | oracle_simple | 57 | 12 (21%) | 25 (44%) | 5 (9%) | 4 (7%) | 11 (19%) |
| **All** | both | 187 | 54 (29%) | 63 (34%) | 15 (8%) | 30 (16%) | 25 (13%) |

Reading it:

- **Dev sets: the validator is the main cause.** 41-44% of the rejected sentences are correct, and another 31-34% are absence sentences with a marker. The model is wrong in 10-21%.
- **UAT: the model is the main cause.** 44% of the rejected sentences are wrong, with the gold chunks too. The validator rejects a correct sentence in 21%, and question-list sources account for 9-16%.
- So "claim validation is the main cause on UAT", written in the Results above, was too strong: about half of what it rejects there deserves it.
- No draft was rejected only as a whole: in every rejected draft at least one sentence fails alone or has no marker. Per-sentence validation by itself therefore passes nothing more; its use is to let a correct sentence stand when another one is dropped.

### (a) Which rules reject correct sentences

54 sentences, by the rule of `_validate_answer_against_evidence` that returned:

| Rule | Count | What it rejects (made-up wording) |
|---|---|---|
| `_explicit_value_answer_is_subject_aligned` | 23 | a short value answer without the subject ("7 ngày làm việc" to "nộp chứng từ trong bao lâu?"), and a sentence copied word for word from the source |
| attendance policy yes/no status | 9 | "Không" or a copied policy sentence on a yes/no question about attendance or overtime |
| `_person_lookup_answer_name_missing` | 5 | a "who" question answered with a role ("trưởng phòng") and no personal name; the answered half of a compound question when the other half asks "who" |
| `_polarity_is_contradicted` | 5 | a correct value followed in the same sentence unit by an absence clause ("… 30% mỗi tuần. [SOURCE_1] Nhiệt độ không được nêu …"): the "không" of the absence clause is read against the claim (4); a plain correct count, once |
| `_numbers_are_contradicted` | 4 | "8 tiếng" against "08 giờ/ngày" in a table row with other numbers; "khoảng 2 người" against "tối thiểu 02 người" |
| annual-leave relation status | 4 | a copied seniority rule |
| bereavement duration status | 2 | "3 ngày" against a table cell "03 ngày" whose label is on another line |
| conditional allowance status, role relation | 2 | a correct amount; a title in Vietnamese where the question uses the English abbreviation |

Two patterns cover most of it. First, the rules were written for legacy's server-built answers and expect a full sentence that restates the subject, while the model answers with the bare value, which is what a short-answer prompt would ask for even more. Second, domain rules written for the legacy route (attendance, leave, bereavement) fire on sentences copied from the source. The compound rows show a third: the sentence splitter keeps a marker that follows a full stop with the next sentence, so a claim and an absence clause are judged as one.

### (b) What the model gets wrong

63 sentences: a value of another row or subject (the role of one person given to another, the limit of one benefit for another), a fact the cited source does not hold (some of them right but cited to the wrong source), an answer in Chinese or English to a Vietnamese question (6 sentences), the retry instruction echoed as the answer, and a question about one thing answered with a nearby fact about another. The validator is right to reject these. On UAT they are 44% of the rejections with the gold chunks in the prompt, so this is the 3B model's reading of long, table-heavy chunks, not retrieval.

### (c) Question-list sources

15 sentences, all on UAT, 10 with real retrieval and 5 with the gold chunks. In 7 the value is the right one, read from a table that sits in a chunk classified QUESTION_LIST as a whole; in the other 8 the model copied a sample question or a page header, wrote an absence sentence, or gave a wrong or vague value. Counting such a source by its answer segments would give the 7 their evidence; the other 8 should still fail.

### (d) Absence sentences with a marker, and a defect of this branch

30 rejected sentences are "Chưa xác minh được …: [SOURCE_1]" (6 of them written "Không xác minh được …", which the absence phrases do not hold). Most are on items that must be refused, so the turn ends at NO_ANSWER, which is the right outcome for the wrong reason.

**The same sentence sometimes passes validation and is returned as an answer with a citation.** In this run that happened on 2 of 25 relevance items with real retrieval, 1 with the gold chunks, and 1 UAT question with the gold chunks. The graders count it as a false answer. It comes from the new wording of `716531f`: the model adds a marker to the absence sentence more often than it did with "tài liệu không đề cập". Only `RAG_ANSWER_MODE=simple` is affected and the default is `legacy`. It is not fixed here because this step changes no behaviour; it is the first item of the proposal below.

### Graded results of this run (not a DEC-026 comparison)

1 run, no `legacy` in the same job, so these numbers cannot be compared with the table in Results under DEC-011. They are here only to show the direction after the wording change. Correct – false refusal – false answer – wrong:

| Set | simple | oracle_simple |
|---|---|---|
| RBAC (36) | 32–3–0–1 | 33–2–0–1 |
| relevance (25) | 16–2–7–0 | 17–2–6–0 |
| false refusal v1 (20) | 12–3–5–0 | 13–2–5–0 |
| false refusal v2 (24) | 16–3–5–0 | 16–3–5–0 |
| compound (12) | 6–3–3–0 | 5–2–5–0 |
| **Dev total (117)** | **82–14–20–1** | **84–11–21–1** |
| UAT (100) | 36–55–0–9 | 51–48–0–1 |

- Compound false answers with real retrieval went from 5 to 3. Of the 3, one is a refuse item answered and two are partial answers whose missing part is still written the old way ("không có thông tin trong tài liệu", or in Chinese), so the prompt rule is not followed every time.
- Relevance false answers went from 4 to 7: 2 are the absence-with-marker defect above. The other 5, like all 5 of false refusal v1 and of v2, are items that must be refused and are answered with a sentence about something else, true or inferred from it. Claim validation passes them because the cited source supports the sentence; `simple` skips the responsiveness check that catches these in legacy. None of the three fixes proposed earlier addresses this.

### What this says about the fixes (for the owner to decide; nothing below is implemented)

1. **Absence sentences.** Recognise an absence sentence whether or not it carries a marker, also in the form "Không xác minh được", and drop its marker. An answer made only of absence sentences is NO_ANSWER. This removes class (d) (30 sentences), the defect above, and the polarity rejections on compound.
2. **Short-answer prompt with the marker in the first draft.** 75-79 of 100 UAT first drafts have no marker. A prompt that shows the expected shape (one short sentence, marker at its end) should cut the second LLM call and class (e). It will not reduce class (b) by itself.
3. **Per-sentence validation** helps only together with a looser subject rule: of the 54 correct sentences rejected, 23 fail `_explicit_value_answer_is_subject_aligned`. The question is whether `simple` should skip that rule (and the legacy domain rules for attendance, leave and bereavement, 15 more) and keep the number, polarity and evidence checks. That is a choice between false refusals and the risk of a wrong-subject value, so it needs the owner's call and a measurement under DEC-026.
4. **Question-list sources by segments:** worth 7 sentences on UAT, none on the dev sets.
5. **Not covered by any of these:** class (b) on UAT (44%), and refuse items answered with a supported but unrelated sentence (15 of the 20 dev false answers of this run). The first is the model's limit on long chunks; the second needs a relevance check between the question and the cited sentence, which `simple` removed on purpose.

## s1-s3 (owner approval 2026-11-16)

The owner approved three cumulative configurations. Each change has its own flag, all off by default, and only read when `RAG_ANSWER_MODE=simple`. The flags are listed in `ENVIRONMENT_VARIABLES.md`.

| Config | Flags | What changes |
|---|---|---|
| s1 | `RAG_SIMPLE_ABSENCE_SENTENCES_ENABLED`, `RAG_SIMPLE_SHORT_PROMPT_ENABLED` | A sentence naming an unverified part ("chưa/không xác minh được", "could not be verified") is never a claim, marked or not; its marker is removed; an answer of such sentences only is NO_ANSWER. A marker after a full stop stays with its sentence, so the next sentence is judged alone. The prompt asks for one short sentence per point asked, marker inside it, from the first draft. |
| s2 | s1 + `RAG_SIMPLE_RELAXED_RULES_ENABLED`, `RAG_SIMPLE_CLAIM_RELEVANCE_ENABLED` | Claim validation skips `_explicit_value_answer_is_subject_aligned` and the attendance, annual-leave and bereavement rules (the number/unit, polarity and evidence checks stay). Each marked claim is compared (e5 cosine) through the source sentence it cites with the question and each of its parts; below the threshold it is dropped; none left is NO_ANSWER with no retry. |
| s3 | s2 + `RAG_SIMPLE_QUESTION_LIST_SEGMENTS_ENABLED` | A whole question-list chunk counts by its segments that are neither questions nor non-answer context. |

Two choices made while implementing, not in the owner's text:

- An unverified-part sentence that holds a number the question does not hold stays a claim and is validated. Without this a fact written after "chưa xác minh được" would reach the user unchecked.
- A claim whose relevance cannot be measured (no marker, no evidence, no embedding provider) is kept, as the legacy responsiveness check does.

### Relevance threshold (calibrated before measuring)

Rule, fixed before computing: on the dev sets of the diagnostic run (`3698da9`, both configurations, UAT excluded), each draft scores the highest similarity among its claims, computed by the service's own code with the s1 split and the s2 validation flags. Positive: an accepted draft of an item to answer that states the item's fact. Negative: any draft of an item to refuse (RBAC: a draft none of whose sources holds the fact). t = the lowest positive score, floored to 0.01, so that no correct dev answer loses all its claims.

Result: **t = 0.78**, from 109 positive drafts (58 items) and 39 negative drafts (18 items). Positive best scores start at 0.780, 0.789, 0.824; negative best scores reach 0.908.

**At t = 0.78 the check is expected to do almost nothing:** 2 of 39 negative drafts and 0 of the 32 accepted ones fall below it. The question and the off-topic source sentence usually share the subject, so e5 rates them close. The trade-off on the same data (items to answer that lose every claim / of the 16 refuse items answered, those caught):

| t | correct items lost (of 58) | false answers caught (of 16) |
|---|---|---|
| 0.78 | 0 | 0 |
| 0.80 | 2 | 1 |
| 0.84 | 3 | 3 |
| 0.86 | 5 | 4 |
| 0.87 | 5 | 8 |
| 0.88 | 9 | 10 |
| 0.90 | 19 | 13 |

The measurement uses 0.78 as the rule gives. A higher value is a choice between false refusals and false answers, for the owner.

### What the relaxed rules let through (checked before measuring)

Replaying the 187 classified rejected sentences of the diagnostic run against their full cited sources with the s2 rules gives the following. Classes (d) and (e) are excluded; they do not depend on these rules.

| | (a) correct, rejected | (b) model wrong, rejected | (c) question list |
|---|---|---|---|
| dev, now SUPPORTED | 17 of 29 | 6 of 11 | – |
| UAT, now SUPPORTED | 13 of 25 | 17 of 52 | 0 of 15 |

So s2's rules accept about as many wrong sentences as correct ones on UAT. Where a retry followed, these sentences are counted once per draft. This is the risk that the "right number, wrong subject" count below is meant to measure.

### Measurement plan (written before measuring, DEC-011)

- **Where:** Actions `eval.yml`, 2 runs, qwen2.5:3b on CPU. Every configuration is compared only with the `legacy` of its own job (DEC-016).
- **Configurations:** `legacy`; `s1` = `EVAL_ANSWER_MODE=simple`, `EVAL_ABLATION=simple_trace`, `EVAL_SIMPLE_S1=true`; `s2` = s1 + `EVAL_SIMPLE_S2=true`; `s3` = s2 + `EVAL_SIMPLE_S3=true`. `scripts/eval/compose.uat-eval.yaml` maps each switch to the flags of its configuration. Every draft of s1-s3 is saved as in the diagnosis.
- **Process note:** the first dispatch (7 jobs, `2fb1b26`) spelled out each flag. Six of them failed before starting, because the `configs` input is part of the job's concurrency group, which is limited to about 400 characters. The one short job (UAT `legacy, s1`, run 43818691901) ran as dispatched, on `2fb1b26` with the per-flag names; the app code is the same in both commits.
- **Jobs:** one job per dev set with `legacy, s1, s2, s3`: RBAC, relevance, false refusal v1, v2, compound. UAT in two jobs, because four configurations × 2 runs exceed the 340-minute job limit (the earlier three-configuration UAT job took 4 h 49): `legacy, s2, s3` (s2 and s3 differ only on question-list sources, which only UAT has) and `legacy, s1`.
- **Per set and configuration:** correct – false refusal – false answer – wrong value or document, leaks, latency; dev totals.
- **Extra counts, defined now:**
  - *Supported but off topic:* false answers on items to refuse (RBAC: negatives) whose answer is not only an unverified sentence and whose every number appears in the text of its cited sources. The other false answers are counted as invented.
  - *Right number, wrong subject (s2's risk):* answered items to answer graded wrong (wrong value or document) whose every number appears in their cited sources; on the dev sets and, for monitoring, on UAT.
  - *s1:* share of first drafts with at least one valid marker, and mean LLM calls per question, from the saved drafts.
  - Drops by the relevance check: `simple_claim_irrelevant` and `simple_no_answer_claim_irrelevant`.
- **Rule (DEC-026), per configuration against the legacy of its job:** leaks = 0 everywhere; dev total of false answers plus wrong answers not above legacy; then fewer false refusals. A change counts only when both runs agree; the others are reported as unstable. UAT is monitoring only, reported by the route legacy took.
- A configuration that meets the rule is reported. **The default is not changed in this step.**
