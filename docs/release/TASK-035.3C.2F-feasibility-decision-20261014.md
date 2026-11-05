# TASK-035.3C.2F — production feasibility and design decision

Date: 2026-10-14. **TASK-035.3C.2F COMPLETED as bounded research. NO SAFE MECHANISM SELECTED.** TASK-035.3C.2 source correction is not ready. TASK-035 remains IN PROGRESS; the frozen TASK-035.3B candidate remains FAILED/preserved; RC sign-off is NOT GRANTED. The accepted isolated UAT Corpus v2 H5.2 baseline is not superseded.

## Decision

Explicit question obligations remain a plausible *problem decomposition*, not a validated production mechanism. The new [specification](TASK-035.3C.2F-question-obligation-spec-20261014.md), [gold review](TASK-035.3C.2F-gold-label-review-20261014.md), [manifest](../../artifacts/task-035-3c2f-20261014/synthetic-manifest.json), and [one-shot results](TASK-035.3C.2F-experimental-results-20261014.md) show a material reduction in unsafe accepts only at the cost of **10/10 final false abstentions**, with two unsafe automatic accepts (a reversed Vietnamese prohibition and a wrong-benefit amount). The conservative validator intersection retains one unsafe benefit-binding accept and still rejects 10/10 valid final answers. The extractor misses 3/3 genuine source-authority conflicts across development and final test. The oracle obligation diagnostic also rejects 10/10 final positives at its development-selected threshold, so improving extraction alone cannot rescue this coverage operator. This is not a safe balance or a production correction.

The current validator's known nonresponsive-verbatim defect is independently reproduced on fresh synthetic cases (11/14 final unsafe accepts), but this research did not identify a safe replacement. The earlier 2E holistic judge failed condition/negation/conflict controls; this question/evidence-only extraction-plus-coverage prototype has different observed failures. Neither result is release acceptance. No final-test prompt or threshold was retuned. No benchmark or policy literal was placed in production code.

## Production feasibility gaps

1. **Extraction truthfulness and implied conditions.** Natural policy prose led the local extractor to invent signature/approval exceptions, produce unrelated-language fragments, misclassify relevant evidence, and miss actual conflicts. Structured JSON validity (36/36) did not protect semantics. An extractor cannot itself be policy authority.
2. **Coverage and entailment.** Cosine scores cannot distinguish prohibition polarity, amount-to-benefit binding, or omitted conditions reliably. Oracle-obligation scoring shows the coverage stage rejects all valid bilingual paraphrases at the safety-weighted threshold. A `SUPPORTED` citation is likewise not a responsiveness verdict.
3. **Authorization and citations.** Experimental input scoping excludes synthetic restricted evidence. It does not verify production RBAC, citation registry validity, materiality, generation repair, or final answer persistence. A future integration must preserve scoped retrieval and zero-citation NO_ANSWER behavior, with no inaccessible source in evaluator prompts/logs.
4. **Unresolved authority.** The model did not detect any actual conflict in this set. A low score happened to block the unqualified assertions but did not identify the reason or support a safe policy decision. Metadata or human authority, not model confidence, is needed to resolve genuine conflicts.
5. **Operational cost/failure.** Extractor median was ~2.0 seconds per case, nearest-rank p95 ~11.23 seconds, max ~13.46 seconds, before application generation/retrieval and excluding E5 cold load. A 35-second timeout, model unavailability, malformed JSON or semantic uncertainty must fail closed; that can further raise false abstention. No production latency budget, contention, timeout tail, resource safety, or rollback plan is qualified.
6. **Evidence quality.** Synthetic 24-case final test was unseen for this one-shot method, but authored by one reviewer and partly paired/correlated. It is not independently adjudicated, statistically representative, or a substitute for V2 candidate broad acceptance. Owner-approved false-acceptance, false-abstention, latency, invalid-output and permission criteria are still missing.

## What would justify a future source correction

Do not implement this prototype or rebuild the frozen candidate. A separately authorized research/engineering proposal should obtain independent bilingual gold review with explicit obligation-to-source mappings and authority metadata; predeclare risk-weighted thresholds; test a relation/entailment mechanism capable of polarity, condition, value and actor binding (any new model/dependency/download needs separate approval); and confirm on another genuinely fresh, untouched set without answer/fixture hardcoding. It must accept essential EN/VI/mixed positive paraphrases and multi-document cases while rejecting every high-risk negative and identifying unresolved conflicts as such. Before any production edit, characterize timeout/unavailability privacy and performance behavior. If evidence then supports a narrow generic fix, seek source-level authorization and run targeted RAG/RBAC/citation/NO_ANSWER/repair tests, then a new same-source isolated API/worker candidate and V2 qualification under the release plan. The failed candidate stays failed; the historical 98/98 does not transfer.

## Protected baseline at this checkpoint

No production Python file was edited. Read-only SHA-256 comparisons match the 035.3C.2E checkpoint for `claim_evidence_validation_service.py`, `grounded_answer_service.py`, `question_analysis.py`, `context_builder.py`, `reranker.py`, and `citations/evidence.py`. A read-only Docker listing showed accepted V2 API/worker/PostgreSQL/Redis up and healthy under the same observed container ID prefixes (`9d510d8b8027`, `2afc4af27fe5`, `1a5a658a2ef2`, `db2961fc9413`). This phase did **not** recheck live/readiness HTTP, database counts, grants, Celery accounting, or broad RAG gates; those prior baselines are not newly certified by this experiment. No stopped candidate was restarted. No protected PostgreSQL/Redis or corpus write occurred.

| Decision field | Result |
| --- | --- |
| TASK-035.3C.2F | COMPLETED for bounded offline experimental scope |
| Selected mechanism / selection confidence | **NONE / INSUFFICIENT** |
| Ready for source correction / new candidate | **NO / NO** |
| Production code changed / new image built | **NO / NO** |
| TASK-035 | **IN PROGRESS** |
| RC sign-off | **NOT GRANTED** |
