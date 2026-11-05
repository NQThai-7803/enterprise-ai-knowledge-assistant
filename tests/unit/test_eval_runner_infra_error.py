"""Eval runner: transport/timeout/5xx are INFRA_ERROR, retried once at the end, not scored."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from scripts.eval import eval_client
from scripts.eval.eval_client import HTTP_ERROR, INFRA_ERROR, OK, EvalClient
from scripts.eval.grade_proxy import grade
from tests.acceptance import rag_h5_2_exact_100 as runner

ANSWER_BODY = {
    "data": {
        "grounding_status": "ANSWERED",
        "retrieved_chunk_count": 3,
        "assistant_message": {"content": "Answer [1]", "citations": [{"document_id": "d1"}]},
    }
}


def _client(handler, **kwargs) -> EvalClient:  # noqa: ANN001
    def routed(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"data": {"access_token": "t", "expires_in": 900}})
        if request.url.path == "/api/v1/chat/sessions":
            return httpx.Response(201, json={"data": {"id": "s1"}})
        return handler(request)

    return EvalClient(
        "http://eval.test",
        email="e",
        password="p",
        transport=httpx.MockTransport(routed),
        retry_sleep_seconds=0.0,
        **kwargs,
    )


def _raise(exc_type):  # noqa: ANN001
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc_type("boom", request=request)

    return handler


@pytest.mark.parametrize(
    ("handler", "expected", "failure"),
    [
        (lambda _r: httpx.Response(201, json=ANSWER_BODY), OK, None),
        (_raise(httpx.ConnectError), INFRA_ERROR, "INFRA_TRANSPORT"),
        (_raise(httpx.ReadTimeout), INFRA_ERROR, "INFRA_TIMEOUT"),
        (lambda _r: httpx.Response(503, json={"error": {}}), INFRA_ERROR, "INFRA_HTTP_5XX"),
        (lambda _r: httpx.Response(500, text="not json"), INFRA_ERROR, "INFRA_HTTP_5XX"),
        (lambda _r: httpx.Response(201, json={"data": {}}), INFRA_ERROR, "INFRA_BAD_RESPONSE"),
        (lambda _r: httpx.Response(429, json={}), INFRA_ERROR, "INFRA_RATE_LIMIT"),
        (lambda _r: httpx.Response(422, json={"error": {}}), HTTP_ERROR, "HTTP_422"),
    ],
    ids=["ok", "transport", "timeout", "503", "500_text", "bad_body", "429", "422"],
)
def test_classification_never_marks_failures_ok(handler, expected, failure) -> None:  # noqa: ANN001
    with _client(handler, rate_limit_retries=1) as client:
        result = client.ask("s1", "q")
    assert result.execution_status == expected
    assert result.failure_class == failure
    flat = eval_client.extract(result)
    assert flat["execution_status"] == expected
    if expected != OK:
        assert flat["status"] == expected and flat["citations"] == []


def test_one_http_client_is_reused_and_401_relogs_once() -> None:
    calls = {"messages": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["messages"] += 1
        if calls["messages"] == 1:
            return httpx.Response(401, json={})
        return httpx.Response(201, json=ANSWER_BODY)

    with _client(handler) as client:
        http = client.http
        first = client.ask("s1", "q")
        second = client.ask("s1", "q")
        assert client.http is http
    assert first.execution_status == OK and second.execution_status == OK
    assert calls["messages"] == 3


class FakeClient:
    """Answers from a per-question script; an exhausted script keeps its last outcome."""

    def __init__(self, script: dict[str, list[str]]) -> None:
        self.script = script
        self.asked: list[str] = []

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def create_session(self, title: str) -> str:
        return title

    def ask(self, session_id: str, question: str) -> eval_client.AskResult:
        self.asked.append(question)
        outcomes = self.script[question]
        outcome = outcomes.pop(0) if len(outcomes) > 1 else outcomes[0]
        if outcome == OK:
            return eval_client.AskResult(201, ANSWER_BODY, 5, OK, None)
        return eval_client.AskResult(0, None, 5, INFRA_ERROR, "INFRA_TRANSPORT")


BENCHMARK = (("Q001", "c", "q1"), ("Q002", "c", "q2"), ("Q003", "c", "q3"))


def _run(tmp_path: Path, script: dict[str, list[str]], *, resume: bool = False):
    fake = FakeClient(script)
    output = tmp_path / "runtime_results.json"
    exit_code = runner.run(
        selected_ids=set(),
        output=output,
        resume=resume,
        delay_seconds=0.0,
        client_factory=lambda _credentials: fake,
        benchmark_loader=lambda: (("e", "p"), BENCHMARK),
    )
    return exit_code, json.loads(output.read_text(encoding="utf-8")), fake


def test_infra_error_is_retried_once_at_the_end_of_the_run(tmp_path: Path) -> None:
    exit_code, payload, fake = _run(
        tmp_path, {"q1": [OK], "q2": [INFRA_ERROR, OK], "q3": [INFRA_ERROR]}
    )

    assert fake.asked == ["q1", "q2", "q3", "q2", "q3"]  # retries after the last question
    cases = {case["id"]: case for case in payload["cases"]}
    assert cases["Q002"]["execution_status"] == OK and cases["Q002"]["attempts"] == 2
    assert cases["Q002"]["first_attempt_failure_class"] == "INFRA_TRANSPORT"
    assert cases["Q003"]["execution_status"] == INFRA_ERROR and cases["Q003"]["attempts"] == 2
    assert payload["infra_error_cases"] == 1
    assert payload["infra_error_retried_cases"] == 2
    assert payload["status"] == "PARTIAL" and exit_code == 1


def test_resume_does_not_retry_an_infra_error_twice(tmp_path: Path) -> None:
    _run(tmp_path, {"q1": [OK], "q2": [OK], "q3": [INFRA_ERROR]})
    _, payload, fake = _run(tmp_path, {"q1": [OK], "q2": [OK], "q3": [OK]}, resume=True)

    assert fake.asked == []
    assert payload["infra_error_cases"] == 1


def test_proxy_grade_excludes_infra_error_and_reports_the_count() -> None:
    manifest = {"documents": [{"id": "d1", "code": "DOC1"}]}
    reference = {
        "cases": [
            {"id": i, "grounding_status": "ANSWERED", "citation_ids": [{"document_id": "d1"}]}
            for i in ("Q001", "Q002")
        ]
    }
    run = {
        "cases": [
            {
                "id": "Q001",
                "status": "ANSWERED",
                "citations": [{"document_id": "d1"}],
                "execution_status": OK,
            },
            {
                "id": "Q002",
                "status": INFRA_ERROR,
                "citations": [],
                "execution_status": INFRA_ERROR,
                "attempts": 2,
            },
        ]
    }

    summary = grade(reference, manifest, manifest, run)["summary"]

    assert summary["cases"] == 2
    assert summary["scored_cases"] == 1
    assert summary["proxy_match"] == 1
    assert summary["excluded_infra_error"] == 1
    assert summary["excluded_infra_error_ids"] == ["Q002"]
    assert summary["retried_cases"] == 1
