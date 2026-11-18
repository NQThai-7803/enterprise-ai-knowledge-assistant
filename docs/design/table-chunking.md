# Table chunking: diagnosis, proposal and implementation behind a flag

Measured 2026-11-17. The owner asked for a diagnosis first and no code.

**Sources:**

- the corpus V2 PDFs (`eval-data/corpus-v2`, 9 files);
- the app's own extractor and chunker, run offline at the corpus V2 settings:
  - `PyMuPDFTextExtractor`, `get_text("text", sort=True)`;
  - `PageAwareTokenChunker` with target 500, max 700, overlap 75, min 50, `cl100k_base`.

Every page has native text, so none goes through OCR. No stack or database was touched; the chunks are rebuilt from the PDFs.

**How tables were found:**

- Tables come from PyMuPDF `find_tables()`.
- **A row is "in a chunk"** when one chunk holds all of its words.
- **"Intact"** when every cell's text also appears unbroken in that chunk.
- **"Interleaved"** when the words are there but some cell's text is broken by another cell's text.

These are heuristics, so I checked samples of each class by hand.

## Tables in corpus V2

`find_tables()` finds 235 regions. Of these, **77 are data tables** (at least 2 columns and 2 body rows) with 380 rows. The other regions are one-row boxes (warnings, notes) and one-column frames.

| Document | Regions | Data tables | Rows | Interleaved rows | Rows without the header in their chunk |
|---|---|---|---|---|---|
| Chính sách nghỉ (`20723824-….pdf`) | 7 | 6 | 27 | 5 | 3 |
| Bảo hiểm và phúc lợi | 44 | 15 | 70 | 50 | 11 |
| Làm việc và chấm công | 34 | 12 | 58 | 33 | 11 |
| Nghỉ của người lao động | 35 | 11 | 49 | 18 | 6 |
| Tiền lương, phụ cấp và thưởng | 40 | 14 | 72 | 37 | 9 |
| Giới thiệu và cơ cấu tổ chức | 34 | 13 | 66 | 20 | 23 |
| Nội quy lao động | 41 | 6 | 38 | 9 | 8 |
| `grounding-handbook.pdf`, `shared-policy.pdf` | 0 | 0 | 0 | 0 | 0 |
| **Total** | **235** | **77** | **380** | **172** | **71** |

## What a chunk keeps of a table

The extractor writes each cell as its own line, in reading order by position.

- A row whose cells each fit on one line stays on one line: "12 ngày Công việc trong điều kiện bình thường".
- A row with a cell of several lines is interleaved: the short cell lands between the lines of the long one.

For the 380 data rows:

| Measure | Rows | Share |
|---|---|---|
| Every cell unbroken in one chunk (intact) | 208 | 55% |
| Cell text broken by another cell (interleaved) | 172 | 45% |
| Row cut across two chunks | 0 | 0% |
| Header words in the same chunk as the row | 309 | 81% |
| All cells of the row on one line | 191 | 50% |

- **29 of the 77 data tables (157 rows) spread over two or more chunks.** The 75-token overlap does not carry the header or the table's title into the next chunk.
  - Most of the 71 rows without their header are in these tables.
  - The rest are key-value tables (document control, contacts), which have no header row.
- **Even with the header in the chunk, no value is bound to its column.** The header is one line at the top of the table, and the rows follow as bare values.

Samples from the chunks:

- **Annual leave** (`20723824-….pdf`, page 3; columns "Mức nghỉ" | "Đối tượng áp dụng"):

  ```
  Người chưa thành niên, người khuyết tật hoặc công việc nặng nhọc, độc hại, nguy
   14 ngày
   hiểm theo danh mục pháp luật
  ```

- **Annual Performance Bonus** (salary, page 9; columns "Xếp hạng mô phỏng" | "Hệ số thưởng mục tiêu" | "Ghi chú"):

  ```
  Phụ thuộc kết quả công ty và phê duyệt
   Exceptional 1,5 - 2,0 tháng Base Salary
   ngân sách.
  ```

- **Five core values** (organisation, page 4): the table spreads over two chunks.
  - Chunk 4 holds the title "Năm giá trị cốt lõi" and values 01-04.
  - Chunk 5 holds value 04 again (overlap) and value 05 "HỌC HỎI LIÊN TỤC", without the title.

## The wrong answers that cite tables

**natural_dev_v1:** every answer that was not correct, for every model and mode of DEC-028, rounds a and b. A citation counts as a table citation when at least 60% of its evidence words are cells of a data table on the cited page.

