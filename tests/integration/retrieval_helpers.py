from __future__ import annotations

import asyncio
import hashlib
import math
import uuid
from collections.abc import Coroutine, Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.models import EmbeddingVector
from app.models import (
    Department,
    Document,
    DocumentAccessScope,
    DocumentChunk,
    DocumentPermission,
    DocumentPermissionLevel,
    DocumentStatus,
    User,
    UserRole,
)
from app.retrieval.semantic_repository import RetrievalRow, search_permitted_chunks

QUERY_VECTOR = tuple([1.0] + [0.0] * 383)


def run_async(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def stable_uuid(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"enterprise-ai-retrieval:{name}")


def checksum(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def similarity_vector(similarity: float, *, axis: int = 1) -> list[float]:
    values = [0.0] * 384
    values[0] = similarity
    if similarity < 1.0:
        values[axis] = math.sqrt(max(0.0, 1.0 - similarity * similarity))
    return values


async def create_department(session: AsyncSession, key: str) -> Department:
    department = Department(
        id=stable_uuid(f"department:{key}"),
        name=f"Department {key}",
        code=f"D{stable_uuid(f'department-code:{key}').hex[:8]}",
    )
    session.add(department)
    await session.commit()
    await session.refresh(department)
    return department


async def create_user(
    session: AsyncSession,
    key: str,
    *,
    role: UserRole = UserRole.STAFF,
    department_id: uuid.UUID | None = None,
    is_active: bool = True,
) -> User:
    user = User(
        id=stable_uuid(f"user:{key}"),
        email=f"{key}@retrieval.example.com",
        full_name=f"Retrieval User {key}",
        hashed_password="not-used",
        role=role,
        department_id=department_id,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_document(
    session: AsyncSession,
    key: str,
    *,
    uploader: User,
    title: str | None = None,
    access_scope: DocumentAccessScope = DocumentAccessScope.PRIVATE,
    department_id: uuid.UUID | None = None,
    status: DocumentStatus = DocumentStatus.READY,
    is_deleted: bool = False,
) -> Document:
    resolved_title = title or f"Document {key}"
    document = Document(
        id=stable_uuid(f"document:{key}"),
        title=resolved_title,
        description=f"Description {key}",
        original_filename=f"{key}.pdf",
        storage_key=f"documents/2026/07/{stable_uuid(f'storage:{key}')}.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum_sha256=checksum(f"document:{key}"),
        status=status,
        access_scope=access_scope,
        department_id=department_id,
        uploaded_by=uploader.id,
        is_deleted=is_deleted,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def create_chunk(
    session: AsyncSession,
    key: str,
    *,
    document: Document,
    chunk_index: int = 0,
    text: str | None = None,
    similarity: float = 1.0,
    axis: int = 1,
    page_numbers: Sequence[int] = (1,),
) -> DocumentChunk:
    resolved_text = text or f"Chunk text {key}"
    pages = tuple(page_numbers)
    chunk = DocumentChunk(
        id=stable_uuid(f"chunk:{key}"),
        document_id=document.id,
        chunk_index=chunk_index,
        text=resolved_text,
        token_count=max(1, len(resolved_text.split())),
        character_count=len(resolved_text),
        page_numbers=list(pages),
        start_page=min(pages),
        end_page=max(pages),
        overlap_token_count=0,
        content_sha256=checksum(resolved_text),
        embedding=similarity_vector(similarity, axis=axis),
        embedding_provider="sentence_transformers",
        embedding_model="fake-model",
        embedding_dimensions=384,
    )
    session.add(chunk)
    await session.commit()
    await session.refresh(chunk)
    return chunk


async def create_permission(
    session: AsyncSession,
    key: str,
    *,
    document: Document,
    creator: User,
    user_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    permission: DocumentPermissionLevel = DocumentPermissionLevel.VIEW,
) -> DocumentPermission:
    grant = DocumentPermission(
        id=stable_uuid(f"grant:{key}"),
        document_id=document.id,
        user_id=user_id,
        department_id=department_id,
        permission=permission,
        created_by=creator.id,
    )
    session.add(grant)
    await session.commit()
    await session.refresh(grant)
    return grant


async def disable_postgres_jit(session: AsyncSession) -> None:
    await session.execute(text("SET LOCAL jit = off"))


async def search_rows(
    session: AsyncSession,
    *,
    user: User,
    top_k: int = 20,
    threshold: float = 0.0,
) -> tuple[RetrievalRow, ...]:
    await disable_postgres_jit(session)
    return await search_permitted_chunks(
        session,
        query_vector=QUERY_VECTOR,
        current_user=user,
        top_k=top_k,
        min_relevance_score=threshold,
    )


class JitOffSessionContext:
    def __init__(self, session_context) -> None:  # noqa: ANN001
        self.session_context = session_context

    async def __aenter__(self):  # noqa: ANN201
        self.session = await self.session_context.__aenter__()
        await disable_postgres_jit(self.session)
        return self.session

    async def __aexit__(self, exc_type, exc, traceback) -> None:  # noqa: ANN001
        await self.session_context.__aexit__(exc_type, exc, traceback)


class JitOffSessionProvider:
    def __init__(self, session_factory) -> None:  # noqa: ANN001
        self.session_factory = session_factory

    def __call__(self) -> JitOffSessionContext:
        return JitOffSessionContext(self.session_factory())


class FakeQueryEmbeddingProvider:
    @property
    def dimensions(self) -> int:
        return 384

    @property
    def model_name(self) -> str:
        return "fake-model"

    def embed_query(self, text: str) -> EmbeddingVector:
        return EmbeddingVector(
            values=QUERY_VECTOR,
            dimensions=384,
            normalized=True,
            model_name="fake-model",
        )

    def embed_passages(
        self, texts: Sequence[str]
    ):  # pragma: no cover - retrieval must not call it.
        raise AssertionError("retrieval must not call embed_passages")


def row_document_ids(rows: Sequence[RetrievalRow]) -> list[uuid.UUID]:
    return [row.document_id for row in rows]


def row_chunk_ids(rows: Sequence[RetrievalRow]) -> list[uuid.UUID]:
    return [row.chunk_id for row in rows]


def assert_marker_absent(
    rows: Sequence[RetrievalRow], marker: str, captured_logs: str = ""
) -> None:
    assert marker not in captured_logs
    assert all(marker not in row.text for row in rows)
    assert all(marker not in row.document_title for row in rows)
    assert all(marker not in repr(row) for row in rows)
