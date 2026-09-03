# CODEX START HERE

## CURRENT HANDOFF -- 2026-08-21

This is the latest handoff and supersedes older 2026-08-19 RAG status text below.

### Current state

TASK-034.1.2 runtime RAG acceptance is complete for the agreed seven-case local UAT set. TASK-035 is not started.

Do not add question-specific runtime answers. The annual-leave 12 / 14 / 16 issue was resolved by restoring intended corpus evidence and reprocessing it through normal ingestion, not by changing RAG logic or directly editing `document_chunks`.

### Corpus action performed

- Restored soft-deleted document `43cb2c93-52bc-44f6-8e03-1b1f075e1d89`, title `Chính sách nghỉ của người lao động`, storage key `documents/2026/08/951776f4-88c3-4c98-8401-c8ce5edad268.pdf`, checksum `24178db420422e474326986672b6c15cc67373ee6adbe1489ba5e8addf95f4f4`.
- Provenance: uploaded by `admin.uat@example.test`, `ORGANIZATION` scope, HR leave-policy fixture in the local Nova Digital UAT corpus.
- Restore path: set `is_deleted=false`, reset to `UPLOADED`, and enqueued normal worker task `274fe326-9d28-421c-9c11-253ec7b74bc2`.
- Worker result: `READY`, `page_count=6`, `chunk_count=12`, `total_tokens=6458`, `embedding_dimensions=384`.
- Verified active clause chunk `4b341201-f0df-4102-b9f2-5ad7091781a6` on page `3` contains the authoritative `12 ngày`, `14 ngày`, and `16 ngày` distinctions.

### Architecture now in place

- Answer-bearing source quality: `app/retrieval/evidence_quality.py` ranks direct clauses/tables above sample-question or reference chunks.
- Focused evidence/citation repair: `app/citations/evidence.py`, `app/citations/pruning.py`, and citation mapping/persistence expose nullable `evidence_text`.
- YES/NO validation is subject/object-aware and supports corrected false premises.
- Relation entailment supports replacement/supplemental relations such as NovaCare vs mandatory BHYT.
- RBAC/access rules remain unchanged and citations still come from authorized retrieved chunks.

### Final runtime UAT

All seven new-chat runtime cases passed with claim validation `SUPPORTED`:

- Own salary: `Có`, salary policy pages 10-11.
- EAP: `Không`, benefits policy page 8.
- NovaCare vs BHYT: `Không`, benefits policy page 4.
- Engineering Manager: `N5`, `42 - 70 triệu đồng`, salary table page 4.
- Head / Director: `N6`, `65 - 110 triệu đồng`, salary table page 4.
- Annual leave: starts `Không`, distinguishes `12 / 14 / 16`, cites the restored real active leave table page 3, no sample-question/test-question citation.
- CEO false premise: starts `Không`, corrects CEO to `Nguyễn Anh Khoa`, organization source page 6.

### Verification counts

```text
python -m pytest tests\unit\test_grounded_answer_service.py -q
75 passed in 1.33s

focused RAG/citation suite
132 passed in 1.56s

combined RAG/citation/validation/output suite
157 passed in 1.71s

python -m pytest tests\unit -q
1061 passed in 8.22s

ruff check on 21 touched Python files
All checks passed!

ruff format --check on 21 touched Python files
21 files already formatted
```

### Remaining debt / recommended next task

Recommended next task: create an automated runtime UAT harness/report for the seven accepted cases, including citations, claim-validation diagnostics, latency, and sample-question citation rejection.

Known debt: replace the restored generic/template leave policy with canonical Nova-branded content; hydrate/cache the configured CrossEncoder reranker or explicitly bless alignment fallback; reduce 94s-186s runtime UAT latency; improve multi-row table `evidence_text`; remove sample-question/test-question sections from production corpus files.

## CURRENT MANUAL HANDOFF — 2026-08-19

This section is the latest handoff and takes precedence over older "current task" wording elsewhere in this file.

### Working mode

