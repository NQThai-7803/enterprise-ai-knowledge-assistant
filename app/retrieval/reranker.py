from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import replace
from math import isfinite
from numbers import Real
from typing import Any, Protocol, runtime_checkable

import anyio

from app.retrieval.models import HybridRetrievalHit
from app.retrieval.question_analysis import (
    QuestionAnalysis,
    analyze_question,
    fold_text,
    question_terms,
)
from app.retrieval.structured import (
    has_explicit_not_specified,
    has_value_expression,
    structured_retrieval_text,
    value_units_for_analysis,
)

logger = logging.getLogger(__name__)

_ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9&/+.-]{1,}\b")
_NAME_TOKEN_RE = re.compile(r"\b[^\W\d_][\w'-]*\b", re.UNICODE)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_PERCENT_RE = re.compile(r"(?<!\d)\d+(?:[.,]\d+)?\s*%")
_TIME_RANGE_RE = re.compile(
    r"(?<!\d)(?:[01]?\d|2[0-3])(?:[:h][0-5]\d)?\s*(?:-|\u2013|\u2014|den|to)\s*"
    r"(?:[01]?\d|2[0-3])(?:[:h][0-5]\d)?",
    re.IGNORECASE,
)
_STRICT_TIME_RANGE_RE = re.compile(
    r"(?<!\d)(?:[01]?\d|2[0-3])[:h][0-5]\d\s*(?:-|den|to)\s*"
    r"(?:[01]?\d|2[0-3])[:h][0-5]\d",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"\b(?:ngay\s+)?\d{1,2}(?:/\d{1,2}(?:/\d{2,4})?)?\b")
_CLOCK_RE = re.compile(r"(?<!\d)(?:[01]?\d|2[0-3])(?:[:h][0-5]\d)(?!\d)")
_NUMBER_UNIT_RE = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(?:\([^)]{1,80}\)\s*)?([^\W\d_/%]+|%|vnd|\u0111|\u20ab)",
    re.UNICODE,
)

_QUERY_STOP_TERMS = frozenset(
    {
        "bao",
        "nhieu",
        "duoc",
        "cua",
        "theo",
        "chinh",
        "sach",
        "nhan",
        "vien",
        "nguoi",
        "what",
        "which",
        "when",
        "how",
        "many",
        "much",
        "moi",
        "toi",
        "da",
        "vao",
        "muc",
        "nao",
        "ngay",
        "gio",
        "does",
        "with",
        "from",
        "the",
    }
)

_POLARITY_CUES = (
    "khong",
    "khong duoc",
    "khong phai",
    "khong can",
    "khong tu dong",
    "duoc phep",
    "phai",
    "bat buoc",
    "yeu cau",
    "must",
    "must not",
    "required",
    "not required",
    "allowed",
    "not allowed",
    "automatically",
)

_ROLE_WORDS = frozenset(
    {
        "ceo",
        "cto",
        "cfo",
        "coo",
        "cio",
        "manager",
        "director",
        "lead",
        "owner",
        "approver",
        "giam doc",
        "truong phong",
        "nguoi phe duyet",
    }
)


_NON_PERSON_NAME_TOKENS = frozenset(
    {
        "ai",
        "admin",
        "an",
        "attt",
        "ban",
        "bao",
        "business",
        "cao",
        "cap",
        "che",
        "chief",
        "company",
        "compliance",
        "cong",
        "contract",
        "customer",
        "data",
        "digital",
        "director",
        "dong",
        "du",
        "giam",
        "hang",
        "ho",
        "hoi",
        "hop",
        "kien",
        "khach",
        "kiem",
        "khoi",
        "legal",
        "lieu",
        "mat",
        "nghe",
        "noi",
        "office",
        "officer",
        "operations",
        "phap",
        "phong",
        "pmo",
        "privacy",
        "product",
        "quyen",
        "rieng",
        "security",
        "service",
        "soc",
        "technology",
        "thong",
        "tin",
        "toan",
        "truc",
        "uy",
        "van",
    }
)
_ORGANIZATION_NAME_TOKENS = frozenset(
    {
        "an",
        "attt",
        "bao",
        "cao",
        "cap",
        "che",
        "compliance",
        "contract",
        "customer",
        "data",
        "dong",
        "du",
        "hang",
        "hoi",
        "hop",
        "kien",
        "khach",
        "kiem",
        "legal",
        "lieu",
        "mat",
        "phap",
        "pmo",
        "privacy",
        "product",
        "quyen",
        "rieng",
        "security",
        "service",
        "soc",
        "thong",
        "tin",
        "toan",
        "truc",
        "uy",
    }
)
_ORGANIZATION_NAME_START_TOKENS = frozenset(
    {"ban", "bo", "hoi", "khoi", "phong", "trung", "uy", "van"}
)


