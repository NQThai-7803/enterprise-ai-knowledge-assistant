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

### Results of s1-s3 (2026-11-16)

Jobs, all on `5d9622c` except UAT `legacy, s1` on `2fb1b26` (same app code): RBAC 43819021449, relevance 43819050099, false refusal v1 43819075562, v2 43819098974, compound 43819124988; UAT 43818691901 (`legacy, s1`), 43819150999 (`legacy, s2, s3`), 43867560167 (`legacy, s2`), 43867565634 (`legacy, s3`). Every s1-s3 draft is saved in its job's artifact as `simple_trace.jsonl` (kept 14 days).

**Process note:** the UAT `legacy, s2, s3` job stopped at its 340-minute limit after legacy ×2, s2 ×1 and s3 ×1; one s2 run took 8,370 s against 2,262 s for legacy. The planned estimate was wrong. The second s2 and s3 runs come from two more jobs, each with its own `legacy`, 1 run each; there the s2 run took 3,416 s.

#### Dev sets

Correct – false refusal – false answer – wrong value or document. **Both runs give the same result on every set and configuration; no item is unstable.**

| Set | legacy | s1 | s2 | s3 |
|---|---|---|---|---|
| RBAC (36) | 23–13–0–0 | 34–2–0–0 | 36–0–0–0 | 36–0–0–0 |
| relevance (25) | 18–3–4–0 | 18–2–4–1 | 20–0–4–1 | 20–0–4–1 |
| false refusal v1 (20) | 13–1–6–0 | 14–2–4–0 | 14–2–4–0 | 14–2–4–0 |
| false refusal v2 (24) | 14–6–4–0 | 18–3–3–0 | 20–1–3–0 | 20–1–3–0 |
| compound (12) | 4–4–3–1 | 6–4–2–0 | 6–4–2–0 | 6–4–2–0 |
| **Dev total (117)** | **72–27–17–1** | **90–13–13–1** | **96–7–13–1** | **96–7–13–1** |
| Leaks | 0 | 0 | 0 | 0 |
| Median latency per set, s | 11.6–55.2 | 1.7–16.0 | 1.7–10.4 | 1.7–10.5 |

Items that change (both runs):

- legacy → s1: 27 items become correct, 9 correct items are lost (5 to a false answer, 3 to a false refusal, 1 to a wrong value). False answers: 10 removed, 6 new (one of them a compound item that legacy refused).
- s1 → s2: 6 false refusals become correct (RBAC 2, relevance 2, false refusal v2 2); nothing gets worse.
- s2 → s3: no item changes.

#### DEC-026

1. Leaks: 0 on every set and configuration (RBAC retrieval-level check: 18 pairs, all conclusive, no chunk seen by a negative). UAT: 0.
2. Dev false answers + wrong: legacy 18; s1, s2, s3 14 each. None increases.
3. Dev false refusals (`natural_dev_v1` does not exist yet): legacy 27; s1 13; s2 7; s3 7.

**s1, s2 and s3 each meet DEC-026 against the legacy of their job. s2 and s3 rank first and are the same item by item on the dev sets;** s3 makes a difference only on UAT. The default is not changed.

#### Extra counts

