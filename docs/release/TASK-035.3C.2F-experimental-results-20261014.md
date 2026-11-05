# TASK-035.3C.2F — independent synthetic experimental results

Date: 2026-10-14. **One-shot final-test result; not a release gate.** The frozen [36-case manifest](../../artifacts/task-035-3c2f-20261014/synthetic-manifest.json) SHA-256 is `e58b81b46df6cc9cc1f18b9a68484957974a951e9c60377946b841d076156a13`. Machine-readable [per-case results](../../artifacts/task-035-3c2f-20261014/results.json) SHA-256 is `de103142268b3a14a070d22a629824a458e592a82c2fccec5f9b9e435deb1633`. The previous 2E held-out pilot was not reused. This new final-test split was inspected only after method/manifest freeze; no threshold, prompt, answer, or gold label was revised using it.

## Common-case comparisons

Development: 12 cases, four ACCEPT/seven REJECT/one UNCERTAIN. Final test: 24 cases, ten ACCEPT/twelve REJECT/two UNCERTAIN; eight cases each EN/VI/MIXED. “False acceptance” counts ACCEPT on any REJECT or UNCERTAIN gold. “False abstention” counts any non-ACCEPT on an ACCEPT gold. “Correct rejection” below means a safe non-ACCEPT on a REJECT gold; exact three-way separately distinguishes REJECT from UNCERTAIN.

| Method | Final correct accepts / 10 | Final false accepts / 14 non-ACCEPT | Final false abstentions / 10 | Final safe non-accepts / 12 REJECT | Gold conflicts correctly UNCERTAIN / 2 | Exact 3-way / 24 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Existing validator | 7 | 11 | 3 | 3 | 0 | 10 |
| Oracle obligation cosine (nondeployable reference) | 0 | 0 | 10 | 12 | 0 | 12 |
| Automatic extraction + per-obligation E5 | 0 | 2 | 10 | 10 | 0 | 7 |
| Existing AND automatic | 0 | 1 | 10 | 11 | 0 | 9 |

The development-only cost rule selected automatic cosine cutoff `0.898772` and oracle cutoff `0.945443`. The four valid development automatic scores were `0.777202–0.855171`, while an omitted-condition negative was `0.897772`; at the safety-weighted cutoff **all four valid development answers were rejected**. The author-written (oracle) obligations also yielded zero accepted development positives and zero accepted final positives at its development cutoff. This is evidence that minimum per-obligation cosine is not a reliable entailment/coverage operator, not merely that extraction needs improvement. It is not a calibrated confidence or policy authority signal.

| Language (final n=8 each) | Existing correct accept / false accept / false abstain | Automatic correct accept / false accept / false abstain | Hybrid correct accept / false accept / false abstain |
| --- | --- | --- | --- |
| English | 3 / 5 / 0 | 0 / 0 / 3 | 0 / 0 / 3 |
| Vietnamese | 2 / 4 / 1 | 0 / 2 / 3 | 0 / 1 / 3 |
| Mixed | 2 / 2 / 2 | 0 / 0 / 4 | 0 / 0 / 4 |

## Hard negatives and positive controls

| Required control | Final IDs | Existing | Automatic | Interpretation |
| --- | --- | --- | --- | --- |
| Cited unrelated answer | F-T02, F-T10 | both unsafe ACCEPT | both UNCERTAIN | No false accept, but extractor hallucinated conflict instead of simply identifying irrelevant evidence. |
| Same-topic wrong action | F-T03, F-T21 | both unsafe ACCEPT | both REJECT | Correct non-accept, though blanket high cutoff also rejects all positives. |
| Correct amount, wrong benefit | F-T04, F-T14 | both unsafe ACCEPT | REJECT, **unsafe ACCEPT** | F-T14 survives the hybrid too; value binding remains unsafe. |
| Omitted mandatory condition | F-T06, F-T13 | both unsafe ACCEPT | both REJECT | No proof of condition sensitivity because matched positives F-T05/T12 are also rejected. |
| Reversed prohibition | F-T11, F-T19 | both REJECT | **unsafe ACCEPT**, REJECT | Vietnamese F-T11 crosses the cosine cutoff despite opposite polarity; hybrid blocks only because baseline rejects. |
| Unresolved authority | F-T07, F-T15 | both unsafe ACCEPT | both REJECT, neither marked conflict | Non-accept is incidental low score, not correct authority reasoning. |
| Restricted fact, visible distractor | F-T18 | REJECT | UNCERTAIN | Restricted field never entered model/registry. This is only synthetic input scoping, not a production RBAC proof. |
| Positive EN paraphrase/condition/multi-doc | F-T01/05/08 | all ACCEPT | all REJECT | All three false abstentions. |
| Positive VI paraphrase/condition/multi-doc | F-T09/12/16 | T12/T16 ACCEPT | all REJECT | All three false abstentions. |
| Positive mixed paraphrase/multi-doc/condition/low-overlap | F-T17/20/22/24 | T20/T22 ACCEPT | all REJECT | All four false abstentions. |

