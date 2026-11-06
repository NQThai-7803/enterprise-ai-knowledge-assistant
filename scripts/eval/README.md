# UAT Q001-Q100 eval harness

Used in PROMPT 3d/3e to compare the runtime before and after a change on an isolated stack.
It never touches the V2, AUTH-02 or main stacks.

| File | Purpose |
|---|---|
| `compose.uat-eval.yaml` | Overlay on `compose.yaml` + `compose.uat-corpus-v2.yaml`. Uses its own image (`P3D_BACKEND_IMAGE`), publishes no DB or Redis ports, and puts the API on 127.0.0.1:18190. Always run it with its own `-p` project. |
| `bootstrap_corpus_v2.py` | Uploads UAT Corpus v2 through the API (hash check, READY wait, grants). Writes its runtime manifest to the path you pass, never to the V2 evidence file. |
| `ollama_warmup.py` | One warm-up request with the app's model, `num_ctx` and `keep_alive`, sent before the questions. Its time goes into the run metadata and it is not scored. |
| `run_uat.sh` | One run: metadata, warm-up, the existing runner `tests/acceptance/rag_h5_2_exact_100.py`, then the proxy grade. The runner retries each `INFRA_ERROR` case once at the end of the run (`--resume` does not retry it again); `metadata.json` records `infra_error_cases`, `infra_error_retried_cases` and `infra_error_ids`. |
| `eval_client.py` | HTTP client of the runner: one keep-alive `httpx.Client` per run. Transport errors, timeouts, 5xx, a 2xx without an answer body and a 429 after its retries are `INFRA_ERROR`, never `OK`; other 4xx are `HTTP_ERROR`. |
| `grade_proxy.py` | Proxy grade against the TASK-035.3B agent grade: status plus cited document codes. **Not a semantic grade.** `INFRA_ERROR` cases are excluded from the score; the summary reports `scored_cases`, `excluded_infra_error` and their IDs. |
| `compare_before_after.py` | Splits cases into (a) identical in every run and (b) changed; (b) is split again into b1 (baseline already varied) and b2 (new change). |
| `reranker_check.py` | Reads `reranker_mode` from `GET /health/ready` and refuses a run whose mode differs from `--expected-reranker-mode` (or `EVAL_EXPECTED_RERANKER_MODE`), unless `--allow-reranker-fallback` accepts `lexical_fallback`. `run_uat.sh` and `run_heldout.sh` expect `lexical_fallback` on the current stacks and write the mode to the metadata. |
| `metrics.py` | Per-run `permission_leak_count`, `false_answer_rate`, `false_refusal_rate`, `answer_accuracy`, `citation_accuracy`. Held-out uses the owner's labels and refuses blank ones; dev uses `grade_proxy.py` output, is marked `proxy` and reports the leak count as null (not measured). |
| `run_rbac_dev.py` | RBAC dev set from `tests/acceptance/rbac_dev_v1.yaml` on the isolated stack `eaka-rbac-dev`: 18 questions from accounts without access, each with a control from an account with access. Controls run first, then the grant is revoked, then the negatives. Score with `metrics.py rbac`. |

| `run_answer_relevance_dev.py` | Frozen relevance dev set from `tests/acceptance/answer_relevance_dev_v1.yaml` on the isolated stack `eaka-relevance-dev`: questions the documents do not answer, with similar ones they do. Refuses a set that differs from its lock. |
| `branch_counters.py` | Reads `enterprise_ai_rag_answer_branch_total` from `GET /metrics`. The relevance, RBAC and UAT runners record the change over the run as `branch_counters`; `null` means not measured. |
| `compare_flag_runs.py` | Compares two baseline runs with two runs of a flag on the relevance, RBAC or UAT set. A case counts as changed only when both sides agree within themselves and differ from each other. |

RBAC dev stack (never add these documents to the main corpus):

```bash
export P3D_BACKEND_IMAGE=eaka-backend:<tag>
docker volume create eaka-rbac-dev_model_cache   # copy the e5 cache in from another stack
docker compose -p eaka-rbac-dev -f compose.yaml -f compose.uat-corpus-v2.yaml \
  -f scripts/eval/compose.uat-eval.yaml up -d --no-build
python scripts/eval/run_rbac_dev.py --output artifacts/rbac-dev/run/runtime_results.json
python scripts/eval/metrics.py rbac artifacts/rbac-dev/run/runtime_results.json
python scripts/diagnostics/rbac_retrieval_check.py --container eaka-rbac-dev-api-1 \
  --output artifacts/rbac-dev/retrieval.json
```

The runner needs `EVAL_PASSWORD_ADMIN`, `_MANAGER`, `_STAFF` and `_OPS` in the environment and `EVAL_EXPECTED_RERANKER_MODE=lexical_fallback` on a stack without cross-encoder weights. Keep the same `_OPS` value between runs: it is set when the account is created.

| `question_leak.py` | Hashed word 4-grams of dev and held-out questions in `question_fingerprints.json`, no question text. `check` compares added `app/` lines, `overlap` compares the two sets; both exit 2 when the source is missing, empty or stale. |

The questions, reference grade and manifests live under the git-ignored `artifacts/` directory.
