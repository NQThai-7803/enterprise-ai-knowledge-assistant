# Corpus v3 (Nova Digital)

The owner's corpus v3, 2026-11-28. Fictional company, `.example` e-mail addresses.

- 14 PDFs, 13 codes: ND-HR-003 has version 2.0 (effective 2026-12-01 to 2026-12-31) and 2.1 (from 2027-01-01).
- `manifest.json`: code, version, classification, visibility, department, grants (labels), effective dates, lifecycle, supersedes. Classification maps to visibility, with one exception the owner decided on 2026-11-28 (the manifest notes say so): ND-COMP-001 is CONFIDENTIAL but PRIVATE, granted by name.
  - The repo copy is the reference. The owner's folder copy is to be brought in line with it.
- `SHA256SUMS`: the PDFs and `manifest.json`.
- `MAPPING.md`: where each corpus V2 section went in v3.
  - **The table of values to watch when writing gold is kept outside the repo only**, in the owner's folder: the repo holds no question or gold text (owner, 2026-11-28).
- `src/`: the markdown sources and the owner's `build.py` and `stamp.py`, byte for byte (not linted). `build.py` expects `src/*.md` and `pdf/` beside it: lay them out so to rebuild.
- Loading: `scripts/eval/bootstrap_corpus_v3.py`. It creates the departments and the 10 accounts, uploads by the manifest, grants by its labels, and checks the access matrix against the manifest and ND-ORG-001 section 7.
  - Never on one stack with corpus V2: both use the same document codes.
- Eval stacks on this corpus layer `scripts/eval/compose.corpus-v3-eval.yaml`: retrieval ranks versions as of `EVAL_AS_OF_DATE` (default 2026-12-15), and every report states that date.
