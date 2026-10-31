"""Run the frozen held-out set against an eval stack, one session per item, as the item's role.

usage (repo root, project venv):
  python scripts/eval/run_heldout.py --output <dir>/runtime_results.json [--resume] [--case HO-001]

Refuses to run unless the SHA256 of docs/eval/heldout-v1.yaml matches docs/eval/heldout-v1.lock.
Passwords come from EVAL_PASSWORD_STAFF / _MANAGER / _ADMIN and are never written to any
output. Transport, timeout and 5xx failures are INFRA_ERROR (scripts/eval/eval_client)
and are retried once at the end of the run. This runner records answers only; it never grades.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_client import INFRA_ERROR, OK, EvalClient, EvalInfraError, extract  # noqa: E402

HELDOUT = ROOT / "docs" / "eval" / "heldout-v1.yaml"
LOCK = ROOT / "docs" / "eval" / "heldout-v1.lock"
ACCOUNTS = {
    "staff": "staff.uat@example.test",
    "manager": "manager.uat@example.test",
    "admin": "admin.uat@example.test",
}


class HeldoutHashMismatchError(RuntimeError):
    """The held-out file differs from the frozen hash."""


def verify_frozen(heldout: Path = HELDOUT, lock: Path = LOCK) -> dict[str, Any]:
    if not lock.is_file():
        raise HeldoutHashMismatchError(f"lock file missing: {lock}")
    expected = json.loads(lock.read_text(encoding="utf-8"))
    actual = hashlib.sha256(heldout.read_bytes()).hexdigest()
    if actual != expected["sha256"]:
        raise HeldoutHashMismatchError(
            f"{heldout.name} sha256 {actual} != frozen {expected['sha256']}; refusing to run"
        )
    return expected


def yaml_items(heldout: Path) -> list[dict[str, Any]]:
    import yaml

    return yaml.safe_load(heldout.read_text(encoding="utf-8"))["items"]


def load_items() -> list[dict[str, Any]]:
    return yaml_items(HELDOUT)


def _ask(client: EvalClient, item: dict[str, Any], attempts: int) -> dict[str, Any]:
    try:
        session_id = client.create_session(f"heldout-v1 {item['id']}")
    except EvalInfraError:
        result: dict[str, Any] = {
            "status": INFRA_ERROR,
            "answer": "",
            "citations": [],
            "retrieved": 0,
            "http": 0,
            "latency_ms": None,
            "execution_status": INFRA_ERROR,
            "failure_class": "INFRA_SESSION",
        }
        session_id = None
    else:
        result = extract(client.ask(session_id, item["question"]))
    result.update(
        {
            "id": item["id"],
            "group": item["group"],
            "role": item["role"],
            "question": item["question"],
            "session_id": session_id,
            "attempts": attempts,
        }
    )
    return result


def run(
    *,
    output: Path,
    selected: set[str],
    resume: bool,
    base_url: str,
    passwords: dict[str, str],
    delay_seconds: float = 0.5,
    client_factory=None,  # noqa: ANN001 - tests inject a fake
) -> int:
    lock = verify_frozen()
    items = [i for i in load_items() if not selected or i["id"] in selected]
    started_at = datetime.now(UTC).isoformat()
    done: dict[str, dict[str, Any]] = {}
    if resume and output.exists():
        previous = json.loads(output.read_text(encoding="utf-8"))
        started_at = previous.get("started_at", started_at)
        done = {
            c["id"]: c
            for c in previous["cases"]
            if c["execution_status"] != INFRA_ERROR or c.get("attempts", 1) > 1
        }

    def make_client(role: str) -> EvalClient:
        if client_factory is not None:
            return client_factory(role)
        return EvalClient(base_url, email=ACCOUNTS[role], password=passwords[role])

    clients: dict[str, EvalClient] = {}
    results: list[dict[str, Any]] = []

    def save(status: str) -> None:
        payload = {
            "status": status,
            "heldout_sha256": lock["sha256"],
            "heldout_version": lock["version"],
            "started_at": started_at,
            "updated_at": datetime.now(UTC).isoformat(),
            "planned_cases": len(items),
            "completed_cases": len(results),
            "infra_error_cases": sum(r["execution_status"] == INFRA_ERROR for r in results),
            "infra_error_retried_cases": sum(r.get("attempts", 1) > 1 for r in results),
            "cases": results,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    try:
        for index, item in enumerate(items, 1):
            if item["id"] in done:
                results.append(done[item["id"]])
                print(f"[{index}/{len(items)}] {item['id']} RESUMED", flush=True)
                continue
            if results and delay_seconds > 0:
                time.sleep(delay_seconds)
            client = clients.setdefault(item["role"], make_client(item["role"]))
            result = _ask(client, item, attempts=1)
            results.append(result)
            save("IN_PROGRESS")
            print(
                f"[{index}/{len(items)}] {item['id']} {item['role']} {result['status']} "
                f"{result['latency_ms']}ms {result['execution_status']}",
                flush=True,
            )
        by_id = {i["id"]: i for i in items}
        for position, result in enumerate(results):
            if result["execution_status"] != INFRA_ERROR or result.get("attempts", 1) > 1:
                continue
            item = by_id[result["id"]]
            client = clients.setdefault(item["role"], make_client(item["role"]))
            retry = _ask(client, item, attempts=2)
            retry["first_attempt_failure_class"] = result.get("failure_class")
            results[position] = retry
            save("IN_PROGRESS")
            print(
                f"[retry] {retry['id']} {retry['status']} {retry['execution_status']}", flush=True
            )
    finally:
        for client in clients.values():
            close = getattr(client, "close", None)
            if close is not None:
                close()
    complete = len(results) == len(items) and all(r["execution_status"] == OK for r in results)
    save("COMPLETE" if complete else "PARTIAL")
    return 0 if complete else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    args = parser.parse_args()
    passwords = {}
    for role in ACCOUNTS:
        value = os.environ.get(f"EVAL_PASSWORD_{role.upper()}")
        if not value:
            parser.error(f"set EVAL_PASSWORD_{role.upper()}")
        passwords[role] = value
    try:
        return run(
            output=args.output,
            selected=set(args.case),
            resume=args.resume,
            base_url=os.environ.get("RAG_ACCEPTANCE_BASE_URL", "http://127.0.0.1:18190"),
            passwords=passwords,
            delay_seconds=max(0.0, args.delay_seconds),
        )
    except HeldoutHashMismatchError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
