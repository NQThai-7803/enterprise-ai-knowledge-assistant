#!/usr/bin/env bash
# One Q001-Q100 run against an isolated UAT eval stack, with an Ollama warm-up, metadata and a
# proxy grade. Run from the repository root (Git Bash on Windows or any POSIX shell).
#
#   EVAL_BACKEND_IMAGE=eaka-backend:<tag> bash scripts/eval/run_uat.sh artifacts/<task>/<run>
#
# Inputs that are git-ignored and must exist locally: artifacts/rag-h5-1-stress-uat.py (questions),
# artifacts/task-035-3b-20261013/case-level-semantic-citation-grade.json (reference grade),
# artifacts/uat-corpus-v2/runtime-manifest.json (reference IDs) and the stack's own runtime
# manifest written by scripts/eval/bootstrap_corpus_v2.py.
set -euo pipefail
OUT="$1"
PROJECT="${EVAL_PROJECT:-eaka-p3d-uat}"
API="${EVAL_API:-http://127.0.0.1:18190}"
OLLAMA="${EVAL_OLLAMA:-http://127.0.0.1:11434}"
STACK_MANIFEST="${EVAL_STACK_MANIFEST:-artifacts/prompt3d/uat-stack/runtime-manifest.json}"
export P3D_BACKEND_IMAGE="${EVAL_BACKEND_IMAGE:?set EVAL_BACKEND_IMAGE to the backend image tag}"
COMPOSE=(docker compose -p "$PROJECT" -f compose.yaml -f compose.uat-corpus-v2.yaml
  -f scripts/eval/compose.uat-eval.yaml)
mkdir -p "$OUT"

API_CID=$("${COMPOSE[@]}" ps -q api)
psql_value() {
  "${COMPOSE[@]}" exec -T postgres psql -U app_user -d enterprise_ai -tAc "$1" | tr -d '\r'
}
API_IMAGE=$(docker inspect "$API_CID" --format '{{.Image}}')
LLM_MODEL=$(docker inspect "$API_CID" --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | sed -n 's/^LLM_OLLAMA_MODEL=//p')
NUM_CTX=$(docker inspect "$API_CID" --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | sed -n 's/^LLM_OLLAMA_NUM_CTX=//p')
KEEP_ALIVE=$(docker inspect "$API_CID" --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | sed -n 's/^LLM_OLLAMA_KEEP_ALIVE=//p')
python - "$OUT/metadata.json" <<EOF
import json, sys
json.dump({
    "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "repo_head": "$(git rev-parse HEAD)",
    "repo_dirty": "$(git status --porcelain --untracked-files=no | wc -l | tr -d ' ')",
    "api_image": "$API_IMAGE",
    "api_image_commit": "$(docker image inspect "$API_IMAGE" --format '{{index .Config.Labels "eaka.commit"}}')",
    "postgres_image": "$(docker inspect "$("${COMPOSE[@]}" ps -q postgres)" --format '{{.Image}}')",
    "pgvector_extversion": "$(psql_value "SELECT extversion FROM pg_extension WHERE extname='vector'")",
    "postgres_server_version": "$(psql_value 'SHOW server_version')",
    "llm": {"provider": "ollama", "model": "$LLM_MODEL", "num_ctx": "$NUM_CTX", "keep_alive": "$KEEP_ALIVE"},
    "compose_project": "$PROJECT",
    "runner": "tests/acceptance/rag_h5_2_exact_100.py",
}, open(sys.argv[1], "w", encoding="utf-8"), indent=1)
EOF

# Warm-up (not scored): load the model with the app's options before the first question.
python scripts/eval/ollama_warmup.py "$OUT/warmup.json" --base-url "$OLLAMA" \
  --model "${LLM_MODEL:-qwen2.5:3b}" --num-ctx "${NUM_CTX:-8192}" --keep-alive "${KEEP_ALIVE:-10m}"

RAG_ACCEPTANCE_BASE_URL=$API PYTHONIOENCODING=utf-8 python tests/acceptance/rag_h5_2_exact_100.py \
  --output "$OUT/runtime_results.json" > "$OUT/runner.log" 2>&1 || echo "runner exit $?" >> "$OUT/runner.log"

python - "$OUT" <<'EOF'
import json, sys
from datetime import UTC, datetime
out = sys.argv[1]
meta = json.load(open(f"{out}/metadata.json", encoding="utf-8"))
meta["warmup"] = json.load(open(f"{out}/warmup.json", encoding="utf-8"))
meta["finished_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
json.dump(meta, open(f"{out}/metadata.json", "w", encoding="utf-8"), indent=1)
EOF
PYTHONIOENCODING=utf-8 python scripts/eval/grade_proxy.py \
  artifacts/task-035-3b-20261013/case-level-semantic-citation-grade.json \
  artifacts/uat-corpus-v2/runtime-manifest.json "$STACK_MANIFEST" \
  "$OUT/runtime_results.json" "$OUT/grade_proxy.json"
