# TASK-035.3J — scratch and research disposition

035.3I's read-only full-repository gate found 24 Ruff lint errors in three
untracked root traces and three format failures: the first two traces and
`tests/unit/test_task0353c2f_eval_harness.py`. The filtered 495-file source
snapshot passes lint/format; the **original full repository does not**.
No file was rewritten, moved, deleted, autoformatted, or added to a Ruff
exclusion.

| Exact path | Tracking / observed purpose | Proposed outcome and why | Required approval |
| --- | --- | --- | --- |
| `tmp_org_retrieval_trace.py` | Untracked retrieval-stage diagnostic; imports DB/session and RAG services. Import, B023 loop-binding and long-line findings; format fails. | **Preserve as immutable historical experiment evidence / archive separately** after privacy scan. It is not a current build or CI test. If promoted as maintained tooling, repair the late-binding defect and style in a separate source change. | Engineering owner, privacy reviewer for runtime trace. |
| `tmp_q085_retrieval_trace.py` | Untracked Q085 diagnostic; DB/retrieval trace, seven long lines; format fails. | **Archive separately**, preserving original bytes/hash; exclude from release source because it is a one-case diagnostic, not a generic maintained gate. | Engineering/evidence owner and privacy reviewer. |
| `tmp_runtime_benefit_trace.py` | Untracked benefit runtime diagnostic; import order and long line; format passes. | **Archive separately** with trace provenance; exclude from release source. Do not execute against active V2. | Engineering/evidence owner and privacy reviewer. |
| `tests/unit/test_task0353c2f_eval_harness.py` | Untracked 035.3C.2F research harness; lint passes, format fails. | **Keep as experimental evidence**, not a required RC unit test now. If owner designates it maintained, include and repair formatting before a future commit. | Engineering/test owner. |
| `tests/unit/test_task0353c2e_eval_harness.py` | Untracked 035.3C.2E experimental harness; no reported Ruff failure. | **Keep as experimental evidence** for method reproducibility. | Engineering/evidence owner. |
| `scripts/release/task0353c2e_eval.py`, `scripts/release/task0353c2f_eval.py` | Untracked research evaluators, source of independent semantic experiments. | **Keep as experimental evidence** with their outputs; not production release tooling until separately reviewed. | Engineering/evidence owner. |

Proposed future CI lint contract: run `ruff check .` and `ruff format --check .`
on the **reviewed, versioned source tree**; do not weaken the repository's
Ruff config to conceal current failures. In the present dirty workspace,
report both full-tree FAIL and the 035.3I filtered-source PASS. If research
files are later versioned as maintained tooling, repair them and include
them in the same CI scope. If retained only as private historical evidence,
keep them outside the candidate source checkout with explicit hashes and
retention ownership. This proposal does not change CI today or erase red
answer-safety tests from the future test inventory.
