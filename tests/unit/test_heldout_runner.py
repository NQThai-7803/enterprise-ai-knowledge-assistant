"""Held-out runner: refuses a hash mismatch and asks each item as its own role."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.eval import run_heldout
from scripts.eval.eval_client import OK, AskResult

ANSWER = {
    "data": {
        "grounding_status": "ANSWERED",
        "retrieved_chunk_count": 1,
        "assistant_message": {"content": "A [1]", "citations": []},
    }
}


def _write_set(tmp_path: Path, *, lock_sha: str | None = None) -> tuple[Path, Path]:
    heldout = tmp_path / "heldout.yaml"
    heldout.write_text(
        "items:\n"
        "  - {id: HO-001, group: A, role: staff, question: q1}\n"
        "  - {id: HO-002, group: A, role: manager, question: q2}\n",
        encoding="utf-8",
    )
    sha = lock_sha or hashlib.sha256(heldout.read_bytes()).hexdigest()
    lock = tmp_path / "heldout.lock"
    lock.write_text(json.dumps({"version": "test", "sha256": sha}), encoding="utf-8")
    return heldout, lock


def test_repository_lock_matches_the_frozen_file() -> None:
    assert run_heldout.verify_frozen()["items"] == 40


def test_hash_mismatch_refuses_to_run(tmp_path: Path) -> None:
    heldout, lock = _write_set(tmp_path, lock_sha="0" * 64)
    with pytest.raises(run_heldout.HeldoutHashMismatchError):
        run_heldout.verify_frozen(heldout, lock)


def test_missing_lock_refuses_to_run(tmp_path: Path) -> None:
    heldout, _ = _write_set(tmp_path)
    with pytest.raises(run_heldout.HeldoutHashMismatchError):
        run_heldout.verify_frozen(heldout, tmp_path / "absent.lock")


class RoleClient:
    def __init__(self, role: str, log: list[tuple[str, str]]) -> None:
        self.role = role
        self.log = log

    def create_session(self, title: str) -> str:
        return title

    def ask(self, session_id: str, question: str) -> AskResult:
        self.log.append((self.role, question))
        return AskResult(201, ANSWER, 3, OK, None)


def test_each_item_is_asked_with_its_role(tmp_path: Path, monkeypatch) -> None:
    heldout, lock = _write_set(tmp_path)
    monkeypatch.setattr(run_heldout, "HELDOUT", heldout)
    monkeypatch.setattr(run_heldout, "LOCK", lock)
    monkeypatch.setattr(run_heldout, "verify_frozen", lambda: {"sha256": "x", "version": "t"})
    monkeypatch.setattr(run_heldout, "load_items", lambda: run_heldout.yaml_items(heldout))
    log: list[tuple[str, str]] = []
    output = tmp_path / "out.json"

    code = run_heldout.run(
        output=output,
        selected=set(),
        resume=False,
        base_url="http://x",
        passwords={},
        delay_seconds=0.0,
        client_factory=lambda role: RoleClient(role, log),
    )

    assert code == 0
    assert log == [("staff", "q1"), ("manager", "q2")]
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert [c["role"] for c in payload["cases"]] == ["staff", "manager"]
    assert "password" not in output.read_text(encoding="utf-8").casefold()