@runtime_checkable
class RetrievalReranker(Protocol):
    async def rerank(
        self,
        *,
        query: str,
        hits: Sequence[HybridRetrievalHit],
        top_k: int,
    ) -> tuple[HybridRetrievalHit, ...]: ...


class HeuristicRetrievalReranker:
    async def rerank(
        self,
        *,
        query: str,
        hits: Sequence[HybridRetrievalHit],
        top_k: int,
    ) -> tuple[HybridRetrievalHit, ...]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        return _rank_with_alignment(query=query, hits=tuple(hits), top_k=top_k)


class SentenceTransformerCrossEncoderReranker:
    def __init__(
        self,
        *,
        model_name: str,
        model_revision: str,
        device: str,
        batch_size: int,
        max_length: int,
        timeout_seconds: float,
        local_files_only: bool,
        cache_folder: str,
        model_loader: Any | None = None,
        fallback: RetrievalReranker | None = None,
    ) -> None:
        if not model_name.strip():
            msg = "model_name must not be empty."
            raise ValueError(msg)
        if not device.strip():
            msg = "device must not be empty."
            raise ValueError(msg)
        if batch_size <= 0:
            msg = "batch_size must be greater than zero."
            raise ValueError(msg)
        if max_length <= 0:
            msg = "max_length must be greater than zero."
            raise ValueError(msg)
        if timeout_seconds <= 0:
            msg = "timeout_seconds must be greater than zero."
            raise ValueError(msg)
        if not cache_folder.strip():
            msg = "cache_folder must not be empty."
            raise ValueError(msg)
        self._model_name = model_name
        self._model_revision = model_revision
        self._device = device
        self._batch_size = batch_size
        self._max_length = max_length
        self._timeout_seconds = timeout_seconds
        self._local_files_only = local_files_only
        self._cache_folder = cache_folder
        self._model_loader = model_loader
        self._model: Any | None = None
        self._model_load_failed = False
        self._fallback = fallback or HeuristicRetrievalReranker()

    async def rerank(
        self,
        *,
        query: str,
        hits: Sequence[HybridRetrievalHit],
        top_k: int,
    ) -> tuple[HybridRetrievalHit, ...]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        hit_tuple = tuple(hits)
        if not hit_tuple:
            return ()
        if self._model_load_failed:
            return await self._fallback.rerank(query=query, hits=hit_tuple, top_k=top_k)
        try:
            with anyio.fail_after(self._timeout_seconds):
                model_scores = await anyio.to_thread.run_sync(
                    self._predict_scores,
                    query,
                    hit_tuple,
                    abandon_on_cancel=True,
                )
        except Exception as exc:
            self._model_load_failed = True
            logger.warning(
                "Retrieval reranker unavailable; falling back to alignment reranking.",
                extra={
                    "provider": "sentence_transformers",
                    "model": self._model_name,
                    "error_type": exc.__class__.__name__,
                },
            )
            return await self._fallback.rerank(query=query, hits=hit_tuple, top_k=top_k)

        alignment_ranked = _scored_hits(query=query, hits=hit_tuple)
        alignment_scores_by_chunk = {
            hit.chunk_id: alignment_score for hit, alignment_score in alignment_ranked
        }
        normalized_model_scores = _normalize_scores(model_scores)
        scored = []
        for index, hit in enumerate(hit_tuple):
            model_score = normalized_model_scores[index]
            alignment_score = alignment_scores_by_chunk.get(hit.chunk_id, 0.0)
            combined = model_score + alignment_score
            scored.append((index, replace(hit, reranker_score=combined), combined))
        return tuple(
            hit
            for index, hit, _ in sorted(
                scored,
                key=lambda row: (-row[2], -row[1].hybrid_score, row[0]),
            )[:top_k]
        )

    def _predict_scores(
        self,
        query: str,
        hits: tuple[HybridRetrievalHit, ...],
    ) -> tuple[float, ...]:
        model = self._get_model()
        pairs = [
            [query, _rerank_passage_text(hit, max_characters=self._max_length * 6)] for hit in hits
        ]
        raw_scores = model.predict(  # noqa: B028 - external API accepts this shape.
            pairs,
            batch_size=self._batch_size,
            show_progress_bar=False,
        )
        if hasattr(raw_scores, "tolist"):
            raw_scores = raw_scores.tolist()
        scores = tuple(_coerce_score(score) for score in raw_scores)
        if len(scores) != len(hits):
            msg = "reranker returned an unexpected score count."
            raise ValueError(msg)
        return scores

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        loader = self._model_loader
        if loader is None:
            from sentence_transformers import CrossEncoder

            loader = CrossEncoder
        kwargs = {
            "device": self._device,
            "max_length": self._max_length,
            "trust_remote_code": False,
        }
        if self._model_revision:
            kwargs["revision"] = self._model_revision
        if self._cache_folder:
            kwargs["cache_folder"] = self._cache_folder
        if self._local_files_only:
            kwargs["automodel_args"] = {"local_files_only": True}
            kwargs["tokenizer_args"] = {"local_files_only": True}
            kwargs["config_args"] = {"local_files_only": True}
        try:
            self._model = loader(self._model_name, **kwargs)
        except TypeError:
            compatible_kwargs = {
                key: value
                for key, value in kwargs.items()
                if key
                not in {
                    "trust_remote_code",
                    "revision",
                    "cache_folder",
                    "automodel_args",
                    "tokenizer_args",
                    "config_args",
                }
            }
            self._model = loader(self._model_name, **compatible_kwargs)
        return self._model


