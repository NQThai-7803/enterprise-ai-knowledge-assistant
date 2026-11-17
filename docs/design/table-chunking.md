# Table chunking: diagnosis and proposal (no behaviour change)

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

## Proposal: one unit per table row (not implemented)

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
