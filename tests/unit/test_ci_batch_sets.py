"""ci_batch.sh accepts every question set a workflow passes it, and refuses an unknown one.

Held-out v3.1 run 44559765410 failed on "unknown set heldout_v3" before its first request: no test
ran ci_batch.sh with the arguments of a workflow. Held-out v3 is validated here on invented items
(a sitecustomize replaces heldout_v3_release.gate): no test reads the held-out files in docs/eval.
"""

from __future__ import annotations

import itertools
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.eval import batch_sets, heldout_v3_release

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
CI_BATCH = "scripts/eval/ci_batch.sh"
BASH = shutil.which("bash")
PASSWORDS = dict.fromkeys(
    ("EVAL_PASSWORD_ADMIN", "EVAL_PASSWORD_MANAGER", "EVAL_PASSWORD_STAFF", "EVAL_PASSWORD_OPS",
     "UAT_STAFF_PASSWORD"),
    "x",
)  # fmt: skip
FAKE_ITEMS = [
    {"id": "X-01", "status": "ACTIVE", "test_account": "Bất kỳ"},
    {"id": "X-02", "status": "EXCLUDED", "test_account": "Bất kỳ"},
]
FAKE_GATE = """
import json, os, sys
sys.path.insert(0, os.environ["EAKA_ROOT"])
from scripts.eval import heldout_v3_release
items = json.loads(os.environ["FAKE_HELDOUT_ITEMS"])
heldout_v3_release.gate = lambda: {"sha256": "fake", "version": "heldout_v3", "items": items}
"""
needs_bash = pytest.mark.skipif(BASH is None, reason="bash is not installed")


def _calls() -> list[dict[str, Any]]:
    """Every ci_batch.sh command line in the workflows, with what its arguments resolve from."""
    calls = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        trigger = doc.get("on", doc.get(True)) or {}  # YAML 1.1 reads the key `on` as True
        inputs = (trigger.get("workflow_dispatch") or {}).get("inputs") or {}
        for job in doc["jobs"].values():
            for index, step in enumerate(job.get("steps", [])):
                for line in step.get("run", "").splitlines():
                    if CI_BATCH not in line:
                        continue
                    words = shlex.split(line, comments=True)
                    args = words[words.index(CI_BATCH) + 1 :]
                    validate = args[:1] == ["--validate-only"]
                    calls.append(
                        {
                            "where": f"{path.name}: {step['name']}",
                            "index": index,
                            "step": step,
                            "validate": validate,
                            "args": args[validate:][:3],  # set, configs, runs
                            "scopes": (step.get("env", {}), job.get("env", {}), doc.get("env", {})),
                            "inputs": inputs,
                        }
                    )
    return calls


def _values(token: str, call: dict[str, Any]) -> list[str]:
    """A literal, or $VAR from the step, job or workflow env; a workflow_dispatch input gives
    every option of a choice, else its default."""
    match = re.fullmatch(r"\$\{?(\w+)\}?", token)
    if not match:
        return [token]
    scope = next((s for s in call["scopes"] if match[1] in s), None)
    assert scope is not None, f"{call['where']}: {token} is not set in the workflow"
    value = str(scope[match[1]])
    expr = re.fullmatch(r"\$\{\{\s*inputs\.(\w+)\s*\}\}", value)
    if not expr:
        return [value]
    spec = call["inputs"][expr[1]]
    return [str(o) for o in spec["options"]] if spec.get("type") == "choice" else [spec["default"]]


def _validate(set_name: str, configs: str, runs: str, tmp_path: Path, **env: str):
    fake = tmp_path / "fake-gate"
    fake.mkdir(exist_ok=True)
    (fake / "sitecustomize.py").write_text(FAKE_GATE, encoding="utf-8")
    full = {
        **os.environ,
        **PASSWORDS,
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""),
        "PYTHONPATH": str(fake),
        "PYTHONIOENCODING": "utf-8",
        "EAKA_ROOT": str(ROOT),
        "FAKE_HELDOUT_ITEMS": json.dumps(FAKE_ITEMS),
        **env,
    }
    args = [BASH, CI_BATCH, "--validate-only", set_name, configs, runs, str(tmp_path / "out")]
    return subprocess.run(
        args, cwd=ROOT, env=full, capture_output=True, text=True, encoding="utf-8", timeout=120
    )


