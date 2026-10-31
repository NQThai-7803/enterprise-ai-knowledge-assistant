# UAT Q001-Q100 eval harness

Used in PROMPT 3d/3e to compare the runtime before and after a change on an isolated stack.
It never touches the V2, AUTH-02 or main stacks.

| File | Purpose |
|---|---|
| `compose.uat-eval.yaml` | Overlay on `compose.yaml` + `compose.uat-corpus-v2.yaml`. Uses its own image (`P3D_BACKEND_IMAGE`), publishes no DB or Redis ports, and puts the API on 127.0.0.1:18190. Always run it with its own `-p` project. |
| `bootstrap_corpus_v2.py` | Uploads UAT Corpus v2 through the API (hash check, READY wait, grants). Writes its runtime manifest to the path you pass, never to the V2 evidence file. |
| `ollama_warmup.py` | One warm-up request with the app's model, `num_ctx` and `keep_alive`, sent before the questions. Its time goes into the run metadata and it is not scored. |
| `run_uat.sh` | One run: metadata, warm-up, the existing runner `tests/acceptance/rag_h5_2_exact_100.py`, then the proxy grade. |
| `grade_proxy.py` | Proxy grade against the TASK-035.3B agent grade: status plus cited document codes. **Not a semantic grade.** |
| `compare_before_after.py` | Splits cases into (a) identical in every run and (b) changed; (b) is split again into b1 (baseline already varied) and b2 (new change). |

The questions, reference grade and manifests live under the git-ignored `artifacts/` directory.