| | legacy | s1 | s2 | s3 |
|---|---|---|---|---|
| Dev false answers that are supported but off topic | 15 | 12 | 12 | 12 |
| Dev false answers that are invented / only an unverified sentence | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Compound half-answerable items answered in full | 2 | 1 | 1 | 1 |
| Right number, wrong subject: dev | 1 | 0 | 0 | 0 |
| Right number, wrong subject: UAT (monitoring), per run | – | 4, 4 | 8, 5 | 8, 7 |
| First drafts with a valid marker: UAT, per run (of 100) | – | 90, 89 | 86, 85 | 84, 83 |
| First drafts with a valid marker: dev, per run (of 117; RBAC's 18 negatives answer with the no-answer sentinel) | – | 94, 93 | 93, 93 | 93, 93 |
| Mean LLM drafts per question: UAT, per run | – | 1.36, 1.35 | 1.28, 1.24 | 1.16, 1.18 |
| Mean LLM drafts per question: dev sets | – | 1.05–1.12 | 1.00–1.08 | 1.00–1.08 |
| Relevance check, claims dropped / questions ended: dev | – | – | 0 / 0 | 0 / 0 |
| Relevance check, claims dropped / questions ended: UAT, per run | – | – | 2 / 2, 2 / 2 | 2 / 2, 2 / 2 |

- **Off topic:** every dev false answer of s1-s3 except one compound partial is a refuse item answered with a sentence its cited source supports. The relevance check at t = 0.78 caught none of them; the lowest claim similarity on the dev sets was 0.780, as the calibration predicted.
- **The UAT questions ended by the relevance check** (Q031 and Q032; in the s3 second run Q032 and Q084) are all items the reference answers, so the check caused 2 false refusals per run there.
- **s1's prompt:** in the diagnosis 21-25 of 100 UAT first drafts had a marker; with s1, 89-90 have one.

#### UAT (monitoring only), by the route legacy took for the same question

Correct – false refusal – false answer – wrong. Legacy is 100–0–0–0 in the first two jobs and 98–1–0–1 in the two second-run jobs (Q002 wrong, Q071 refused, both on its LLM route); its route split is 76/24 (deterministic/LLM) in job 43819150999 and 75/25 in the others.

| Config | Run (job) | All | Legacy deterministic route | Legacy LLM route |
|---|---|---|---|---|
| s1 | 1 and 2 (43818691901), same | 39–54–1–6 | 28–43–0–4 | 11–11–1–2 |
| s2 | 1 (43819150999) | 44–45–1–10 | 33–36–0–7 | 11–9–1–3 |
| s2 | 2 (43867560167) | 47–45–1–7 | 36–35–0–4 | 11–10–1–3 |
| s3 | 1 (43819150999) | 56–33–1–10 | 45–24–0–7 | 11–9–1–3 |
| s3 | 2 (43867565634) | 50–37–1–12 | 40–26–0–9 | 10–11–1–3 |

- **s3 against s2, run 1, same job:** 14 false refusals become correct and 2 correct answers become false refusals, all on questions legacy answers on its deterministic route.
- **Runs in different jobs differ.** Within one job the two runs are identical everywhere (dev sets and UAT `legacy, s1`), but between jobs (another runner) s2 changes on 10 UAT questions and s3 on 14, and legacy on 2. So the second run in a job does not measure this variation, and the dev results above each come from one runner.
- **s2's risk shows on UAT only.** UAT wrong answers: s1 6 and 6, s2 10 and 7, s3 10 and 12; right number, wrong subject: s1 4 and 4, s2 8 and 5, s3 8 and 7. The 4 extra wrong answers of s2 run 1 against s1, read one by one (Q044, Q048, Q068, Q096; s1 is in another job): a leave duration for another family relation, a notice period from a conflicting document, a holiday-overtime answer saying there is no minimum, and an answer to the other half of a two-part question. The dev sets have no wrong answer of this kind under s2.
- Median latency: legacy 0.6-1.1 s (most answers are server-built); s1 28.7 s; s2 73.0 and 24.8 s; s3 64.2 and 42.5 s. Job wall time per run: legacy 1,423-2,262 s, s1 3,093-4,074 s, s2 8,370 and 3,416 s, s3 5,655 and 5,218 s. The slow s2 run 1 was that runner, not s2.

#### Summary (for the owner; nothing is switched on)

- s1 fixes the absence-sentence defect and the missing first-draft marker: 89-90 of 100 UAT first drafts now carry one (was 21-25), and dev false refusals fall from 27 to 13 with fewer false answers (18 → 14).
- s2 turns 6 more dev false refusals into correct answers with no dev regression. Its relevance check at 0.78 drops nothing on the dev sets and 2 correct UAT answers per run; with its relaxed rules the UAT right-number-wrong-subject count goes from 4 (s1) to 5-8.
- s3 equals s2 on the dev sets. On UAT it has 12 more correct answers than s2 in the same job (run 1); the second runs, in separate jobs, give 50 against 47.
- Not solved by any of the three: refuse items answered with a supported but off-topic sentence (12 of the 13 dev false answers).
- **Meets DEC-026: s1, s2 and s3; s2 and s3 rank first.** Choosing one, and whether the UAT wrong-subject risk of s2 is acceptable or the threshold should be raised (trade-off table above), is the owner's call.

## s4-s5 (owner decision 2026-11-16, second round)

The owner kept `legacy` as the default and named s3 the candidate, to be switched on only once it wins on `natural_dev_v1` and the wrong-subject risk is handled. Two more configurations, each with its own flag, off by default (`ENVIRONMENT_VARIABLES.md`):

| Config | Flags | What changes |
|---|---|---|
| s4 | s3 + `RAG_SIMPLE_SUBJECT_BINDING_ENABLED` | Each value in a claim (a number, read with the word after it) must sit in a cited sentence or table row that names the subject the question asks about. The answer need not repeat the subject. A failing claim is dropped; none left is NO_ANSWER with no retry. |
| s5 | s4 + `RAG_SIMPLE_CLAIM_CROSS_ENCODER_ENABLED` | The per-claim relevance check scores (question or one of its parts, cited source sentence) with `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` instead of e5 0.78. Threshold `RAG_SIMPLE_CLAIM_CROSS_ENCODER_MIN_SCORE`, calibrated below. |

### How s4 reads "the subject" (implementer's choices, before measuring)

- **Units:** each cited source is split into sentences and table rows. A PDF table comes out one row per line; a line that starts in lower case or holds only a value is the rest of the line before it (a wrapped cell). A row also carries the numbered section heading above it ("3.3 …"), because a table's subject often sits there and not in the rows.
- **Same kind:** the units holding a value with the same word after the number as the claim's value (ngày with ngày, đồng with đồng, % with %).
- **Subject:** the words the question asks about (question words and particles removed, syllables of 2 letters and more) that appear in some of those units but not all. A part of a two-part question is judged on its own.
- **Verdict per part:** no unit of that kind names any of its words → the part says nothing; every unit names the same ones → bound; else bound if a unit holding the value names a subject word. The claim fails only when some part says "not bound" and none says "bound". A value the question itself states is not checked.
- **Checked before measuring, dev only:** replayed on the 120 s3 run-1 drafts of the 5 dev jobs (93 claims), s4 drops none. One rule was changed after this replay: a part whose words all units name now counts as bound; before, a correct value of a two-part question was dropped because the other part's subject was in another row. The dev sets have no wrong-subject answer under s3, so s4 can only cost false refusals there; its effect is expected on UAT (monitoring) and `natural_dev_v1`.
- **Known limit:** words are matched as written, so a synonym ("cưới" for "kết hôn") does not name the subject.

### Cross-encoder threshold (rule fixed before computing)

On the dev sets only (UAT excluded): the s3 run-1 drafts of the 5 dev jobs of s1-s3. Each claim that s4 keeps scores the highest cross-encoder score (raw logit) of (question or one of its parts, the cited source sentence), computed by the service's own code; a draft scores its highest claim. Positive: an accepted draft of an item to answer that states the item's fact. Negative: any draft of an item to refuse (RBAC: a draft none of whose sources holds the fact). **t = the lowest positive score, floored to 0.1**, so that no correct dev answer loses all its claims. The trade-off table is reported as for e5.

Result: **t = −4.2**, from 60 positive drafts (60 items) and 12 negative drafts (12 items, all accepted, on relevance and both false-refusal sets and compound; RBAC has none under s3). Positive best scores start at −4.19, −0.22, 0.65; negative best scores reach 7.63. As with e5, the rule gives a threshold that catches none of them. The cross-encoder separates the two groups better than e5 did, which the owner may want to use (items to answer that lose every claim / of the 12 refuse items answered, those caught):

| t | correct items lost (of 60) | false answers caught (of 12) |
|---|---|---|
| −4.2 | 0 | 0 |
| −2.0 | 1 | 4 |
| 0.0 | 2 | 4 |
| 0.5 | 2 | 5 |
| 1.0 | 4 | 6 |
| 2.0 | 7 | 8 |
| 3.0 | 9 | 10 |

Model files: snapshot `1427fd65` of the Hugging Face repository (safetensors only on Actions). Measured locally on the owner's laptop CPU: loading takes about 6 s and adds about 790 MB of working set; one claim with 2 (question part, sentence) pairs takes about 38 ms. A claim it cannot score (model missing, timeout) is kept.

### Measurement plan (written before measuring, DEC-011, DEC-026, DEC-027)

- **Configurations:** `legacy`; `s3`, `s4`, `s5` = `EVAL_ABLATION=simple_trace,EVAL_SIMPLE_LEVEL=n` (`scripts/eval/ci_batch.sh` turns level n into simple mode with s1…sn on). Every draft is saved in `simple_trace.jsonl`, with s4's verdict per claim (`bindings`) and the relevance score per claim (`similarities`, the cross-encoder's under s5).
- **Two separate jobs per set (rounds a and b), each with its own `legacy`, 1 run per configuration (DEC-027).** Dev sets: one job per set and round with `legacy, s3, s4, s5`. UAT: three jobs per round, `legacy, s3`, `legacy, s4`, `legacy, s5`, to stay under the 340-minute limit. The two rounds run at the same time on different runners; `legacy` carries `EVAL_ROUND=a|b` only so that their concurrency groups differ.
- **Per set and configuration:** correct – false refusal – false answer – wrong, leaks, latency; dev totals; UAT by legacy route. UAT also: right number, wrong subject, and supported but off topic (definitions as for s1-s3). Drops by s4 and by the relevance check, from the traces.
- **Cost of s5:** extra median latency per question against s4 of the same job, and the runner's peak memory while s5 ran against s4 (`memory.log`).
- **Rule:** DEC-026 inside each job (leaks = 0; dev false answers + wrong not above legacy; then fewer false refusals), and DEC-027 across the two jobs: a difference counts only with the same sign in both jobs and larger than the largest change of either configuration between the jobs on that count; otherwise it is a tie.
- `natural_dev_v1` joins this matrix (legacy, s3, s4, s5, 2 jobs) once the owner approves its gold; it is then the first dev set in DEC-026. **The default is not changed in this step.**

