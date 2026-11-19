"""DEC-039: a held-out workflow uploads only its public folder, after the private split and the
fingerprint scan; nothing a run writes reaches the public job summary unscanned. The public
summary.md carries the run status, also when the job failed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.eval import heldout_status

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.repo_layout(".github/workflows/heldout-v2.yml", ".github/workflows/heldout-v3.yml")
@pytest.mark.parametrize("name", ["heldout-v2", "heldout-v3"])
def test_only_the_scanned_public_folder_is_uploaded(name: str) -> None:
    job = yaml.safe_load((ROOT / ".github" / "workflows" / f"{name}.yml").read_text("utf-8"))
    steps = job["jobs"][name]["steps"]
    names = [step["name"] for step in steps]
    check = names.index("Check where the owner's full results go (DEC-039)")
    status = names.index("Write the run status (DEC-039)")
    private = names.index("Keep the full results private (DEC-039)")
    scan = names.index("Scan the public folder for question text (DEC-039)")
    assert check < names.index("Generate throwaway credentials")
    assert "HELDOUT_AGE_RECIPIENT" in steps[check]["env"]
    assert names.index("Collect logs") < status < private < scan == len(steps) - 2
    assert "heldout_publish.sh" in steps[private]["run"]
    assert '"$OUT/status/summary.md"' in steps[private]["run"]
    # the exit trap is set before anything else, and every run step has an id to name it by
    assert "BASH_ENV=" in steps[0]["run"] and steps[1]["uses"].startswith("actions/checkout@")
    assert all(step.get("id") for step in steps if "run" in step and step is not steps[-1])
    assert all(steps[i]["if"] == "always()" for i in (status, private, scan))
    assert "question_leak.py scan" in steps[scan]["run"]
    uploads = [step for step in steps if "upload-artifact" in step.get("uses", "")]
    assert uploads == [steps[-1]] and uploads[0]["with"]["path"] == f"{name}-public/"
    # also after a failed split, whose public folder holds the text-free files only
    assert uploads[0]["if"] == "always() && steps.scan.outcome == 'success'"
    summary_writers = [step for step in steps if "GITHUB_STEP_SUMMARY" in step.get("run", "")]
    assert summary_writers == [steps[scan]]


ACCESS = 'api-1  | INFO:     172.18.0.1:5000 - "{} {} HTTP/1.1" 200 OK'


def test_the_status_names_the_failing_step_and_counts_the_questions(tmp_path: Path) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text(
        "    steps:\n      - name: Gate it\n        id: gate\n"
        "      - name: Run the batch\n        id: batch\n        run: x\n",
        "utf-8",
    )
    trap = tmp_path / "failed-steps.txt"
    trap.write_text("batch 2\ngrade 1\n", "utf-8")  # the first failing step is the one named
    log = tmp_path / "stack.log"
    requests = [
        ("GET", "/health/ready"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/chat/sessions/abc/messages"),
        ("POST", "/api/v1/chat/sessions/abc/messages/stream"),
        ("GET", "/api/v1/chat/sessions/abc/messages"),
    ]
    log.write_text("\n".join(ACCESS.format(*request) for request in requests), "utf-8")
    grading = tmp_path / "grading.md"
    grading.write_text("| legacy | run1 | 3 |\n", "utf-8")
    out = tmp_path / "out" / "summary.md"
    args = ["--workflow", str(workflow), "--preflight", "false", "--failed-steps", str(trap)]
    args += ["--stack-log", str(log), "--summary", str(grading), "--output", str(out)]
    assert heldout_status.main([*args, "--job-status", "failure"]) == 0
    lines = out.read_text("utf-8").splitlines()
    assert lines[2:8] == [
        "- status=failed", "- preflight=false", "- failed_step=Run the batch", "- exit_code=2",
        "- questions_sent_to_api=2", "- api_requests=4",
    ]  # fmt: skip
    assert lines[-1] == "| legacy | run1 | 3 |"


def test_the_status_never_reports_a_zero_it_did_not_measure(tmp_path: Path) -> None:
    log = tmp_path / "stack.log"
    log.write_text("api-1  | started without any request\n", "utf-8")
    unknown = {"questions_sent_to_api": "unknown", "api_requests": "unknown"}
    assert heldout_status.requests(log) == heldout_status.requests(tmp_path / "x") == unknown
    steps = json.dumps({"checkout": {"outcome": "failure"}})  # a `uses:` step the trap misses
    found = heldout_status.failure("failure", tmp_path / "x", steps, {"checkout": "Checkout"})
    assert found == {"failed_step": "Checkout", "exit_code": "unknown"}
    assert heldout_status.failure("success", tmp_path / "x", "", {})["failed_step"] == "none"
    assert heldout_status.failure("failure", tmp_path / "x", "", {})["exit_code"] == "unknown"
