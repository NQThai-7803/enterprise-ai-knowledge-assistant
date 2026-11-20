# DEC-041 measurement: legacy, s3t and hybrid on the dev sets (2026-11-20)

Branch `feat/hybrid-answer-mode` at 6b28be4, `eval.yml` on GitHub-hosted CPU runners (Ollama
0.40.15, CPU), one job per set, configurations in this order in the same job, same image and
Ollama, 1 run, LLM timeout 600 s:

- `legacy` = `legacy:EVAL_ANSWER_MODE=legacy,EVAL_LLM_MODEL=qwen2.5:3b` (the DEC-040 rollback);
- `s3t` = the DEC-040 default (simple, s1-s3, `qwen3.5-text:4b`);
- `hybrid` = `hybrid:EVAL_ANSWER_MODE=hybrid` (legacy's deterministic route first, else the s3t
  path).

Runs: uat 44694882404, natural 44694886339, rbac 44694890976, relevance 44694894702,
false_refusal 44694898735, false_refusal_v2 44694902590, compound 44694907240; the natural
simple-mode trace for the GPU replay (`s3t` and `hybrid` with `EVAL_ABLATION=simple_trace`, not
scored here) 44694912116. Held-out sets were not used. Ids and counts only; the tables come from
`scripts/eval/route_matrix.py` on the downloaded artifacts.

Categories (`scripts/diagnostics/summarize_ablation.py`): correct; false refusal (an answer was
expected, NO_ANSWER); wrong value (answered, wrong value or documents); false answer (a refusal
or an RBAC negative was expected, an answer came); infra. "Route det / repair / none": the
answer's `answer_route` was the deterministic route before any LLM call / after it / anything
else.

## Results

| Set | Config | Correct | False refusal | Wrong value | False answer | Infra | Leaks | Seconds | p50 ms | Route det / repair / none |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| uat (100) | legacy | 97 | 2 | 1 | 0 | 0 | 0 | 1575 | 714 | 74 / 0 / 26 |
| uat (100) | s3t | 68 | 22 | 10 | 0 | 0 | 0 | 5563 | 42612 | 0 / 0 / 100 |
| uat (100) | hybrid | 92 | 6 | 2 | 0 | 0 | 0 | 2198 | 714 | 74 / 0 / 26 |
| natural (20) | legacy | 3 | 8 | 8 | 1 | 0 | 0 | 706 | 25274 | 4 / 0 / 16 |
| natural (20) | s3t | 8 | 6 | 5 | 1 | 0 | 0 | 1211 | 48383 | 0 / 0 / 20 |
| natural (20) | hybrid | 6 | 5 | 8 | 1 | 0 | 0 | 1043 | 46410 | 4 / 0 / 16 |
| rbac (36) | legacy | 23 | 13 | 0 | 0 | 0 | 0 | 949 | 15150 | 3 / 0 / 33 |
| rbac (36) | s3t | 36 | 0 | 0 | 0 | 0 | 0 | 705 | 11270 | 0 / 0 / 36 |
| rbac (36) | hybrid | 36 | 0 | 0 | 0 | 0 | 0 | 667 | 9190 | 3 / 0 / 33 |
| relevance (25) | legacy | 18 | 3 | 0 | 4 | 0 | 0 | 752 | 15843 | 2 / 0 / 23 |
| relevance (25) | s3t | 23 | 0 | 0 | 2 | 0 | 0 | 746 | 19072 | 0 / 0 / 25 |
| relevance (25) | hybrid | 23 | 0 | 0 | 2 | 0 | 0 | 685 | 18668 | 2 / 0 / 23 |
| false_refusal (20) | legacy | 13 | 1 | 0 | 6 | 0 | 0 | 639 | 19402 | 4 / 0 / 16 |
| false_refusal (20) | s3t | 17 | 0 | 0 | 3 | 0 | 0 | 666 | 24086 | 0 / 0 / 20 |
| false_refusal (20) | hybrid | 17 | 0 | 0 | 3 | 0 | 0 | 571 | 23884 | 4 / 0 / 16 |
| false_refusal_v2 (24) | legacy | 14 | 6 | 0 | 4 | 0 | 0 | 1509 | 53073 | 1 / 0 / 23 |
| false_refusal_v2 (24) | s3t | 21 | 0 | 1 | 2 | 0 | 0 | 1465 | 50790 | 0 / 0 / 24 |
| false_refusal_v2 (24) | hybrid | 21 | 0 | 0 | 3 | 0 | 0 | 1353 | 50758 | 1 / 0 / 23 |
| compound (12) | legacy | 4 | 5 | 1 | 2 | 0 | 0 | 453 | 24090 | 0 / 0 / 12 |
| compound (12) | s3t | 9 | 1 | 0 | 2 | 0 | 0 | 349 | 15833 | 0 / 0 / 12 |
| compound (12) | hybrid | 9 | 1 | 0 | 2 | 0 | 0 | 346 | 15557 | 0 / 0 / 12 |

Route matrix: legacy's route x legacy correct x s3t correct (items).

