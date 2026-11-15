# Simple answer mode (`RAG_ANSWER_MODE`)

Started 2026-11-15, owner prompt "GIAI ĐOẠN MỚI — Simple answer mode, nhắm vào từ chối sai và trả lời lạc đề". Selection rule: DEC-026. Default stays `legacy`.

## Why

On new questions about 53% of the answers are false refusals, caused by the stack of hand-written checks. This is the only conclusion taken from held-out v1/v2; no held-out item was used to design this mode.

## What `simple` does

1. **Retrieval:** the same hybrid retrieval as legacy (semantic + keyword + fusion, with the permission filter in SQL). The first 5 chunks in hybrid order, at most 2 from one document. No subqueries, supplements, reranking cut, low-alignment filter or excerpt: each chunk goes in whole.
2. **One prompt** (`build_simple_grounded_prompt`). The system message holds only the rules, never retrieved text. The rules:
   - answer only from the sources and invent nothing;
   - end each sentence that uses a source with its `[SOURCE_n]` marker;
   - say "Tài liệu không đề cập …" (or "The documents do not mention …") for a part the sources do not hold;
   - reply with the no-answer sentinel when no part is answered;
   - answer in the question's language.

   The answer is plain text, not JSON.
3. **Checks, and only these:**
   - the citation markers are valid and the cited chunks are still permitted (`CitationValidationService.validate_and_map`);
   - claim validation (`ClaimEvidenceValidationService.validate`) against the cited sources, with number/unit normalization forced on for this call (`number_normalization()`). A sentence with no marker that says the documents do not mention something states an absence, not a claim, so it is not validated: a partial answer is checked on its stated part. A sentence with a marker is always validated.
4. **One retry:** a missing marker, an unknown marker or an unsupported claim is retried once, with the specific reason and the rejected answer marked as not evidence. A second failure gives the fixed NO_ANSWER. The sentinel, an answer that only states absences, and a permission failure give NO_ANSWER at once, with no retry.
5. **Skipped in `simple`:** the deterministic route, the low-alignment filter, the completeness checks (c1/c3, D2), the responsiveness check, terminal blocks, compound partial and every repair after the LLM. Legacy code is unchanged.

`simple_det` is `simple` plus the strict deterministic route (`_structured_value_answer_draft`) as a fast path, tried before the LLM on the same 5 sources.

### Counters (`/metrics`, `enterprise_ai_rag_answer_branch_total`)

| Counter | Meaning |
|---|---|
| `simple_retry` | the one retry was used |
| `simple_deterministic` | `simple_det` answered on the deterministic fast path |
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
