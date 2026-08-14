from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from app.chat.models import SelectedContext, SelectedContextItem
from app.citations.models import PromptSource
from app.document_processing.tokenization.base import TokenCounter
from app.models import CitationSourceType
from app.retrieval.models import HybridRetrievalHit
from app.retrieval.question_analysis import QuestionAnalysis, analyze_question
from app.retrieval.structured import selected_structural_line_indexes
from app.web_search.models import WebSearchResult

CONTEXT_START = "<retrieved_context>"
CONTEXT_END = "</retrieved_context>"

_QUERY_TERM_PATTERN = re.compile(r"\w+", re.UNICODE)
_ACRONYM_PATTERN = re.compile(r"\b[A-Z][A-Z0-9&/+.-]{1,}\b")
_NUMBER_UNIT_PATTERN = re.compile(r"(?<!\d)(\d+)\s*(?:\([^)]{1,80}\)\s*)?([^\W\d_]+)", re.UNICODE)
_EXCERPT_MAX_CHARACTERS = 1400
_EXCERPT_BEFORE_CHARACTERS = 350
_EXCERPT_AFTER_CHARACTERS = 900
_MIN_QUERY_TERM_CHARACTERS = 3
_MAX_QUERY_NEEDLES = 32
_QUANTITY_STOP_TERMS = frozenset({"bao", "nhieu", "how", "many", "cua", "duoc"})
_MULTI_VALUE_QUESTION_CUES = ("moi", "tat ca", "deu", "all", "every")
_CHANGE_QUESTION_CUES = (
    "thay doi",
    "change",
)
_CHANGE_EVIDENCE_CUES = (
    "tang",
    "them",
    "giam",
    "bot",
    "dieu chinh",
    "increase",
    "additional",
    "extra",
    "decrease",
    "reduce",
    "adjust",
)


def render_context_item(ordinal: int, text: str) -> str:
    return f"--- CONTEXT ITEM {ordinal} START ---\n{text}\n--- CONTEXT ITEM {ordinal} END ---"


def render_context(items: Sequence[SelectedContextItem]) -> str:
    if not items:
        return f"{CONTEXT_START}\n{CONTEXT_END}"
    rendered_items = "\n\n".join(render_context_item(item.ordinal, item.text) for item in items)
    return f"{CONTEXT_START}\n{rendered_items}\n{CONTEXT_END}"


def render_source_context(sources: Sequence[PromptSource]) -> str:
    if not sources:
        return f"{CONTEXT_START}\n{CONTEXT_END}"
    rendered_items = "\n\n".join(render_source_context_item(source) for source in sources)
    return f"{CONTEXT_START}\n{rendered_items}\n{CONTEXT_END}"


def render_source_context_item(source: PromptSource) -> str:
    if source.source_type == CitationSourceType.WEB:
        domain_line = _web_domain_line(source.source_url)
        return (
            f"--- {source.label} START ---\n"
            "Source type: WEB\n"
            f"Web source title: {source.document_title}\n"
            f"{domain_line}"
            "Content:\n"
            f"{source.text}\n"
            f"--- {source.label} END ---"
        )
    return (
        f"--- {source.label} START ---\n"
        f"Document title: {source.document_title}\n"
        f"Page: {source.start_page}\n"
        "Content:\n"
        f"{source.text}\n"
        f"--- {source.label} END ---"
    )


def render_hit_source_context_item(
    ordinal: int,
    hit: HybridRetrievalHit,
    *,
    source_text: str | None = None,
) -> str:
    label = f"SOURCE_{ordinal}"
    content = hit.text if source_text is None else source_text
    return (
        f"--- {label} START ---\n"
        f"Document title: {hit.document_title}\n"
        f"Page: {hit.start_page}\n"
        "Content:\n"
        f"{content}\n"
        f"--- {label} END ---"
    )


def render_web_result_source_context_item(ordinal: int, result: WebSearchResult) -> str:
    label = f"SOURCE_{ordinal}"
    return (
        f"--- {label} START ---\n"
        "Source type: WEB\n"
        f"Web source title: {result.title}\n"
        f"Web source domain: {result.domain}\n"
        "Content:\n"
        f"{result.content}\n"
        f"--- {label} END ---"
    )


