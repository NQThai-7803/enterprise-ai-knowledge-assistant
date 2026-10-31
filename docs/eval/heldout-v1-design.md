# Design: held-out evaluation set v1

Status: **PROPOSED, waiting for owner review (PROMPT 4 item 1).** No questions or gold exist yet.
Date: 2026-10-31.

## 1. Purpose

UAT Q001-Q100 has been used to tune the runtime since TASK-035, so it now measures fit to those
questions as much as quality. Held-out v1 is a second, independent set. It is used only to
measure the system at milestones and never to tune it. In `eaka-rag-change-guard` terms,
Q001-Q100 is the **dev** split and held-out v1 is the **test** split.

## 2. Scope

- **Corpus:** UAT Corpus v2 as it is now (`uat/corpus-v2/manifest.json`: 9 documents, 143
  chunks, 1 grant). No document is added or changed for this set.
- **Questions:** new questions only. They must not paraphrase Q001-Q100 (duplicate check in
  section 6).
- **Size:** 40 questions (section 4).
- **Source of gold:** gold is written only from the source PDFs listed in the manifest, after
  their SHA256 is checked against the manifest. The system is never run to write or check gold.

## 3. Roles and what each role can see

Accounts come from `app/scripts/seed_uat_data.py`; access follows `app.core.permissions`
(`can_view_document`, `build_accessible_document_filter`).

| Account | Role | Department | Can see |
|---|---|---|---|
| `staff.uat@example.test` | STAFF | knowledge | the 8 ORGANIZATION documents |
| `manager.uat@example.test` | MANAGER | knowledge | the 8 ORGANIZATION documents + `UAT-GROUNDING-001` (direct VIEW grant) |
| `admin.uat@example.test` | ADMIN | none | all 9 documents (admin sees everything; also the owner of all 9) |

| Code | Title | Scope | Pages | Visible to |
|---|---|---|---|---|
| ND-CORP-001 | Giới thiệu và cơ cấu tổ chức Công ty Công nghệ Nova Digital | ORGANIZATION | 10 | all |
| ND-HR-002 | Nội quy lao động … | ORGANIZATION | 15 | all |
| ND-HR-003 | Chính sách làm việc và chấm công … | ORGANIZATION | 12 | all |
| ND-HR-004 | Chính sách nghỉ của người lao động … | ORGANIZATION | 13 | all |
| ND-HR-005 | Chính sách tiền lương phụ cấp và thưởng … | ORGANIZATION | 14 | all |
| ND-HR-006 | Chính sách bảo hiểm và phúc lợi … | ORGANIZATION | 14 | all |
| UAT-LEAVE-AUTHORITY-001 | Chính sách nghỉ của người lao động | ORGANIZATION | 6 | all |
| UAT-GROUNDING-001 | UAT Grounding Handbook | **PRIVATE**, grant VIEW to manager | 1 | manager, admin |
| UAT-SHARED-001 | UAT Shared Knowledge Policy | ORGANIZATION | 1 | all |

