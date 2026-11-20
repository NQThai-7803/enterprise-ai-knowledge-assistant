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


def test_similarity_buckets_are_read_per_route_with_every_cosine_of_a_case() -> None:
    text = "\n".join(
        (
            'enterprise_ai_rag_answer_branch_total{branch="route_llm"} 3',
            'enterprise_ai_rag_question_evidence_similarity_total{bucket="0.83",route="llm"} 2',
            'enterprise_ai_rag_question_evidence_similarity_total{bucket="0.91",route="local"} 1',
        )
    )
    before = branch_counters.parse(text)
    assert before == {"route_llm": 3, "similarity_llm_0.83": 2, "similarity_local_0.91": 1}
    after = dict(before, **{"similarity_llm_0.83": 4, "similarity_llm_0.79": 1})
    delta = branch_counters.delta(before, after)
    # An intermediate draft at 0.79 and two at 0.83; the server-built 0.91 is not an LLM draft.
    assert branch_counters.similarities(delta) == [0.79, 0.83, 0.83]
    assert branch_counters.similarities(branch_counters.delta(before, before)) == []
    assert branch_counters.similarities(None) is None


def test_the_api_route_label_wins_and_an_older_api_falls_back_to_two_routes() -> None:
    assert branch_counters.answer_route({"answer_route_det_overtime_rate": 1, "route_llm": 0}) == (
        "det_overtime_rate"
    )
    assert branch_counters.answer_route({"answer_route_llm_simple": 1, "route_llm": 1}) == (
        "llm_simple"
    )
    assert branch_counters.answer_route({"route_deterministic": 1, "route_llm": 0}) == (
        "deterministic"
    )
    assert branch_counters.answer_route({"answer_route_llm_simple": 2}) is None  # two answers
    assert branch_counters.answer_route(None) is None


def test_coarse_route_keeps_the_two_routes_the_uat_reports_split_by() -> None:
    assert [
        branch_counters.coarse_route(r)
        for r in ("det_x", "repair_y", "deterministic", "llm_simple", "refusal_gate", "llm", None)
    ] == ["deterministic", "deterministic", "deterministic", "llm", "llm", "llm", None]


def test_route_fields_hold_the_route_and_every_no_answer_reason_of_one_question() -> None:
    before = {"answer_route_llm_simple": 4, "no_answer_simple_claim_insufficient": 1}
    after = {
        "answer_route_llm_simple": 5,
        "no_answer_simple_claim_insufficient": 2,
        "no_answer_simple_llm_refused": 1,
    }
    assert branch_counters.route_fields(before, after) == {
        "answer_route": "llm_simple",
        "no_answer_reasons": ["simple_claim_insufficient", "simple_llm_refused"],
    }
    assert branch_counters.route_fields(None, after) == {
        "answer_route": None,
        "no_answer_reasons": None,
    }