def select_context_for_prompt(
    *,
    hits: Sequence[HybridRetrievalHit],
    history_messages: Sequence[object],
    web_results: Sequence[WebSearchResult] = (),
    conversation_history: str | None = None,
    question: str,
    system_prompt: str,
    token_counter: TokenCounter,
    max_tokens: int,
) -> SelectedContext:
    if max_tokens <= 0:
        raise ValueError("max_tokens must be greater than zero.")
    selected: list[SelectedContextItem] = []
    base_text = _base_budget_text(
        system_prompt=system_prompt,
        history_messages=history_messages,
        conversation_history=conversation_history,
        question=question,
    )
    used_tokens = token_counter.count(base_text) + token_counter.count(render_source_context(()))
    for hit in hits:
        source_text = query_focused_excerpt(hit.text, question)
        candidate_text = render_hit_source_context_item(
            len(selected) + 1,
            hit,
            source_text=source_text,
        )
        candidate_tokens = token_counter.count(candidate_text)
        if used_tokens + candidate_tokens > max_tokens:
            continue
        selected.append(
            SelectedContextItem(
                ordinal=len(selected) + 1,
                text=source_text,
                token_count=candidate_tokens,
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                document_title=hit.document_title,
                source_type=CitationSourceType.INTERNAL,
                page_numbers=hit.page_numbers,
                start_page=hit.start_page,
                end_page=hit.end_page,
                semantic_score=hit.semantic_score,
                keyword_score=hit.keyword_score,
                hybrid_score=hit.hybrid_score,
                reranker_score=hit.reranker_score,
            )
        )
        used_tokens += candidate_tokens
    for result in web_results:
        candidate_text = render_web_result_source_context_item(len(selected) + 1, result)
        candidate_tokens = token_counter.count(candidate_text)
        if used_tokens + candidate_tokens > max_tokens:
            continue
        selected.append(
            SelectedContextItem(
                ordinal=len(selected) + 1,
                text=result.content,
                token_count=candidate_tokens,
                document_title=result.title,
                source_type=CitationSourceType.WEB,
                source_url=result.url,
                page_numbers=(1,),
                start_page=1,
                end_page=1,
                semantic_score=None,
                keyword_score=None,
                hybrid_score=result.score or 0.0,
            )
        )
        used_tokens += candidate_tokens
    return SelectedContext(
        items=tuple(selected),
        selected_chunk_count=len(selected),
        estimated_token_count=used_tokens,
    )


def query_focused_excerpt(text: str, question: str) -> str:
    normalized_text = _collapse_whitespace(text)
    analysis = analyze_question(question)
    folded_text = _fold_text(normalized_text)
    number_unit_count = len(tuple(_NUMBER_UNIT_PATTERN.finditer(folded_text)))
    quantity_focus = _is_quantity_question(question) and number_unit_count >= 3
    multi_value_focus = _is_multi_value_question(question) and number_unit_count >= 2
    change_focus = _is_change_question(question) and number_unit_count >= 2
    person_focus = _is_person_acronym_question(question) and _has_multiple_acronym_records(
        normalized_text
    )
    if (
        len(normalized_text) <= _EXCERPT_MAX_CHARACTERS
        and not quantity_focus
        and not multi_value_focus
        and not change_focus
        and not person_focus
        and not analysis.asks_for_explicit_value
        and not analysis.asks_for_person
        and not analysis.is_yes_no
        and not analysis.asks_for_policy_condition
    ):
        return normalized_text

    phrases, terms, numbers = _query_needles(question)
    if person_focus:
        person_excerpt = _person_acronym_excerpt(normalized_text, question)
        if person_excerpt:
            return person_excerpt
    if not multi_value_focus and (
        analysis.asks_for_explicit_value
        or analysis.asks_for_person
        or analysis.is_yes_no
        or analysis.asks_for_policy_condition
    ):
        structured_excerpt = _structured_query_excerpt(
            normalized_text,
            question=question,
            analysis=analysis,
        )
        if structured_excerpt:
            return structured_excerpt
    if multi_value_focus:
        positions = _multi_value_focus_positions(
            folded_text,
            phrases=phrases,
            terms=terms,
            numbers=numbers,
        )
    elif quantity_focus or change_focus:
        positions = _quantity_focus_positions(
            folded_text,
            question=question,
            phrases=phrases,
            terms=terms,
        )
    else:
        phrase_positions = _needle_positions(folded_text, phrases)
        number_positions = _needle_positions(folded_text, numbers)
        term_positions = _needle_positions(folded_text, terms)
        positions = phrase_positions + tuple(
            position for position in number_positions if position not in phrase_positions
        )
        if not positions:
            positions = term_positions
    if not positions:
        return normalized_text[:_EXCERPT_MAX_CHARACTERS].strip()

    if multi_value_focus:
        before_characters = 0
        after_characters = 640
        max_characters = 1000
    elif quantity_focus:
        before_characters = 80
        after_characters = 180
        max_characters = 500
    elif change_focus:
        before_characters = 120
        after_characters = 320
        max_characters = 800
    else:
        before_characters = _EXCERPT_BEFORE_CHARACTERS
        after_characters = _EXCERPT_AFTER_CHARACTERS
        max_characters = _EXCERPT_MAX_CHARACTERS
    windows: list[tuple[int, int]] = []
    for position in positions[:3]:
        start = max(0, position - before_characters)
        end = min(len(normalized_text), position + after_characters)
        windows.append((start, end))

    merged: list[tuple[int, int]] = []
    for start, end in sorted(windows):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))

    parts: list[str] = []
    remaining = max_characters
    for start, end in merged:
        if remaining <= 0:
            break
        part = normalized_text[start:end].strip()
        if len(part) > remaining:
            part = part[:remaining].strip()
        if part:
            parts.append(part)
            remaining -= len(part)
    excerpt = "\n".join(parts) or normalized_text[:_EXCERPT_MAX_CHARACTERS].strip()
    if multi_value_focus:
        return _format_multi_value_excerpt(excerpt)
    return excerpt


