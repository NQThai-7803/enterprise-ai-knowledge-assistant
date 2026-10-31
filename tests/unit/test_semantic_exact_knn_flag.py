"""RAG_SEMANTIC_EXACT_PERMITTED_KNN_ENABLED: default, env name and wiring into the repository."""

from __future__ import annotations

import pytest
from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.models import User, UserRole
from app.retrieval.semantic_repository import (
    SemanticRetrievalRepository,
    _exact_permitted_knn_statement,
)
from app.retrieval.semantic_service import SemanticRetrievalService


class _NoEmbedding:
    dimensions = 384
    model_name = "unused"


def _service(settings: Settings) -> SemanticRetrievalService:
    return SemanticRetrievalService(
        settings=settings, embedding_provider=_NoEmbedding(), session_provider=lambda: None
    )


def test_flag_defaults_to_exact_knn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAG_SEMANTIC_EXACT_PERMITTED_KNN_ENABLED", raising=False)
    settings = Settings(_env_file=None)

    assert settings.rag_semantic_exact_permitted_knn_enabled is True
    assert _service(settings).repository.exact_permitted_knn is True
    assert SemanticRetrievalRepository().exact_permitted_knn is True


def test_flag_can_be_turned_off_for_rollback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_SEMANTIC_EXACT_PERMITTED_KNN_ENABLED", "false")
    settings = Settings(_env_file=None)

    assert settings.rag_semantic_exact_permitted_knn_enabled is False
    assert _service(settings).repository.exact_permitted_knn is False


def test_injected_repository_is_kept() -> None:
    repository = SemanticRetrievalRepository()
    service = SemanticRetrievalService(
        settings=Settings(_env_file=None, rag_semantic_exact_permitted_knn_enabled=False),
        embedding_provider=_NoEmbedding(),
        session_provider=lambda: None,
        repository=repository,
    )

    assert service.repository is repository


def test_exact_statement_fences_the_permission_subquery() -> None:
    user = User(role=UserRole.ADMIN)
    statement = _exact_permitted_knn_statement(
        vector=[0.0] * 384, current_user=user, top_k=5, max_cosine_distance=1.0
    )
    sql = str(statement.compile(dialect=postgresql.dialect()))

    inner, outer = sql.split(") AS permitted_chunks", 1)
    assert "OFFSET" in inner
    assert "ORDER BY" not in inner
    assert "ORDER BY permitted_chunks.cosine_distance ASC" in outer
    assert "LIMIT" in outer
