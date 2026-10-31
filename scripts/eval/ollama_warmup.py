"""Send one warm-up chat request to Ollama before an eval run and report what it cost.

The request mirrors the app's OpenAI-compatible call (same model, num_ctx and keep_alive, and the
/no_think prefix used with reasoning_effort=none), so Ollama keeps the same loaded runner for the
eval questions instead of reloading it. The result is not part of any eval score.

usage: ollama_warmup.py <out.json> [--base-url URL] [--model M] [--num-ctx N] [--keep-alive D]
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from urllib.request import Request, urlopen


def _get(url: str) -> object:
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode())


def _loaded_models(base_url: str) -> list[dict[str, object]]:
    models = _get(f"{base_url}/api/ps").get("models", [])  # type: ignore[union-attr]
    return [
        {key: model.get(key) for key in ("name", "digest", "size_vram", "expires_at")}
        for model in models
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--num-ctx", type=int, default=8192)
    parser.add_argument("--keep-alive", default="10m")
    args = parser.parse_args()

    before = _loaded_models(args.base_url)
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": "/no_think\nReply with OK."}],
        "temperature": 0,
        "max_tokens": 8,
        "stream": False,
        "options": {"num_ctx": args.num_ctx},
        "keep_alive": args.keep_alive,
    }
    request = Request(
        f"{args.base_url}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=600) as response:
        status = response.status
        body = json.loads(response.read().decode())
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    record = {
        "at": datetime.now(UTC).isoformat(),
        "model": args.model,
        "num_ctx": args.num_ctx,
        "keep_alive": args.keep_alive,
        "http_status": status,
        "elapsed_ms": elapsed_ms,
        "model_was_loaded_before": any(m["name"] == args.model for m in before),
        "loaded_before": before,
        "loaded_after": _loaded_models(args.base_url),
        "completion_tokens": (body.get("usage") or {}).get("completion_tokens"),
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=1)
    print(json.dumps({k: record[k] for k in ("elapsed_ms", "model_was_loaded_before")}))


if __name__ == "__main__":
    main()
