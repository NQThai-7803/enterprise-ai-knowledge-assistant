#!/usr/bin/env bash
# DEC-039: split a held-out run so that only ids, counts, the verdict and the lock are ever public.
# usage: heldout_publish.sh <name> <out> <public> <run id> <public file>...
#   <public file>: copied into <public> when it exists (the lock, the text-free summary/verdict).
#   Everything in <out> stays private, by runner (RUNNER_KIND = the job's runner.environment):
#   - self-hosted: copied to ${HELDOUT_PRIVATE_DIR:-C:/dev/eaka-private/<name>}/<run id>, never
#     uploaded;
#   - github-hosted: tar | age -r "$HELDOUT_AGE_RECIPIENT" into <public>/private-results.tar.gz.age;
#     without a valid recipient the step fails: there is no plaintext fallback.
# <public> is filled before the private part, so a failed split still leaves the text-free files
# only. The workflow then runs `question_leak.py scan <public>` and uploads <public> if it passes.
set -euo pipefail
name=$1 out=$2 public=$3 run_id=$4
shift 4
[[ "$name" =~ ^heldout-v[0-9.]+$ ]] || { echo "bad name: $name"; exit 2; }
[[ "$public" =~ ^heldout-v[0-9.]+-public$ ]] || { echo "refusing to recreate $public"; exit 2; }
[[ "$run_id" =~ ^[0-9A-Za-z_-]+$ ]] || { echo "bad run id"; exit 2; }
rm -rf "$public"
mkdir -p "$public" "$out"
for file in "$@"; do
  if [ -f "$file" ]; then cp "$file" "$public/"; fi
done
case "${RUNNER_KIND:-}" in
  self-hosted)
    dest="${HELDOUT_PRIVATE_DIR:-C:/dev/eaka-private/$name}/$run_id"
    mkdir -p "$dest"
    cp -R "$out/." "$dest/"
    echo "private results kept on this runner, not uploaded: $dest" ;;
  github-hosted)
    [[ "${HELDOUT_AGE_RECIPIENT:-}" =~ ^age1[0-9a-z]{58}$ ]] \
      || { echo "HELDOUT_AGE_RECIPIENT is not an age public key: nothing private is kept"; exit 1; }
    command -v age >/dev/null || { echo "age is not installed"; exit 1; }
    tar -czf - -C "$out" . | age -r "$HELDOUT_AGE_RECIPIENT" -o "$public/private-results.tar.gz.age"
    echo "private results encrypted for the owner's key: private-results.tar.gz.age" ;;
  *) echo "unknown runner environment: '${RUNNER_KIND:-}'"; exit 1 ;;
esac