def _rank_with_alignment(
    *,
    query: str,
    hits: tuple[HybridRetrievalHit, ...],
    top_k: int,
) -> tuple[HybridRetrievalHit, ...]:
    scored = _scored_hits(query=query, hits=hits)
    return tuple(
        replace(hit, reranker_score=score)
        for hit, score in sorted(
            scored,
            key=lambda row: (
                -row[1],
                -row[0].hybrid_score,
                row[0].chunk_index,
                row[0].chunk_id.hex,
            ),
        )[:top_k]
    )


def _scored_hits(
    *,
    query: str,
    hits: tuple[HybridRetrievalHit, ...],
) -> tuple[tuple[HybridRetrievalHit, float], ...]:
    analysis = analyze_question(query)
    terms = tuple(term for term in question_terms(query) if term not in _QUERY_STOP_TERMS)
    phrases = _query_phrases(terms)
    role_terms = _role_terms(query, terms)
    return tuple(
        (
            hit,
            _alignment_score(
                hit,
                analysis=analysis,
                terms=terms,
                phrases=phrases,
                role_terms=role_terms,
            ),
        )
        for hit in hits
    )


def _alignment_score(
    hit: HybridRetrievalHit,
    *,
    analysis: QuestionAnalysis,
    terms: tuple[str, ...],
    phrases: tuple[str, ...],
    role_terms: tuple[str, ...],
) -> float:
    passage = _rerank_passage_text(hit)
    folded = fold_text(passage)
    score = hit.hybrid_score * 20.0

    for phrase in phrases:
        if phrase in folded:
            score += 18.0 + len(phrase.split()) * 3.0
    matched_terms = tuple(term for term in terms if term in folded)
    score += len(matched_terms) * 5.0
    score += sum(8.0 for term in matched_terms if len(term) >= 8)
    score += _important_term_coverage_score(folded, terms)

    if role_terms:
        exact_role_matches = tuple(term for term in role_terms if term in folded)
        score += len(exact_role_matches) * 45.0
        if _has_role_person_association(hit.text, role_terms):
            score += 120.0
        elif analysis.asks_for_person and _has_person_name_sequence(hit.text):
            score += 40.0
        if not exact_role_matches:
            score -= 45.0

    if analysis.asks_for_explicit_value:
        if has_value_expression(passage):
            score += 45.0
        score += _value_alignment_score(
            folded,
            analysis=analysis,
            terms=terms,
        )
        if has_explicit_not_specified(passage):
            score += 160.0

    if analysis.answer_type == "YEAR" and _YEAR_RE.search(folded):
        score += 140.0
    if analysis.answer_type == "DATE":
        if _DATE_RE.search(folded):
            score += 80.0
        if "tra luong" in folded or "ngay tra luong" in folded or "payroll" in folded:
            score += 180.0
        elif any(term in terms for term in ("luong", "salary", "payroll")):
            score -= 140.0
    if analysis.asks_for_count and any(
        unit in folded for unit in (" nhan su", " nhan vien", " nguoi", " employee", " people")
    ):
        score += 95.0
    if analysis.asks_for_percentage:
        if _PERCENT_RE.search(folded):
            score += 180.0
        elif not has_explicit_not_specified(passage):
            score -= 180.0
    if analysis.asks_for_time_range:
        has_time_value = (
            _STRICT_TIME_RANGE_RE.search(folded) is not None or _CLOCK_RE.search(folded) is not None
        )
        if has_time_value:
            score += 220.0
        else:
            score -= 260.0
        if "gio cot loi" in folded or "core hour" in folded:
            score += 120.0
        elif "gia tri cot loi" in folded:
            score -= 260.0
    if analysis.answer_type == "TIME" and _CLOCK_RE.search(folded):
        score += 120.0
    score += _numeric_query_alignment_score(folded, terms)
    if analysis.answer_type == "YES_NO":
        if any(cue in folded for cue in _POLARITY_CUES):
            score += 75.0
        else:
            score -= 90.0
        if "tu dong" in folded or "automatically" in folded:
            score += 40.0
        if "khong tu dong" in folded or "not automatically" in folded:
            score += 140.0

    if _looks_like_question_appendix_without_answer(folded):
        score -= 220.0

    return max(score, 0.0)