| | Answers with citations | Cite a table row |
|---|---|---|
| False answer | 16 | **16** (all ND-002) |
| Wrong (wrong value or subject) | 130 | 25 |
| `legacy` (every model) | 85 | 30 |
| `s3` (every model) | 61 | 11, of which 8 are ND-002 |

The three items that stay wrong with every model, and the other wrong-subject items of s3:

- **ND-002: yes, a flattened table.**
  - All models cite the bonus table on page 9 of the salary policy ("Chương trình" | "Mức mô phỏng" | "Điều kiện"). All 4 of its rows are interleaved.
  - The chunk reads: "Ứng viên được tuyển và hoàn thành mốc / Employee Referral Bonus 3 - 15 triệu đồng / thử việc/điều kiện chương trình".
  - The "Điều kiện" column says when the referrer is paid. Flattened, the condition reads as the person who is paid.
  - Of the 21 citations of wrong ND-002 answers, 11 are this table and 5 are the benefits table on page 5 ("Nhóm quyền lợi" | "Hạn mức mô phỏng/năm" | "Điều kiện chính").
- **ND-003: yes, a table spread over two chunks, for the models that find the right page.**
  - The fifth value sits in a chunk without the title "Năm giá trị cốt lõi". `legacy` with `qwen3.5:4b` lists four values; `legacy` with 7B cites page 4 and is still graded wrong.
  - `s3` cites page 3 instead (the positioning paragraph). That is retrieval and selection, and the reranker rule against "giá trị cốt lõi" passages (TASKS, rule cleanup) acts on it.
- **ND-014: no.** The citations are the bullet text on page 9 of the benefits policy ("Company trip/retreat…", "Team building budget…"). The events table is on the same page and in the same chunk, but less than 60% of the evidence comes from it.
- **ND-011: not for `s3`; `s3` cites a Q&A list.** The question-list passage says "Nhân viên báo cáo sự cố bảo mật qua đâu? … soc@", and s3 reads it as the answer to an ethics-report question. `legacy` cites a table (working policy, page 7) in 3 answers.
- **ND-019: no.** No citation of a wrong answer is mostly table text.
- **Other items with table citations, mostly `legacy`:**
  - ND-006 (10 answers). `legacy` answers "Không. Giá trị là 2.000.000 đ." from a lone cell of the benefits table on page 8.
  - ND-010 (5 answers). `legacy` cites interleaved text of the events table ("ngân sách giới hạn. Tự động theo dữ liệu HRM nếu nhân viên Sinh nhật 500.000 đ/người…").
  - ND-017 (2), ND-018 (1).

**Dev sets:** the documents of the 5 dev sets are plain text without tables. No dev error comes from tables, and a table change must leave them unchanged.

**UAT** (`s3` + `qwen3.5:4b` and `legacy` + 3B, two rounds, DEC-029; list in `docs/review/uat-s3-q35-2026-11-17.md`):

- **Same rule:** at least 60% of a citation's evidence words are cells of a data table on the cited page.
- **Correct answers, as a base rate:**
  - `s3`: 49 of 117 cite a table row (42%);
  - `legacy`: 84 of 191 (44%).
- **The six wrong values of `s3` all cite a table row:** Q019, Q048, Q049, Q054, Q077, Q079, in both rounds.
  - Five of them take a cell from the wrong row or column:
    - Q048 and Q049 take the "≥ 5 days" notice row;
    - Q077 and Q079 swap the per-visit and per-year limits;
    - Q019 takes the start of the end-time range.
  - Q054 cites the pay-date table but gives only the holiday rule.
- **`legacy` answers all six correctly on its deterministic route,** which reads the values itself.
- **The answers the proxy grades wrong** (a different document, mostly with the right value): 1 of 17 cites a table.

## Proposal: one unit per table row

Implemented on 2026-11-18 behind `DOCUMENT_TABLE_ROW_CHUNKING_ENABLED` (off), with changes from this proposal listed in the next section.

**Extraction.** On a page with a data table (at least 2 columns and 2 body rows), take the table's region out of the page text and emit one line per row:

```
<table title> | <column 1>: <cell 1>; <column 2>: <cell 2>; …
```

- **Table title:** the nearest heading line above the table (e.g. "1. Thưởng hiệu suất năm (Annual Performance Bonus)"), else the document title and page.
- **Columns:** the table's header row. A two-column table without a header row is written as `<key>: <value>`.
- Multi-line cells are joined with spaces.
- The rest of the page text stays as it is now.

