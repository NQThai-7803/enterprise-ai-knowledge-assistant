#!/usr/bin/env bash
# One measurement batch inside a single CI job (DEC-011, DEC-013, DEC-016): every flag
# configuration runs RUNS times on the same image and the same Ollama, interleaved
# (run 1 of every configuration, then run 2), and each later configuration is compared with
# the first one.
#
#   bash scripts/eval/ci_batch.sh [--validate-only] <set> "<configs>" <runs> <out> [case ids...]
#
# --validate-only: resolve the set, parse the configurations, count the questions and check the
#          eval accounts they need, then stop: no stack, no API, no model. Every run does it first.
# set:     a name of scripts/eval/batch_sets.py: uat | rbac | relevance | false_refusal |
#          false_refusal_v2 | compound | natural | heldout_v3 (only from heldout-v3.yml)
# configs: ";"-separated "name" or "name:EVAL_VAR=value,EVAL_VAR=value", first one is the baseline,
#          e.g. "base; f303:EVAL_SHORT_ANSWER_QUESTION_TERMS=true". EVAL_* variables are read by
#          scripts/eval/compose.uat-eval.yaml; EVAL_UAT_UNACCENTED=1 asks UAT without diacritics.
# Needs: the eval stack started by the workflow (PROJECT, FILES), Ollama with EVAL_OLLAMA_LOG.
set -uo pipefail
VALIDATE_ONLY=""; [ "${1:-}" = --validate-only ] && { VALIDATE_ONLY=1; shift; }
SET="$1"; CONFIGS="$2"; RUNS="$3"; OUT="$4"; shift 4
# Held-out v3 (DEC-035) runs only from the gated .github/workflows/heldout-v3.yml.
[ "$SET" != heldout_v3 ] || [ "${HELDOUT_V3_APPROVED:-}" = 1 ]   || { echo "heldout_v3 runs only from heldout-v3.yml after its gate"; exit 2; }
CASE_IDS=("$@")
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
  # EVAL_S3T=1: the DEC-029/034 candidate's answer path, s3 with the simple-mode trace (keeps
  # four configurations under the 400-character concurrency group; name the model explicitly).
  [[ ",$vars," == *",EVAL_S3T=1,"* ]] && vars+=",EVAL_ABLATION=simple_trace,EVAL_SIMPLE_LEVEL=3"
  # EVAL_SIMPLE_LEVEL=n: simple mode with s1..sn on and the later ones off
  # (docs/design/simple-answer-mode.md; the eval stack's defaults have s1-s3 on since DEC-040), so
  # that a configuration stays short; the configs input is part of a 400-character concurrency group.
  if [[ ",$vars," =~ ,EVAL_SIMPLE_LEVEL=([1-9]), ]]; then
    vars+=",EVAL_ANSWER_MODE=simple"
    for n in 1 2 3 4 5; do
      if [ "$n" -le "${BASH_REMATCH[1]}" ]; then vars+=",EVAL_SIMPLE_S$n=true"; else vars+=",EVAL_SIMPLE_S$n=false"; fi
    done
  fi
  # EVAL_TABLE_ROWS=true acts at ingestion: these configurations run last, on a corpus ingested
  # again with the flag on (reingest_table_rows), so they must follow every other one.
  if [[ ",$vars," == *",EVAL_TABLE_ROWS=true,"* ]]; then
    ROWS_FROM="${ROWS_FROM:-${#NAMES[@]}}"
  elif [ -n "${ROWS_FROM:-}" ]; then
    echo "configuration $name without EVAL_TABLE_ROWS follows one with it"; exit 2
  fi
  NAMES+=("$name"); ENVS+=("$vars")
done
[ "${#NAMES[@]}" -ge 1 ] || { echo "no configuration"; exit 2; }
# A second run of the baseline would find the re-ingested corpus.
[ -n "${ROWS_FROM:-}" ] && [ "$RUNS" != 1 ] && { echo "EVAL_TABLE_ROWS needs runs=1"; exit 2; }
# The set, its questions and accounts (scripts/eval/batch_sets.py), then the configurations.
python scripts/eval/batch_sets.py validate "$SET" --configs "${NAMES[*]}"   ${CASE_IDS[@]+"${CASE_IDS[@]}"} || exit 2
echo "runs: $RUNS"
for index in "${!NAMES[@]}"; do
  vars="${ENVS[$index]#,}"; echo "config ${NAMES[$index]}: ${vars:-application defaults}"
done
[ -z "$VALIDATE_ONLY" ] || exit 0

: "${PROJECT:?}" "${EVAL_OLLAMA_LOG:?}"
read -r -a FILES <<< "${COMPOSE_FILES:?space-separated -f arguments}"
API=http://127.0.0.1:18190
mkdir -p "$OUT"
REINGESTED=""
LOG_DIR="$OUT/before-batch"; LOG_SINCE=""

save_logs() {  # a recreated or removed container takes its log with it (run 44575927833)
  mkdir -p "$LOG_DIR"
  docker logs "$PROJECT-api-1" > "$LOG_DIR/api.log" 2>&1 || true
  docker compose -p "$PROJECT" "${FILES[@]}" logs --no-color ${LOG_SINCE:+--since "$LOG_SINCE"} worker     > "$LOG_DIR/worker.log" 2>&1 || true
}

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

