#!/usr/bin/env bash
# One measurement batch inside a single CI job (DEC-011, DEC-013, DEC-016): every flag
# configuration runs RUNS times on the same image and the same Ollama, interleaved
# (run 1 of every configuration, then run 2), and each later configuration is compared with
# the first one.
#
#   bash scripts/eval/ci_batch.sh <set> "<configs>" <runs> <out> [case ids...]
#
# set:     uat | rbac | relevance | false_refusal | false_refusal_v2
# configs: ";"-separated "name" or "name:EVAL_VAR=value,EVAL_VAR=value", first one is the baseline,
#          e.g. "base; f303:EVAL_SHORT_ANSWER_QUESTION_TERMS=true". EVAL_* variables are read by
#          scripts/eval/compose.uat-eval.yaml; EVAL_UAT_UNACCENTED=1 asks UAT without diacritics.
# Needs: the eval stack started by the workflow (PROJECT, FILES), Ollama with EVAL_OLLAMA_LOG.
set -uo pipefail
SET="$1"; CONFIGS="$2"; RUNS="$3"; OUT="$4"; shift 4
CASE_IDS=("$@")
: "${PROJECT:?}" "${EVAL_OLLAMA_LOG:?}"
read -r -a FILES <<< "${COMPOSE_FILES:?space-separated -f arguments}"
API=http://127.0.0.1:18190
mkdir -p "$OUT"

case "$SET" in uat|rbac|relevance|false_refusal|false_refusal_v2) ;; *) echo "unknown set $SET"; exit 2 ;; esac
[[ "$RUNS" =~ ^[12]$ ]] || { echo "runs must be 1 or 2"; exit 2; }

NAMES=(); ENVS=()
IFS=';' read -r -a ENTRIES <<< "$CONFIGS"
for entry in "${ENTRIES[@]}"; do
  entry="$(echo "$entry" | tr -d ' ')"
  [ -n "$entry" ] || continue
  name="${entry%%:*}"; vars=""; [[ "$entry" == *:* ]] && vars="${entry#*:}"
  [[ "$name" =~ ^[a-z0-9_-]{1,32}$ ]] || { echo "bad config name: $name"; exit 2; }
  IFS=',' read -r -a PAIRS <<< "$vars"
  for pair in "${PAIRS[@]}"; do
    [[ "$pair" =~ ^EVAL_[A-Z0-9_]+=[A-Za-z0-9_./:-]+$ ]] || { echo "bad setting: $pair"; exit 2; }
    # Git Bash rewrites /path arguments to C:/Program Files/Git/path when dispatching from Windows.
    [[ "${pair#*=}" =~ ^[A-Za-z]:/ ]] && { echo "host-rewritten path in $pair (MSYS_NO_PATHCONV=1)"; exit 2; }
  done
  NAMES+=("$name"); ENVS+=("$vars")
done
[ "${#NAMES[@]}" -ge 1 ] || { echo "no configuration"; exit 2; }

backend() {
  python - "$EVAL_OLLAMA_LOG" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
text = text[text.rfind("Listening on"):]
print("+".join(sorted({m.upper() for m in re.findall(r'msg="inference compute".*?library=(\S+)', text)})) or "UNKNOWN")
PY
}

start_api() {  # $1 = comma-separated EVAL_ settings of the configuration
  (
    IFS=',' read -r -a PAIRS <<< "$1"
    for pair in "${PAIRS[@]}"; do export "${pair?}"; done
    docker compose -p "$PROJECT" "${FILES[@]}" up -d --no-deps --no-build --force-recreate api >/dev/null
  )
  for _ in $(seq 1 90); do
    [ "$(docker inspect "$PROJECT-api-1" --format '{{.State.Health.Status}}')" = healthy ] && return 0
    sleep 5
  done
  echo "api not healthy"; return 1
}

