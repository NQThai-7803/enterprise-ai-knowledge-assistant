"""DEC-039: a held-out workflow uploads only its public folder, after the private split and the
fingerprint scan; nothing a run writes reaches the public job summary unscanned."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.repo_layout(".github/workflows/heldout-v2.yml", ".github/workflows/heldout-v3.yml")
@pytest.mark.parametrize("name", ["heldout-v2", "heldout-v3"])
def test_only_the_scanned_public_folder_is_uploaded(name: str) -> None:
    job = yaml.safe_load((ROOT / ".github" / "workflows" / f"{name}.yml").read_text("utf-8"))
    steps = job["jobs"][name]["steps"]
    names = [step["name"] for step in steps]
    check = names.index("Check where the owner's full results go (DEC-039)")
    private = names.index("Keep the full results private (DEC-039)")
    scan = names.index("Scan the public folder for question text (DEC-039)")
    assert check < names.index("Generate throwaway credentials")
    assert "HELDOUT_AGE_RECIPIENT" in steps[check]["env"]
    assert names.index("Collect logs") < private < scan == len(steps) - 2
    assert "heldout_publish.sh" in steps[private]["run"]
    assert "question_leak.py scan" in steps[scan]["run"]
    uploads = [step for step in steps if "upload-artifact" in step.get("uses", "")]
    assert uploads == [steps[-1]] and uploads[0]["with"]["path"] == f"{name}-public/"
    for needed in ("steps.private.outcome == 'success'", "steps.scan.outcome == 'success'"):
        assert needed in uploads[0]["if"]
    summary_writers = [step for step in steps if "GITHUB_STEP_SUMMARY" in step.get("run", "")]
    assert summary_writers == [steps[scan]]
