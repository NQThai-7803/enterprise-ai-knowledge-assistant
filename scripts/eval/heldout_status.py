"""Status block of a held-out workflow run (DEC-039), at the top of the public summary.md whether
the job passed or failed: the status, the step that failed and its exit code, and how many
requests reached the API. Text-free: no question, answer or log line. Standard library only, so
that it runs even when the job failed before Python was set up.

usage: python3 scripts/eval/heldout_status.py --workflow <yml> --job-status <job.status>
         --preflight <true|false> --failed-steps <file> --stack-log <file>
         [--summary <grading summary.md>] --output <summary.md>

- --failed-steps: "<step id> <exit code>" lines, written by the job's exit trap (BASH_ENV).
- STEPS_JSON (environment, optional): toJSON(steps), for a failing `uses:` step the trap misses.
- Requests are counted from the API's uvicorn access log in the stack log: questions are the POSTs
  to /chat/sessions/<id>/messages(/stream); health checks are left out of the total. A stack log
  with no access line at all gives "unknown", never 0.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Sequence
from pathlib import Path

ACCESS = re.compile(r'"([A-Z]+) (/\S*) HTTP/[0-9.]+" \d{3}')
QUESTION = re.compile(r"^/api/v1/chat/sessions/[^/]+/messages(?:/stream)?(?:\?|$)")


def step_names(workflow: Path) -> dict[str, str]:
    """step id -> step name, read from the workflow text (no YAML library needed)."""
    names: dict[str, str] = {}
    current = None
    for line in workflow.read_text(encoding="utf-8").splitlines():
        if match := re.match(r"\s*- name: (.+)", line):
            current = match[1].strip().strip("\"'")
        elif (match := re.match(r"\s+id: (\S+)", line)) and current:
            names[match[1]] = current
    return names


def requests(stack_log: Path) -> dict[str, int | str]:
    if not stack_log.is_file():
        return {"questions_sent_to_api": "unknown", "api_requests": "unknown"}
    seen = questions = other = 0
    for line in stack_log.read_text(encoding="utf-8", errors="replace").splitlines():
        if not (match := ACCESS.search(line)):
            continue
        seen += 1
        method, path = match.groups()
        if path.startswith("/health"):
            continue
        other += 1
        questions += method == "POST" and bool(QUESTION.match(path))
    if not seen:  # the API never logged a request, not even a health check: not a measured 0
        return {"questions_sent_to_api": "unknown", "api_requests": "unknown"}
    return {"questions_sent_to_api": questions, "api_requests": other}


def failure(
    job_status: str, trap_file: Path, steps_json: str, names: dict[str, str]
) -> dict[str, str]:
    lines = trap_file.read_text(encoding="utf-8").split("\n") if trap_file.is_file() else []
    recorded = [line.split() for line in lines if len(line.split()) == 2]
    if recorded:
        step, code = recorded[0]
        return {"failed_step": names.get(step, step), "exit_code": code}
    steps = json.loads(steps_json or "{}")
    failed = [step for step, data in steps.items() if data.get("outcome") == "failure"]
    if failed:
        return {"failed_step": names.get(failed[0], failed[0]), "exit_code": "unknown"}
    if job_status == "success":
        return {"failed_step": "none", "exit_code": "0"}
    return {"failed_step": "unknown", "exit_code": "unknown"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--job-status", required=True)
    parser.add_argument("--preflight", choices=("true", "false"), required=True)
    parser.add_argument("--failed-steps", type=Path, required=True)
    parser.add_argument("--stack-log", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    found = failure(
        args.job_status,
        args.failed_steps,
        os.environ.get("STEPS_JSON", ""),
        step_names(args.workflow),
    )
    status = {"failure": "failed"}.get(args.job_status, args.job_status)
    if found["failed_step"] not in ("none", "unknown"):
        status = "failed"
    fields = {"status": status, "preflight": args.preflight, **found, **requests(args.stack_log)}
    text = ["# Run status (DEC-039)", "", *(f"- {key}={value}" for key, value in fields.items())]
    if args.summary and args.summary.is_file():
        text += ["", args.summary.read_text(encoding="utf-8").rstrip("\n")]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text[2 : 2 + len(fields)]))  # the status lines only: ids and counts
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
