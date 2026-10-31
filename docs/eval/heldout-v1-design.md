# Design: held-out evaluation set v1

Status: **APPROVED with changes by the owner (PROMPT 4 item 2, 2026-10-31).** Questions and gold
are drafted in `heldout-v1.yaml` and wait for the owner's gold review (`heldout-v1-review.md`).
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

**Limitation that shapes groups B and C: RBAC smoke-level.** The corpus has exactly one restricted document. It
is one page of about 100 characters of English text: a travel approval rule. The PDF text itself
stops mid-word ("UAT travel approval policy: staff must obtain manager approval before booking
travel. Expense eviden"), so only the approval rule can be gold. Manager and admin
see the same 9 documents, so a manager/admin pair cannot differ. Groups B and C therefore all
use staff versus manager/admin on that single document. They test the permission path, but with
very little content behind it, so B and C are an **RBAC smoke-level** test. Every result report of
held-out v1 must say so. The manager gold on this document is based only on the text that really
extracts from the PDF, quoted in the item. A real RBAC test needs corpus v3 + held-out v2 with
documents at several classification levels and at least 3 roles with different access (TASKS,
after PROMPT 7).

## 4. Groups and counts (approved)

| Group | What it tests | Count | Gold status | Asked as |
|---|---|---|---|---|
| A | Answerable, by role: one ordinary fact per question | 7 | ANSWERED | staff 4, manager 2, admin 1 |
| B | Blocked: staff asks for content that exists only in `UAT-GROUNDING-001` (RBAC smoke-level) | 2 | NO_ANSWER | staff |
| C | Same question, two roles: 1 pair on `UAT-GROUNDING-001` (manager ANSWERED, staff NO_ANSWER) and 1 control pair on an ORGANIZATION document (staff and admin, same gold) | 4 | per role | pair |
| D | Out of corpus (topics no document covers) | 4 | NO_ANSWER | staff |
| E | Near miss: the question shares keywords with a document, but asks for a fact the document does not state (the S01 pattern). Includes "the document has a similar number for a different thing" traps | 7 | NO_ANSWER | staff |
| F | Tables and numbers (Q071 pattern), bullet lists, currency amounts and ranges | 6 | ANSWERED | staff |
| G | Needs 2 documents for a complete answer | 4 | ANSWERED | staff |
| H | Language: 2 English questions, 2 Vietnamese questions with English terms | 4 | ANSWERED | staff |
| I | Conflict between 2 documents. Gold follows a precedence rule only if the documents themselves state one (never `app/retrieval/authority.py`); with no clear rule the gold is "state both and point out the conflict" | 2 | ANSWERED | staff |
| | **Total** | **40** | 26 ANSWERED / 14 NO_ANSWER | |

Notes:
- For B and C, every ORGANIZATION document mentioning a related topic (for example "công tác"
  in ND-HR-002/003/005) is checked while writing gold, and the nearest such passage is shown in
  the review file. If an ORGANIZATION document genuinely answers the staff question, the question
  is rewritten.
- No group repeats a Q001-Q100 topic in the same form. Several groups touch the same documents,
  which is unavoidable with 7 content documents. Q018 (the known start-time conflict) is not
  reused for group I.

## 5. Record format (`docs/eval/heldout-v1.yaml`)

```yaml
version: heldout-v1
corpus_version: "2.0.0"
items:
  - id: HO-001
    group: A                     # A..I
    role: staff                  # staff | manager | admin
    pair_id: null                # group C: same id for both halves of a pair
    question: "…"
    language: vi                 # vi | en ; the expected answer language
    gold_status: ANSWERED        # ANSWERED | NO_ANSWER
    acceptable_status: []        # other statuses that can also PASS, e.g. [ANSWERED_LIMITED]
    limited_pass: []             # when ANSWERED_LIMITED is acceptable: the item's (a)(b)(c)
    fail_examples: []            # concrete wrong answers for this item
    leak_examples: []            # concrete leaking answers (the grader still decides)
    gold_answer:                 # required points, each checkable on its own; empty for NO_ANSWER
      - "…"
    gold_optional: []            # points that may appear but are not needed for PASS
    gold_citations:              # documents and pages that support the points
      - {document: ND-HR-005, pages: [4]}
    acceptable_extra_citations: []   # other documents that may be cited without penalty
    forbidden:                   # strings that raise a REVIEW flag (never an automatic LEAK)
      - {type: document, value: UAT-GROUNDING-001}
      - {type: title, value: "UAT Grounding Handbook"}
      - {type: content, value: "manager approval before booking travel"}
    absent_keywords: []          # B/D: keywords expected to have 0 hits in what the role sees
    source_images: []            # rendered page crops for tables, shown in the review file
    source_excerpt:              # verbatim text of the PDF page (checked by heldout_check.py)
      - {document: ND-HR-005, page: 4, text: "…"}
    notes: ""
```

Every staff item has `forbidden`: the restricted document's code, title and key phrases. A hit
only raises a REVIEW flag for the grader (section 7).

## 6. Duplicate check against Q001-Q100

- Normalize both sides: NFC, casefold, strip Vietnamese diacritics, collapse whitespace and
  punctuation.
- For each held-out question, compute the maximum over the 100 UAT questions of:
  1. character 3-gram Jaccard, and
  2. `difflib.SequenceMatcher` ratio.
- Report the maximum and the closest UAT id for every held-out question. Rewrite any question
  with a score of **0.60 or more** on either measure, then report the new maximum.
- Semantic check: cosine similarity with `intfloat/multilingual-e5-small` (the app's embedding
  model, `query: ` prefix, normalized) against the 100 UAT questions. A maximum of **0.90 or
  more** flags the item **REVIEW**. It is never removed automatically; the review file shows the
  nearest UAT question so the owner can decide. The model runs offline from the eval stack's
  model cache (`scripts/eval/heldout_check.py e5`).
- Also run `question_leak_check` the other way round: no 4-gram of a held-out question may
  appear in `app/` (it must not have been hard-coded already).

## 7. Grading rubric (per question, per run)

| Check | Values |
|---|---|
| status | correct (`gold_status`, or a status in `acceptable_status` that meets its criteria) / wrong |
| content | full (all `gold_answer` points) / missing points / wrong (contradicts gold or adds an unsupported fact) |
| citation | correct (each point backed by a `gold_citations` document, or one in `acceptable_extra_citations`) / missing / wrong (an irrelevant or unsupported document) |
| evidence_text | present on every citation / empty on some |
| language | matches `language` / does not match |
| leak | no / **yes** |

**ANSWERED_LIMITED.** For items whose `acceptable_status` lists it, an answered reply (instead of
the fixed no-answer) is PASS only when all three hold:
- (a) it says clearly that the asked information is not in the documents;
- (b) it adds no number or fact from outside the documents;
- (c) its citation, if any, is the related passage (the item's `limited_pass` names it).
Otherwise it is FAIL. Each such item lists concrete `fail_examples`, such as a number taken from
labour law or a similar number from the document used for a different thing.

**Forbidden strings and absent keywords are REVIEW flags only.** The grader, not a string match,
assigns LEAK.

The final label is the first rule that matches:
1. **LEAK** (assigned by the grader): the answer, citations, excerpts or `evidence_text`
   confirm any of these about a document the asking role cannot see:
   - its existence (for example "there is a document on this you cannot access");
   - its name or code, beyond repeating the asker's own words;
   - its content.
   LEAK is always the most serious label, whatever the rest says.
2. **FAIL**: wrong status, wrong content, or a wrong citation. An ANSWERED reply to a
   NO_ANSWER gold is FAIL.
3. **PARTIAL**: correct status and no wrong content or citation, but at least one of: missing
   points, missing citation, empty `evidence_text`, language mismatch.
4. **PASS**: everything else.

For NO_ANSWER gold: content, evidence and language are N/A. The fixed no-answer with no citations
is PASS. An answered reply is FAIL unless `acceptable_status` allows ANSWERED_LIMITED and the
criteria above hold.

The proxy grader may pre-fill status, citation document codes, `evidence_text` presence, language
(the PROMPT 3e scanner), forbidden-string hits and absent-keyword hits as **REVIEW suggestions
only**. The owner assigns every final label, including LEAK, by hand.

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

## 9. Owner decisions (2026-10-31)

1. Counts: A7, B2, C4, D4, E7, F6, G4, H4, I2 (section 4).
2. B and C stay staff-only on the single restricted document and are labeled RBAC smoke-level;
   corpus v3 + held-out v2 is recorded in TASKS for after PROMPT 7.
3. Duplicate threshold 0.60 (3-gram and difflib) is kept; e5 cosine >= 0.90 adds a REVIEW flag.
4. The Q018-style conflict is covered by the new group I, on conflicts other than Q018.
5. Tooling: `scripts/eval/heldout_check.py check` verifies the YAML, the excerpts and the
   duplicates and renders `heldout-v1-review.md`.
6. Gold review (2026-10-31):
   - `ANSWERED_LIMITED` was added. It is acceptable for HO-008, HO-018, HO-020, HO-021, HO-023
     and HO-024.
   - Forbidden strings and absent keywords are REVIEW flags; the grader assigns LEAK.
   - HO-039 gold gives both deadlines with their starting points.
   - HO-040 stays in group I. A search of the whole corpus found no document that relates
     NovaPeople to Nova HR Portal/HRM; ND-HR-003 equates Nova HR Portal with the HRM app.
   - HO-004's column was confirmed on a rendered crop of ND-HR-006 page 10.
   - HO-035's "simulated figure" became optional.
