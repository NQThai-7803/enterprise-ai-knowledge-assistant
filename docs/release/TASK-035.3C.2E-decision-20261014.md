# TASK-035.3C.2E — evaluation decision and privacy/failure review

Date: 2026-10-14 (Asia/Saigon). **TASK-035.3C.2E COMPLETED for bounded offline research. Recommendation: NO SAFE MECHANISM SELECTED.** This does not authorize or implement a source-level correction. TASK-035.3C.2 remains PARTIAL/BLOCKED, TASK-035 remains IN PROGRESS, the frozen TASK-035.3B candidate remains FAILED, and RC sign-off is NOT GRANTED.

## Decision evidence

The 36-case synthetic manifest and 12/24 development/held-out split were frozen before model runs. On the common 24-case *pilot held-out* set, the existing validator had 7/14 unsafe ACCEPTs and 5/10 false abstentions; local E5 similarity had 2/14 unsafe ACCEPTs and 10/10 false abstentions; the initial constrained Qwen judge had 0 unsafe ACCEPTs but 10/10 false abstentions and 2/24 malformed outputs. All failed to classify the two unresolved authority conflicts correctly. Full confusion matrices, language breakdown, category examples, p50/p95/max latency, token counts, local resource observations, hybrid combinations, result hashes and method limitations are in [comparative metrics](../../artifacts/task-035-3c2e-20261014/comparative-metrics.md).

The pilot judge prompt incorrectly drove `complete_conditions=false` for valid unconditional answers. A development-only clarification defaulted to UNCERTAIN (0/4 positive acceptance, 9/12 uncertain). A schema-constrained third rubric recovered all four development positives but falsely ACCEPTed three high-risk cases: an omitted mandatory condition (D04), Vietnamese prohibition reversal (D06), and contradictory authority without precedence (D12). The third rubric repeated the same 12/12 decisions at fixed seed and temperature, **including** all three unsafe errors. No blind performance is claimed for that revised rubric: the original 24 held-out cases were already exposed, and the revised rubric failed development safety before a new confirmatory hold-out was justified.

The configured cross-encoder reranker was not loaded because weights are absent from the inspected host and active V2 model caches, and downloads are outside authorization; the stopped candidate's protected cache was not mounted for this check. The cached multilingual E5 model is an encoder for retrieval, not a relation/entailment classifier; development threshold `0.913549` rejected all four development positives and did not eliminate held-out false accepts. Its wrong-signatory/negation scores overlapped valid paraphrase scores, so neither one global cutoff nor a relative normalized reranker zero has a demonstrated safe operating point. The existing `analyze_question` expresses output type and selected value/time/person flags but not a general bilingual subject–action–object–condition–authority representation. A new hand-built synonym/ontology layer based on this small corpus would be an unqualified expansion and risks benchmark-like shortcuts.

Conservative A AND B had 2/14 false acceptance **and** 10/10 false abstention on the pilot held-out set. A AND initial judge accepted no answers. A OR B inherited A's 7/14 unsafe acceptance. No measured staged hybrid improves both safety and usefulness. One positive prompt-injection control (H23) was rejected by each pilot method, but that is not injection robustness proof. The synthetic permission case only proves that the research harness excluded its restricted source text; it does not replace production RBAC testing.

## Privacy and failure-mode assessment

| Situation | Observed research behavior | Required production safety if a future evaluator is approved |
| --- | --- | --- |
| Missing authorized evidence | A/B reject; C pilot rejected the checked cases. The harness never includes the `restricted_evidence` field in model payloads. | No answering citation or evaluator prompt may use inaccessible source; final NO_ANSWER must have zero citations. |
| Model unavailable / local cache incomplete | BGE cross-encoder weights absent, so not loaded/downloaded. Harness checks Qwen installation before calling. | A missing evaluator must not silently turn an unsupported answer into ANSWERED; use explicit safe failure/NO_ANSWER and telemetry without source text. |
| Timeout | 0 observed C timeouts under 75 seconds; fake transport timeout unit test returned UNCERTAIN. | Enforce a release-approved budget and fail closed. Uncertainty may cause false abstention; measure it. |
| Malformed structured output | Initial C pilot 2/36 invalid outputs; parser mapped them to UNCERTAIN. Third development rubric 0/24 invalid across run/repeat. | Reject/abstain on malformed output; valid JSON alone is not semantic correctness. |
| Ambiguous or conflicting authority | A/B falsely accepted conflict examples; third C rubric falsely accepted D12. | Do not invent supersession; abstain or require authoritative metadata/human decision. |
| Unsupported or wrong relation | A false accepted grounded unrelated clauses; B accepted a wrong signatory; C third rubric accepted omitted condition and negation reversal. | Entailment, responsiveness, completeness and polarity must be separately satisfied before ANSWERED. |
| Unexpected language or paraphrase | A false abstained most held-out mixed-language positives; B/C pilot abstained all. | Qualify language coverage and uncertainty behavior; do not substitute lexical overlap for semantics. |
| Prompt injection in source | H23 was rejected in pilot, but this single test is insufficient. | Treat evidence as data, never instructions; separately test adversarial multilingual injections. |
| External/privacy exposure | **None in this experiment.** All model calls went to localhost with invented text and only authorized-evidence arrays. | Any future external judge requires separate provider/privacy approval. A proposed final answer itself may repeat sensitive text, even when restricted source text is excluded. |
| Logging | Harness outputs IDs, scores/dimensions, latency and usage, not raw prompts/evidence. Manifest holds only synthetic text. | Never log raw private documents, credentials, full prompts, or sensitive user content. |
| Excessive latency/resource pressure | Initial C cold call 15.87 s; held-out warm p95 1.25 s. E5 cold initialization was roughly 80 s on this host; warm held-out p95 111 ms. Local Qwen occupied ~2.1 GB GPU; approximately 0.9 GB free RAM was observed during evaluation. | Establish an actual performance budget and contention test before any production call; ensure timeouts/OOM cannot bypass safety. |

