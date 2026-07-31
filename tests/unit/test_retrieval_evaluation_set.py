from __future__ import annotations

import json
from pathlib import Path


def test_retrieval_evaluation_set_is_well_formed() -> None:
    path = Path("tests/fixtures/retrieval_evaluation_set.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["version"] == 1
    assert payload["items"]
    for item in payload["items"]:
        assert item["id"]
        assert item["query"].strip()
        assert item["permission_scope"] in {"authorized_user", "unauthorized_user"}
        assert isinstance(item["expected_terms"], list)
        if item["permission_scope"] == "authorized_user":
            assert item["expected_document_title"]
            assert item["expected_terms"]
