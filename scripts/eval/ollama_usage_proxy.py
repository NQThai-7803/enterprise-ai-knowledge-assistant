"""Logging proxy between the API and Ollama that records token usage per LLM call.

Eval only. Forwards every request to the upstream Ollama unchanged and, for chat completions,
appends one JSON line with the matched eval case id, prompt/completion tokens, message count,
prompt size in characters and elapsed time. It never stores prompt or answer text; the case id is
found by looking for each question of the question file inside the last user message.
With --tiktoken-encoding it also records tiktoken_tokens: the sum of the tiktoken token counts of
the message contents, the same count the app's prompt budget guard multiplies by
LLM_TOKEN_ESTIMATE_RATIO (PROMPT 4 item 0b calibration).

usage: ollama_usage_proxy.py <out.jsonl> [--listen 127.0.0.1:11435]
       [--upstream http://127.0.0.1:11434] [--questions artifacts/rag-h5-1-stress-uat.py]
       [--tiktoken-encoding cl100k_base]
Point the API at it with EVAL_OLLAMA_BASE_URL=http://host.docker.internal:11435.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import runpy
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

LOCK = threading.Lock()


def make_handler(upstream: str, out_path: str, questions: list[tuple[str, str]], encoding=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002 - silence default access log
            return

        def _forward(self, body: bytes | None) -> tuple[int, dict[str, str], bytes]:
            headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host",)}
            request = Request(upstream + self.path, data=body, headers=headers, method=self.command)
            try:
                with urlopen(request, timeout=900) as response:
                    return response.status, dict(response.headers), response.read()
            except HTTPError as exc:
                return exc.code, dict(exc.headers), exc.read()

        def _reply(self, status: int, headers: dict[str, str], payload: bytes) -> None:
            self.send_response(status)
            for key, value in headers.items():
                if key.lower() not in ("transfer-encoding", "connection", "content-length"):
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):  # noqa: N802
            self._reply(*self._forward(None))

        def do_POST(self):  # noqa: N802
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            started = time.perf_counter()
            status, headers, payload = self._forward(body)
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            if self.path.endswith("/chat/completions"):
                self._record(body, status, payload, elapsed_ms)
            self._reply(status, headers, payload)

        def _record(self, body: bytes, status: int, payload: bytes, elapsed_ms: int) -> None:
            try:
                request = json.loads(body)
            except ValueError:
                request = {}
            messages = request.get("messages") or []
            last_user = next(
                (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), ""
            )
            case_id = next((cid for cid, q in questions if q and q in last_user), None)
            usage: dict[str, object] = {}
            with contextlib.suppress(ValueError):
                usage = json.loads(payload).get("usage") or {}
            record = {
                "at": datetime.now(UTC).isoformat(),
                "case": case_id,
                "status": status,
                "elapsed_ms": elapsed_ms,
                "messages": len(messages),
                "prompt_chars": sum(len(str(m.get("content", ""))) for m in messages),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "max_tokens": request.get("max_tokens"),
                "num_ctx_option": (request.get("options") or {}).get("num_ctx"),
            }
            if encoding is not None:
                record["tiktoken_tokens"] = sum(
                    len(encoding.encode(str(m.get("content", "")))) for m in messages
                )
            with LOCK, open(out_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--listen", default="127.0.0.1:11435")
    parser.add_argument("--upstream", default="http://127.0.0.1:11434")
    parser.add_argument("--questions", default="artifacts/rag-h5-1-stress-uat.py")
    parser.add_argument("--tiktoken-encoding", default=None)
    args = parser.parse_args()
    encoding = None
    if args.tiktoken_encoding:
        import tiktoken

        encoding = tiktoken.get_encoding(args.tiktoken_encoding)
    core = runpy.run_path(args.questions)["CORE"]
    # Longest question first, so a question that contains another one is matched first.
    questions = sorted(((row[0], row[2]) for row in core), key=lambda item: -len(item[1]))
    host, port = args.listen.rsplit(":", 1)
    server = ThreadingHTTPServer(
        (host, int(port)), make_handler(args.upstream, args.out, questions, encoding)
    )
    print(f"proxy {args.listen} -> {args.upstream}, logging to {args.out}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