### Results of s4-s5 (2026-11-17)

Jobs on `012ee8b` (round a: RBAC 43914469601, relevance 43914482325, false refusal v1 43914497353, v2 43914511636; UAT 43914538373 `legacy, s3`, 43914553130 `legacy, s4`, 43914568334 `legacy, s5`. Round b: RBAC 43914581686, relevance 43914596883, v2 43914625810, compound 43914639957; UAT 43914654247, 43914668424, 43914681662). Compound round a is 43949754203 and false refusal v1 round b is 43949786222, both on `5450a29` (same app code, see the process note). 1 run per configuration; every draft is in the job's `simple_trace.jsonl`.

**Process note:** in two jobs one configuration did not run (compound 43914524934 without s4, false refusal v1 43914610692 without s3): `ci_batch.sh` reported "ablation not applied in the API" for an API that had applied it. Under `set -o pipefail`, `grep -q` stops reading at the first match and the SIGPIPE it leaves `docker logs` failed the pipeline. Fixed in `5450a29` (grep reads to the end); the two sets were run again as complete jobs with all four configurations. The incomplete jobs agree with the complete ones (compound: legacy 4–5–2–1, s3 and s5 7–3–2–0; false refusal v1: legacy 13–1–6–0, s4 and s5 14–2–4–0).

