from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from numbers import Real

from app.retrieval.errors import RetrievalError, RetrievalFailureCode
from app.retrieval.models import HybridRetrievalHit, KeywordRetrievalHit, RetrievalHit


@dataclass(frozen=True, slots=True)
class FusedRetrievalResult:
    hits: tuple[HybridRetrievalHit, ...]
    fused_candidate_count: int


def fuse_retrieval_hits(
    *,
    semantic_hits: Sequence[RetrievalHit],
    keyword_hits: Sequence[KeywordRetrievalHit],
    top_k: int,
    rrf_k: int,
    semantic_weight: float,
    keyword_weight: float,
) -> FusedRetrievalResult:
    _validate_fusion_configuration(
        top_k=top_k,
        rrf_k=rrf_k,
        semantic_weight=semantic_weight,
        keyword_weight=keyword_weight,
    )
    semantic_ranked = _first_ranked_semantic_hits(semantic_hits)
    keyword_ranked = _first_ranked_keyword_hits(keyword_hits)
    chunk_ids = sorted(
        set(semantic_ranked) | set(keyword_ranked),
        key=lambda chunk_id: chunk_id.hex,
    )

    fused_hits = tuple(
        _fuse_chunk(
            chunk_id=chunk_id,
            semantic_ranked=semantic_ranked,
            keyword_ranked=keyword_ranked,
            rrf_k=rrf_k,
            semantic_weight=float(semantic_weight),
            keyword_weight=float(keyword_weight),
        )
        for chunk_id in chunk_ids
    )
    ordered_hits = tuple(sorted(fused_hits, key=_hybrid_sort_key))
    return FusedRetrievalResult(
        hits=ordered_hits[:top_k],
        fused_candidate_count=len(ordered_hits),
    )


def _validate_fusion_configuration(
    *,
    top_k: int,
    rrf_k: int,
    semantic_weight: float,
    keyword_weight: float,
) -> None:
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise RetrievalError(RetrievalFailureCode.INVALID_HYBRID_CONFIGURATION)
    if isinstance(rrf_k, bool) or not isinstance(rrf_k, int) or rrf_k < 1:
        raise RetrievalError(RetrievalFailureCode.INVALID_HYBRID_CONFIGURATION)
    semantic = _coerce_weight(semantic_weight)
    keyword = _coerce_weight(keyword_weight)
    if semantic == 0.0 and keyword == 0.0:
        raise RetrievalError(RetrievalFailureCode.INVALID_HYBRID_CONFIGURATION)


def _coerce_weight(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise RetrievalError(RetrievalFailureCode.INVALID_HYBRID_CONFIGURATION)
    numeric_value = float(value)
    if not isfinite(numeric_value) or numeric_value < 0.0:
        raise RetrievalError(RetrievalFailureCode.INVALID_HYBRID_CONFIGURATION)
    return numeric_value


def _first_ranked_semantic_hits(
    hits: Sequence[RetrievalHit],
) -> dict[object, tuple[int, RetrievalHit]]:
    ranked: dict[object, tuple[int, RetrievalHit]] = {}
    for index, hit in enumerate(hits, start=1):
        ranked.setdefault(hit.chunk_id, (index, hit))
    return ranked


def _first_ranked_keyword_hits(
    hits: Sequence[KeywordRetrievalHit],
) -> dict[object, tuple[int, KeywordRetrievalHit]]:
    ranked: dict[object, tuple[int, KeywordRetrievalHit]] = {}
    for index, hit in enumerate(hits, start=1):
        ranked.setdefault(hit.chunk_id, (index, hit))
    return ranked


def _fuse_chunk(
    *,
    chunk_id: object,
    semantic_ranked: dict[object, tuple[int, RetrievalHit]],
    keyword_ranked: dict[object, tuple[int, KeywordRetrievalHit]],
    rrf_k: int,
    semantic_weight: float,
    keyword_weight: float,
) -> HybridRetrievalHit:
    semantic_entry = semantic_ranked.get(chunk_id)
    keyword_entry = keyword_ranked.get(chunk_id)
    semantic_rank = semantic_entry[0] if semantic_entry is not None else None
    keyword_rank = keyword_entry[0] if keyword_entry is not None else None
    semantic_hit = semantic_entry[1] if semantic_entry is not None else None
    keyword_hit = keyword_entry[1] if keyword_entry is not None else None
    source_hit = semantic_hit or keyword_hit
    if source_hit is None:  # pragma: no cover - defensive guard for impossible state.
        raise RetrievalError(RetrievalFailureCode.HYBRID_RETRIEVAL_FAILED)
    if semantic_hit is not None and keyword_hit is not None:
        _validate_same_chunk_metadata(semantic_hit, keyword_hit)

    hybrid_score = 0.0
    if semantic_rank is not None:
        hybrid_score += semantic_weight / (rrf_k + semantic_rank)
    if keyword_rank is not None:
        hybrid_score += keyword_weight / (rrf_k + keyword_rank)

    matched_by = tuple(
        channel
        for channel, rank in (("semantic", semantic_rank), ("keyword", keyword_rank))
        if rank is not None
    )
    return HybridRetrievalHit(
        chunk_id=source_hit.chunk_id,
        document_id=source_hit.document_id,
        document_title=source_hit.document_title,
        chunk_index=source_hit.chunk_index,
        text=source_hit.text,
        page_numbers=source_hit.page_numbers,
        start_page=source_hit.start_page,
        end_page=source_hit.end_page,
        token_count=source_hit.token_count,
        hybrid_score=hybrid_score,
        semantic_score=semantic_hit.relevance_score if semantic_hit is not None else None,
        semantic_rank=semantic_rank,
        keyword_score=keyword_hit.keyword_rank if keyword_hit is not None else None,
        keyword_rank=keyword_rank,
        matched_by=matched_by,
    )


def _validate_same_chunk_metadata(
    semantic_hit: RetrievalHit,
    keyword_hit: KeywordRetrievalHit,
) -> None:
    if (
        semantic_hit.document_id != keyword_hit.document_id
        or semantic_hit.document_title != keyword_hit.document_title
        or semantic_hit.chunk_index != keyword_hit.chunk_index
        or semantic_hit.text != keyword_hit.text
        or semantic_hit.page_numbers != keyword_hit.page_numbers
        or semantic_hit.start_page != keyword_hit.start_page
        or semantic_hit.end_page != keyword_hit.end_page
        or semantic_hit.token_count != keyword_hit.token_count
    ):
        raise RetrievalError(RetrievalFailureCode.HYBRID_RETRIEVAL_FAILED)


def _hybrid_sort_key(hit: HybridRetrievalHit) -> tuple[float, int, int, int, str, int, str]:
    null_rank = 2**31 - 1
    return (
        -hit.hybrid_score,
        -len(hit.matched_by),
        hit.semantic_rank if hit.semantic_rank is not None else null_rank,
        hit.keyword_rank if hit.keyword_rank is not None else null_rank,
        hit.document_id.hex,
        hit.chunk_index,
        hit.chunk_id.hex,
    )
