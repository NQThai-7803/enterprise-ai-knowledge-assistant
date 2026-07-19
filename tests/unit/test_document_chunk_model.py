from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.db.base import Base
from app.models import Document, DocumentChunk


def _check_constraint_sql(table: object) -> list[str]:
    return [
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    ]


def _unique_constraint_column_sets(table: object) -> set[tuple[str, ...]]:
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_document_chunk_table_registered() -> None:
    assert DocumentChunk.__tablename__ == "document_chunks"
    assert "document_chunks" in Base.metadata.tables
    assert hasattr(Document, "chunks")


def test_document_chunk_embedding_dimension() -> None:
    assert "VECTOR(384)" in str(DocumentChunk.__table__.c.embedding.type)


def test_document_chunk_document_index_unique_constraint() -> None:
    assert ("document_id", "chunk_index") in _unique_constraint_column_sets(DocumentChunk.__table__)


def test_document_chunk_token_count_constraint() -> None:
    constraints = _check_constraint_sql(DocumentChunk.__table__)

    assert any("token_count" in constraint and "> 0" in constraint for constraint in constraints)


def test_document_chunk_character_count_constraint() -> None:
    constraints = _check_constraint_sql(DocumentChunk.__table__)

    assert any(
        "character_count" in constraint and "> 0" in constraint for constraint in constraints
    )


def test_document_chunk_page_constraint() -> None:
    constraints = _check_constraint_sql(DocumentChunk.__table__)

    assert any("start_page" in constraint and "> 0" in constraint for constraint in constraints)
    assert any(
        "end_page" in constraint and "start_page" in constraint for constraint in constraints
    )
    assert any(
        "cardinality" in constraint and "page_numbers" in constraint for constraint in constraints
    )


def test_document_chunk_overlap_constraint() -> None:
    constraints = _check_constraint_sql(DocumentChunk.__table__)

    assert any(
        "overlap_token_count" in constraint and ">= 0" in constraint for constraint in constraints
    )


def test_document_chunk_checksum_constraint() -> None:
    constraints = _check_constraint_sql(DocumentChunk.__table__)

    assert any("content_sha256" in constraint and "64" in constraint for constraint in constraints)


def test_document_chunk_foreign_key_cascades() -> None:
    constraints = [
        constraint
        for constraint in DocumentChunk.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert any(constraint.ondelete == "CASCADE" for constraint in constraints)


def test_document_chunk_hnsw_index_declared() -> None:
    index = next(
        idx
        for idx in DocumentChunk.__table__.indexes
        if idx.name == "ix_document_chunks_embedding_hnsw_cosine"
    )

    assert index.dialect_options["postgresql"]["using"] == "hnsw"
    assert index.dialect_options["postgresql"]["ops"] == {"embedding": "vector_cosine_ops"}
