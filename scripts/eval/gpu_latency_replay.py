"""DEC-041: LLM time per question on a local GPU, replayed from a CI simple-mode trace.

usage: python scripts/eval/gpu_latency_replay.py <name>=<simple_trace.jsonl>... --out <out.json>
           [--ids ND-001 ...] [--base-url http://127.0.0.1:11434] [--model qwen3.5-text:4b]

Each trace comes from a natural_dev_v1 run with EVAL_ABLATION=simple_trace (one per
configuration, e.g. s3t=... hybrid=...): every simple-mode draft with its question, sources,
attempt and outcome. For each item asked, the script rebuilds every draft's prompt as the simple
path does (build_simple_grounded_prompt; a retry adds the rejection reason and the first draft)
and sends it through the app's own provider with the eval stack's LLM settings (Ollama, num_ctx
8192, seed, 512 output tokens, reasoning effort none, temperature 0). A question costs the sum of
its calls; one with no draft in the trace (the deterministic route answered it, or a refusal
gate before the LLM) costs no LLM time. Retrieval, embeddings and validation are not included.
One warm-up call loads the model first and is not counted. Prints ids, counts and ms only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import sys
import unicodedata
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.chat.prompt_builder import build_simple_grounded_prompt  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.llm.factory import create_llm_provider  # noqa: E402
from app.llm.models import LLMMessage  # noqa: E402
from app.models.enums import CitationSourceType  # noqa: E402
from app.services.grounded_answer_service import SIMPLE_RETRY_INSTRUCTIONS  # noqa: E402

DEFAULT_IDS = [f"ND-{n:03d}" for n in range(1, 11)]


def _key(text: str) -> str:
    return unicodedata.normalize("NFC", " ".join(text.split()))


def eval_settings(base_url: str, model: str) -> Settings:
    """The eval stack's LLM settings (eval.yml .env, compose.uat-eval.yaml)."""
    return Settings(
        _env_file=None,
        llm_enabled=True,
        llm_provider="ollama",
        llm_ollama_base_url=base_url,
        llm_ollama_model=model,
        llm_ollama_num_ctx=8192,
        llm_ollama_keep_alive="10m",
        llm_ollama_reasoning_effort="none",
        llm_max_output_tokens=512,
        llm_temperature=0.0,
        llm_seed=20261031,
        llm_timeout_seconds=600,
    )


def prompts(drafts: list[dict[str, Any]], settings: Settings) -> list[tuple[LLMMessage, ...]]:
    """The prompt of each draft of one question, in attempt order."""
    out = []
    previous: dict[str, Any] | None = None
    for draft in sorted(drafts, key=lambda d: d.get("attempt") or 0):
        sources = [
            SimpleNamespace(
                source_type=CitationSourceType.INTERNAL,
                label=s["label"],
                document_title=s["title"],
                start_page=(s.get("pages") or [None])[0],
                text=s["text"],
            )
            for s in draft["sources"]
        ]
        reason = None
        if previous is not None:
            outcome = previous["outcome"]
            reason = SIMPLE_RETRY_INSTRUCTIONS.get(
                "claim" if outcome.startswith("claim_") else outcome
            )
        out.append(
            build_simple_grounded_prompt(
                question=draft["question"],
                source_registry=SimpleNamespace(sources=sources),
                no_answer_sentinel=settings.llm_no_answer_sentinel,
                retry_reason=reason,
                previous_answer=previous["draft"] if previous else None,
                short=settings.rag_simple_short_prompt_enabled,
            )
        )
        previous = draft
    return out


def percentile(values: list[int], q: float) -> int:
    """Nearest rank: with 10 values p50 is the 5th and p95 the 10th."""
    ranked = sorted(values)
    return ranked[max(0, math.ceil(q * len(ranked)) - 1)]


async def replay(
    traces: dict[str, Path], items: list[dict[str, Any]], settings: Settings
) -> dict[str, Any]:
    provider = create_llm_provider(settings)
    args = {"temperature": settings.llm_temperature, "max_output_tokens": 512}
    warm = await provider.generate(messages=(LLMMessage(role="user", content="OK?"),), **args)
    result: dict[str, Any] = {"warmup_ms": warm.response_time_ms, "configs": {}}
    for name, path in traces.items():
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        per_item = {}
        for item in items:
            drafts = [
                r
                for r in records
                if "draft" in r and _key(r.get("asked") or "") == _key(item["question"])
            ]
            times = []
            for messages in prompts(drafts, settings):
                generation = await provider.generate(messages=messages, **args)
                times.append(generation.response_time_ms)
            per_item[item["id"]] = {"calls": len(times), "llm_ms": sum(times)}
        totals = [row["llm_ms"] for row in per_item.values()]
        result["configs"][name] = {
            "items": per_item,
            "p50_ms": percentile(totals, 0.50),
            "p95_ms": percentile(totals, 0.95),
            "mean_ms": int(statistics.mean(totals)),
            "calls": sum(row["calls"] for row in per_item.values()),
        }
    close = getattr(provider, "aclose", None)
    if close is not None:
        await close()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("traces", nargs="+", help="name=path/to/simple_trace.jsonl")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ids", nargs="+", default=DEFAULT_IDS)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="qwen3.5-text:4b")
    args = parser.parse_args(argv)
    from scripts.eval.run_natural_dev import verified_inputs

    by_id = {item["id"]: item for item in verified_inputs()["items"]}
    items = [by_id[i] for i in args.ids]
    traces = dict(entry.split("=", 1) for entry in args.traces)
    result = asyncio.run(
        replay(
            {k: Path(v) for k, v in traces.items()},
            items,
            eval_settings(args.base_url, args.model),
        )
    )
    result |= {"model": args.model, "ids": args.ids}
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    for name, config in result["configs"].items():
        print(
            f"{name}: p50 {config['p50_ms']} ms, p95 {config['p95_ms']} ms, calls {config['calls']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
