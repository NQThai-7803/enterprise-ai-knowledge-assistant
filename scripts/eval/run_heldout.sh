#!/usr/bin/env bash
# One held-out v1 run against the isolated UAT eval stack (baseline v2 protocol): metadata,
# Ollama warm-up, then the frozen set as each item's role, with a host resource sample per item.
#
#   EVAL_BACKEND_IMAGE=eaka-backend:<tag> EVAL_PASSWORD_STAFF=... EVAL_PASSWORD_MANAGER=... \
#   EVAL_PASSWORD_ADMIN=... bash scripts/eval/run_heldout.sh <out dir> [all|part1|part2]
#
# part1 writes metadata, warms up and runs HO-001..HO-020; part2 resumes the rest from the same
# checkpoint. Passwords are read from the environment and never written.
set -euo pipefail
OUT="$1"
PHASE="${2:-all}"
PROJECT="${EVAL_PROJECT:-eaka-p3d-uat}"
OLLAMA="${EVAL_OLLAMA:-http://127.0.0.1:11434}"
export P3D_BACKEND_IMAGE="${EVAL_BACKEND_IMAGE:?set EVAL_BACKEND_IMAGE to the backend image tag}"
COMPOSE=(docker compose -p "$PROJECT" -f compose.yaml -f compose.uat-corpus-v2.yaml
  -f scripts/eval/compose.uat-eval.yaml)
mkdir -p "$OUT"
API_CID=$("${COMPOSE[@]}" ps -q api)
env_of() {
  docker inspect "$API_CID" --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n "s/^$1=//p"
}
RUNNER=(env RAG_ACCEPTANCE_BASE_URL="${EVAL_API:-http://127.0.0.1:18190}" EVAL_OLLAMA="$OLLAMA"
  PYTHONIOENCODING=utf-8 python scripts/eval/run_heldout.py --monitor
  --output "$OUT/runtime_results.json")

if [ "$PHASE" != "part2" ]; then
API_IMAGE=$(docker inspect "$API_CID" --format '{{.Image}}')
python - "$OUT/metadata.json" <<PY
import json, sys
json.dump({
    "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "repo_head": "$(git rev-parse HEAD)",
    "repo_dirty": "$(git status --porcelain --untracked-files=no | wc -l | tr -d ' ')",
    "api_image": "$API_IMAGE",
    "api_image_commit": "$(docker image inspect "$API_IMAGE" --format '{{index .Config.Labels "eaka.commit"}}')",
    "heldout_sha256": "$(sha256sum docs/eval/heldout-v1.yaml | cut -d' ' -f1)",
    "llm": {"provider": "$(env_of LLM_PROVIDER)", "model": "$(env_of LLM_OLLAMA_MODEL)",
            "num_ctx_option": "$(env_of LLM_OLLAMA_NUM_CTX)", "seed": "$(env_of LLM_SEED)",
            "temperature": "$(env_of LLM_TEMPERATURE)", "base_url": "$(env_of LLM_OLLAMA_BASE_URL)"},
    "flags_set_on_api": {
        "LLM_PROMPT_TRUNCATION_GUARD_ENABLED": "$(env_of LLM_PROMPT_TRUNCATION_GUARD_ENABLED)",
        "RAG_SEMANTIC_EXACT_PERMITTED_KNN_ENABLED": "$(env_of RAG_SEMANTIC_EXACT_PERMITTED_KNN_ENABLED)",
        "WEB_SEARCH_ENABLED": "$(env_of WEB_SEARCH_ENABLED)",
    },
    "compose_project": "$PROJECT",
    "runner": "scripts/eval/run_heldout.py",
}, open(sys.argv[1], "w", encoding="utf-8"), indent=1)
PY
python scripts/eval/ollama_warmup.py "$OUT/warmup.json" --base-url "$OLLAMA" \
  --model "$(env_of LLM_OLLAMA_MODEL)" --num-ctx 8192 --keep-alive 10m --seed "$(env_of LLM_SEED)"
curl -s "$OLLAMA/api/ps" > "$OUT/ollama_ps_after_warmup.json"
fi

case "$PHASE" in
  part1)
    CASES=(); for i in $(seq -w 1 20); do CASES+=(--case "HO-0$i"); done
    "${RUNNER[@]}" "${CASES[@]}" >> "$OUT/runner.log" 2>&1 || echo "runner exit $?" >> "$OUT/runner.log" ;;
  part2)
    "${RUNNER[@]}" --resume >> "$OUT/runner.log" 2>&1 || echo "runner exit $?" >> "$OUT/runner.log" ;;
  *)
    "${RUNNER[@]}" > "$OUT/runner.log" 2>&1 || echo "runner exit $?" >> "$OUT/runner.log" ;;
esac
