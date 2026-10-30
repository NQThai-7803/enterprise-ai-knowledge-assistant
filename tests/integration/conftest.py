"""Integration fixtures are defined in tests/conftest.py."""

from collections.abc import Generator

import pytest

from tests.integration.semantic_query_diagnostics import (
    record_failed_phases,
    semantic_query_diagnostics,
)

__all__ = ["semantic_query_diagnostics"]


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    report = yield
    record_failed_phases(item, report)
    return report