def _structured_query_excerpt(
    text: str,
    *,
    question: str,
    analysis: QuestionAnalysis,
) -> str:
    indexes = selected_structural_line_indexes(text, question, analysis)
    if not indexes:
        return ""
    lines = tuple(line.strip() for line in text.splitlines() if line.strip())
    selected = [lines[index] for index in indexes if 0 <= index < len(lines)]
    excerpt = "\n".join(dict.fromkeys(selected)).strip()
    if not excerpt:
        return ""
    excerpt = f"Answer-focused evidence:\n{excerpt}"
    if len(excerpt) <= _EXCERPT_MAX_CHARACTERS:
        return excerpt
    return excerpt[:_EXCERPT_MAX_CHARACTERS].strip()


def _format_multi_value_excerpt(text: str) -> str:
    separated = re.sub(
        r"(?<!^)(?<!\n)(?<!\d)(\d+\s*(?:\([^)]{1,80}\)\s*)?[^\W\d_]+)",
        r"\n\1",
        text,
    ).strip()
    lines = [line.strip() for line in separated.splitlines() if line.strip()]
    formatted: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if _is_standalone_number_unit_line(line) and index + 1 < len(lines):
            suffix = lines[index + 1]
            prefix = ""
            if formatted and not _line_starts_with_number_unit(formatted[-1]):
                prefix = formatted.pop()
            if prefix and not _line_starts_with_number_unit(suffix):
                formatted.append(f"{line} {prefix} {suffix}".strip())
                index += 2
                continue
            if not _line_starts_with_number_unit(suffix):
                formatted.append(f"{line} {suffix}".strip())
                index += 2
                continue
            if prefix:
                formatted.append(prefix)
        formatted.append(line)
        index += 1
    return "\n".join(_bullet_multi_value_line(line) for line in formatted)


def _bullet_multi_value_line(text: str) -> str:
    if _line_starts_with_number_unit(text):
        return f"- {text}"
    return text


def _is_standalone_number_unit_line(text: str) -> bool:
    return _NUMBER_UNIT_PATTERN.fullmatch(_fold_text(text)) is not None


def _line_starts_with_number_unit(text: str) -> bool:
    return _NUMBER_UNIT_PATTERN.match(_fold_text(text)) is not None


def _query_needles(question: str) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    terms = tuple(
        dict.fromkeys(
            term.strip("_")
            for term in _QUERY_TERM_PATTERN.findall(_fold_text(question))
            if _is_query_term(term.strip("_"))
        )
    )[:_MAX_QUERY_NEEDLES]
    numbers = tuple(term for term in terms if term.isdecimal())
    non_numeric_terms = tuple(term for term in terms if not term.isdecimal())
    phrases: list[str] = []
    for size in (4, 3, 2):
        if len(non_numeric_terms) < size:
            continue
        for index in range(len(non_numeric_terms) - size + 1):
            phrase = " ".join(non_numeric_terms[index : index + size])
            if len(phrase) >= 8:
                phrases.append(phrase)
    return tuple(dict.fromkeys(phrases)), non_numeric_terms, numbers


