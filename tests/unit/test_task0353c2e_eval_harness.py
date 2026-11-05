"""Safety checks for the isolated, synthetic-only research harness."""

from __future__ import annotations

import json

import httpx
import pytest

from scripts.release import task0353c2e_eval as evaluation

requires_manifest = pytest.mark.skipif(
    not evaluation.MANIFEST.exists(),
    reason=(
        f"{evaluation.MANIFEST.relative_to(evaluation.ROOT).as_posix()} is missing; artifacts/ "
        "is git-ignored, so fresh clones lack the frozen synthetic manifest."
    ),
)


@requires_manifest
def test_manifest_is_frozen_and_split_before_evaluation() -> None:
    cases, digest = evaluation._load_manifest(evaluation.MANIFEST)
    assert len(cases) == 36
    assert len(digest) == 64
    assert sum(case["split"] == "development" for case in cases) == 12
    assert sum(case["split"] == "held_out" for case in cases) == 24


@requires_manifest
def test_restricted_synthetic_evidence_is_excluded_from_registry() -> None:
    cases, _ = evaluation._load_manifest(evaluation.MANIFEST)
    case = next(case for case in cases if case["id"] == "H22")
    visible = "\n".join(source.text for source in evaluation._registry(case).sources)
    assert case["authorized_evidence"][0] in visible
    assert case["restricted_evidence"][0] not in visible


def test_malformed_judgment_abstains() -> None:
    assert evaluation._parse_judge("not json") == ("UNCERTAIN", {})
    assert evaluation._parse_judge('{"unexpected": true}') == ("UNCERTAIN", {})


def test_complete_judgment_and_conflict_rule() -> None:
    dimensions = {key: True for key in evaluation.DIMENSIONS[:4]}
    dimensions.update(conflicting_authority=False, genuinely_uncertain=False)
    assert evaluation._parse_judge(json.dumps(dimensions))[0] == "ACCEPT"
    dimensions["conflicting_authority"] = True
    assert evaluation._parse_judge(json.dumps(dimensions))[0] == "UNCERTAIN"


def test_development_threshold_ignores_held_out_scores() -> None:
    cases = [
        {"id": "dev-a", "split": "development", "gold": "ACCEPT"},
        {"id": "dev-r", "split": "development", "gold": "REJECT"},
        {"id": "held", "split": "held_out", "gold": "ACCEPT"},
    ]
    rows = [
        {"id": "dev-a", "score": 0.8},
        {"id": "dev-r", "score": 0.2},
        {"id": "held", "score": 0.0},
    ]
    threshold = evaluation._select_dev_threshold(cases, rows)
    rows[-1]["score"] = 1.0
    assert evaluation._select_dev_threshold(cases, rows) == threshold


@requires_manifest
def test_judge_transport_excludes_restricted_text(monkeypatch) -> None:
    cases, _ = evaluation._load_manifest(evaluation.MANIFEST)
    case = next(case for case in cases if case["id"] == "H22")
    captured = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self):  # noqa: ANN201
            if "payload" not in captured:
                return {"models": [{"name": evaluation.OLLAMA_MODEL}]}
            return {
                "message": {
                    "content": json.dumps(
                        {
                            "evidence_relevant": False,
                            "answer_entailed": False,
                            "answers_question": False,
                            "complete_conditions": True,
                            "conflicting_authority": False,
                            "genuinely_uncertain": False,
                        }
                    )
                }
            }

    class Client:
        def __init__(self, **kwargs):  # noqa: ANN003
            self.kwargs = kwargs

        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *_args):  # noqa: ANN002, ANN204
            return None

        def get(self, _url):  # noqa: ANN001, ANN201
            return Response()

        def post(self, _url, *, json):  # noqa: ANN001, ANN201
            captured["payload"] = json
            return Response()

    monkeypatch.setattr(httpx, "Client", Client)
    result = evaluation._evaluate_judge([case])
    sent = json.loads(captured["payload"]["messages"][1]["content"])
    assert sent["authorized_evidence"] == case["authorized_evidence"]
    assert "restricted_evidence" not in sent
    assert case["restricted_evidence"][0] not in sent["authorized_evidence"]
    assert result[0]["decision"] == "REJECT"


@requires_manifest
def test_judge_timeout_becomes_uncertain(monkeypatch) -> None:
    cases, _ = evaluation._load_manifest(evaluation.MANIFEST)

    class Client:
        def __init__(self, **_kwargs):  # noqa: ANN003
            return None

        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *_args):  # noqa: ANN002, ANN204
            return None

        def get(self, _url):  # noqa: ANN001, ANN201
            class Response:
                def raise_for_status(self) -> None:
                    return None

                def json(self):  # noqa: ANN201
                    return {"models": [{"name": evaluation.OLLAMA_MODEL}]}

            return Response()

        def post(self, _url, **_kwargs):  # noqa: ANN001, ANN003, ANN201
            raise httpx.TimeoutException("synthetic timeout")

    monkeypatch.setattr(httpx, "Client", Client)
    result = evaluation._evaluate_judge([cases[0]])
    assert result[0]["decision"] == "UNCERTAIN"
    assert result[0]["timeout"] is True
