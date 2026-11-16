"""Simple answer mode (RAG_ANSWER_MODE=simple). Invented questions and sources only."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from app.chat.context_builder import select_context_for_prompt
from app.chat.models import GroundingStatus
from app.chat.prompt_builder import build_simple_grounded_prompt, build_simple_system_prompt
from app.citations.errors import CitationFailureCode, CitationValidationError
from app.citations.models import PromptSourceRegistry
from app.llm.models import LLMGenerationResult
from app.observability.metrics import GLOBAL_METRICS
from app.retrieval.subclaims import information_need_queries
from app.services import claim_evidence_validation_service as validation
from app.services.grounded_answer_service import (
    _simple_claim_text,
    _simple_select_hits,
    _simple_split_absences,
)
from tests.unit.test_grounded_answer_service import (
    FakeCitationValidationService,
    FakeCounter,
    FakeRetrievalService,
    SequentialFakeLLMProvider,
    chat_session,
    hit,
    make_service,
    retrieval_result,
    settings,
    user,
)

SOURCE = (
    "Quy dinh xe toi. Tai trong toi da cua xe toi la 2.500 kg. Day cap duoc kiem tra 2 lan moi quy."
)
QUESTION = "Xe toi co tai trong toi da the nao?"
GOOD = "Tai trong toi da cua xe toi la 2.500 kg [SOURCE_1]."


def _generation(content: str) -> LLMGenerationResult:
    return LLMGenerationResult(
        content=content, model="fake", finish_reason="stop", prompt_tokens=1,
        completion_tokens=1, response_time_ms=1,
    )  # fmt: skip


class StrictCitationValidation(FakeCitationValidationService):
    """Refuses a marker that is not in the registry, as the real service does."""

    async def validate_and_map(self, *, answer: str, source_registry, current_user):  # noqa: ANN001
        known = {source.marker for source in source_registry.sources}
        import re

        if any(marker not in known for marker in re.findall(r"\[SOURCE_\d+\]", answer)):
            raise CitationValidationError(CitationFailureCode.CITATION_MARKER_UNKNOWN)
        return await super().validate_and_map(
            answer=answer, source_registry=source_registry, current_user=current_user
        )


def _ask(
    *contents: str,
    mode: str = "simple",
    hits: tuple = (),
    embeddings: Any = None,
    question: str = QUESTION,
    **flags: Any,
) -> tuple:
    llm = SequentialFakeLLMProvider(*(_generation(c) for c in contents))
    retrieval = FakeRetrievalService(retrieval_result(*(hits or (hit(SOURCE),))))
    if embeddings is not None:
        retrieval.semantic_retrieval_service = SimpleNamespace(embedding_provider=embeddings)
    service, _, _, _, resolved_llm, _, _ = make_service(
        retrieval=retrieval,
        llm=llm,
        citation_validation=StrictCitationValidation(),
        settings_obj=settings(rag_answer_mode=mode, **flags),
    )
    result = asyncio.run(
        service.answer_question(
            current_user=user(), session_id=chat_session().id, question=question
        )
    )
    return result, resolved_llm


@pytest.fixture(autouse=True)
def _clean_counters() -> Any:
    GLOBAL_METRICS.reset()
    yield
    GLOBAL_METRICS.reset()


def _hit(doc: int, chunk: int) -> Any:
    return replace(
        hit(f"doc {doc} chunk {chunk}"),
        chunk_id=UUID(int=1000 + 10 * doc + chunk),
        document_id=UUID(int=doc),
    )


def test_simple_takes_the_first_five_chunks_with_at_most_two_per_document() -> None:
    hits = (_hit(1, 1), _hit(1, 2), _hit(1, 3), _hit(2, 1), _hit(1, 4), _hit(3, 1), _hit(2, 2),
            _hit(4, 1))  # fmt: skip
    chosen = _simple_select_hits(hits)
    assert [(h.document_id.int, h.text[-7:]) for h in chosen] == [
        (1, "chunk 1"), (1, "chunk 2"), (2, "chunk 1"), (3, "chunk 1"), (2, "chunk 2"),
    ]  # fmt: skip


def test_whole_chunks_skip_the_query_focused_excerpt(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat import context_builder

    monkeypatch.setattr(context_builder, "query_focused_excerpt", lambda text, q, **_: "excerpt")
    common = {"hits": (hit(SOURCE),), "history_messages": (), "question": QUESTION,
              "system_prompt": "s", "token_counter": FakeCounter(), "max_tokens": 1000}  # fmt: skip
    assert select_context_for_prompt(**common).items[0].text == "excerpt"
    assert select_context_for_prompt(**common, whole_chunks=True).items[0].text == SOURCE


def test_the_prompt_keeps_sources_out_of_the_system_message() -> None:
    from app.citations.registry import build_prompt_source_registry

    items = select_context_for_prompt(
        hits=(hit(SOURCE),), history_messages=(), question=QUESTION, system_prompt="s",
        token_counter=FakeCounter(), max_tokens=1000, whole_chunks=True,
    ).items  # fmt: skip
    registry: PromptSourceRegistry = build_prompt_source_registry(
        context_items=items, max_sources=5
    )
    system, user_message = build_simple_grounded_prompt(
        question=QUESTION, source_registry=registry, no_answer_sentinel="__NO_ANSWER__"
    )
    assert system.role == "system" and "2.500 kg" not in system.content
    assert "[SOURCE_1]" in system.content and "Chưa xác minh được" in system.content
    assert "SOURCE_1" in user_message.content and "2.500 kg" in user_message.content
    _, retry = build_simple_grounded_prompt(
        question=QUESTION, source_registry=registry, no_answer_sentinel="__NO_ANSWER__",
        retry_reason="it has no source marker.", previous_answer="x " * 500,
    )  # fmt: skip
    assert "Reason: it has no source marker." in retry.content
    assert len(retry.content) < len(user_message.content) + 800  # the old answer is cut


def test_a_supported_answer_with_a_valid_marker_is_answered_in_one_call() -> None:
    result, llm = _ask(GOOD)
    assert result.grounding_status == GroundingStatus.ANSWERED and llm.calls == 1
    assert "[SOURCE_1]" not in result.assistant_message.content  # renumbered by the mapper
    assert GLOBAL_METRICS.answer_branch_counts()["route_llm"] == 1


def test_a_bad_marker_is_retried_once_with_its_reason() -> None:
    result, llm = _ask("Tai trong toi da cua xe toi la 2.500 kg [SOURCE_9].", GOOD)
    assert result.grounding_status == GroundingStatus.ANSWERED and llm.calls == 2
    assert "Reason: it uses a marker that is not one of the sources" in (
        llm.message_history[1][1].content
    )
    assert GLOBAL_METRICS.answer_branch_counts()["simple_retry"] == 1


@pytest.mark.parametrize(
    ("contents", "reason", "calls"),
    [
        (("Tai trong toi da [SOURCE_9].",) * 2, "citation_invalid", 2),
        (("Tai trong toi da cua xe toi la 2.500 kg.",) * 2, "citation_missing", 2),
        (("Tai trong toi da cua xe toi la 9.900 kg [SOURCE_1].",) * 2, "claim_", 2),
        (("__NO_ANSWER__",), "llm_refused", 1),
        (("Tài liệu không đề cập tải trọng của xe tải.",), "refusal_text", 1),
    ],
)
def test_each_refusal_is_counted_with_its_reason(contents: tuple, reason: str, calls: int) -> None:
    result, llm = _ask(*contents)
    assert result.grounding_status == GroundingStatus.NO_ANSWER and llm.calls == calls
    counted = {k: v for k, v in GLOBAL_METRICS.answer_branch_counts().items() if v}
    assert any(k.startswith(f"simple_no_answer_{reason}") for k in counted), counted
    assert counted.get("simple_retry", 0) == (1 if calls == 2 else 0)


def test_no_retrieved_chunk_refuses_without_calling_the_llm() -> None:
    llm = SequentialFakeLLMProvider(_generation(GOOD))
    service, _, _, _, resolved_llm, _, _ = make_service(
        retrieval=FakeRetrievalService(retrieval_result()),
        llm=llm,
        settings_obj=settings(rag_answer_mode="simple"),
    )
    result = asyncio.run(
        service.answer_question(current_user=user(), session_id=chat_session().id, question="q?")
    )
    assert result.grounding_status == GroundingStatus.NO_ANSWER and resolved_llm.calls == 0
    assert GLOBAL_METRICS.answer_branch_counts()["simple_no_answer_no_sources"] == 1


def test_legacy_stays_the_default() -> None:
    assert settings().rag_answer_mode == "legacy"


def test_unmarked_absence_sentences_are_not_claims() -> None:
    assert _simple_claim_text("Tài liệu không đề cập mức phụ cấp.") == ""
    assert _simple_claim_text("The documents do not mention the allowance.") == ""
    assert _simple_claim_text("Chưa xác minh được từ tài liệu: mức phụ cấp.") == ""
    assert _simple_claim_text("Could not be verified from the documents: the allowance.") == ""
    partial = "Phụ cấp là 500.000 đồng [SOURCE_1]. Tài liệu không đề cập thời điểm chi trả."
    assert _simple_claim_text(partial) == "Phụ cấp là 500.000 đồng ."
    assert _simple_claim_text("Tài liệu không đề cập A.\nB là 5 ngày. [SOURCE_2]") == (
        "B là 5 ngày."
    )
    # With a marker it is a claim to check, even with a negation inside.
    assert _simple_claim_text("Công ty không cung cấp xe đưa đón [SOURCE_1].") != ""
    # A fact without a marker is still a claim (and then has no citation).
    assert _simple_claim_text("Phụ cấp là 500.000 đồng.") == "Phụ cấp là 500.000 đồng."


def test_a_partial_answer_is_validated_on_its_stated_part() -> None:
    result, llm = _ask(GOOD[:-1] + ". Tài liệu không đề cập người kiểm định xe.")
    assert result.grounding_status == GroundingStatus.ANSWERED and llm.calls == 1
    assert "không đề cập người kiểm định" in result.assistant_message.content


def test_number_normalization_applies_only_inside_its_block() -> None:
    answer, evidence = "kiem tra 1 lan moi nam", "kiem tra 01 lan/nam"
    assert validation._numbers_are_contradicted(answer, evidence)  # F is off by default
    with validation.number_normalization():
        assert not validation._numbers_are_contradicted(answer, evidence)
    assert validation._numbers_are_contradicted(answer, evidence)


def _validate_whole_chunk(text: str, answer: str, question: str) -> Any:
    from app.citations.registry import build_prompt_source_registry

    items = select_context_for_prompt(
        hits=(hit(text),), history_messages=(), question=question, system_prompt="s",
        token_counter=FakeCounter(), max_tokens=1000, whole_chunks=True,
    ).items  # fmt: skip
    registry = build_prompt_source_registry(context_items=items, max_sources=5)
    return asyncio.run(
        validation.ClaimEvidenceValidationService().validate(
            question=question, answer=answer, source_registry=registry,
            cited_source_labels=("SOURCE_1",),
        )
    ).status  # fmt: skip


CONTROLLED = (
    "So tay kho lanh. Ma kiem soat tai lieu: KL-0042. Ke tang 2 chiu toi da 640 kg. "
    "Cua kho mo luc 6 gio."
)


def test_a_document_control_line_does_not_hide_the_other_facts_of_a_whole_chunk() -> None:
    args = (CONTROLLED, "Ke tang 2 chiu toi da 640 kg.", "Ke tang 2 chiu toi da bao nhieu?")
    supported = validation.ClaimEvidenceStatus.SUPPORTED
    assert _validate_whole_chunk(*args) != supported  # legacy rule: the whole chunk is reference
    with validation.simple_validation():
        assert _validate_whole_chunk(*args) == supported
        # the control line itself is still no evidence
        assert _validate_whole_chunk(CONTROLLED, "Ma tai lieu la KL-0042.", "Ma tai lieu?") != (
            supported
        )
        # a question list stays out whole
        questions = "Cau hoi mau: Ke tang 2 chiu toi da 640 kg? Cua kho mo luc may gio?"
        assert _validate_whole_chunk(questions, "Ke tang 2 chiu toi da 640 kg.", args[2]) != (
            supported
        )


# --- s1-s3 (owner decision 2026-11-16), each behind its flag ------------------------------

S1 = {"rag_simple_absence_sentences_enabled": True}
UNVERIFIED = "Chưa xác minh được từ tài liệu bạn được phép truy cập"


def test_s1_an_unverified_part_is_never_a_claim_marked_or_not() -> None:
    q = "Muc in thay may lan va ai ky phieu?"
    shown, claims = _simple_split_absences(
        f"Muc in duoc thay 2 lan moi thang. [SOURCE_1] {UNVERIFIED}: nguoi ky phieu [SOURCE_1].",
        question=q,
    )
    # the marker after the full stop stays with its sentence; the next one starts a sentence
    assert claims == ("Muc in duoc thay 2 lan moi thang [SOURCE_1].",)
    assert shown.endswith(f"{UNVERIFIED}: nguoi ky phieu.")
    assert _simple_split_absences(f"{UNVERIFIED}: [SOURCE_1]", question=q) == (f"{UNVERIFIED}:", ())
    assert _simple_split_absences("Không xác minh được: người ký.", question=q)[1] == ()
    # a number the question does not hold may carry a fact: it stays a claim
    fact = "Không xác minh được: mức phạt là 300 nghìn [SOURCE_1]."
    assert _simple_split_absences(fact, question=q)[1] == (fact,)


def test_s1_an_answer_of_unverified_parts_only_is_no_answer_without_a_retry() -> None:
    marked = f"{UNVERIFIED}: tai trong cua xe [SOURCE_1]."
    result, llm = _ask(marked, **S1)
    assert result.grounding_status == GroundingStatus.NO_ANSWER and llm.calls == 1
    assert GLOBAL_METRICS.answer_branch_counts()["simple_no_answer_refusal_text"] == 1
    _, old = _ask(marked, marked)  # flag off: the marked sentence is a claim and is retried
    assert old.calls == 2


def test_s1_a_partial_answer_shows_the_unverified_part_without_a_citation() -> None:
    citations = StrictCitationValidation()
    llm = SequentialFakeLLMProvider(
        _generation(f"{GOOD[:-1]}. {UNVERIFIED}: nguoi kiem dinh xe [SOURCE_1].")
    )
    service, _, _, _, resolved, _, _ = make_service(
        retrieval=FakeRetrievalService(retrieval_result(hit(SOURCE))), llm=llm,
        citation_validation=citations, settings_obj=settings(rag_answer_mode="simple", **S1),
    )  # fmt: skip
    result = asyncio.run(
        service.answer_question(
            current_user=user(), session_id=chat_session().id, question=QUESTION
        )
    )
    assert result.grounding_status == GroundingStatus.ANSWERED and resolved.calls == 1
    assert citations.answers[0].count("[SOURCE_1]") == 1  # only the claim cites
    assert result.assistant_message.content.endswith(f"{UNVERIFIED}: nguoi kiem dinh xe.")


def test_s1_short_prompt_asks_for_the_marker_inside_each_sentence() -> None:
    short = build_simple_system_prompt(no_answer_sentinel="__NO__", short=True)
    assert "one short sentence for each point" in short and "without a marker" in short
    assert "2.500" not in short  # holds no source text
    assert build_simple_system_prompt(no_answer_sentinel="__NO__") != short
    _, llm = _ask(GOOD, rag_simple_short_prompt_enabled=True)
    assert "one short sentence for each point" in llm.message_history[0][0].content


PRINTER = (
    "So tay xuong in. Phieu bao hanh may in phai gui trong 05 ngay lam viec sau khi nhan may. "
    "Muc in duoc thay 2 lan moi thang."
)
PRINTER_Q = "Phieu bao hanh may in phai gui trong bao lau?"


def test_s2_relaxed_rules_accept_a_bare_value_but_still_catch_a_wrong_number() -> None:
    supported = validation.ClaimEvidenceStatus.SUPPORTED
    with validation.simple_validation():
        assert _validate_whole_chunk(PRINTER, "5 ngay lam viec.", PRINTER_Q) != supported
    with validation.simple_validation(relaxed_rules=True):
        assert _validate_whole_chunk(PRINTER, "5 ngay lam viec.", PRINTER_Q) == supported
        assert _validate_whole_chunk(PRINTER, "9 ngay lam viec.", PRINTER_Q) == (
            validation.ClaimEvidenceStatus.CONTRADICTED
        )


class _ByWordEmbeddings:
    """The query is (1, 0); a passage holding `near` is (1, 0), any other (0, 1)."""

    def __init__(self, near: str) -> None:
        self.near = near

    def embed_query(self, text: str) -> Any:
        return SimpleNamespace(values=(1.0, 0.0))

    def embed_passages(self, texts: Any) -> Any:
        return SimpleNamespace(
            vectors=[SimpleNamespace(values=(1.0, 0.0) if self.near in t else (0.0, 1.0))
                     for t in texts]
        )  # fmt: skip


S2 = {**S1, "rag_simple_relaxed_rules_enabled": True, "rag_simple_claim_relevance_enabled": True}
OFF_TOPIC = "Day cap duoc kiem tra 2 lan moi quy [SOURCE_1]."


def test_s2_a_claim_whose_source_sentence_is_off_topic_is_dropped() -> None:
    result, llm = _ask(f"{GOOD} {OFF_TOPIC}", embeddings=_ByWordEmbeddings("2.500"), **S2)
    assert result.grounding_status == GroundingStatus.ANSWERED and llm.calls == 1
    assert "Day cap" not in result.assistant_message.content
    assert "2.500 kg" in result.assistant_message.content
    assert GLOBAL_METRICS.answer_branch_counts()["simple_claim_irrelevant"] == 1


def test_s2_no_relevant_claim_left_ends_at_no_answer_without_a_retry() -> None:
    result, llm = _ask(OFF_TOPIC, GOOD, embeddings=_ByWordEmbeddings("2.500"), **S2)
    assert result.grounding_status == GroundingStatus.NO_ANSWER and llm.calls == 1
    assert GLOBAL_METRICS.answer_branch_counts()["simple_no_answer_claim_irrelevant"] == 1


def test_s2_relevance_is_skipped_when_it_cannot_be_measured() -> None:
    result, llm = _ask(GOOD, **S2)  # no embedding provider
    assert result.grounding_status == GroundingStatus.ANSWERED and llm.calls == 1


def test_s3_a_question_list_counts_by_its_non_question_segments() -> None:
    from app.retrieval.evidence_quality import EvidenceContextKind, classify_evidence_context

    faq = (
        "Phu luc cau hoi kiem thu. Muc in duoc thay may lan moi thang? "
        "Muc in duoc thay 2 lan moi thang. Ai ky phieu bao hanh?"
    )
    assert classify_evidence_context(faq) == EvidenceContextKind.QUESTION_LIST
    q, supported = "Muc in duoc thay may lan moi thang?", validation.ClaimEvidenceStatus.SUPPORTED
    with validation.simple_validation():
        assert _validate_whole_chunk(faq, "Muc in duoc thay 2 lan moi thang.", q) != supported
    with validation.simple_validation(question_list_segments=True):
        assert _validate_whole_chunk(faq, "Muc in duoc thay 2 lan moi thang.", q) == supported
        # its questions are still no evidence
        assert _validate_whole_chunk(faq, "Ai ky phieu bao hanh.", "Ai ky phieu?") != supported


def test_the_new_flags_are_off_by_default() -> None:
    s = settings()
    assert not (
        s.rag_simple_absence_sentences_enabled or s.rag_simple_short_prompt_enabled
        or s.rag_simple_relaxed_rules_enabled or s.rag_simple_claim_relevance_enabled
        or s.rag_simple_question_list_segments_enabled or s.rag_simple_subject_binding_enabled
        or s.rag_simple_claim_cross_encoder_enabled
    )  # fmt: skip


# --- s4, s5 (owner decision 2026-11-16, second round), each behind its flag -------------------

SHIFTS = (
    "Bảng phụ cấp ca.\nCa ngày 50.000 đồng\nCa đêm 80.000 đồng\nCa lễ, Tết và\n120.000 đồng\n"
    "ngày nghỉ bù"
)
NIGHT = "Phụ cấp ca đêm là bao nhiêu?"


def _bound(question: str, claim: str, evidence: str) -> bool:
    needs = tuple(dict.fromkeys((question, *information_need_queries(question))))
    return validation.value_bound_to_subject(needs=needs, claim=claim, evidence=evidence)


def test_s4_a_value_counts_only_in_the_row_that_names_the_subject() -> None:
    assert _bound(NIGHT, "Mức phụ cấp là 80.000 đồng.", SHIFTS)  # no need to restate "ca đêm"
    assert not _bound(NIGHT, "Mức phụ cấp là 50.000 đồng.", SHIFTS)
    # a row wrapped over three lines is one row
    assert _bound("Phụ cấp ca lễ là bao nhiêu?", "120.000 đồng.", SHIFTS)
    assert not _bound("Phụ cấp ca lễ là bao nhiêu?", "80.000 đồng.", SHIFTS)
    # a value the question states, and a claim with no value, are not checked
    assert _bound("Ca ngày có được 50.000 đồng không?", "Có, 50.000 đồng.", SHIFTS)
    assert _bound(NIGHT, "Có phụ cấp ca.", SHIFTS)


def test_s4_a_row_takes_the_subject_of_its_numbered_heading() -> None:
    headed = (
        "3.1 Phụ cấp ca đêm\nMỗi ca được 80.000 đồng.\n"
        "3.2 Phụ cấp ca ngày\nMỗi ca được 50.000 đồng."
    )
    assert _bound(NIGHT, "80.000 đồng.", headed)
    assert not _bound(NIGHT, "50.000 đồng.", headed)


def test_s4_each_part_of_a_two_part_question_binds_its_own_value() -> None:
    question = "Phụ cấp ca đêm là bao nhiêu và máy chủ được sao lưu mấy lần mỗi tuần?"
    evidence = f"{SHIFTS}\n\nMáy chủ được sao lưu 3 lần mỗi tuần. Ổ đĩa được thay 2 lần mỗi năm."
    assert _bound(question, "80.000 đồng.", evidence)
    assert _bound(question, "Sao lưu 3 lần mỗi tuần.", evidence)
    assert not _bound(question, "Thay 2 lần mỗi năm.", evidence)
    assert not _bound(question, "50.000 đồng.", evidence)
    # rows that all name a part's subject are bound to it, whatever the other part asks
    books = "Thời hạn mượn sách là 21 ngày. Trả sách trễ bị dừng quyền mượn trong 14 ngày."
    asked = "Sách mượn được mấy ngày và trả trễ thì dừng quyền mượn bao lâu?"
    assert _bound(asked, "21 ngày.", books)


def test_s4_conflicting_documents_are_judged_row_by_row() -> None:
    first = "Thẻ ra vào được cấp lại trong 2 ngày làm việc."
    second = (
        "Thẻ ra vào được cấp lại trong 4 ngày làm việc. "
        "Đồng phục được cấp lại trong 7 ngày làm việc."
    )
    question = "Thẻ ra vào được cấp lại trong bao lâu?"
    assert _bound(question, "4 ngày làm việc.", second)
    assert _bound(question, "2 ngày làm việc.", first)  # which document wins is not this check
    assert not _bound(question, "7 ngày làm việc.", second)
    assert not _bound(question, "7 ngày làm việc.", f"{first}\n\n{second}")


S4 = {**S2, "rag_simple_question_list_segments_enabled": True,
      "rag_simple_subject_binding_enabled": True}  # fmt: skip


def test_s4_drops_a_value_of_another_row_and_none_left_is_no_answer() -> None:
    right, wrong = "Ca đêm được 80.000 đồng [SOURCE_1].", "Ca lễ được 50.000 đồng [SOURCE_1]."
    result, llm = _ask(f"{right} {wrong}", hits=(hit(SHIFTS),), question=NIGHT, **S4)
    assert result.grounding_status == GroundingStatus.ANSWERED and llm.calls == 1
    assert "80.000" in result.assistant_message.content
    assert "50.000" not in result.assistant_message.content
    assert GLOBAL_METRICS.answer_branch_counts()["simple_claim_unbound"] == 1
    result, llm = _ask(wrong, right, hits=(hit(SHIFTS),), question=NIGHT, **S4)
    assert result.grounding_status == GroundingStatus.NO_ANSWER and llm.calls == 1
    assert GLOBAL_METRICS.answer_branch_counts()["simple_no_answer_claim_unbound"] == 1


class _FakeCrossEncoder:
    """Scores 3.0 a passage holding `near`, -3.0 any other; None when `broken`."""

    def __init__(self, near: str, broken: bool = False) -> None:
        self.near, self.broken, self.pairs = near, broken, []

    async def score_pairs(self, pairs: Any) -> Any:
        self.pairs += list(pairs)
        return None if self.broken else tuple(3.0 if self.near in p else -3.0 for _, p in pairs)


S5 = {**S4, "rag_simple_claim_cross_encoder_enabled": True,
      "rag_simple_claim_cross_encoder_min_score": 0.0}  # fmt: skip


def test_s5_the_cross_encoder_replaces_e5_for_relevance(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.grounded_answer_service as gas

    scorer = _FakeCrossEncoder("2.500")
    monkeypatch.setattr(gas, "create_claim_relevance_cross_encoder", lambda settings: scorer)
    # e5 here would drop GOOD (nothing near "xyz"); the cross-encoder keeps it
    result, llm = _ask(f"{GOOD} {OFF_TOPIC}", embeddings=_ByWordEmbeddings("xyz"), **S5)
    assert result.grounding_status == GroundingStatus.ANSWERED and llm.calls == 1
    assert "2.500 kg" in result.assistant_message.content
    assert "Day cap" not in result.assistant_message.content
    assert scorer.pairs[0][0] == QUESTION and "2.500" in scorer.pairs[0][1]
    assert GLOBAL_METRICS.answer_branch_counts()["simple_claim_irrelevant"] == 1


def test_s5_a_claim_the_model_cannot_score_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.grounded_answer_service as gas

    monkeypatch.setattr(
        gas, "create_claim_relevance_cross_encoder", lambda s: _FakeCrossEncoder("", broken=True)
    )
    result, _ = _ask(GOOD, **S5)
    assert result.grounding_status == GroundingStatus.ANSWERED


def test_cross_encoder_scores_pairs_and_reports_failure_as_none() -> None:
    from app.retrieval.reranker import SentenceTransformerCrossEncoderReranker

    class Model:
        def __init__(self, fail: bool) -> None:
            self.fail = fail

        def predict(self, pairs: Any, **kwargs: Any) -> list[float]:
            if self.fail:
                raise RuntimeError("boom")
            return [float(len(passage)) for _, passage in pairs]

    def scorer(fail: bool) -> SentenceTransformerCrossEncoderReranker:
        return SentenceTransformerCrossEncoderReranker(
            model_name="m", model_revision="", device="cpu", batch_size=2, max_length=64,
            timeout_seconds=5, local_files_only=True, cache_folder="x",
            model_loader=lambda name, **kwargs: Model(fail),
        )  # fmt: skip

    assert asyncio.run(scorer(False).score_pairs([("q", "ab"), ("q", "abc")])) == (2.0, 3.0)
    assert asyncio.run(scorer(True).score_pairs([("q", "ab")])) is None
    assert asyncio.run(scorer(False).score_pairs([])) is None
