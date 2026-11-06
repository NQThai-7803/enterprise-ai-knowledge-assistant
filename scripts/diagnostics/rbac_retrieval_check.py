"""Check the RBAC dev set at retrieval level, without the LLM. Run on the host, stack up.

usage: EVAL_PASSWORD_ADMIN=... python scripts/diagnostics/rbac_retrieval_check.py
           --container eaka-rbac-dev-api-1 --output artifacts/rbac-dev/retrieval.json

A failed control in run_rbac_dev.py can come from the answer layers, so its negative proves
nothing about permissions. Here a pair is conclusive when the authorized account retrieves the
document's chunk and the other account gets it at no layer, using heldout_trace.py in route mode.
Output holds ids, counts and verdicts only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.run_rbac_dev import ACCOUNTS, _Admin, load_set  # noqa: E402

TRACE = ROOT / "scripts" / "diagnostics" / "heldout_trace.py"
ENV = {**os.environ, "MSYS_NO_PATHCONV": "1"}


def seen_at(result: Mapping[str, Any]) -> list[str]:
    """Trace layers that held the document's chunk."""
    chunks = set(result["gold_chunks"]["chunks"])
    trace = result["trace"]
    layers = {
        "retrieve": trace["retrieve"],
        "semantic": trace["semantic"],
        "keyword": trace["keyword"],
        "prepared": trace["prepared"],
        "rerank": [entry["output"] for entry in trace["rerank"]],
    }
    seen = [
        name
        for name, entries in layers.items()
        if any(chunks & set(entry["cut_chunks"]) for entry in entries)
    ]
    if chunks & {source["chunk"] for source in trace.get("sources", [])}:
        seen.append("sources")
    return seen


def verdicts(
    control: Mapping[str, list[str]], negative: Mapping[str, list[str]]
) -> dict[str, dict[str, Any]]:
    return {
        case_id: {
            "control_layers": control[case_id],
            "negative_layers": negative[case_id],
            "conclusive": bool(control[case_id]) and not negative[case_id],
            "leak": bool(negative[case_id]),
        }
        for case_id in control
    }


def _trace(container: str, items: list[dict[str, Any]], codes: dict[str, str]) -> dict[str, list]:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "in.json"
        out = Path(folder) / "out.json"
        path.write_text(json.dumps({"codes": codes, "items": items}), encoding="utf-8")
        for source, target in ((TRACE, "/tmp/heldout_trace.py"), (path, "/tmp/rbac_in.json")):
            subprocess.run(
                ["docker", "cp", str(source), f"{container}:{target}"], check=True, env=ENV
            )
        subprocess.run(
            [
                "docker",
                "exec",
                "-w",
                "/app",
                "-e",
                "PYTHONPATH=/app",
                container,
                "python",
                "/tmp/heldout_trace.py",
                "--input",
                "/tmp/rbac_in.json",
                "--output",
                "/tmp/rbac_out.json",
                "--mode",
                "route",
            ],
            check=True,
            env=ENV,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["docker", "cp", f"{container}:/tmp/rbac_out.json", str(out)], check=True, env=ENV
        )
        results = json.loads(out.read_text(encoding="utf-8"))["results"]
    return {result["id"]: seen_at(result) for result in results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = load_set()
    base_url = os.environ.get("RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:18190")
    admin = _Admin(base_url, os.environ["EVAL_PASSWORD_ADMIN"])
    ids = {d["document_code"]: d["id"] for d in admin.get("/api/v1/documents?page_size=100")}
    codes = {document_id: code for code, document_id in ids.items()}
    revocable = next(d for d in data["documents"] if d.get("revocable_grant"))
    role = revocable["revocable_grant"]

    def items(key: str) -> list[dict[str, Any]]:
        return [
            {
                "id": item["id"],
                "role": item[key],
                "email": ACCOUNTS[item[key]],
                "question": item["question"],
                "gold_citations": [{"document": item["document"], "pages": [1]}],
            }
            for item in data["items"]
        ]

    admin.grant(ids[revocable["code"]], role)
    control = _trace(args.container, items("control"), codes)
    admin.revoke(ids[revocable["code"]], role)
    negative = _trace(args.container, items("account"), codes)
    result = verdicts(control, negative)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=1), encoding="utf-8")
    conclusive = sum(row["conclusive"] for row in result.values())
    leaks = [case_id for case_id, row in result.items() if row["leak"]]
    print(f"pairs: {len(result)}; conclusive: {conclusive}; chunk seen by the negative: {leaks}")
    return 1 if leaks else 0


if __name__ == "__main__":
    raise SystemExit(main())
