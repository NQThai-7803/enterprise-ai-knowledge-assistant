# eval-data

Inputs the eval runners need, kept in git so CI (`.github/workflows/eval.yml`) can run them.
Everything here is fictional test data: Nova Digital is a made-up company, the e-mail
addresses use the reserved `.example` domain, and the PDF metadata says "Fictional Sample".

- `corpus-v2/`: the nine PDFs of UAT corpus V2, byte for byte. `SHA256SUMS` matches
  `uat/corpus-v2/manifest.json`; `scripts/eval/bootstrap_corpus_v2.py` checks each hash before
  uploading, and `tests/unit/test_eval_data.py` checks both files agree.
- `uat/questions.json`: Q001-Q100, copied word for word from the CORE list of
  `artifacts/rag-h5-1-stress-uat.py`. It names the account and the environment variable for its
  password (`UAT_STAFF_PASSWORD`); no password is stored.

- `uat/reference-grade.json`: the manually reviewed TASK-035.3B grade of Q001-Q100 (status, answer and cited
  documents per question), and `uat/reference-runtime-manifest.json`: the V2 document ids it cites. Both are
  copies from `artifacts/`; `scripts/eval/grade_proxy.py` uses them to grade UAT runs on Actions.

These are dev sets. Held-out sets never go here. Any edit to a file here changes what a
measurement means: record it in DECISIONS.md and re-run the baseline in the same batch.
