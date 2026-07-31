from __future__ import annotations

from app.citations.parser import parse_citation_markers


def test_parser_finds_single_marker() -> None:
    parsed = parse_citation_markers("Answer [SOURCE_1].")

    assert parsed.ordered_unique_markers == ("[SOURCE_1]",)
    assert parsed.all_marker_occurrences == ("[SOURCE_1]",)


def test_parser_finds_multiple_markers() -> None:
    parsed = parse_citation_markers("A [SOURCE_1]. B [SOURCE_2].")

    assert parsed.all_marker_occurrences == ("[SOURCE_1]", "[SOURCE_2]")


def test_parser_preserves_first_appearance_order() -> None:
    parsed = parse_citation_markers("B [SOURCE_2]. A [SOURCE_1].")

    assert parsed.ordered_unique_markers == ("[SOURCE_2]", "[SOURCE_1]")


def test_parser_deduplicates_repeated_marker() -> None:
    parsed = parse_citation_markers("A [SOURCE_1]. Again [SOURCE_1].")

    assert parsed.ordered_unique_markers == ("[SOURCE_1]",)
    assert parsed.all_marker_occurrences == ("[SOURCE_1]", "[SOURCE_1]")


def test_parser_distinguishes_source_1_and_source_10() -> None:
    parsed = parse_citation_markers("[SOURCE_1] [SOURCE_10]")

    assert parsed.ordered_unique_markers == ("[SOURCE_1]", "[SOURCE_10]")


def test_parser_ignores_malformed_marker() -> None:
    parsed = parse_citation_markers("[SOURCE_0] [SOURCE_X] [SOURCE_01]")

    assert parsed.ordered_unique_markers == ()


def test_parser_does_not_parse_document_ids() -> None:
    parsed = parse_citation_markers('{"document_id": "SOURCE_1"} [DOCUMENT abc]')

    assert parsed.ordered_unique_markers == ()


def test_parser_is_bounded_for_long_answer() -> None:
    answer = "word " * 20_000 + "[SOURCE_1]"

    parsed = parse_citation_markers(answer)

    assert parsed.ordered_unique_markers == ("[SOURCE_1]",)