def _is_quantity_question(question: str) -> bool:
    folded_question = _fold_text(question)
    return "bao nhieu" in folded_question or "how many" in folded_question


def _is_multi_value_question(question: str) -> bool:
    folded_question = _fold_text(question)
    return any(cue in folded_question for cue in _MULTI_VALUE_QUESTION_CUES)


def _is_person_acronym_question(question: str) -> bool:
    folded_question = _fold_text(question).strip()
    return bool(_ACRONYM_PATTERN.search(question)) and (
        " la ai" in folded_question
        or folded_question.endswith(" ai")
        or " who " in f" {folded_question} "
        or " dung khong" in folded_question
        or " phai khong" in folded_question
        or folded_question.startswith("co phai")
        or folded_question.endswith(" khong")
        or folded_question.endswith(" khong?")
    )


def _has_multiple_acronym_records(text: str) -> bool:
    return len(tuple(_ACRONYM_PATTERN.finditer(text))) >= 2


def _person_acronym_excerpt(text: str, question: str) -> str:
    acronyms = tuple(dict.fromkeys(_ACRONYM_PATTERN.findall(question)))
    if not acronyms:
        return ""
    lines = text.splitlines()
    folded_lines = tuple(_fold_text(line) for line in lines)
    selected_line_indexes: list[int] = []
    for acronym in acronyms:
        folded_acronym = _fold_text(acronym)
        for index, line in enumerate(folded_lines):
            if not _contains_folded_token(line, folded_acronym):
                continue
            for selected_index in range(max(0, index - 1), min(len(lines), index + 5)):
                if selected_index not in selected_line_indexes:
                    selected_line_indexes.append(selected_index)
    parts = [lines[index].strip() for index in selected_line_indexes if lines[index].strip()]
    excerpt = _format_person_record_excerpt(parts)
    return excerpt[:600].strip()


def _format_person_record_excerpt(lines: Sequence[str]) -> str:
    formatted: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if " - " in line and index + 1 < len(lines):
            role_line = lines[index + 1].strip()
            if _ACRONYM_PATTERN.search(role_line):
                name, description = line.split(" - ", 1)
                continuation: list[str] = []
                next_index = index + 2
                while next_index < len(lines) and len(continuation) < 1:
                    continuation_line = lines[next_index].strip()
                    if " - " in continuation_line or _ACRONYM_PATTERN.search(continuation_line):
                        break
                    continuation.append(continuation_line)
                    next_index += 1
                full_description = " ".join((description.strip(), *continuation)).strip()
                formatted.append(f"{name.strip()} - {role_line} - {full_description}".strip(" -"))
                index = next_index
                continue
        formatted.append(line)
        index += 1
    return "\n".join(formatted)


def _contains_folded_token(text: str, token: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(token)}(?!\w)", text) is not None


def _multi_value_focus_positions(
    text: str,
    *,
    phrases: tuple[str, ...],
    terms: tuple[str, ...],
    numbers: tuple[str, ...],
) -> tuple[int, ...]:
    spans = _number_unit_spans(text)
    if not spans:
        return ()
    question_units = {unit for _, unit, _, _ in spans if unit in terms}
    if question_units:
        spans = tuple(span for span in spans if span[1] in question_units)
    if not spans:
        return ()
    focused_terms = tuple(
        term for term in terms if term not in _QUANTITY_STOP_TERMS and term not in question_units
    )
    candidate_spans = tuple(
        (index, span) for index, span in enumerate(spans) if not numbers or span[0] in numbers
    )
    if not candidate_spans:
        candidate_spans = tuple(enumerate(spans))
    scored = tuple(
        (
            index,
            start,
            _quantity_span_score(
                text,
                start=start,
                end=end,
                phrases=phrases,
                terms=focused_terms,
            )
            + (40 if number in numbers else 0),
        )
        for index, (number, _, start, end) in candidate_spans
    )
    best_score = max(score for _, _, score in scored)
    best_positions = tuple((index, start) for index, start, score in scored if score == best_score)
    anchor_index, anchor_start = min(best_positions, key=lambda row: row[1])
    if numbers:
        cluster_indexes = {
            index
            for index, (_, _, start, _) in enumerate(spans)
            if index >= anchor_index and (start - anchor_start <= 420 or index - anchor_index <= 3)
        }
    else:
        cluster_indexes = {
            index
            for index, (_, _, start, _) in enumerate(spans)
            if abs(start - anchor_start) <= 320 or abs(index - anchor_index) <= 2
        }
    cluster_positions = tuple(
        start for index, (_, _, start, _) in enumerate(spans) if index in cluster_indexes
    )
    return tuple(sorted(cluster_positions, key=lambda start: (abs(start - anchor_start), start)))