def _important_term_coverage_score(folded: str, terms: tuple[str, ...]) -> float:
    important_terms = tuple(
        term
        for term in terms
        if len(term) >= 4
        and term
        not in {
            "nova",
            "digital",
            "nhan",
            "vien",
            "duoc",
            "bao",
            "nhieu",
            "ngay",
            "tuan",
            "thang",
            "nam",
            "gio",
        }
    )
    if not important_terms:
        return 0.0
    matched_count = sum(1 for term in important_terms if term in folded)
    if matched_count == 0:
        return -90.0
    score = matched_count * 35.0
    if matched_count == len(important_terms):
        score += 80.0
    return score


def _numeric_query_alignment_score(folded: str, terms: tuple[str, ...]) -> float:
    numbers = tuple(term for term in terms if term.isdecimal())
    if not numbers:
        return 0.0
    score = 0.0
    for number in numbers:
        if re.search(rf"\b0*{re.escape(number)}\s*(?:gio|ngay|tuan|thang|nam|%)", folded):
            score += 110.0
        elif re.search(rf"\b0*{re.escape(number)}\b", folded):
            score += 20.0
        else:
            score -= 120.0
    return score


def _looks_like_question_appendix_without_answer(folded: str) -> bool:
    if not any(cue in folded for cue in ("cau hoi goi y", "kiem thu rag", "sample question")):
        return False
    if has_explicit_not_specified(folded):
        return False
    return not (_PERCENT_RE.search(folded) or _TIME_RANGE_RE.search(folded))


