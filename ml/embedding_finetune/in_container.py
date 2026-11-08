"""Runs INSIDE the API container of an eval stack (copied there by common.run_in_container).

usage: python in_container.py chunks            < {"account": "admin.uat@example.test"}
       python in_container.py retrieve          < {"account": ..., "queries": [...], "top_k": 20}

`chunks` prints every chunk of every READY document the account may read: id, document code,
chunk index, pages and text. `retrieve` runs the app's own hybrid retrieval (semantic + keyword +
fusion, with the account's permission filter) and prints the ranked chunk ids per query. Reads
only; writes nothing to the database.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enums import DocumentStatus
from app.repositories.user_repository import get_by_email
from app.retrieval.factory import create_hybrid_retrieval_service


async def _user(email: str):
    async with async_session_factory() as session:
        user = await get_by_email(session, email)
    if user is None:
        raise SystemExit(f"no account {email}")
    return user


async def chunks(payload: dict) -> list[dict]:
    await _user(payload["account"])  # the account must exist; admin reads every document
    async with async_session_factory() as session:
        rows = await session.execute(
            select(DocumentChunk, Document.document_code)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.status == DocumentStatus.READY)
            .order_by(Document.document_code, DocumentChunk.chunk_index)
        )
        return [
            {
                "chunk_id": str(chunk.id),
                "document_code": code,
                "chunk_index": chunk.chunk_index,
                "page_numbers": list(chunk.page_numbers or []),
                "text": chunk.text,
            }
            for chunk, code in rows.all()
        ]


async def retrieve(payload: dict) -> list[dict]:
    user = await _user(payload["account"])
    service = create_hybrid_retrieval_service(get_settings())
    out = []
    for query in payload["queries"]:
        result = await service.retrieve(query=query, current_user=user, top_k=payload["top_k"])
        out.append({"query": query, "chunk_ids": [str(hit.chunk_id) for hit in result.hits]})
    return out


def main() -> None:
    logging.disable(logging.CRITICAL)  # stdout carries only the JSON result
    command = sys.argv[1]
    payload = json.loads(sys.stdin.read())
    handler = {"chunks": chunks, "retrieve": retrieve}[command]
    print(json.dumps(asyncio.run(handler(payload)), ensure_ascii=False))


if __name__ == "__main__":
    main()