def _quantity_focus_positions(
    text: str,
    *,
    question: str,
    phrases: tuple[str, ...],
    terms: tuple[str, ...],
) -> tuple[int, ...]:
    spans = _number_unit_spans(text)
    if not spans:
        return ()
    question_units = {unit for _, unit, _, _ in spans if unit in terms}
    if question_units:
        spans = tuple(span for span in spans if span[1] in question_units)
    if not spans:
        return ()

    question_is_change = _is_change_question(question)
    focused_terms = tuple(
        term for term in terms if term not in _QUANTITY_STOP_TERMS and term not in question_units
    )
    scored = tuple(
        (
            start,
            _quantity_span_score(
                text,
                start=start,
                end=end,
                phrases=phrases,
                terms=focused_terms,
            ),
            _quantity_span_has_change_evidence(text, start=start, end=end),
        )
        for _, _, start, end in spans
    )
    if question_is_change and any(has_change for _, _, has_change in scored):
        scored = tuple(row for row in scored if row[2])
    if not question_is_change and any(not has_change for _, _, has_change in scored):
        scored = tuple(row for row in scored if not row[2])
    best_score = max(score for _, score, _ in scored)
    return tuple(start for start, score, _ in scored if score == best_score)


def _number_unit_spans(text: str) -> tuple[tuple[str, str, int, int], ...]:
    spans: list[tuple[str, str, int, int]] = []
    for match in _NUMBER_UNIT_PATTERN.finditer(text):
        unit = match.group(2).strip("_ ")
        if len(unit) >= 2:
            spans.append((str(int(match.group(1))), unit, match.start(), match.end()))
    return tuple(spans)


def _quantity_span_score(
    text: str,
    *,
    start: int,
    end: int,
    phrases: tuple[str, ...],
    terms: tuple[str, ...],
) -> int:
    window = text[max(0, start - 80) : min(len(text), end + 140)]
    score = sum(1 for term in terms if term in window)
    score += sum(3 for phrase in phrases if phrase in window)
    return score


def _quantity_span_has_change_evidence(text: str, *, start: int, end: int) -> bool:
    window = text[max(0, start - 80) : min(len(text), end + 140)]
    return any(cue in window for cue in _CHANGE_EVIDENCE_CUES)


def _is_change_question(question: str) -> bool:
    folded_question = _fold_text(question)
    return any(cue in folded_question for cue in _CHANGE_QUESTION_CUES)


def _fold_text(text: str) -> str:
    normalized = unicodedata.normalize(
        "NFKD",
        text.casefold().replace("\u0111", "d").replace("\u0110", "d"),
    )
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _is_query_term(term: str) -> bool:
    return bool(term) and (term.isdecimal() or len(term) >= _MIN_QUERY_TERM_CHARACTERS)


def _needle_positions(text: str, needles: tuple[str, ...]) -> tuple[int, ...]:
    positions: list[int] = []
    for needle in needles:
        position = text.find(needle)
        if position >= 0:
            positions.append(position)
    return tuple(dict.fromkeys(sorted(positions)))


def _collapse_whitespace(text: str) -> str:
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _base_budget_text(
    *,
    system_prompt: str,
    history_messages: Sequence[object],
    conversation_history: str | None,
    question: str,
) -> str:
    rendered_history = conversation_history
    if rendered_history is None:
        history_text = "\n".join(
            f"{getattr(message, 'role', '')}: {getattr(message, 'content', '')}"
            for message in history_messages
        )
        rendered_history = f"<conversation_history>\n{history_text}\n</conversation_history>"
    return (
        f"{system_prompt}\n{rendered_history}\n<current_question>\n{question}\n</current_question>"
    )


def _web_domain_line(source_url: str | None) -> str:
    if not source_url:
        return ""
    try:
        from app.web_search.content import normalize_web_url

        domain = normalize_web_url(source_url, return_hostname=True)
    except ValueError:
        return ""
    return f"Web source domain: {domain}\n"