No PostgreSQL/Redis write, corpus read for model input, external model download, API/worker build, stopped-candidate restart, or active V2 recreation occurred. After inference, active V2 API live/ready remained HTTP 200; API, worker, PostgreSQL and Redis were healthy with the same container identities, restart count 0 and OOM false. The frozen candidate API/worker identities remained exited. The original H5.2 data-integrity claim rests on the prior TASK-035.3C.1 143-chunk/source-hash rebaseline; this phase checked runtime identity and health, not another full database scan. Historical Celery accounting remains UNKNOWN.

## Next evidence gate and recommendation

**NO SAFE MECHANISM SELECTED; mechanism-selection confidence INSUFFICIENT.** Do not integrate A, B, the Qwen rubric, or their measured hybrids into production. Do not build a new candidate from unchanged source and claim the defect fixed. The next defensible research step would require owner approval to obtain or use a locally isolated multilingual entailment/claim-verification model (or a materially different, tightly scoped structured-relation architecture), together with a larger independently adjudicated English/Vietnamese/mixed corpus and a genuinely fresh held-out set. Any model download/new dependency, additional production LLM call, provider privacy change, or revised release contract needs its own approval. Define acceptable false-acceptance, false-abstention, latency, invalid-output and timeout criteria with the owner before source integration; the engineering criteria in the [evaluation design](TASK-035.3C.2E-evaluation-design-20261014.md) are proposals, not approved thresholds.

If later evidence supports a correction, the existing question-aware claim/final-answer boundary remains the likely integration point. Preserve RBAC-filtered evidence and citation materiality, validate repaired final claims, and then run multilingual positive/negative, permission, NO_ANSWER, citation, compound-answer and representative H5.2 unit gates. Only after source-level correction is separately authorized and passes those gates should a **new** reviewed source snapshot, same-source API/worker images and isolated V2 broad requalification be considered. The failed frozen candidate must remain failed and preserved; historical 98/98 does not transfer to new images.

## Final checkpoint fields

| Field | Result |
| --- | --- |
| TASK-035.3C.2E | **COMPLETED** as bounded offline research |
| EVALUATION CASES / HELD-OUT CASES | 36 synthetic total; 12 development / 24 initial held-out pilot, 8 EN / 8 VI / 8 MIXED held-out |
| APPROACH A | Existing claim validator: 7/14 held-out unsafe accepts, 5/10 false abstentions |
| APPROACH B | Local E5 similarity: 2/14 unsafe accepts, 10/10 false abstentions; BGE reranker weights unavailable locally |
| APPROACH C | Initial judge pilot 0 unsafe accepts but 10/10 false abstentions; revised Boolean rubric 3/8 unsafe accepts on development, no fresh held-out run |
| HYBRID APPROACH | No measured combination improved both safety and usefulness |
| ENGLISH / VIETNAMESE / MIXED PERFORMANCE | Separate held-out counts in comparative metrics; mixed-language positives especially prone to false abstention |
| MULTI-DOCUMENT PERFORMANCE | A 2/3 positives, B/C pilot 0/3 on held-out H04/H14/H21 |
| LATENCY / TIMEOUT / FAILURE | Measured in comparative metrics; 0 observed timeouts, 2/36 initial judge invalid outputs; synthetic timeout safely UNCERTAIN |
| PRIVACY | Synthetic authorized evidence to localhost only; no external/private source transmission |
| RECOMMENDED MECHANISM | **NO SAFE MECHANISM SELECTED** |
| MECHANISM SELECTION CONFIDENCE | **INSUFFICIENT** |
| PRODUCTION IMPLEMENTATION | **NOT STARTED** |
| ORIGINAL H5.2 BASELINE | **INTACT for checked runtime identity/health and prior data fingerprints**, not newly broad-requalified |
| FAILED FROZEN CANDIDATE | **PRESERVED**, database integrity still not verified after exit 255 |
| READY FOR SOURCE-LEVEL CORRECTION | **NO** |
| READY FOR NEW CANDIDATE BUILD | **NO** |
| TASK-035 | **IN PROGRESS** |
| RC SIGN-OFF | **NOT GRANTED** |