**Chunking.**

- The rows of one table are grouped up to the target size. Every chunk that holds rows of a table starts with the title and the header line.
- Rows of two tables are never mixed in one chunk.
- A table that fits one chunk stays whole.

**Flag.** `DOCUMENT_TABLE_ROW_CHUNKING_ENABLED` (default off), added to `ENVIRONMENT_VARIABLES.md`.

- Chunks are written at ingestion, so the flag acts when a document is processed.
- An existing corpus changes only when it is reprocessed through the pipeline, never by editing `document_chunks`.

**Risks:**

1. **Wrong regions.** `find_tables()` finds 235 regions, of which only 77 are data tables. Boxes, notes and the organisation chart (organisation, page 6) would be reformatted wrongly. The rule must keep only data tables, and that rule needs its own check on all 9 PDFs.
2. **Wrong headers.** On the core-values table, the first value was taken as the header. Key-value tables have no header row.
3. **Citations.** `excerpt` and `evidence_text` are built from chunk text, so they would show "column: value" rather than the PDF's line, and the page of each row must be kept. The claim validators compare answers with chunk text, so their results can change.
4. **Duplicates.** If the table text stays in the page text as well, retrieval sees each row twice, so the table region must be cut out.
5. **Size.** A header repeated in every chunk costs tokens. s3 admits 5 chunks, at most 2 per document, so a chunk holds fewer facts.
6. **Retrieval moves.** Short, label-rich row chunks embed differently from mixed chunks. Every question that touches a table, including UAT questions answered today, can change.
7. **The `legacy` deterministic route** reads values out of chunk text. A new layout can change its answers in both directions.
8. **No per-question logic.** The change must be general, with no rules for particular documents or tables (CLAUDE.md).

**How to measure (to be fixed in a DEC before running):**

- **Offline:** rerun this diagnosis with the flag on.
  - Every data row must be intact, with its title and header in its chunk.
  - Also count the regions that would be reformatted, and read them by hand.
- **Unit tests** with made-up PDFs that contain a table: one row per unit, header and title present, page kept, no duplicate text.
- **Eval:**
  - Corpus V2 is loaded inside every `natural` and `uat` job, so one job ingests with the flag off and another with it on. The answer path is the same in both: `legacy` + 3B and `s3` + `qwen3.5:4b`.
  - Two rounds of such pairs (DEC-027).
  - Sets: `natural_dev_v1`, UAT (monitoring only, DEC-026), and the 5 dev sets as the no-change control.
  - Rule: DEC-026.
  - Diagnostics: the 41 table-cited natural answers, ND-002, ND-003, ND-006 and ND-010, and the UAT items in the list above.

## Implementation (2026-11-18, DEC-031)

`app/document_processing/extractors/table_rows.py`, called by `PyMuPDFTextExtractor` when the flag is on. It differs from the proposal in these points:

- **No chunker change.** Each row is its own paragraph and carries its title and column names, so the existing chunker cuts only between rows. Tables are therefore not kept in one chunk, and rows of two tables can share a chunk; each row stays readable on its own.
- **Data table:** at least 2 columns and **3 rows**. PyMuPDF's header guess is not used for this.
- **Column names**, against risk 2:
  - The first row counts as a header only if it has at least two distinct short labels (≤ 60 characters, no final full stop), every cell is bold, and the next row is not all bold.
  - PyMuPDF's own header guess is not used: it took the title line above a table as an "external" header, and the first value of the core-values table as column names.
  - Without a header, a row is written `<first cell>: <other cells>`. The document-control and contact tables come out as `Mã tài liệu: ND-HR-002`, `Sự cố an ninh mạng: Security Operations: …`.