The automatic method's only final false accepts were F-T11 (prohibition reversal) and F-T14 (wrong benefit amount). The hybrid retained F-T14. The baseline's 11 final unsafe accepts were F-T02/03/04/06/07/10/13/14/15/21/23. The 10 valid final answers rejected by automatic extraction/coverage were F-T01/05/08/09/12/16/17/20/22/24. No final positive paraphrase or two-document answer was accepted by that method.

## Extraction, coverage, failure, and latency observations

The extractor returned syntactically valid JSON in 36/36 local calls and no transport timeout was observed under a 35-second per-call timeout. Syntax success did not mean semantic validity. It marked **none** of the three gold authority conflicts (F-D11/F-T07/F-T15) as `unresolved_conflict`, while inventing a conflict for unrelated-evidence F-D02/F-T02/F-T10 and the restricted-evidence F-T18. It invented obligations absent from evidence: supervisor signature for F-T05, end-user approval and refusal right for F-T09, and unsupported “no exceptions” / “no other actions” clauses elsewhere. F-T10/F-T15 produced Chinese-language fragments for Vietnamese input; F-D08 produced unrelated Indonesian fragments. It also marked relevant positive evidence irrelevant for F-T20/F-T22/F-T24. These are extraction/semantic errors, not malformed-output exceptions. It saw only question and authorized evidence, not answer, label, restricted evidence, or private V2 text.

Answer coverage was measured as the minimum E5 cosine of obligation-to-answer. This accepted F-T11's opposite polarity and F-T14's amount attached to the wrong benefit, demonstrating semantic overmatching. The oracle-obligation diagnostic eliminated false acceptance only by rejecting every valid answer, including low-overlap translations and two-document answers. A single global cutoff at this granularity is no safer than the prior whole-answer score as a production gate.

Observed per-case latency: existing validator p50 `0.679 ms`, max `5.763 ms`; Qwen extraction p50 `2,006.169 ms`, p95 nearest-rank `11,230.897 ms`, max `13,463.025 ms`, sum `94.423 s` across 36 sequential calls; warm E5 scoring p50 `142.407 ms`, p95 nearest-rank `265.485 ms`, max `697.911 ms`, sum `5.971 s`. E5 model initialization/cold start is **excluded** from per-case scoring; the previous 2E run reported roughly 80 seconds in its environment, but no precise cold-start measurement was made here. No production contention, p95 SLO, or evaluator failover was tested. Unit tests confirm malformed extraction maps to UNCERTAIN and conflict flags prevent acceptance; they do not establish that the model detects real conflicts. A timeout/transport exception is also coded to yield UNCERTAIN, but no real timeout occurred in these 36 calls. No external transmission or download occurred.

## Result integrity and scope

The [harness](../../scripts/release/task0353c2f_eval.py) and [focused tests](../../tests/unit/test_task0353c2f_eval_harness.py) are experimental paths. After the one-shot run, the identical question+authorized-evidence payload construction was extracted into a helper solely to test restricted-field exclusion; no model prompt, threshold, decision rule, manifest, or result was changed and the final set was not rerun. The harness uses the prior synthetic registry baseline and performs no Docker, database, Redis, API, document, or corpus writes. It stores case IDs, decisions, extracted synthetic propositions, scores and latency; all text is invented. The one author-provided gold set and 24 correlated final cases are insufficient for statistical safety claims. The frozen prior H5.2 98/98 acceptance remains a separate historical baseline, not validation of this research prototype.
