from scripts.eval import branch_counters

SAMPLE = (
    "# TYPE enterprise_ai_rag_answer_branch_total counter\n"
    'enterprise_ai_rag_answer_branch_total{branch="reselect_after_rejection"} 4\n'
    'enterprise_ai_rag_answer_branch_total{branch="reselect_guard_would_change"} 1\n'
    'enterprise_ai_http_requests_total{route="/x"} 9\n'
)


def test_parse_reads_only_the_branch_counters() -> None:
    assert branch_counters.parse(SAMPLE) == {
        "reselect_after_rejection": 4,
        "reselect_guard_would_change": 1,
    }


def test_parse_of_a_stack_without_counters_is_not_measured_rather_than_zero() -> None:
    assert branch_counters.parse('enterprise_ai_http_requests_total{route="/x"} 9\n') is None


def test_delta_is_the_change_over_the_run() -> None:
    assert branch_counters.delta({"a": 1, "b": 0}, {"a": 4, "b": 0}) == {"a": 3, "b": 0}


def test_delta_is_not_measured_when_a_side_is_missing_or_the_counter_fell() -> None:
    assert branch_counters.delta(None, {"a": 1}) is None
    assert branch_counters.delta({"a": 1}, None) is None
    assert branch_counters.delta({"a": 5}, {"a": 1}) is None