- The current work is being performed manually with ChatGPT guidance; Codex has NOT been used for these changes.
- When Codex is resumed later, it must inspect the real current files before editing and must not assume that an older task snapshot is still current.
- After every completed manual or Codex task, update at minimum `TASKS.md`, `PROJECT_STATUS.md`, and `CHANGELOG.md`, plus any affected design/spec/test document.

### Non-negotiable RAG rule

Regression/UAT questions are TEST INPUTS ONLY.

Do NOT implement runtime question-to-answer mappings, special-case answers, or hard-coded expected answers for the regression questions. Runtime answers must continue to come from permission-authorized retrieved document evidence.

The goal is to improve general capabilities:

```text
query understanding
-> hybrid retrieval
-> reranking
-> evidence selection
-> grounded generation
-> claim/citation validation
```

### Current manual implementation snapshot

Exact Evidence support has been implemented across backend persistence/API and is visible in the frontend citation UI:

- `app/citations/evidence.py`
- `app/citations/models.py`
- `app/citations/mapper.py`
- `app/models/message_citation.py`
- `app/repositories/message_citation_repository.py`
- `app/schemas/chat.py`
- `app/db/migrations/versions/cd124fa71c86_add_citation_evidence_text.py`
- `tests/unit/test_citation_mapping.py`
- `frontend/src/api/types.ts`
- `frontend/src/features/chat/ChatPage.tsx`

Verified behavior:

- exact evidence extraction focused suite reached `15 passed`;
- PostgreSQL persists nullable `message_citations.evidence_text`;
- API/session history returns `evidence_text`;
- real local example persisted `evidence_text = "180 người"`;
- historical citations remain compatible with `evidence_text = NULL`;
- original PDF/DOCX files are never modified by evidence highlighting.

Migration note:

- revision `cd124fa71c86` was initially created empty and was accidentally stamped as applied;
- it was corrected to add `message_citations.evidence_text` plus `ck_message_citations_evidence_text_not_blank`, stamped back to `20260803_0010`, and upgraded again;
- final DB/API verification confirmed persistence.

### Current in-progress work

Minimal Citation Selection is IMPLEMENTED + UNIT VERIFIED; LIVE RUNTIME VERIFICATION PENDING.

Desired general rule:

- same internal `document_id` + same normalized `evidence_text` => redundant evidence; keep the strongest citation;
- same document + different evidence => keep separate citations when they support different claims;
- do NOT deduplicate only by document ID;
- do NOT hide duplicate citations only in React; pruning must happen before public citation numbering.

Final focused test status:

```text
17 passed in 0.19s
```

Punctuation-whitespace cleanup after redundant marker removal is verified.

Before starting RAG Accuracy Hardening, run one live new-message runtime verification for same-document/same-evidence pruning. After that passes, inspect the real query-understanding, hybrid-retrieval, and reranking implementation before coding.

### Accuracy UAT finding

A manual cross-document Vietnamese UAT exposed several general RAG weaknesses even though the facts exist in the documents, including:

- retrieval misses for `Engineering Manager`, `Head`, Salary Review, post-timesheet-lock corrections, and probation benefits;
- wrong table-row selection for Sunday overtime and night overtime;
- semantic contradiction mistakes for own-salary access (`Có` vs `Không`);
- intent confusion such as employee sickness vs child sickness;
- workflow-role confusion such as policy approver vs leave-request approver.

These examples must be used as regression/UAT cases only. Fix retrieval/reranking/claim validation generally; never encode their answers into runtime lookup rules.

### Next sequence

1. Finish Minimal Citation Selection and make the focused citation-mapping suite fully green.
2. Add/verify general regression coverage for same-evidence pruning and multi-claim evidence preservation.
3. Start RAG Accuracy Hardening: query understanding, retrieval recall, reranking precision, table-row discrimination, and contradiction validation.
4. Continue UI-04B Document Viewer navigation only after citation/evidence quality is stable.


## Má»¥c Ä‘Ã­ch