@pytest.mark.repo_layout(".github/workflows/eval.yml", ".github/workflows/heldout-v3.yml")
def test_the_scan_finds_the_batch_calls_of_eval_and_held_out_v3() -> None:
    found = {(c["where"].split(":")[0], c["validate"]) for c in _calls()}
    assert {("eval.yml", False), ("heldout-v3.yml", True), ("heldout-v3.yml", False)} <= found


@pytest.mark.repo_layout(".github/workflows/heldout-v3.yml")
def test_the_held_out_v3_validate_step_runs_in_preflight_with_the_run_step_s_arguments() -> None:
    calls = [c for c in _calls() if c["where"].startswith("heldout-v3.yml")]
    validate = next(c for c in calls if c["validate"])
    run = next(c for c in calls if not c["validate"])
    assert validate["args"] == run["args"] and validate["index"] < run["index"]
    assert "if" not in validate["step"]  # preflight_only=true runs it too
    assert validate["step"]["env"] == run["step"]["env"] == {"HELDOUT_V3_APPROVED": "1"}


@needs_bash
@pytest.mark.repo_layout(".github/workflows", "eval-data/uat/questions.json")
def test_every_set_a_workflow_passes_to_ci_batch_is_accepted(tmp_path: Path) -> None:
    seen, failures = set(), []
    for call in _calls():
        env = {k: v for k, v in call["step"].get("env", {}).items() if k == "HELDOUT_V3_APPROVED"}
        set_names, configs, runs = (_values(token, call) for token in call["args"])
        assert all(re.fullmatch(r"[12]", r) for r in runs), call["where"]  # ci_batch.sh's rule
        for args in itertools.product(set_names, configs, runs[:1]):  # one bash call per set
            if args in seen:
                continue
            seen.add(args)
            done = _validate(*args, tmp_path, **env)
            lines = done.stdout.splitlines()
            if done.returncode or f"set: {args[0]}" not in lines or "questions: 0" in lines:
                failures.append(f"{call['where']} {args}: exit {done.returncode} {done.stderr}")
    assert {args[0] for args in seen} >= {"heldout_v3", "uat", "rbac", "natural"}
    assert not failures


@needs_bash
@pytest.mark.repo_layout("eval-data/uat/questions.json")
def test_an_unknown_set_or_an_unapproved_held_out_run_is_refused(tmp_path: Path) -> None:
    done = _validate("heldout_v4", "base", "1", tmp_path)
    assert done.returncode == 2 and "unknown set heldout_v4" in done.stderr
    configs = "legacy;s3t:EVAL_SIMPLE_LEVEL=3"
    assert _validate("heldout_v3", configs, "2", tmp_path).returncode == 2  # not approved
    approved = _validate("heldout_v3", configs, "2", tmp_path, HELDOUT_V3_APPROVED="1")
    assert approved.returncode == 0
    assert approved.stdout.splitlines()[:4] == [
        "set: heldout_v3", "questions: 1", "ids: X-01", "not run: X-02"
    ]  # fmt: skip


def test_every_registered_set_has_a_runner_branch_in_ci_batch() -> None:
    text = (ROOT / CI_BATCH).read_text(encoding="utf-8")
    groups = re.findall(r"^ {4}([a-z0-9_|]+)\)", text, re.M)  # the runner case labels
    labels = {name for group in groups for name in group.split("|")}
    assert set(batch_sets.SETS) <= labels


def test_held_out_v3_refuses_pending_items_and_other_configurations(monkeypatch) -> None:
    items = [*FAKE_ITEMS, {"id": "X-03", "status": "PENDING_AUTHOR_REVIEW", "test_account": "x"}]
    monkeypatch.setattr(heldout_v3_release, "gate", lambda: {"items": items})
    monkeypatch.setenv("EVAL_PASSWORD_STAFF", "x")
    with pytest.raises(batch_sets.BatchSetError, match="X-03"):
        batch_sets.validate("heldout_v3", ["legacy", "s3t"], [])
    monkeypatch.setattr(heldout_v3_release, "gate", lambda: {"items": FAKE_ITEMS})
    assert batch_sets.validate("heldout_v3", ["legacy", "s3t"], [])[:2] == (["X-01"], ["X-02"])
    with pytest.raises(batch_sets.BatchSetError, match="configurations"):
        batch_sets.validate("heldout_v3", ["base"], [])
    monkeypatch.delenv("EVAL_PASSWORD_STAFF")
    with pytest.raises(batch_sets.BatchSetError, match="EVAL_PASSWORD_STAFF"):
        batch_sets.validate("heldout_v3", ["legacy", "s3t"], [])
