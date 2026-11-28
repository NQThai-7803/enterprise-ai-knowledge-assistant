# eval-data

Inputs the eval runners need, kept in git so CI (`.github/workflows/eval.yml`) can run them.
Everything here is fictional test data: Nova Digital is a made-up company, the e-mail
addresses use the reserved `.example` domain, and the PDF metadata says "Fictional Sample".

- `corpus-v2/`: the nine PDFs of UAT corpus V2, byte for byte. `SHA256SUMS` matches
  `uat/corpus-v2/manifest.json`; `scripts/eval/bootstrap_corpus_v2.py` checks each hash before
  uploading, and `tests/unit/test_eval_data.py` checks both files agree.
- `corpus-v3/` (2026-11-28, owner's corpus v3 of Nova Digital): 14 PDFs, manifest, mapping,
  checksums and sources; see `corpus-v3/README.md`. No question set uses it yet.
- `uat/questions.json`: Q001-Q100, copied word for word from the CORE list of
  `artifacts/rag-h5-1-stress-uat.py`. It names the account and the environment variable for its
  password (`UAT_STAFF_PASSWORD`); no password is stored.

- `uat/reference-grade.json`: the manually reviewed TASK-035.3B grade of Q001-Q100 (status, answer and cited
  documents per question), and `uat/reference-runtime-manifest.json`: the V2 document ids it cites. Both are
  copies from `artifacts/`; `scripts/eval/grade_proxy.py` uses them to grade UAT runs on Actions.
- `uat/retrieval-gold.json`: the document and page each reviewed answer cited, for the oracle and
  retrieval-gate ablations (`scripts/diagnostics/build_oracle.py`).
- `uat/gold.lock`: SHA-256 of `reference-grade.json` and `retrieval-gold.json`, with the owner's
  approval. `grade_proxy.py` and `build_oracle.py` refuse a file that differs from it. Q044 was moved
  from the template UAT-LEAVE-AUTHORITY-001 to ND-HR-004 page 6 on 2026-11-18 (DEC-033); the change
  is recorded in both files.

These are dev sets. Held-out sets never go here. Any edit to a file here changes what a
measurement means: record it in DECISIONS.md and re-run the baseline in the same batch.
