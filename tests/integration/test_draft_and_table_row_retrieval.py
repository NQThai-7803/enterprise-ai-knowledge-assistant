"""DEC-033 (DRAFT documents under RAG_DRAFT_DOCUMENT_POLICY) and DEC-034 (TABLE_ROW chunks) on a
real PostgreSQL: semantic and keyword retrieval, the group of a row, and the chunk write."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.models import DocumentChunk, DocumentLifecycleStatus, UserRole
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.retrieval import authority
from app.retrieval.keyword_repository import search_permitted_chunks_by_keyword
from app.services.document_embedding_service import build_document_chunk_rows
from tests.integration.retrieval_helpers import (
    create_chunk,
    create_document,
    create_user,
    disable_postgres_jit,
    row_document_ids,
    run_async,
    search_rows,
)

pytestmark = pytest.mark.integration


def _policy(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    settings = get_settings().model_copy(update={"rag_draft_document_policy": value})
    monkeypatch.setattr(authority, "get_settings", lambda: settings)


async def _keyword(session: AsyncSession, user, query: str):
    await disable_postgres_jit(session)
    return await search_permitted_chunks_by_keyword(
        session, query=query, current_user=user, top_k=20, min_keyword_rank=0.0
    )


@pytest.mark.parametrize("policy", ["off", "exclude"])
def test_a_draft_document_is_answer_evidence_only_when_the_policy_is_off(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    policy: str,
) -> None:
    _policy(monkeypatch, policy)

    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, f"draft-{policy}-admin", role=UserRole.ADMIN)
            issued = await create_document(session, f"draft-{policy}-issued", uploader=admin)
            draft = await create_document(session, f"draft-{policy}-draft", uploader=admin)
            draft.lifecycle_status = DocumentLifecycleStatus.DRAFT
            await session.commit()
            for document in (issued, draft):
                await create_chunk(
                    session,
                    f"{document.id}-chunk",
                    document=document,
                    text="Marriage leave is three paid days.",
                )

            semantic = set(row_document_ids(await search_rows(session, user=admin)))
            keyword = set(row_document_ids(await _keyword(session, admin, "marriage leave")))

            expected = {issued.id, draft.id} if policy == "off" else {issued.id}
            assert semantic == expected
            assert keyword == expected

    run_async(scenario())


def test_a_row_chunk_matches_its_cells_not_the_labels_and_groups_with_its_parent(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "rows-admin", role=UserRole.ADMIN)
            document = await create_document(session, "rows-doc", uploader=admin)
            parent = await create_chunk(
                session,
                "rows-parent",
                document=document,
                text="Benefits table. Plan Limit Condition. Inpatient 150 million probation.",
            )
            row = await create_chunk(
                session,
                "rows-row",
                document=document,
                chunk_index=1,
                text="Benefits table | Plan: Inpatient; Limit: 150 million; Condition: probation",
                chunk_kind="TABLE_ROW",
                parent_chunk_id=parent.id,
                search_text="Inpatient; 150 million; probation",
            )

            by_label = {r.chunk_id for r in await _keyword(session, admin, "Condition")}
            by_cell = {r.chunk_id: r for r in await _keyword(session, admin, "Inpatient")}
            semantic = {r.chunk_id: r for r in await search_rows(session, user=admin)}

            assert by_label == {parent.id}  # the label is indexed once, in the text chunk
            assert set(by_cell) == {parent.id, row.id}
            assert by_cell[row.id].group_id == parent.id
            assert by_cell[parent.id].group_id == parent.id
            assert semantic[row.id].group_id == parent.id

    run_async(scenario())


def test_the_chunk_write_links_a_row_to_its_parent(
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
) -> None:
    from app.document_processing.chunking.models import TextChunk
    from app.embeddings.models import EmbeddingVector

    def chunk(index: int, text: str, **extra) -> TextChunk:
        import hashlib

        return TextChunk(
            chunk_index=index,
            text=text,
            token_count=3,
            character_count=len(text),
            page_numbers=(1,),
            start_page=1,
            end_page=1,
            overlap_token_count=0,
            content_sha256=hashlib.sha256(text.encode()).hexdigest(),
            **extra,
        )

    vector = EmbeddingVector(
        values=tuple([1.0] + [0.0] * 383), dimensions=384, normalized=True, model_name="fake"
    )

    async def scenario() -> None:
        async with async_session_factory_for_tests() as session:
            admin = await create_user(session, "rows-write-admin", role=UserRole.ADMIN)
            document = await create_document(session, "rows-write-doc", uploader=admin)
            chunks = (
                chunk(0, "Table text"),
                chunk(
                    1,
                    "T | A: 1; B: 2; C: 3",
                    kind="TABLE_ROW",
                    search_text="1; 2; 3",
                    parent_index=0,
                ),  # fmt: skip
            )
            await DocumentChunkRepository(session).replace_for_document(
                document_id=document.id, chunks=build_document_chunk_rows(chunks, [vector] * 2)
            )
            await session.commit()
            stored = (
                await session.scalars(
                    select(DocumentChunk)
                    .where(DocumentChunk.document_id == document.id)
                    .order_by(DocumentChunk.chunk_index)
                )
            ).all()
            assert [c.chunk_kind for c in stored] == ["TEXT", "TABLE_ROW"]
            assert stored[1].parent_chunk_id == stored[0].id
            assert (stored[0].search_text, stored[1].search_text) == (None, "1; 2; 3")

    run_async(scenario())
