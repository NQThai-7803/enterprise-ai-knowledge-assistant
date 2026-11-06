from __future__ import annotations

from scripts.diagnostics import heldout_trace


def _passes() -> bool:
    return True


def _text() -> str:
    return "ignored"


def _rule() -> bool:
    _text()
    result = _passes()
    return result


def test_child_checks_report_direct_helpers_and_the_exit_line() -> None:
    seen = {}

    def after(result, kwargs, checks, line) -> None:
        seen.update(result=result, kwargs=kwargs, checks=checks, line=line)

    wrapped = heldout_trace._with_child_checks(_rule, after)

    assert wrapped() is True
    assert [check["check"] for check in seen["checks"]] == ["_passes"]
    assert seen["checks"][0]["result"] is True
    assert seen["line"] == _rule.__code__.co_firstlineno + 3