reingest_table_rows() {  # fresh database and redis on this throwaway CI stack, worker with the flag
  echo "$(date -u +%FT%TZ) re-ingest, DOCUMENT_TABLE_ROW_CHUNKING_ENABLED=true" | tee -a "$OUT/batch.log"
  export EVAL_TABLE_ROWS=true
  local compose=(docker compose -p "$PROJECT" "${FILES[@]}")
  "${compose[@]}" rm --stop --force api worker postgres redis >/dev/null || return 1
  docker volume rm "${PROJECT}_postgres_data" "${PROJECT}_redis_data" >/dev/null || return 1
  "${compose[@]}" up -d --wait --no-build postgres redis >/dev/null || return 1
  "${compose[@]}" run --rm --no-deps migration >/dev/null || return 1
  "${compose[@]}" run --rm --no-deps uat-v2-accounts >/dev/null || return 1
  "${compose[@]}" up -d --no-build --no-deps worker >/dev/null || return 1
  docker inspect "$PROJECT-worker-1" --format '{{range .Config.Env}}{{println .}}{{end}}' \
    | grep -x 'DOCUMENT_TABLE_ROW_CHUNKING_ENABLED=true' >/dev/null \
    || { echo "worker without the flag"; return 1; }
}

run_one() {  # $1 = config index, $2 = run number
  local name="${NAMES[$1]}" vars="${ENVS[$1]}" dir
  dir="$OUT/$name/run$2"; mkdir -p "$dir"
  # The live API container's log goes to the run it served (before-batch: the corpus load) before
  # the recreate below removes it; the last run's container stays for the workflow to collect.
  save_logs
  LOG_DIR="$dir"; LOG_SINCE="$(date -u +%FT%TZ)"
  if [ -n "${ROWS_FROM:-}" ] && [ "$1" -ge "$ROWS_FROM" ] && [ -z "$REINGESTED" ]; then
    reingest_table_rows || return 1
    start_api "$vars" || return 1
    if [ "$SET" = uat ] || [ "$SET" = natural ]; then  # new document ids: a new runtime manifest
      mv "$OUT/runtime-manifest.json" "$OUT/runtime-manifest-before-rows.json"
      python scripts/eval/bootstrap_corpus_v2.py . "$API" "$OUT/runtime-manifest.json" \
        > "$OUT/reingest.log" 2>&1 || { echo "corpus V2 reload failed"; return 1; }
    fi
    REINGESTED=1
  else
    start_api "$vars" || return 1
  fi
  # grep reads to the end: with pipefail, grep -q exiting early SIGPIPEs docker logs (false miss)
  if [[ ",$vars," == *",EVAL_ABLATION="* ]] \
    && ! docker logs "$PROJECT-api-1" 2>&1 | grep "ABLATION applied" >/dev/null; then
    echo "ablation not applied in the API" | tee "$dir/runner.log"; return 1
  fi
  ( # the runner sees the configuration too (e.g. EVAL_EXPECTED_RERANKER_MODE)
  IFS=',' read -r -a PAIRS <<< "$vars"
  for pair in "${PAIRS[@]}"; do export "${pair?}"; done
  docker inspect "$PROJECT-api-1" --format '{{range .Config.Env}}{{println .}}{{end}}' \
    | grep -E '^(RAG_|RERANKER_|EVAL_ABLATION|EVAL_ORACLE|LLM_OLLAMA_MODEL)' | sort > "$dir/flags.txt"
  python scripts/eval/ollama_warmup.py "$dir/warmup.json" --base-url http://127.0.0.1:11434 \
    --model "${EVAL_LLM_MODEL:-qwen3.5-text:4b}" --num-ctx 8192 --keep-alive 10m --seed 20261031 >/dev/null
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
    false_refusal|false_refusal_v2|compound)
      local frozen=false_refusal_dev_v1; [ "$SET" = false_refusal_v2 ] && frozen=false_refusal_dev_v2
      [ "$SET" = compound ] && frozen=compound_partial_dev_v1
      python scripts/eval/run_answer_relevance_dev.py --set "$frozen" \
        --output "$dir/results.json" > "$dir/runner.log" 2>&1 \
        || echo "runner exit $?" >> "$dir/runner.log" ;;
    heldout_v3)  # DEC-035: counts only on stdout; answers stay private (DEC-039)
      python scripts/eval/heldout_v3_release.py run --manifest "$OUT/runtime-manifest.json"         --output "$dir/results.json" > "$dir/runner.log" 2>&1         || echo "runner exit $?" >> "$dir/runner.log" ;;
    natural)  # owner-written questions over corpus V2, proxy-graded on the locked gold
      python scripts/eval/run_natural_dev.py --manifest "$OUT/runtime-manifest.json" \
        --output "$dir/results.json" > "$dir/runner.log" 2>&1 \
        || echo "runner exit $?" >> "$dir/runner.log" ;;
    *) echo "no runner for set $SET" > "$dir/runner.log" ;;
  esac
  echo "seconds=$(( $(date +%s) - started ))" > "$dir/timing.txt"
  if [[ ",$vars," == *",EVAL_ABLATION="*simple_trace* || ",$vars," == *",EVAL_ABLATION="*retrieval_oracle* ]]; then
    # every simple-mode draft, or the retrieval gate's chosen chunks (DEC-034)
    docker cp "$PROJECT-api-1:/tmp/simple_trace.jsonl" "$dir/simple_trace.jsonl" >/dev/null 2>&1 \
      || echo "no simple trace" >> "$dir/runner.log"
  fi
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
KIND="$SET"; [[ "$SET" == false_refusal* || "$SET" == compound || "$SET" == natural || "$SET" == heldout_v3 ]] && KIND=relevance
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
