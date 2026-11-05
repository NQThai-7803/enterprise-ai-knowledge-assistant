from __future__ import annotations

from app.core.config import Settings
from app.retrieval.reranker import (
    RERANKER_MODE_CROSS_ENCODER,
    RERANKER_MODE_DISABLED,
    RERANKER_MODE_LEXICAL_FALLBACK,
    HeuristicRetrievalReranker,
    RetrievalReranker,
    SentenceTransformerCrossEncoderReranker,
    log_reranker_fallback_active,
)

_RERANKER_CACHE: dict[tuple[object, ...], RetrievalReranker] = {}


def create_retrieval_reranker(settings: Settings) -> RetrievalReranker:
    cache_key = (
        settings.reranker_provider,
        settings.reranker_model,
        settings.reranker_model_revision,
        settings.reranker_device,
        settings.reranker_batch_size,
        settings.reranker_max_length,
        settings.reranker_timeout_seconds,
        settings.reranker_local_files_only,
        settings.reranker_model_cache_path,
    )
    cached = _RERANKER_CACHE.get(cache_key)
    if cached is not None:
        return cached
    fallback = HeuristicRetrievalReranker()
    if settings.reranker_provider == "heuristic":
        reranker: RetrievalReranker = fallback
    else:
        reranker = SentenceTransformerCrossEncoderReranker(
            model_name=settings.reranker_model,
            model_revision=settings.reranker_model_revision,
            device=settings.reranker_device,
            batch_size=settings.reranker_batch_size,
            max_length=settings.reranker_max_length,
            timeout_seconds=settings.reranker_timeout_seconds,
            local_files_only=settings.reranker_local_files_only,
            cache_folder=settings.reranker_model_cache_path,
            fallback=fallback,
        )
    _RERANKER_CACHE[cache_key] = reranker
    return reranker


def resolve_reranker_mode(settings: Settings) -> str:
    """Report what ranks candidates now: cross_encoder, lexical_fallback or disabled."""
    if not settings.reranker_enabled:
        return RERANKER_MODE_DISABLED
    return getattr(create_retrieval_reranker(settings), "mode", RERANKER_MODE_CROSS_ENCODER)


def log_reranker_startup_status(settings: Settings) -> str:
    mode = resolve_reranker_mode(settings)
    if mode == RERANKER_MODE_LEXICAL_FALLBACK:
        log_reranker_fallback_active(context="startup")
    return mode
