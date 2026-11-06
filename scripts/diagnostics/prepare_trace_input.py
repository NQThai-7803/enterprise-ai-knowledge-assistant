"""Write the inputs of heldout_trace.py under artifacts/heldout-v1-diagnosis/. Run on the host.

usage: python scripts/diagnostics/prepare_trace_input.py
The inputs hold question and gold text, so they stay under the git-ignored artifacts/.
"""

from __future__ import annotations

import json
import runpy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "heldout-v1-diagnosis"
DETERMINISTIC_FIRST = ["HO-004", "HO-008", "HO-020", "HO-023", "HO-026", "HO-039"]
FALSE_REFUSALS = [
    "HO-001",
    "HO-005",
    "HO-007",
    "HO-012",
    "HO-013",
    "HO-025",
    "HO-028",
    "HO-031",
    "HO-032",
    "HO-033",
    "HO-035",
    "HO-036",
    "HO-037",
    "HO-038",
]
OTHERS = ["HO-002", "HO-010", "HO-011", "HO-022"]
# Same meaning in the other language, written for this diagnosis only.
LANGUAGE_PAIRS = {
    "HO-035": {"vi": "Ngân sách team building hằng năm cho mỗi nhân viên là bao nhiêu?"},
    "HO-036": {"vi": "Theo chính sách chia sẻ tri thức, ai được xem tài liệu của tổ chức?"},
    "HO-037": {"en": "How much is the Employee Referral Bonus and what are the conditions?"},
    "HO-038": {
        "en": "What is the maximum number of hours for a Wellness Check, is leave deducted?"
    },
}


def _item(raw: dict) -> dict:
    return {
        "id": raw["id"],
        "group": raw["group"],
        "role": raw["role"],
        "question": raw["question"],
        "gold_status": raw["gold_status"],
        "gold_citations": raw.get("gold_citations", []),
        "excerpts": raw.get("source_excerpt", []),
    }


def main() -> None:
    items = yaml.safe_load((ROOT / "docs/eval/heldout-v1.yaml").read_text(encoding="utf-8"))[
        "items"
    ]
    by_id = {raw["id"]: raw for raw in items}
    manifest_path = ROOT / "artifacts/prompt3d/uat-stack/runtime-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    codes = {doc["id"]: doc["code"] for doc in manifest["documents"]}
    OUT.mkdir(parents=True, exist_ok=True)

    full = [_item(by_id[i]) for i in [*DETERMINISTIC_FIRST, *FALSE_REFUSALS, *OTHERS]]
    pairs = []
    for case_id, other in LANGUAGE_PAIRS.items():
        base = _item(by_id[case_id])
        language = by_id[case_id]["language"]
        translated_key, translated = next(iter(other.items()))
        full.append({**base, "id": f"{case_id}-{translated_key}", "question": translated})
        pairs.append({**base, language: base["question"], translated_key: translated})
    (OUT / "input_full.json").write_text(
        json.dumps({"codes": codes, "items": full, "pairs": pairs}, ensure_ascii=False),
        encoding="utf-8",
    )

    namespace = runpy.run_path(str(ROOT / "artifacts/rag-h5-1-stress-uat.py"))
    role = namespace["EMAIL"].split(".")[0]
    dev = [{"id": row[0], "role": role, "question": row[2]} for row in namespace["CORE"]]
    route = [_item(raw) for raw in items] + dev
    (OUT / "input_route.json").write_text(
        json.dumps({"codes": codes, "items": route}, ensure_ascii=False), encoding="utf-8"
    )
    print(f"full {len(full)}; route {len(route)}; dev role {role}")


if __name__ == "__main__":
    main()