#### Dev sets

Correct – false refusal – false answer – wrong value or document; job of round a / job of round b.

| Set | legacy | s3 | s4 | s5 |
|---|---|---|---|---|
| RBAC (36) | 23–13–0–0 / same | 35–1–0–0 / 36–0–0–0 | = s3 | = s3 |
| relevance (25) | 18–3–4–0 / same | 20–0–5–0 / 21–0–4–0 | = s3 | = s3 |
| false refusal v1 (20) | 13–1–6–0 / same | 14–2–4–0 / 15–2–3–0 | = s3 | = s3 |
| false refusal v2 (24) | 14–6–4–0 / same | 21–1–2–0 / 20–1–3–0 | = s3 | 20–2–2–0 / 19–2–3–0 |
| compound (12) | 4–5–2–1 / same | 7–3–2–0 / 6–4–2–0 | = s3 | = s3 |
| **Dev total (117)** | **72–28–16–1 / same** | **97–7–13–0 / 98–7–12–0** | **= s3** | **96–8–13–0 / 97–8–12–0** |
| Leaks | 0 | 0 | 0 | 0 |
| Median latency per set, s | 15.0–53.2 | 2.1–28.2 | 2.1–15.7 | 2.2–15.7 |

- **Between the two jobs** (another runner) each simple configuration changes on 1 item per set; legacy on 0 (relevance: 2 items, same totals).
- **s4 against s3: no dev item changes** in either job. s4 checked the drafts and found every value bound (0 claims dropped), as the replay before measuring predicted.
- **s5 against s4: one item, FR2-F04, correct → false refusal in both jobs.** Its first draft scores −8.11 with the cross-encoder. With e5 (0.81) that draft passes the relevance check, fails the contradiction check, and the retry answers correctly. With the cross-encoder the relevance check ends the turn first, and that check does not retry. The calibration scored only accepted drafts (that draft was rejected under s3), so it did not see this case. No other dev claim scores below −4.2.
- legacy → s3 per item (round a / round b): RBAC 12 / 13 false refusals become correct; relevance 8 / 9 changes (3 false refusals and 2-3 false answers become correct, 2-3 correct items become false answers); false refusal v1 5 / 4; v2 9 / 10; compound 4 / 4 (the wrong item becomes correct in both).

