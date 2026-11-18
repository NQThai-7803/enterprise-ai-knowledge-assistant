# Template and draft documents: company documents win

Status:

- **Proposed** on 2026-11-18.
- **Approved and implemented the same day (DEC-033):**
  - `exclude` only;
  - the lifecycle value `DRAFT`;
  - the flag `RAG_DRAFT_DOCUMENT_POLICY`, default `off`;
  - the gold edits below, with new locks.
- `demote` and the citation mark are not implemented.
- **Since DEC-036, `exclude` is the default** for every configuration (the owner's data policy).

Owner decision this builds on: **a company document wins over a template.**

## The case

Corpus V2 has two leave policies:

| | ND-HR-004 | UAT-LEAVE-AUTHORITY-001 |
|---|---|---|
| Title | Chính sách nghỉ của người lao động Công ty Công nghệ Nova Digital | Chính sách nghỉ của người lao động |
| Inside | ND-HR-004, version 1.0, issued 12/08/2026 (simulated) | HR-POL-LEAVE-01, `[Tên doanh nghiệp]` |
| Footer | INTERNAL - Bản mô phỏng | Tài liệu mẫu - cần được rà soát trước khi ban hành chính thức |
| Page 1 | - | Tài liệu mẫu - chưa phải văn bản ban hành |
| `lifecycle_status` | ACTIVE | ACTIVE (the upload default) |

The template is in the corpus because "annual-leave acceptance uses its statutory allocation evidence" (manifest provenance).

## What it costs today

The figures are graded value-aware (DEC-032), on UAT runs 44148578890, 44148605005, 44148631493 and 44148657545.

- **Wrong answers citing the template**, both rounds:
  - `s3` + `qwen3.5-text:4b`: 4 (Q039, Q040, Q042, Q043). Every value is right, but the hand grade expects ND-HR-004.
  - With row chunks (DEC-031): 6 (Q042, Q043, Q045, Q048, Q049, Q051).
    - Q048 and Q049 take the template's notice periods (10 and 03 days) instead of ND-HR-004's.
    - Its chunks take 2 of the 5 sources for Q049.
  - `legacy` + 3B: none. Its deterministic route reads ND-HR-004.
- **Q043:** the cited passage of the template (carry-over of up to 03 years) does not support the answer (03 days of marriage leave). The claim check passes it because of the shared number.

## What exists

- `documents.lifecycle_status`: ACTIVE, SUPERSEDED or ARCHIVED. Also `effective_from` / `effective_to` and `supersedes_document_id` (migration 0011).
- `current_authority_order_expression()` (`app/retrieval/authority.py`):
  - A currently effective ACTIVE document ranks 2, any other ACTIVE document ranks 1, and the rest rank 0.
  - The keyword and semantic repositories use it as an ordering term unless the question asks for history.
  - The template is ACTIVE with no dates, so it ranks like ND-HR-004.
- The upload API already takes `lifecycle_status` as a form field.

## Proposal

**1. Metadata, set by a person, not by the text.**

- Add the lifecycle value `DRAFT` ("not an issued document": templates, drafts, documents under review).
- Migration: add the enum value only. Existing rows stay ACTIVE.
- Set by the uploader or an admin at upload or later, through the existing field. Audit-logged like any document change.
- **Not inferred from the content.** The company documents also say "Bản mô phỏng", and ND-HR-004 has a page of "tình huống mẫu" (sample cases). A text rule would hit them too, and a rule keyed on one document's code or title is per-document logic (CLAUDE.md).
- Optional help for the admin, outside the answer path: list the documents whose pages say "tài liệu mẫu", "bản nháp", "chưa ban hành" or "draft", so a person can decide. The detector never changes a status.

**2. Answer policy behind a flag, off by default.**

`RAG_DRAFT_DOCUMENT_POLICY` = `off` | `demote` | `exclude`.

- **`demote`:**
  - A DRAFT document ranks 0 in `current_authority_order_expression()`, like SUPERSEDED.
  - At context admission, when chunks of an ACTIVE document and of a DRAFT document are both admitted, the DRAFT chunks are dropped and their slots go to the next ACTIVE chunks.
  - A DRAFT chunk stays usable when no ACTIVE document reaches the context. Its citation is then marked as a draft (`document_lifecycle_status` in the citation payload, shown by the UI).
- **`exclude`:**
  - DRAFT documents are not retrieved for answers at all.
  - They stay visible and searchable in document management, and permission checks are unchanged.
- **Recommended:** `exclude`. It is the plain reading of "company documents win", and a draft answering alone still misleads.
  - Use `demote` only if the owner wants drafts as a last resort, with the mark.

**3. Permissions are not involved.** The policy narrows what an authorized user's answer can use. It never widens access, and it runs after the permission filter, like the authority order today.

## Effect on the gold of existing sets

The UAT and dev gold is not edited without the owner. Each change below needs a new lock where the set has one.

- **UAT Q044.**
  - The hand grade (TASK-035.3B) cites only the template.
  - ND-HR-004 page 6 has the same value ("con đẻ hoặc con nuôi kết hôn 01 ngày").
  - Under `exclude` or `demote`, a correct answer cites ND-HR-004, so the proxy would count it as the wrong document. The expected citation must become ND-HR-004.
- **`natural_dev_v1` ND-001** (total public holidays).
  - The gold cites the template, the only document that writes the total (11 days). ND-HR-004 is acceptable: it lists each occasion, which sum to 11, but writes no total.
  - Under `exclude`, the answer must add up ND-HR-004's rows. The item either moves to ND-HR-004 as gold (`natural_dev_v1_gold.yaml` + lock), or the owner accepts that it becomes harder.
- **`natural_dev_v1` ND-004, ND-012, ND-019.** The template is only an acceptable extra citation. Under `exclude` it can be dropped from the gold; nothing else changes.
- **UAT Q039, Q040, Q042, Q043.** Already graded against ND-HR-004. They should turn correct, or Q043 a refusal.
- **Synthetic dev sets** (relevance, false refusal v1/v2, compound, RBAC): their documents are generated per set, with no template. No change.
- **Held-out v2 and v3: not checked.** They may not be opened for design (DEC-012; owner rule for v3). Whether their gold cites the template is for the measurement milestone.

## Measurement (when approved)

- Mark UAT-LEAVE-AUTHORITY-001 as DRAFT in an eval stack only, via the API on the job's own corpus load. The V2 volume is never touched.
- Configurations: flag `off` vs `exclude` (and `demote` if wanted), on `s3` + `qwen3.5-text:4b`. Sets: natural, the 5 dev sets, and UAT (monitoring). 2 jobs (DEC-027), rule DEC-026, value-aware grading.
- Diagnostics:
  - the items above;
  - every answer that cites a DRAFT document;
  - Q044 and ND-001 under both the old and the owner-approved gold.

## Order of work

1. Owner decides:
   - `exclude` or `demote`;
   - Q044's expected citation;
   - ND-001's gold.
2. Code: the enum value and migration, the flag, the policy at retrieval and admission, the citation field, and the API docs. Unit tests plus the permission and retrieval tests of the change guard.
3. Measure as above, then stop and report.
