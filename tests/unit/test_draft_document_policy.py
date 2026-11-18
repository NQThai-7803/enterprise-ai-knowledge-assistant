"""DEC-033: RAG_DRAFT_DOCUMENT_POLICY, compiled to SQL (no database)."""

from __future__ import annotations

from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.models import DocumentLifecycleStatus
from app.retrieval import authority


def _sql(expression) -> str:
    return str(
        expression.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


def test_off_means_no_filter_and_exclude_is_the_default(monkeypatch) -> None:
    assert Settings.model_fields["rag_draft_document_policy"].default == "exclude"  # DEC-036
    monkeypatch.setattr(
        authority, "get_settings", lambda: Settings(rag_draft_document_policy="off")
    )
    assert _sql(authority.answer_document_filter()) == "true"


def test_exclude_filters_draft_documents(monkeypatch) -> None:
    monkeypatch.setattr(
        authority, "get_settings", lambda: Settings(rag_draft_document_policy="exclude")
    )
    assert _sql(authority.answer_document_filter()) == "documents.lifecycle_status != 'DRAFT'"


def test_a_draft_ranks_like_an_active_document() -> None:
    sql = _sql(authority.current_authority_order_expression())
    assert "lifecycle_status IN ('ACTIVE', 'DRAFT')" in sql
    assert DocumentLifecycleStatus.DRAFT.value == "DRAFT"