| Set | Legacy route | Legacy correct | s3t correct | Items |
|---|---|---|---|---:|
| uat | det | False | False | 1 |
| uat | det | True | False | 24 |
| uat | det | True | True | 49 |
| uat | none | False | False | 2 |
| uat | none | True | False | 5 |
| uat | none | True | True | 19 |
| natural | det | False | False | 1 |
| natural | det | False | True | 2 |
| natural | det | True | True | 1 |
| natural | none | False | False | 10 |
| natural | none | False | True | 4 |
| natural | none | True | False | 1 |
| natural | none | True | True | 1 |
| rbac | det | True | True | 3 |
| rbac | none | False | True | 13 |
| rbac | none | True | True | 20 |
| relevance | det | False | False | 1 |
| relevance | det | True | True | 1 |
| relevance | none | False | True | 6 |
| relevance | none | True | False | 1 |
| relevance | none | True | True | 16 |
| false_refusal | det | True | True | 4 |
| false_refusal | none | False | False | 3 |
| false_refusal | none | False | True | 4 |
| false_refusal | none | True | True | 9 |
| false_refusal_v2 | det | True | True | 1 |
| false_refusal_v2 | none | False | False | 1 |
| false_refusal_v2 | none | False | True | 9 |
| false_refusal_v2 | none | True | False | 2 |
| false_refusal_v2 | none | True | True | 11 |
| compound | none | False | False | 2 |
| compound | none | False | True | 6 |
| compound | none | True | False | 1 |
| compound | none | True | True | 3 |

| Set | Route fired (legacy) | Right | Route fired (hybrid) | Right | Hybrid loses to s3t | Hybrid loses to legacy | Route mismatch |
|---|---:|---:|---:|---:|---|---|---|
| uat | 74 | 73 | 74 | 73 | - | Q007 Q033 Q071 Q096 Q097 | - |
| natural | 4 | 1 | 4 | 1 | ND-019 ND-020 | ND-017 | - |
| rbac | 3 | 3 | 3 | 3 | - | - | - |
| relevance | 2 | 1 | 2 | 1 | - | REL-203 | - |
| false_refusal | 4 | 4 | 4 | 4 | - | - | - |
| false_refusal_v2 | 1 | 1 | 1 | 1 | FR2-L06 | FR2-L05 | - |
| compound | 0 | 0 | 0 | 0 | - | CP1-R03 | - |

## Notes

- "Route fired" counts the items whose answer came from the deterministic route before any LLM
  call. legacy and hybrid made the same route decision on every item of every set ("route
  mismatch" is empty); no legacy answer came from a repair after the LLM.
- Route misfires (the route answered and was not right), outside UAT: ND-006
  (`det_direct_value`, wrong value; s3t refused), ND-019 (`det_leave_policy_clause`, wrong
  value; s3t right), ND-020 (`det_attendance_policy`, wrong value; s3t right), REL-103
  (`det_condition_value`, false answer; s3t also a false answer). On UAT: Q066
  (`det_unspecified_value`, wrong in all three configurations).
- UAT route answers use 22 different builders; the most used are `direct_value` (20),
  `attendance_policy` (11), `leave_duration` (7), `role_person` (5), `time_range` (4).
- Hybrid against legacy on UAT: the 5 items it loses (Q007, Q033, Q071, Q096, Q097) are items no
  route answers; legacy's LLM path answered them and the simple path refused.
- The simple path of s3t and hybrid is the same code with the same model in the same job, yet
  2 items outside the route differ: FR2-L01 (s3t wrong value, hybrid right) and FR2-L06 (s3t
  right, hybrid false answer). One run is deterministic for a fixed request order, but a
  different order (hybrid skips the route items) changes some LLM outputs, so a difference of
  1-2 items between s3t and hybrid is within noise.
- Across jobs the same configuration moves by a few items: s3t had 7 / 20 on natural_dev_v1 and
  71 / 100 on UAT in runs 44669873227 / 44669869629, against 8 and 68 here; legacy 96 against 97
  on UAT.
- RBAC: no chunk of a negative's document reached the negative's retrieval in any configuration
  (`rbac_retrieval_check.py`), and no negative answered.
- `no_answer_reasons` is recorded where the API logs a no-answer diagnostic: every simple-path
  refusal, legacy's refusal gates and validator rejections; several legacy NO_ANSWER branches
  (completeness, compound) log none.

## LLM latency on the owner's GPU

Not measured on 2026-11-20: the owner's machine had about 640 MB of RAM available (8029 MB
total, VRAM 3935 MiB free), below what loading the model and its host-side prompt cache needs.
The owner's rule is to stop and not close any application. The replay is ready
(`scripts/eval/gpu_latency_replay.py`): on ND-001 to ND-010, s3t makes 13 LLM calls and hybrid 10
(the route answers ND-004 and ND-006). For comparison only, the end-to-end CI CPU latency of
those 10 items was p50 48.2 s / p95 70.8 s (s3t) and p50 47.4 s / p95 72.9 s (hybrid), trace
overhead included.

To run it when at least about 2 GB of RAM is free (VRAM free at least 3 GB, `qwen3.5-text:4b`
built as in `DEPLOYMENT.md` 3.3, Ollama on 127.0.0.1:11434; no stack is needed):

```powershell
gh run download 44694912116 -D artifacts\dec041-trace
.venv312\Scripts\python.exe scripts\eval\gpu_latency_replay.py `
  s3t=artifacts\dec041-trace\eval-natural-44694912116\s3t\run1\simple_trace.jsonl `
  hybrid=artifacts\dec041-trace\eval-natural-44694912116\hybrid\run1\simple_trace.jsonl `
  --out artifacts\dec041-trace\gpu-latency.json
ollama ps   # the PROCESSOR column must read 100% GPU
```

It prints p50 / p95 of LLM milliseconds per question for each configuration and writes the
per-item calls and times to the JSON.