run_one() {  # $1 = config index, $2 = run number
  local name="${NAMES[$1]}" vars="${ENVS[$1]}" dir
  dir="$OUT/$name/run$2"; mkdir -p "$dir"
  start_api "$vars" || return 1
  if [[ ",$vars," == *",EVAL_ABLATION="* ]] \
    && ! docker logs "$PROJECT-api-1" 2>&1 | grep -q "ABLATION applied"; then
    echo "ablation not applied in the API" | tee "$dir/runner.log"; return 1
  fi
  ( # the runner sees the configuration too (e.g. EVAL_EXPECTED_RERANKER_MODE)
  IFS=',' read -r -a PAIRS <<< "$vars"
  for pair in "${PAIRS[@]}"; do export "${pair?}"; done
  docker inspect "$PROJECT-api-1" --format '{{range .Config.Env}}{{println .}}{{end}}' \
    | grep -E '^(RAG_|RERANKER_|EVAL_ABLATION|EVAL_ORACLE|LLM_OLLAMA_MODEL)' | sort > "$dir/flags.txt"
  python scripts/eval/ollama_warmup.py "$dir/warmup.json" --base-url http://127.0.0.1:11434 \
    --model "${EVAL_LLM_MODEL:-qwen2.5:3b}" --num-ctx 8192 --keep-alive 10m --seed 20261031 >/dev/null
  local started; started=$(date +%s)
  case "$SET" in
    uat)
      local args=(--output "$dir/runtime_results.json")
      for id in "${CASE_IDS[@]}"; do args+=(--case "$id"); done
      [[ ",$vars," == *",EVAL_UAT_UNACCENTED=1,"* ]] && args+=(--unaccented)
      python tests/acceptance/rag_h5_2_exact_100.py "${args[@]}" > "$dir/runner.log" 2>&1 \
        || echo "runner exit $?" >> "$dir/runner.log"
      python scripts/eval/grade_proxy.py eval-data/uat/reference-grade.json \
        eval-data/uat/reference-runtime-manifest.json "$OUT/runtime-manifest.json" \
        "$dir/runtime_results.json" "$dir/results.json" >> "$dir/runner.log" 2>&1 ;;
    rbac)
      python scripts/eval/run_rbac_dev.py --output "$dir/results.json" > "$dir/runner.log" 2>&1 \
        || echo "runner exit $?" >> "$dir/runner.log"
      python scripts/diagnostics/rbac_retrieval_check.py --container "$PROJECT-api-1" \
        --output "$dir/retrieval.json" >> "$dir/runner.log" 2>&1 \
        || echo "retrieval check exit $?" >> "$dir/runner.log" ;;
    relevance)
      python scripts/eval/run_answer_relevance_dev.py --output "$dir/results.json" \
        > "$dir/runner.log" 2>&1 || echo "runner exit $?" >> "$dir/runner.log" ;;
    false_refusal|false_refusal_v2)
      local version=v1; [ "$SET" = false_refusal_v2 ] && version=v2
      python scripts/eval/run_answer_relevance_dev.py --set "false_refusal_dev_$version" \
        --output "$dir/results.json" > "$dir/runner.log" 2>&1 \
        || echo "runner exit $?" >> "$dir/runner.log" ;;
  esac
  echo "seconds=$(( $(date +%s) - started ))" > "$dir/timing.txt"
  )
  echo "$(date -u +%FT%TZ) $name run$2 $(cat "$dir/timing.txt") $(tail -1 "$dir/runner.log")" \
    | tee -a "$OUT/batch.log"
}

if [[ "$CONFIGS" == *EVAL_ABLATION=*oracle* ]]; then  # gold map, mounted read-only at /oracle
  python scripts/diagnostics/build_oracle.py --set "$SET" --output "${ORACLE_DIR:?}/oracle.json" \
    | tee -a "$OUT/batch.log"
fi

python - "$OUT/batch.json" "$SET" "$CONFIGS" "$RUNS" "$(backend)" <<'PY'
import json, subprocess, sys
from datetime import UTC, datetime
out, set_name, configs, runs, backend = sys.argv[1:]
version = subprocess.run(["ollama", "--version"], capture_output=True, text=True).stdout.strip()
json.dump({
    "set": set_name, "configs": configs, "runs": int(runs),
    "ollama_backend": backend, "ollama_version": version,
    "git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
    "started_at": datetime.now(UTC).isoformat(),
    "rule": "DEC-016: baseline and candidates in this one job; never compared with local runs",
}, open(out, "w", encoding="utf-8"), indent=1)
PY

for run in $(seq 1 "$RUNS"); do
  for index in "${!NAMES[@]}"; do run_one "$index" "$run" || echo "config ${NAMES[$index]} run$run failed" | tee -a "$OUT/batch.log"; done
done

# Compare every later configuration with the first one (needs 2 runs per side).
KIND="$SET"; [[ "$SET" == false_refusal* ]] && KIND=relevance
if [ "$RUNS" = 2 ]; then
  base="${NAMES[0]}"
  for name in "${NAMES[@]:1}"; do
    python scripts/eval/compare_flag_runs.py "$KIND" "$OUT/$base/run1/results.json" \
      "$OUT/$base/run2/results.json" "$OUT/$name/run1/results.json" "$OUT/$name/run2/results.json" \
      > "$OUT/compare-$name.json" 2>&1 || true
  done
fi
python - "$OUT" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
meta = json.loads((out / "batch.json").read_text(encoding="utf-8"))
from datetime import UTC, datetime
meta["finished_at"] = datetime.now(UTC).isoformat()
(out / "batch.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
lines = [f"# Batch {meta['set']} ({meta['ollama_backend']}, Ollama {meta['ollama_version']})", ""]
for path in sorted(out.glob("*/run*/results.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    summary = data.get("summary", {})
    shown = {k: (len(v) if isinstance(v, list) else v) for k, v in summary.items() if k != "note"}
    if meta["set"] == "rbac":
        cases = data.get("cases", [])
        shown["api_leaks"] = sum(bool(c.get("leak_reasons")) for c in cases)
        shown["controls_passed"] = sum(bool(c.get("control_passed")) for c in cases)
        retrieval = path.with_name("retrieval.json")
        if retrieval.is_file():
            rows = json.loads(retrieval.read_text(encoding="utf-8")).values()
            shown["retrieval_leaks"] = sum(row["leak"] for row in rows)
            shown["retrieval_conclusive"] = f"{sum(row['conclusive'] for row in rows)}/{len(rows)}"
        else:
            shown["retrieval_leaks"] = "NOT RUN"
    lines.append(f"- {path.parent.parent.name}/{path.parent.name}: " + json.dumps(shown))
for path in sorted(out.glob("compare-*.json")):
    lines += ["", f"## {path.stem}", "```", path.read_text(encoding="utf-8")[:4000], "```"]
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
PY
