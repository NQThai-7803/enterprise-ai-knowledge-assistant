from __future__ import annotations

from app.core.config import Settings
from app.db.session import async_session_factory
from app.embeddings.factory import create_embedding_provider
from app.retrieval.base import HybridRetrievalService, KeywordRetrievalService, RetrievalService
from app.retrieval.hybrid_service import HybridRetrievalService as SemanticKeywordHybridService
from app.retrieval.keyword_service import KeywordRetrievalService as PostgresKeywordRetrievalService
from app.retrieval.semantic_service import SemanticRetrievalService


def create_semantic_retrieval_service(settings: Settings) -> RetrievalService:
    return SemanticRetrievalService(
        settings=settings,
        embedding_provider=create_embedding_provider(settings),
        session_provider=async_session_factory,
    )


def create_keyword_retrieval_service(settings: Settings) -> KeywordRetrievalService:
    return PostgresKeywordRetrievalService(
        settings=settings,
        session_provider=async_session_factory,
    )


def create_hybrid_retrieval_service(settings: Settings) -> HybridRetrievalService:
    return SemanticKeywordHybridService(
        settings=settings,
        semantic_retrieval_service=create_semantic_retrieval_service(settings),
        keyword_retrieval_service=create_keyword_retrieval_service(settings),
    )
