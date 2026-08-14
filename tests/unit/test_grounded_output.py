from __future__ import annotations

import pytest

from app.citations.grounded_output import parse_grounded_llm_output


def test_parse_valid_answer_with_one_citation() -> None:
    output = parse_grounded_llm_output(
        '{"answer":"Nguyen Anh Khoa la CEO.","citations":["SOURCE_1"]}',
        allowed_identifiers={"SOURCE_1"},
    )

    assert output.answer == "Nguyen Anh Khoa la CEO."
    assert output.citations == ("SOURCE_1",)


def test_parse_valid_answer_with_multiple_citations() -> None:
    output = parse_grounded_llm_output(
        '{"answer":"The policy has two supported conditions.","citations":["SOURCE_2","SOURCE_3"]}',
        allowed_identifiers={"SOURCE_1", "SOURCE_2", "SOURCE_3"},
    )

    assert output.citations == ("SOURCE_2", "SOURCE_3")


def test_parse_deduplicates_citations_preserving_order() -> None:
    output = parse_grounded_llm_output(
        '{"answer":"The policy is supported.","citations":["SOURCE_2","SOURCE_1","SOURCE_2"]}',
        allowed_identifiers={"SOURCE_1", "SOURCE_2"},
    )

    assert output.citations == ("SOURCE_2", "SOURCE_1")


def test_parse_rejects_unknown_citation_identifier() -> None:
    with pytest.raises(ValueError, match="source registry"):
        parse_grounded_llm_output(
            '{"answer":"The policy is supported.","citations":["SOURCE_9"]}',
            allowed_identifiers={"SOURCE_1"},
        )


@pytest.mark.parametrize("answer", ["", "   "])
def test_parse_rejects_empty_answer(answer: str) -> None:
    with pytest.raises(ValueError, match="answer"):
        parse_grounded_llm_output(
            f'{{"answer":{answer!r},"citations":["SOURCE_1"]}}'.replace("'", '"')
        )


@pytest.mark.parametrize("citations", ["[]", "null"])
def test_parse_rejects_empty_citations(citations: str) -> None:
    with pytest.raises(ValueError, match="citations"):
        parse_grounded_llm_output(
            f'{{"answer":"The policy is supported.","citations":{citations}}}'
        )


@pytest.mark.parametrize(
    "content",
    [
        '{"answer":"[SOURCE_3]","citations":["SOURCE_3"]}',
        '{"answer":"[1]","citations":["SOURCE_1"]}',
    ],
)
def test_parse_rejects_citation_only_answer(content: str) -> None:
    with pytest.raises(ValueError, match="citation"):
        parse_grounded_llm_output(content, allowed_identifiers={"SOURCE_1", "SOURCE_3"})


def test_parse_rejects_numeric_only_answer() -> None:
    with pytest.raises(ValueError, match="natural-language"):
        parse_grounded_llm_output(
            '{"answer":"12","citations":["SOURCE_1"]}',
            allowed_identifiers={"SOURCE_1"},
        )


def test_parse_rejects_answer_without_citations() -> None:
    with pytest.raises(ValueError, match="citations"):
        parse_grounded_llm_output('{"answer":"The policy is supported."}')


@pytest.mark.parametrize(
    "content",
    [
        "12 ngay",
        '{"answer":"The policy is supported.","citations":[SOURCE_1]}',
        '[{"answer":"The policy is supported.","citations":["SOURCE_1"]}]',
    ],
)
def test_parse_rejects_malformed_json(content: str) -> None:
    with pytest.raises(ValueError):
        parse_grounded_llm_output(content)


def test_parse_handles_single_markdown_json_fence() -> None:
    output = parse_grounded_llm_output(
        '```json\n{"answer":"The policy is supported.","citations":["SOURCE_1"]}\n```',
        allowed_identifiers={"SOURCE_1"},
    )

    assert output.answer == "The policy is supported."
    assert output.citations == ("SOURCE_1",)


def test_parse_rejects_bracketed_or_malformed_identifiers() -> None:
    for citation in ("[SOURCE_1]", "SOURCE_0", "SOURCE_01", "SOURCE_X", "source_1"):
        with pytest.raises(ValueError):
            parse_grounded_llm_output(
                f'{{"answer":"The policy is supported.","citations":["{citation}"]}}'
            )


def test_exact_no_answer_is_handled_outside_parser() -> None:
    with pytest.raises(ValueError):
        parse_grounded_llm_output("__NO_ANSWER__")