TÃ i liá»‡u nÃ y lÃ  Ä‘iá»ƒm báº¯t Ä‘áº§u báº¯t buá»™c cho má»i phiÃªn lÃ m viá»‡c vá»›i Codex trong dá»± Ã¡n **Enterprise AI Knowledge Assistant**.

Codex pháº£i Ä‘á»c cÃ¡c tÃ i liá»‡u theo thá»© tá»± sau trÆ°á»›c khi sá»­a code:

1. `CODEX_START_HERE.md`
2. `README.md`
3. `PROJECT_OVERVIEW.md`
4. `PRODUCT_REQUIREMENTS.md`
5. `ARCHITECTURE.md`
6. `DATABASE_DESIGN.md`
7. `API_SPEC.md`
8. `SECURITY.md`
9. `RAG_DESIGN.md`
10. `CODING_STANDARDS.md`
11. `TESTING_STRATEGY.md`
12. `PROJECT_ROADMAP.md`
13. `PROJECT_STATUS.md`
14. `TASKS.md`

## Quy táº¯c báº¯t buá»™c cho Codex

- KhÃ´ng tá»± Ã½ thay Ä‘á»•i pháº¡m vi dá»± Ã¡n.
- KhÃ´ng tá»± thÃªm thÆ° viá»‡n náº¿u chÆ°a giáº£i thÃ­ch lÃ½ do.
- KhÃ´ng sá»­a nhiá»u module khÃ´ng liÃªn quan trong cÃ¹ng má»™t task.
- KhÃ´ng xÃ³a code Ä‘ang hoáº¡t Ä‘á»™ng chá»‰ Ä‘á»ƒ viáº¿t láº¡i theo sá»Ÿ thÃ­ch.
- KhÃ´ng lÆ°u secret, API key hoáº·c máº­t kháº©u vÃ o Git.
- KhÃ´ng bá» qua migration khi thay Ä‘á»•i database.
- KhÃ´ng cho AI truy xuáº¥t tÃ i liá»‡u mÃ  ngÆ°á»i dÃ¹ng khÃ´ng cÃ³ quyá»n xem.
- KhÃ´ng táº¡o cÃ¢u tráº£ lá»i khÃ´ng cÃ³ nguá»“n náº¿u chá»©c nÄƒng yÃªu cáº§u citation.
- KhÃ´ng giáº£ Ä‘á»‹nh file, model hoáº·c cáº¥u hÃ¬nh Ä‘Ã£ tá»“n táº¡i; pháº£i kiá»ƒm tra trÆ°á»›c.
- Má»—i task pháº£i cÃ³ cÃ¡ch kiá»ƒm thá»­ rÃµ rÃ ng.
- Sau má»—i task pháº£i cáº­p nháº­t `PROJECT_STATUS.md` vÃ  `CHANGELOG.md`.

## Quy trÃ¬nh lÃ m má»™t task

1. Äá»c task hiá»‡n táº¡i trong `TASKS.md`.
2. Kiá»ƒm tra cÃ¡c file liÃªn quan Ä‘ang tá»“n táº¡i.
3. TÃ³m táº¯t ngáº¯n nhá»¯ng gÃ¬ sáº½ thay Ä‘á»•i.
4. Thá»±c hiá»‡n thay Ä‘á»•i nhá», cÃ³ kiá»ƒm soÃ¡t.
5. Cháº¡y lint, test hoáº·c kiá»ƒm thá»­ thá»§ cÃ´ng phÃ¹ há»£p.
6. Ghi láº¡i file Ä‘Ã£ thÃªm/sá»­a.
7. Cáº­p nháº­t `PROJECT_STATUS.md`.
8. Cáº­p nháº­t `CHANGELOG.md`.
9. BÃ¡o rÃµ giá»›i háº¡n hoáº·c lá»—i cÃ²n tá»“n táº¡i.

## Chuáº©n Ä‘áº§u ra sau má»—i task

Codex pháº£i bÃ¡o cÃ¡o theo máº«u:

```text
TASK COMPLETED: <tÃªn task>

Files created:
- ...

Files modified:
- ...

How to test:
1. ...
2. ...

Known limitations:
- ...

Documentation updated:
- PROJECT_STATUS.md
- CHANGELOG.md
```

## Quy táº¯c há»i láº¡i

Chá»‰ há»i ngÆ°á»i dÃ¹ng khi thiáº¿u má»™t trong cÃ¡c thÃ´ng tin sau vÃ  khÃ´ng thá»ƒ suy ra an toÃ n:

- API key hoáº·c lá»±a chá»n nhÃ  cung cáº¥p LLM.
- File máº«u cáº§n xá»­ lÃ½.
- ChÃ­nh sÃ¡ch phÃ¢n quyá»n chÆ°a Ä‘Æ°á»£c Ä‘á»‹nh nghÄ©a.
- ThÃ´ng tin triá»ƒn khai thá»±c táº¿ nhÆ° domain, server, cloud provider.
- Quyáº¿t Ä‘á»‹nh cÃ³ áº£nh hÆ°á»Ÿng lá»›n tá»›i kiáº¿n trÃºc.

Náº¿u khÃ´ng thiáº¿u cÃ¡c thÃ´ng tin trÃªn, Codex pháº£i tiáº¿p tá»¥c báº±ng phÆ°Æ¡ng Ã¡n máº·c Ä‘á»‹nh Ä‘Ã£ mÃ´ táº£ trong tÃ i liá»‡u.



### Latest RAG-H2.1 handoff

Reranker authority bug is fixed and unit verified.

Changed behavior:

```python
# old
for hit in (*ranked_hits, *reranked_hits):

# new
for hit in (*reranked_hits, *ranked_hits):
```

Verification:

```text
61 passed
27 passed
147 passed combined
```

Runtime still logs cross-encoder fallback to `HeuristicRetrievalReranker`.

`RAG_DIAGNOSTICS_ENABLED` is not present in the API container, so diagnostics remain disabled. Before further tuning, inspect the actual Compose environment injection and enable diagnostics without guessing the Compose structure.


### Latest runtime incident handoff

Do not debug Ollama for the resolved `LLM_GENERATION_FAILED` incident.

Verified:
- `qwen2.5:7b-instruct-8k` exists and runs.
- API container reaches Ollama.
- `/v1/chat/completions` returns valid JSON.
- Project `OpenAICompatibleLLMProvider` generation succeeds.

Actual root cause was `NameError: grounding_question is not defined` in `_draft_from_generation()` after an incomplete attempt to pass the question into claim validation. The invalid argument was removed because the current validator contract does not yet accept `question`.

Tests after recovery:
- grounded answer service: 61 passed
- focused combined RAG/retrieval suite: 147 passed

Current live issue: `Dải lương tham khảo của Head là bao nhiêu?` returns NO_ANSWER although ND-HR-005 contains `N6 Head / Director 65 - 110 triệu đồng`.

`RAG_DIAGNOSTICS_ENABLED=True`, but INFO-level RAG diagnostics are not visible in Docker logs. Investigate logging visibility first; do not tune retrieval blindly.

### Latest RAG handoff — salary fixed; YES/NO next

Do not revisit retrieval/model/context for the salary `Head` probe. It is now passing.

Completed:
- salary `AMOUNT` false quantity-gate bug fixed;
- 63 grounded-answer tests passed;
- 149 combined focused RAG/retrieval tests passed;
- live Head and Engineering Manager salary probes pass.

Current YES/NO failure:
- question classified YES_NO;
- correct salary-policy sources reach SourceRegistry;
- claim validation is `SUPPORTED` three times;
- each generated draft is rejected by `yes_no_missing_leading_polarity`;
- final result becomes NO_ANSWER.

Therefore the next fix must separate semantic support from answer-presentation canonicalization. Do not add question-specific hardcoding.

Citation UX direction:
`evidence_text` / evidence highlighting should identify the minimal source passage actually used to support or derive the answer. If an answer is synthesized, underline the supporting source clause/row rather than requiring the final answer wording to appear verbatim in the source.
