#!/bin/sh
# Run the PostgreSQL-backed CI pytest lanes (same markers as .github/workflows/ci.yml) and
# write one JUnit XML and one log per lane into the given directory.
# Lanes that need a real embedding model, a Celery worker or a real LLM are not run here.
set -u
OUT="${1:?usage: run_integration_lanes.sh <output-dir>}"
mkdir -p "$OUT" /tmp/ci-data/uploads /tmp/ci-data/models
status=0

run_lane() {
  name="$1"
  shift
  python -m pytest "$@" -q -p no:cacheprovider -rfEsxX --junitxml="$OUT/$name.xml" \
    > "$OUT/$name.log" 2>&1
  code=$?
  echo "lane=$name exit=$code :: $(tail -n 1 "$OUT/$name.log")"
  [ "$code" -eq 0 ] || status=1
}

run_lane api-unit tests/api -m "not integration"
run_lane api-integration tests/api -m integration
run_lane integration tests/integration -m "integration and not celery_integration and not embedding_model_integration and not processing_pipeline_model_integration and not processing_pipeline_celery_integration and not semantic_retrieval_model_integration and not hybrid_retrieval_model_integration"
run_lane llm-provider -m llm_provider_integration

exit "$status"
