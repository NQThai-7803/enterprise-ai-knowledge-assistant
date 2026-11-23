"""DEC-042 direction 2 (RAG_PROMPT_CHUNK_SELECTION): which retrieved chunks reach the prompt."""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

import pytest

from app.core.config import Settings
from app.services.grounded_answer_service import _simple_select_hits
from tests.unit.test_grounded_answer_service import hit

QUESTION = "Mức phụ cấp ca đêm cho kho lạnh là bao nhiêu?"


def chunk(name: str, document: str, text: str = "nội dung chung") -> object:
    return replace(
        hit(text),
        chunk_id=UUID(int=hash(name) % 2**64),
        document_id=UUID(int=ord(document)),
        document_title=name,
    )


# hybrid order: three chunks of A first, its third holding the asked words, then B, C, D, E
HITS = (
    chunk("A1", "A"),
    chunk("A2", "A"),
    chunk("A3", "A", "Phụ cấp ca đêm cho kho lạnh là 40.000 đồng mỗi ca."),
    chunk("B1", "B"),
    chunk("C1", "C"),
    chunk("D1", "D"),
    chunk("E1", "E"),
)


def names(hits: tuple) -> list[str]:
    return [h.document_title for h in hits]


def test_default_keeps_two_chunks_per_document_in_hybrid_order() -> None:
    assert names(_simple_select_hits(HITS)) == ["A1", "A2", "B1", "C1", "D1"]
    assert Settings(_env_file=None).rag_prompt_chunk_selection == "rrf"


def test_per_document_3_lets_a_third_chunk_in_and_keeps_five_sources() -> None:
    chosen = _simple_select_hits(HITS, selection="per_document_3", question=QUESTION)
    assert names(chosen) == ["A1", "A2", "A3", "B1", "C1"]


def test_lexical_gives_a_documents_places_to_its_closest_chunks() -> None:
    chosen = _simple_select_hits(HITS, selection="lexical", question=QUESTION)
    # A keeps its two places, the first now taken by the chunk with the asked words
    assert names(chosen) == ["A3", "A1", "B1", "C1", "D1"]


@pytest.mark.parametrize("selection", ["rrf", "per_document_3", "lexical"])
def test_only_retrieved_hits_are_chosen(selection: str) -> None:
    chosen = _simple_select_hits(HITS[3:], selection=selection, question=QUESTION)
    assert set(names(chosen)) <= {"B1", "C1", "D1", "E1"}
