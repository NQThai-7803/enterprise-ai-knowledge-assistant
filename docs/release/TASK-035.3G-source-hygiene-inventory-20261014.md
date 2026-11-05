# TASK-035.3G — source-hygiene disposition inventory

Date: 2026-10-14. `python -m ruff check --no-cache .` exited 1 with 24
errors. `python -m ruff format --check --no-cache .` exited 1 with three
unformatted files (412 already formatted). Neither command used `--fix`.
No file was removed, moved, reformatted or excluded; the dirty working tree
and failed 035.3B candidate are preserved.

| File | Git/source category | Observed failure | Recommended disposition (not executed) |
| --- | --- | --- | --- |
| `tmp_org_retrieval_trace.py` | Untracked root-level experimental retrieval trace, not application module | Ruff import order, B023 loop bindings, line lengths; format check | **Preserve as explicit experimental artifact** pending owner review; if promoted to release source, include and repair. Do not call disposable. |
| `tmp_q085_retrieval_trace.py` | Untracked root-level experimental trace | Ruff line lengths; format check | **Preserve as explicit experimental artifact** pending owner review; consider separately archiving after evidence provenance is recorded. |
| `tmp_runtime_benefit_trace.py` | Untracked root-level runtime diagnostic trace | Ruff import order and line length; formatter already accepts it | **Preserve as explicit experimental artifact** pending owner review; do not run against protected V2 in this task. |
| `tests/unit/test_task0353c2f_eval_harness.py` | Untracked release/evaluation harness, not a production app module | Format check only; Ruff check accepts it | **Include and repair** under a reviewed test/evidence-source change, or explicitly preserve as research artifact if not an RC gate. Do not silently omit. |

All 24 lint errors are in the three `tmp_*` traces, not in `app/` or the
frontend. The format failure also includes the 3C.2F harness. Existing
generated `artifacts/` and `frontend/test-results/` are Git-ignored;
`frontend/node_modules/` and `frontend/dist/` are ignored as well. The new
035.3G build is local, ignored evidence; the new qualification test and
release reports are untracked until a separately authorized versioning step.
No reviewed Ruff exclusion configuration was added. Repository-wide quality
gates remain **FAIL** pending an explicit source-hygiene disposition.