def _value_alignment_score(
    folded: str,
    *,
    analysis: QuestionAnalysis,
    terms: tuple[str, ...],
) -> float:
    units = value_units_for_analysis(analysis)
    number_unit_matches = tuple(_NUMBER_UNIT_RE.finditer(folded))
    if not number_unit_matches:
        return 0.0
    score = 0.0
    for match in number_unit_matches:
        unit = match.group(2).strip("_ ")
        window = folded[max(0, match.start() - 140) : min(len(folded), match.end() + 180)]
        if any(term in window for term in terms):
            score += 45.0
        if any(unit == expected or expected in window for expected in units):
            score += 40.0
    return score


def _role_terms(query: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    acronyms = tuple(dict.fromkeys(fold_text(match) for match in _ACRONYM_RE.findall(query)))
    roles = tuple(term for term in terms if term in _ROLE_WORDS)
    return tuple(dict.fromkeys((*acronyms, *roles)))


def _has_role_person_association(text: str, role_terms: tuple[str, ...]) -> bool:
    folded = fold_text(text)
    for role in role_terms:
        start = 0
        while True:
            position = folded.find(role, start)
            if position < 0:
                break
            window_start = max(0, position - 240)
            window_end = min(len(text), position + 240)
            if _has_person_name_sequence(text[window_start:window_end]):
                return True
            start = position + len(role)
    return False


def _has_person_name_sequence(text: str) -> bool:
    current: list[str] = []
    for match in _NAME_TOKEN_RE.finditer(text):
        token = match.group(0)
        if _is_name_token_candidate(token):
            current.append(token)
            if _looks_like_person_name_sequence(current):
                return True
            continue
        current = []
    return False


def _is_name_token_candidate(token: str) -> bool:
    return len(token) >= 2 and token[:1].isupper() and not token.isupper()


def _looks_like_person_name_sequence(tokens: Sequence[str]) -> bool:
    if len(tokens) < 2:
        return False
    folded_tokens = tuple(fold_text(token).strip("_ ") for token in tokens)
    if any(token in _NON_PERSON_NAME_TOKENS for token in folded_tokens):
        return False
    if folded_tokens and folded_tokens[0] in _ORGANIZATION_NAME_START_TOKENS:
        return False
    organization_token_count = sum(
        1 for token in folded_tokens if token in _ORGANIZATION_NAME_TOKENS
    )
    return organization_token_count < 2


def _query_phrases(terms: tuple[str, ...]) -> tuple[str, ...]:
    phrases: list[str] = []
    for size in (4, 3, 2):
        if len(terms) < size:
            continue
        for index in range(len(terms) - size + 1):
            phrase = " ".join(terms[index : index + size])
            if len(phrase) >= 8:
                phrases.append(phrase)
    return tuple(dict.fromkeys(phrases))


def _rerank_passage_text(hit: HybridRetrievalHit, *, max_characters: int = 2400) -> str:
    text = structured_retrieval_text(f"{hit.document_title}\n{hit.text}")
    return text[:max_characters]


def _normalize_scores(scores: tuple[float, ...]) -> tuple[float, ...]:
    if not scores:
        return ()
    if len(scores) == 1:
        return (50.0,)
    minimum = min(scores)
    maximum = max(scores)
    if maximum == minimum:
        return tuple(50.0 for _ in scores)
    return tuple(((score - minimum) / (maximum - minimum)) * 100.0 for score in scores)


def _coerce_score(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        msg = "reranker score must be a finite number."
        raise ValueError(msg)
    score = float(value)
    if not isfinite(score):
        msg = "reranker score must be finite."
        raise ValueError(msg)
    return score
