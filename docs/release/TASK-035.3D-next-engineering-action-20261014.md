# TASK-035.3D — recommended next engineering action

Date: 2026-10-14. **Recommendation A: narrowly scoped, evidence-backed context-admission remediation investigation.** This is a future-action charter, **not** authorization to execute it in TASK-035.3D. Current release strategy remains RC NO-GO. The 2E/2F holistic judging, embedding cutoff and obligation-extraction prototypes are not selected and must not be retuned on exposed pilot/final cases.

## Strict question

Can the first observed incorrect progression—admitting only unrelated, permission-visible chunks as answer evidence—be prevented by a *generic, demonstrable* context-admission rule while preserving relevant authorized evidence, multilingual paraphrases, mixed-language queries and multi-document support? This is distinct from proving final answer responsiveness. The independent verbatim-`SUPPORTED` defect remains a separate necessary safety boundary even if context admission improves.

## Prerequisites and evidence collection

1. Product/release owner confirms the intended Q&A scope and security owner confirms diagnostic handling of private-source identifiers. Existing saved captures may be read; no private content is sent outside the approved local environment. If the old stopped candidate must be started to inspect its database, obtain **separate** startup approval. Do not assume it is healthy or replay Celery tasks.
2. Freeze current source/image/corpus/evidence identities. Preserve the accepted V2 stack and all failed-candidate resources. Use static source trace and fake-only, invented-policy fixtures first. Do not query or mutate active V2, run a broad benchmark, build an image, or alter a database in this investigation.
3. Reconstruct the relevant *decision boundaries*: permission-filtered semantic and keyword candidate lists; raw per-channel scores; fusion ranks; raw and normalized reranker components; any supplemental/adjacent hit expansion; final context ordering/excerpts and source registry; generation draft/retry/repair; claim/citation statuses; final response. Where the original trace lacks raw values, mark UNKNOWN and use clearly labeled synthetic controls rather than inventing them.
4. Include paired controls: inaccessible relevant private evidence plus unrelated visible evidence must produce no answering context/NO_ANSWER; granted user must retain material answer; relevant singleton with normalized zero must **not** be blindly dropped; English, Vietnamese, mixed and low-literal-overlap relevant clauses survive; unrelated same-topic wrong-action/value/negation clauses do not become answer evidence; two distinct documents jointly supply needed conditions; no unauthorized/non-READY source enters context.

## Evidence gate before any implementation proposal

The investigation may propose a smallest generic change only if it identifies a specific origin boundary, demonstrates the proposed decision on both negative and matched positive controls, explains source-score semantics without a global `reranker_score==0` shortcut, and shows how final-answer validation remains a separate guard. Record false accepts **and** false abstentions and all unknown boundaries. A written design must include impact on RBAC, READY, citation materiality, structured/repair paths, latency and rollback. No benchmark IDs, expected answer literals or document-specific exceptions may enter production logic.

If raw evidence cannot distinguish relevant from irrelevant in the proposed boundary, if positives collapse, if a condition/negation/conflict gap remains unaddressed, or if the mechanism requires unapproved model/dependency/privacy changes, **stop with no code correction**. Do not turn the investigation into another open-ended similarity/threshold/prompt experiment.

## Authorization and later gates

This 035.3D task authorizes only decision documentation. A separate explicit request is needed to execute even this bounded investigation if it requires new runtime probing or persistent evidence capture. A later **production correction** needs its own authorization and must begin with focused fake-only and isolated permission/RAG/citation/NO_ANSWER/EN/VI/mixed/multi-document tests, then Ruff/format/compile/security checks. Any new same-source API/worker images and isolated V2 restore/broad acceptance require distinct build/runtime authorization. Preserve the failed 035.3B candidate as FAILED; never promote it on the basis of diagnostic success. No exact numeric release threshold is approved by this charter.
