"""Question fingerprints on made-up questions: matching, refusal on no source, no plain text."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.eval import question_leak as leak
from scripts.eval.question_leak import QuestionSourceError

DEV = [("D1", "Một hai ba bốn năm sáu bảy tám")]
HELDOUT = [("T1", "alpha beta gamma delta epsilon")]
EXPECTED = {"dev": 1, "heldout": 1}


def _files(tmp_path: Path, payload: object, sha: str = "abc") -> tuple[Path, Path]:
    path = tmp_path / "fingerprints.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"sha256": sha}), encoding="utf-8")
    return path, lock


def _payload(dev=DEV, heldout=HELDOUT) -> dict:
    return leak.build_payload(dev, heldout, "abc")


def test_folding_makes_diacritics_case_and_escapes_compare_equal() -> None:
    plain = leak.words("Được nghỉ PHÉP năm")
    assert plain == ["duoc", "nghi", "phep", "nam"]
    assert leak.words(r"Được nghỉ phép năm") == plain


def test_payload_holds_no_question_text() -> None:
    text = json.dumps(_payload())
    for word in ("alpha", "epsilon", "bốn", "bon", "Một"):
        assert word not in text


def test_a_line_sharing_a_4_gram_is_a_hit_and_names_only_the_source_and_id() -> None:
    lines = [
        ("app/a.py", 7, 'x = "ALPHA beta GAMMA delta"'),
        ("app/a.py", 8, 'y = "alpha beta gamma"'),
        ("app/b.py", 3, "# hai ba bon nam"),
    ]
    assert leak.find_hits(_payload(), lines) == [
        ("app/a.py", 7, "heldout", "T1"),
        ("app/b.py", 3, "dev", "D1"),
    ]


def test_short_question_still_gets_a_fingerprint() -> None:
    assert len(leak.fingerprint("hai từ")) == 1
    assert leak.fingerprint("!!!") == []


def test_a_line_holding_a_whole_short_question_is_a_hit() -> None:
    payload = _payload(heldout=[("T2", "Omega là gì?")])
    lines = [("app/a.py", 1, 'x = "Omega la gi?"'), ("app/a.py", 2, 'y = "Omega la')]
    assert leak.find_hits(payload, lines) == [("app/a.py", 1, "heldout", "T2")]


def test_stale_held_out_v2_lock_fails(tmp_path: Path) -> None:
    payload = leak.build_payload(DEV, HELDOUT, "abc", heldout_v2=HELDOUT, lock_v2_sha256="v2")
    path, lock = _files(tmp_path, payload)
    lock_v2 = tmp_path / "lock_v2.json"
    lock_v2.write_text(json.dumps({"sha256": "other"}), encoding="utf-8")
    expected = {**EXPECTED, "heldout_v2": 1}
    with pytest.raises(QuestionSourceError, match="held-out v2"):
        leak.load_fingerprints(path, lock, expected, lock_v2)
    lock_v2.write_text(json.dumps({"sha256": "v2"}), encoding="utf-8")
    assert leak.load_fingerprints(path, lock, expected, lock_v2)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"sources": {}},
        {"sources": {"dev": {"items": {}}, "heldout": {"items": {"T1": ["x"]}}}},
        {"sources": {"dev": {"items": {"D1": []}}, "heldout": {"items": {"T1": []}}}},
    ],
)
def test_empty_or_broken_source_fails(tmp_path: Path, payload: dict) -> None:
    path, lock = _files(tmp_path, payload)
    with pytest.raises(QuestionSourceError):
        leak.load_fingerprints(path, lock, EXPECTED)


def test_missing_file_and_stale_lock_fail(tmp_path: Path) -> None:
    path, lock = _files(tmp_path, _payload(), sha="other")
    with pytest.raises(QuestionSourceError, match="another held-out"):
        leak.load_fingerprints(path, lock, EXPECTED)
    with pytest.raises(QuestionSourceError, match="missing"):
        leak.load_fingerprints(tmp_path / "absent.json", lock, EXPECTED)
    lock.unlink()
    with pytest.raises(QuestionSourceError, match="lock missing"):
        leak.load_fingerprints(path, lock, EXPECTED)


def test_valid_file_loads(tmp_path: Path) -> None:
    path, lock = _files(tmp_path, _payload())
    assert leak.load_fingerprints(path, lock, EXPECTED)["sources"]["dev"]["count"] == 1


def test_no_source_exits_2_never_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    real = leak.load_fingerprints
    monkeypatch.setattr(leak, "load_fingerprints", lambda: real(tmp_path / "x", tmp_path / "y", {}))
    assert leak.main(["check"]) == 2
    assert leak.main(["overlap"]) == 2
    assert "fingerprint file missing" in capsys.readouterr().err


def test_check_exit_codes_for_a_hit_and_clean_diff(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(leak, "load_fingerprints", _payload)
    monkeypatch.setattr(leak, "added_lines", lambda *_: [("app/a.py", 1, "alpha beta gamma delta")])
    assert leak.main(["check"]) == 1
    out = capsys.readouterr().out
    assert "heldout T1" in out
    assert "alpha" not in out
    monkeypatch.setattr(leak, "added_lines", lambda *_: [("app/a.py", 1, "other words only here")])
    assert leak.main(["check"]) == 0


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_added_lines_reads_real_diff_line_numbers(tmp_path: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    (tmp_path / "app").mkdir()
    source = tmp_path / "app" / "a.py"
    source.write_text("one\ntwo\n", encoding="utf-8")
    git("init")
    git("add", ".")
    git("-c", "user.name=t", "-c", "user.email=t@example.test", "commit", "-m", "base")
    source.write_text("one\nnew line\ntwo\n", encoding="utf-8")
    assert leak.added_lines(tmp_path, "HEAD", False, "app") == [("app/a.py", 2, "new line")]
    git("add", ".")
    assert leak.added_lines(tmp_path, "HEAD", True, "app") == [("app/a.py", 2, "new line")]


def test_overlap_fails_at_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    same = _payload(dev=[("D1", HELDOUT[0][1])])
    assert leak.max_overlap(same) == (1.0, "D1", "T1")
    monkeypatch.setattr(leak, "load_fingerprints", lambda: same)
    assert leak.main(["overlap"]) == 1
    apart = _payload()
    assert leak.max_overlap(apart)[0] == 0.0
    monkeypatch.setattr(leak, "load_fingerprints", lambda: apart)
    assert leak.main(["overlap"]) == 0


def test_committed_fingerprints_cover_both_sets_without_plain_text() -> None:
    payload = json.loads(leak.FINGERPRINTS.read_text(encoding="utf-8"))
    for name, count in leak.EXPECTED_COUNTS.items():
        items = payload["sources"][name]["items"]
        assert len(items) == count
        assert all(
            len(value) == 16 and set(value) <= set("0123456789abcdef")
            for hashes in items.values()
            for value in hashes
        )
