# TASK-035.3I — source-hygiene disposition matrix

Read-only rerun: full repository `ruff check --no-cache .` **FAIL**, 24
findings, all in the three untracked root traces. `ruff format --check
--no-cache .` **FAIL**, three files; 412 already formatted. No `--fix`,
configuration change, deletion or original-source reformat occurred.

| Path | Finding and purpose | Candidate / reproducibility decision |
| --- | --- | --- |
| `tmp_org_retrieval_trace.py` | Import order, late-bound loop variables, long lines; formatting. Untracked live/retrieval diagnostic. | **ARCHIVE_SEPARATELY** after sensitive-data review; exclude from candidate with explicit reason. Preserve original. If promoted, repair B023 and style under separate authorization. |
| `tmp_q085_retrieval_trace.py` | Seven long-line findings; formatting. Untracked Q085 diagnostic. | **ARCHIVE_SEPARATELY** after review; exclude from candidate, retain original/evidence provenance. |
| `tmp_runtime_benefit_trace.py` | Import order and long line; formatter accepts. Untracked runtime diagnostic, not unit gate. | **ARCHIVE_SEPARATELY** after review; exclude from candidate, never run against protected V2 in this checkpoint. |
| `tests/unit/test_task0353c2f_eval_harness.py` | Ruff lint accepts; formatting fails. Untracked experimental evaluation harness. | **INCLUDE_AS_EXPERIMENTAL** in a separately governed research/evidence set, not this candidate copy. If made a required RC gate, **INCLUDE_AND_REPAIR** before a future candidate. Owner must select. |

The source-copy decision is not a Ruff exclusion rule. The reviewed archive
passes Ruff check and format because its inclusion list omits separately
classified research/diagnostic files; the **full original repository remains
FAIL**. Two other 035.3C.2E/2F evaluation scripts and the 2E harness were
also preserved as experimental rather than silently treated as production
tests. Known red multilingual/unsupported-answer contracts remain in the
candidate test inventory and keep the safety blocker visible.