**Limitation that shapes groups B and C.** The corpus has exactly one restricted document. It
is one page of about 100 characters of English text: a travel approval rule. The PDF text itself
stops mid-word ("UAT travel approval policy: staff must obtain manager approval before booking
travel. Expense eviden"), so only the approval rule can be gold. Manager and admin
see the same 9 documents, so a manager/admin pair cannot differ. Groups B and C therefore all
use staff versus manager/admin on that single document. They test the permission path, but with
very little content behind it. More restricted content needs a corpus change, and that would be
held-out v2, outside this scope.

## 4. Groups and proposed counts

| Group | What it tests | Count | Gold status | Asked as |
|---|---|---|---|---|
| A | Answerable, by role: one ordinary fact per question, spread over the 7 large documents | 7 | ANSWERED | staff 4, manager 2, admin 1 |
| B | Blocked: staff asks for content that exists only in `UAT-GROUNDING-001` | 4 | NO_ANSWER | staff |
| C | Same question, two roles (3 pairs): 2 pairs on `UAT-GROUNDING-001` (manager or admin ANSWERED, staff NO_ANSWER) and 1 control pair on an ORGANIZATION document (both ANSWERED, same gold) | 6 | per role | pair |
| D | Out of corpus (topics no document covers) | 4 | NO_ANSWER | staff |
| E | Near miss: wording close to a covered topic, but the asked fact is not in any document (the S01 pattern, where an unrelated chunk tempts an answer) | 5 | NO_ANSWER | staff |
| F | Tables and numbers (Q071 pattern), bullet lists, currency amounts and ranges | 6 | ANSWERED | staff |
| G | Needs 2 documents for a complete answer | 4 | ANSWERED | staff |
| H | Language: 2 English questions, 2 Vietnamese questions with English terms (for example "payroll", "on-call", "stipend") | 4 | ANSWERED | staff |
| | **Total** | **40** | 27 ANSWERED / 13 NO_ANSWER | |

Notes:
- B and the staff half of C ask about the same restricted fact in different words. So that the
  "not leaked" result does not rest on one wording, B uses 4 phrasings that differ in language
  and specificity.
- For B and C, every ORGANIZATION document mentioning a related topic (for example "công tác"
  in ND-HR-002/003/005) is checked while writing gold. If an ORGANIZATION document genuinely
  answers the staff question, the question is rewritten. Gold must not depend on a coincidence.
- No group repeats a Q001-Q100 topic in the same form. Several groups will touch the same
  documents, which is unavoidable with 7 content documents.

## 5. Record format (`docs/eval/heldout-v1.yaml`)

```yaml
version: heldout-v1
corpus_version: "2.0.0"
items:
  - id: HO-001
    group: A                     # A..H
    role: staff                  # staff | manager | admin
    pair_id: null                # group C: same id for both halves of a pair
    question: "…"
    language: vi                 # vi | en ; the expected answer language
    gold_status: ANSWERED        # ANSWERED | NO_ANSWER
    gold_answer:                 # required points, each checkable on its own; empty for NO_ANSWER
      - "…"
    gold_citations:              # documents and pages that support the points
      - {document: ND-HR-005, pages: [4]}
    acceptable_extra_citations: []   # other documents that may be cited without penalty
    forbidden:                   # must not appear in answer, citations, excerpt or evidence_text
      - {type: document, value: UAT-GROUNDING-001}
      - {type: title, value: "UAT Grounding Handbook"}
      - {type: content, value: "manager approval before booking travel"}
    source_excerpt:              # verbatim lines from the PDF, for the owner's review only
      - {document: ND-HR-005, page: 4, text: "…"}
    notes: ""
```

Every item has `forbidden`. Groups B and C (staff) list the restricted document's code, title
and key phrases. The other groups list nothing restricted, but any reference to
`UAT-GROUNDING-001` by staff is still a LEAK (section 7).

## 6. Duplicate check against Q001-Q100

- Normalize both sides: NFC, casefold, strip Vietnamese diacritics, collapse whitespace and
  punctuation.
- For each held-out question, compute the maximum over the 100 UAT questions of:
  1. character 3-gram Jaccard, and
  2. `difflib.SequenceMatcher` ratio.
- Report the maximum and the closest UAT id for every held-out question. Rewrite any question
  with a score of **0.60 or more** on either measure, then report the new maximum.
- Also run `question_leak_check` the other way round: no 4-gram of a held-out question may
  appear in `app/` (it must not have been hard-coded already).

## 7. Grading rubric (per question, per run)

| Check | Values |
|---|---|
| status | correct / wrong |
| content | full (all `gold_answer` points) / missing points / wrong (contradicts gold or adds an unsupported fact) |
| citation | correct (each point backed by a `gold_citations` document, or one in `acceptable_extra_citations`) / missing / wrong (an irrelevant or unsupported document) |
| evidence_text | present on every citation / empty on some |
| language | matches `language` / does not match |
| leak | no / **yes** |

The final label is the first rule that matches:
1. **LEAK**: any `forbidden` item, or any mention of a document the asking role cannot see (code,
   title, content, or a statement that such a document exists). Checked in the answer, citations,
   excerpts and `evidence_text`. LEAK is always the most serious label, whatever the rest says.
2. **FAIL**: wrong status, wrong content, or a wrong citation. An ANSWERED reply to a
   NO_ANSWER gold is FAIL.
3. **PARTIAL**: correct status and no wrong content or citation, but at least one of: missing
   points, missing citation, empty `evidence_text`, language mismatch.
4. **PASS**: everything else.

For NO_ANSWER gold: content, evidence and language are N/A. The fixed no-answer with no citations
is PASS.

The proxy grader may pre-fill status, citation document codes, `evidence_text` presence, language
(the PROMPT 3e scanner) and forbidden-string hits as **suggestions only**. The owner assigns
every final label by hand.

## 8. Rules

1. **Freeze before the first run.** After the owner approves the gold, record the SHA256 of
   `heldout-v1.yaml` in `docs/eval/heldout-v1.sha256` and in `CHANGELOG.md`. The runner refuses to
   run when the file's hash differs. Any later edit makes a new version (`heldout-v1.1`) with a
   new hash. Results from different versions are never compared directly.
2. **No tuning on this set.** No runtime change may be motivated by a held-out result, and none
   may cite a held-out question. A held-out failure is recorded as a finding; a fix has to be
   justified and checked on Q001-Q100 (dev) and general tests. `question_leak_check` is extended
   to the held-out questions, so a diff into `app/` that contains one of their 4-grams fails.
3. **Milestones only.** Run at milestones the owner names, such as before a default flip
   (`eaka-rag-change-guard` gate) or before a release. Each run stores, under
   `artifacts/heldout-v1/<date>-<short commit>/`:
   - the commit and image ID;
   - the full config (LLM provider, model and digest, seed, temperature, context, exact-KNN flag
     and every RAG flag);
   - the `heldout-v1.yaml` hash;
   - the answers and citations;
   - the grading sheet.
4. **Two runs per milestone**, with the baseline v2 protocol (cold model, warm-up, seed). The two
   runs are graded separately, and any difference between them is reported as noise. It is never
   averaged away.
5. **Runner.** The UAT runner is extended to read `heldout-v1.yaml` and log in as the role of each
   item. It uses the `eval_client` INFRA_ERROR rules: an INFRA_ERROR is never graded and is
   reported separately. Passwords come from environment variables and are never written to
   artifacts.

## 9. Open points for the owner

1. Are the group counts in section 4 right? This draft gives A 7, B 4, C 6, D 4, E 5, F 6, G 4,
   H 4, for 40 in total.
2. Should the staff-only design of B and C stay? The corpus has one restricted document; held-out
   v2 with more restricted documents is the alternative.
3. Is a duplicate threshold of 0.60 acceptable?
4. Should the Q018-style authority conflict (ND-HR-002 vs ND-HR-003) get a held-out item? This
   draft leaves it out, because its expected behavior is already fixed by `known_conflicts`.