- **Merged cells:** a cell merged from above takes its text; one merged from the left is written once.
- **Tables across pages:** a table that ends in the lower quarter of its page, with no body text after it above the footer, passes its title and columns to the next page's first table. That table must have no title of its own, the same number of columns, and no header or the same header.
- **Title:** the nearest line above the table, outside every table region (so not the page's header band), within 60 points.

**Offline on corpus V2** (the app's extractor and chunker at the corpus V2 settings):

- 143 chunks without the flag, 167 with it. Every row line sits whole in one chunk. The largest chunk is 700 tokens.
- The 18 documents of the 5 dev sets are unchanged with the flag on.
- Risk 1 is still open: the organisation chart (ND-CORP-001 page 6) is read as a table and stays garbled, as it is without the flag.

**Unit tests:** `tests/unit/test_table_row_extraction.py`, on made-up PDFs. They cover:

- a page without a table, unchanged;
- a multi-column table with title and reading order;
- a table continued on the next page, with and without a repeated header;
- vertical and horizontal merges;
- a key-value table without a bold header;
- a long table, where no chunk boundary cuts a row;
- the flag reaching both extractors, off by default.

## Measurement (DEC-031)

**Setup.**

- Two job rounds (`d`, `e`) per set. Each job runs `legacy` + 3B, then `s3` + `qwen3.5-text:4b`, then the same with the flag on.
- For the flag run, the job rebuilds its own postgres and redis volumes and reloads corpus V2 with the worker started with the flag. The V2 volume is never touched.
- Re-ingestion was checked in every job: `re-ingest, DOCUMENT_TABLE_ROW_CHUNKING_ENABLED=true` in `batch.log`, and all 9 documents READY in `reingest.log`.
- Prompt cache capped at 2048 MiB in every job.
- Runs: natural 44148260972 and 44148409028. The 5 dev sets: 44148286143 to 44148384526 and 44148432685 to 44148534878. UAT: 44148578890, 44148605005, 44148631493 and 44148657545.
- **Graded value-aware (DEC-032).** Regrading the dev sets changed no case. The UAT figures moved; both gradings are given below.

**Dev sets (DEC-026 / DEC-027)**, flag on vs flag off, both `s3` + `qwen3.5-text:4b`, jobs d / e:

| Set | Correct | False refusal | False answer + wrong |
|---|---|---|---|
| natural_dev_v1 | 9/9 vs 11/11 (**−2, real**) | 7/7 vs 5/5 (**+2, real**) | 4/4 vs 4/4 |
| the 5 dev sets | 107/108 vs 108/107 | 1/1 vs 1/1 | 9/8 vs 8/9 (tie) |
| all six | 116/117 vs 119/118 | 8/8 vs 6/6 (**+2, real**) | 13/12 vs 12/13 (tie) |

- Leaks: 0 everywhere.
- Rule (DEC-026): false answers + wrong are tied, and false refusals on `natural_dev_v1` rise by 2 in both jobs. The flag is **not adopted**; the default stays off.

**UAT** (monitoring only), correct - false refusal - false answer - wrong per round of 100:

| Configuration | A, proxy | A, value-aware | B, proxy | B, value-aware |
|---|---|---|---|---|
| `legacy` + 3B | 100-0-0-0 | 100-0-0-0 | 98-1-0-1 | 98-1-0-1 |
| `s3` + `qwen3.5-text:4b` | 69-23-1-7 | 62-23-1-14 | 67-24-1-8 | 60-24-1-15 |
| same + row chunks | 54-35-1-10 | 53-35-1-11 | 56-33-1-10 | 55-33-1-11 |

- **Proxy grading** (no values): the flag looked worse on every count.
- **Value-aware grading:** with the flag, false answers + wrong fall by 3 and 4 (12 vs 15 and 16). Correct falls by 9 and 5, and false refusals rise by 12 and 9.
  - Several answers that gave a wrong value now refuse instead.
  - The conclusion does not change: UAT is not the rule, and the rule set already decides.

**The nine UAT items read as wrong on 2026-11-17** (value-aware, rounds A / B):

| Item | flag off | flag on | |
|---|---|---|---|
| Q041 | wrong / wrong | correct / correct | seniority row: 10 years → 2 more days |
| Q077 | wrong / wrong | correct / correct | NovaCare inpatient row: 150 million per year |
| Q019 | wrong / wrong | false refusal / wrong | |
| Q020, Q054, Q079 | wrong / wrong | false refusal / false refusal | the right value no longer reaches the context, or the model refuses |
| Q048, Q049 | wrong / wrong | wrong / wrong | now cite the template UAT-LEAVE-AUTHORITY-001 (10 and 03 days) |
| Q018 | false answer / false answer | false answer / false answer | conflicting sources, not a table |

**ND-002 and ND-003** (natural, both jobs):

- **ND-003 is fixed.**
  - Flag off: none of the 5 core values is in the first context.
  - Flag on: all 5 are, and the answer is correct.
- **ND-002 stays a false answer.**
  - With the flag, the row reads correctly: `Chương trình: Employee Referral Bonus; Mức mô phỏng: 3 - 15 triệu đồng; Điều kiện: Ứng viên được tuyển và hoàn thành mốc thử việc…`.
  - The model still says the hired candidate receives the bonus. That is a subject error (who receives it), which chunking cannot fix.

### Per item: what the flag changes

UAT: 27 items change the same way in both rounds and 10 differ between rounds.

**Fixed (6):**

- Q041 and Q077: a table row reaches the context.
- Q039 and Q040: ND-HR-004 cited instead of the template.
- Q017 and Q046.

**Broken: 11 correct answers become false refusals.** In the evidence check, "share" is the share of word 5-grams of the passage cited with the flag off that also appear in the first context with the flag on.

- **8 lose their evidence** (share 0.00): Q004, Q010, Q032, Q035, Q038, Q056, Q073, Q099.
  - The context still has 5 sources of about the same size, but the passage that held the answer is not among them.
  - The model then writes "Chưa xác minh được…".
- **3 keep it but are rejected** (share 0.60-1.00): Q013 and Q014 (`claim_irrelevant`), Q074 (`claim_contradicted`).

**Other changes:**

- **3 correct answers become wrong:**
  - Q016: ND-HR-003 cited instead of ND-HR-002, with the same value.
  - Q051: the template is cited as well.
  - Q069: the answer adds the separate 20 % night-overtime rule. This is a false conflict of the value check; the answer is right.
- **3 false refusals become wrong:** Q037, Q045 (template) and Q096.
- **4 wrong answers become false refusals:** Q002, Q020, Q054, Q079.

**natural_dev_v1:**

- **Fixed:** ND-003, ND-006, ND-017. For ND-003 and ND-017, the table facts now reach the context (0/5 → 5/5 and 3/5 → 5/5).
- **Broken:**
  - ND-018: its evidence leaves the context.
  - ND-005, ND-013, ND-019 and ND-020: the facts are still in the context, but the model refuses, words the answer differently, or is rejected. In ND-013 it copies the table label: "mức hỗ trợ **mô phỏng** là 2.000.000 đ/lần" → `claim_insufficient`.
  - ND-015: the model breaks its markers (`…escalationsource_1`).

**Why the evidence moves.** In the contexts read for Q048 and Q049:

- **Repeated labels crowd the context.** The title and column names repeat in every row, so a table's chunk repeats its labels many times. A chunk with many matching labels then outranks the passage with the answer.
  - The benefits matrix of ND-HR-006 (`Quyền lợi: …; Trong nghỉ không lương dài ngày: …`) enters the context of both leave-notice questions.
- **The template gains slots.** UAT-LEAVE-AUTHORITY-001 has the same title as ND-HR-004 without the company name. Its chunks now take 2 of the 5 sources for Q049.
- **Answers cite the template more.** Wrong answers citing it: 4 per round with the flag off (Q039, Q040, Q042, Q043), 6 with it on (Q042, Q043, Q045, Q048, Q049, Q051).
- **Chunk boundaries shift.** The flag adds 24 chunks over corpus V2 (143 → 167). The prose next to a table now falls into different chunks.

### Proposed adjustment (not implemented; needs owner approval)

1. **Keep both representations.**
   - The page text is chunked exactly as without the flag, so every answer of today keeps its chunk.
   - The row lines become additional units of a `table_row` kind, linked to the chunk that holds the table.
   - Retrieval scores both kinds.
   - Context admission counts a chunk and its own rows as one source: one slot per table, so a row never takes a second slot from the passage it came from.
   - Citations keep the page of the row.
2. **Write the labels once for keyword retrieval.**
   - The keyword index of a row unit holds the cells only. The title and column names are indexed once per table.
   - The embedded text keeps `title | column: cell`.
   - This removes the repeated-label effect.
3. **Rows only where the page text loses the structure.**
   - These are tables with at least 3 columns, or with numeric cells in more than one column.
   - Two-column key-value tables already read correctly in the page text ("Ngày làm việc Thứ Hai - Thứ Sáu").
4. **Measure retrieval before any LLM job.**
   - For the UAT items and natural items with a gold page, check whether the gold page reaches the first 5 sources.
   - Compare: flag off, flag on, and 1-3.
   - Run an LLM job only when 1-3 keeps every gold page that is reached today and adds the table ones (Q041, Q077, ND-003, ND-017).
5. **Template documents** (Q045, Q048, Q049, Q051 with the flag): `docs/design/document-authority.md`. That change does not depend on the table format.