#### DEC-026 and DEC-027

1. Leaks: 0 on every set, configuration and job (RBAC retrieval-level check: 18 pairs per configuration, all conclusive, no chunk seen by a negative). UAT: 0.
2. Dev false answers + wrong, per job: legacy 17 / 17; s3 13 / 12; s4 13 / 12; s5 13 / 12. None increases.
3. Dev false refusals (`natural_dev_v1` is not in the matrix yet): legacy 28 / 28; s3 7 / 7; s4 7 / 7; s5 8 / 8.

DEC-027 across the two jobs (difference per job; it counts only with the same sign in both and larger than either configuration's change between the jobs on that count):

| Comparison | False refusals | False answers + wrong | Verdict |
|---|---|---|---|
| s3 vs legacy | −21, −21 (variation 0) | −4, −5 (variation 1) | **s3 better** on both |
| s4 vs s3 | 0, 0 | 0, 0 | **tie** (identical) |
| s5 vs s4 | +1, +1 (variation 0) | 0, 0 | **s5 worse** (one more false refusal, FR2-F04) |
| s4 vs legacy | −21, −21 | −4, −5 | s4 better |
| s5 vs legacy | −20, −20 | −4, −5 | s5 better |

**s3, s4 and s5 each meet DEC-026 in both jobs; s3 = s4 rank first; s5 ranks below s4.** The default is not changed.

#### UAT (monitoring only), by the route legacy took for the same question

Correct – false refusal – false answer – wrong. Legacy is 98–1–0–1 or 100–0–0–0 in each of the six jobs (route split 75/25 or 76/24) and changes on 0-2 questions between jobs.

| Config | Job | All | Legacy deterministic route | Legacy LLM route |
|---|---|---|---|---|
| s3 | a (43914538373) | 50–37–1–12 | 39–27–0–9 | 11–10–1–3 |
| s3 | b (43914654247) | 55–35–1–9 | 43–26–0–7 | 12–9–1–2 |
| s4 | a (43914553130) | 51–39–1–9 | 40–30–0–6 | 11–9–1–3 |
| s4 | b (43914668424) | 51–39–0–10 | 38–30–0–8 | 13–9–0–2 |
| s5 | a (43914568334) | 34–59–0–7 | 23–47–0–5 | 11–12–0–2 |
| s5 | b (43914681662) | 34–62–0–4 | 23–49–0–3 | 11–13–0–1 |

| Per job a, b | s3 | s4 | s5 |
|---|---|---|---|
| Right number, wrong subject | 7, 6 | 8, 6 | 5, 3 |
| Other wrong answers | 5, 3 | 1, 4 | 2, 1 |
| Supported but off topic (refuse items answered) | 1, 1 | 1, 0 | 0, 0 |
| Questions ended by s4 (claim not bound) | – | 4, 4 | 5, 6 |
| Questions ended by the relevance check | 2, 3 | 2, 3 | 25, 27 |
| First drafts with a valid marker (of 100) | 84, 85 | 84, 83 | 83, 85 |
| Mean LLM drafts per question | 1.19, 1.15 | 1.18, 1.19 | 1.13, 1.12 |
| Questions that change between the two jobs | 11 | 10 | 9 |

- **s4 does not catch the wrong-subject answers.** Every UAT wrong answer whose numbers are all in the cited excerpts (8 and 6) passed s4's check: the check found each value in a unit naming a subject word. The 4 questions s4 ended per job were answered correctly by s3 in the same round in 7 of 8 cases, and 6 of the 8 dropped drafts are word for word drafts s3 also produced; one (round b) was a refuse item that s3 had answered, which s4 refused correctly.
- **s5's threshold does not carry over to UAT.** The cross-encoder dropped 25 and 28 UAT claims (scores −9.53 to −4.29, median about −5.6; kept claims have a median of about −1.3), and every one of those questions ended as a false refusal. 12 and 17 of them were answered correctly by s3 in the same round, 5 and 3 wrongly. On the dev sets the only claim below −4.2 is FR2-F04's (−8.11, both jobs); the UAT questions (longer, often first person) score lower.
- s5's lower wrong counts (7 and 4) come with 20-23 fewer correct answers than s4.
- **Runs in different jobs differ** by 9-11 UAT questions for each simple configuration (legacy 0-2), as in s1-s3.

#### Cost of s5

- Median latency per question, s5 against s4 of the same job, dev sets: −1.4 s to +0.12 s (median −0.1 s). The cross-encoder (about 38 ms per claim measured locally) is below the LLM's variation. On UAT s5 is faster (25.1 and 42.2 s against 74.1 and 74.8 s) because a quarter of the questions end before a retry.
- Runner peak memory while s5 ran, against s4 of the same job: +318 to +394 MB in 8 of 10 dev jobs (median +344 MB), +936 and −26 MB in the two RBAC jobs; UAT +343 and +576 MB (different jobs). The model loaded in every s5 job (only deprecation warnings in the logs, no timeout).

#### Summary (for the owner; nothing is switched on)

- **s4 = s3 on the dev sets** (no item changes) and does not reduce the UAT wrong-subject answers (8 and 6 against 7 and 6); on UAT it ends 4 questions per job, mostly correct ones. The wrong-subject risk is not handled by s4.
- **s5 is worse than s4 on the dev sets under DEC-027** (one more false refusal in both jobs), and its dev-calibrated threshold refuses 25-27 UAT questions per job. The calibration rule missed drafts that the relevance check ends before another check would have retried them.
- **s3 (= s4) meets DEC-026 in both jobs and wins against legacy under DEC-027**, as in s1-s3. Per the owner's rule it stays a candidate: `natural_dev_v1` is not measured yet (gold waiting for approval) and the wrong-subject risk is still open.

#### Owner decision (2026-11-17)

**s4 and s5 are dropped; s3 is the only candidate.** Their code stays behind `RAG_SIMPLE_SUBJECT_BINDING_ENABLED` and `RAG_SIMPLE_CLAIM_CROSS_ENCODER_ENABLED` (off) and is not measured further. The conclusion stands as recorded above: s4 changes no dev item and catches no UAT wrong-subject answer; s5 loses a dev item in both jobs and refuses a quarter of UAT.

## s3 on `natural_dev_v1` (owner decision 2026-11-17)

The owner approved the gold (ND-002, ND-008, ND-011, ND-014 as decided, the other 16 as drafted) and kept all 11 items flagged for overlap. Gold locked in `tests/acceptance/natural_dev_v1_gold.lock` (sha256 `0e942996…`, approved by "owner (NQThai-7803)") before any run on the set.

### Measurement plan (written before measuring, DEC-026, DEC-027)

- **Set:** `natural_dev_v1`, 20 questions as `staff` over corpus V2 (`eval.yml` `set=natural`, `scripts/eval/run_natural_dev.py`), one session per question.
- **Configurations:** `legacy`; `s3` = `EVAL_ABLATION=simple_trace,EVAL_SIMPLE_LEVEL=3`. **Two separate jobs, each with its own `legacy`, 1 run per configuration** (DEC-027).
- **Proxy grade** (`tests/acceptance/natural_dev_v1_proxy.yaml`, written from the locked gold before the run): leak = a citation of `UAT-GROUNDING-001` or a forbidden value; an ANSWERED item is correct when it answers, cites a gold or acceptable document, states every fact group of its keys and hits no `wrong` form; an ANSWERED_LIMITED item must also say what the documents do not state, and is a false answer (over-claim) without that, or wrong when a `wrong` form shows. Categories as on the other dev sets: correct – false refusal – false answer – wrong.
- **Report:** per job and configuration: correct – false refusal – false answer – wrong, leaks; split near UAT (7 items: e5 to the nearest Q001-Q100 ≥ 0.90, the held-out v2 rule: ND-001, 004, 005, 006, 008, 012, 013) / the rest (13); changes between the two jobs; every s3 answer with a value of the wrong subject, read one by one against the gold (the proxy cannot see a subject). Where a reading of an answer disagrees with the proxy, both are reported; the proxy is not edited after the run.
- **Rule:** DEC-026 with `natural_dev_v1` first (leaks = 0; dev false answers + wrong not above legacy; then fewer false refusals on `natural_dev_v1`), and DEC-027 across the two jobs. The other dev sets are as measured in "Results of s4-s5" (s3 meets DEC-026 there). **The default is not changed in this step.**
