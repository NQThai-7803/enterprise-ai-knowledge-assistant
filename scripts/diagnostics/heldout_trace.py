"""Trace grounded answers layer by layer, from outside app/. Run inside the API image.

usage (inside the container, working directory /app):
  python /tmp/heldout_trace.py --input /tmp/in.json --output /tmp/out.json --mode full|route
      [--embedding-pairs]

It wraps functions of app.services.grounded_answer_service and the retrieval services in this
process only, and calls GroundedAnswerService._prepare_answer_draft, which persists nothing.
`route` stops at the first LLM call, to count routes cheaply. Output stays under artifacts/: it
holds question text and chunk previews and must not be committed.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import functools
import inspect
import json
import logging
import re
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select

import app.services.grounded_answer_service as gas
from app.core.config import get_settings
from app.db.session import async_session_factory
from app.document_processing.tokenization import TiktokenTokenCounter
from app.llm.manager import LLMProviderManager
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.repositories.user_repository import get_by_email
from app.retrieval.factory import create_hybrid_retrieval_service
from app.retrieval.question_analysis import analyze_question
from app.retrieval.reranker_factory import create_retrieval_reranker

FILTERS = (
    "_filter_to_role_person_hits",
    "_filter_to_named_document_title_hits",
    "_filter_non_answer_context_hits",
    "_filter_to_salary_band_hits",
    "_filter_to_conditional_allowance_hits",
    "_filter_to_work_schedule_hits",
    "_filter_to_leave_policy_hits",
    "_filter_to_specific_term_hits",
    "_filter_low_alignment_documents",
)
TOP = 20
ROLE_EMAIL = "{}.uat@example.test"


class RouteStop(BaseException):
    """Raised at the first LLM call in route mode; not an Exception, so nothing swallows it."""


class Recorder:
    def __init__(self) -> None:
        self.trace: dict[str, Any] = {}
        self.gold: set[str] = set()
        self.codes: dict[str, str] = {}
        self.mode = "full"

    def start(self, gold: set[str]) -> None:
        self.gold = gold
        self.trace = {
            "retrieve": [],
            "semantic": [],
            "keyword": [],
            "rerank": [],
            "filters": [],
            "rank": [],
            "prepared": [],
            "llm": [],
            "structured_hits": [],
            "no_answer_reasons": [],
            "no_answer_calls": [],
            "claim_validation": [],
            "citation_errors": [],
            "generation_errors": [],
            "retry_checks": [],
            "deterministic_repair": [],
        }

    def hit(self, hit: Any, rank: int | None = None) -> dict[str, Any]:
        chunk_id = str(getattr(hit, "chunk_id", ""))
        document_id = str(getattr(hit, "document_id", ""))
        view = {
            "rank": rank,
            "chunk": chunk_id,
            "code": self.codes.get(document_id, document_id),
            "pages": list(getattr(hit, "page_numbers", ()) or ()),
            "gold": chunk_id in self.gold,
        }
        for name in (
            "hybrid_score",
            "semantic_score",
            "keyword_score",
            "reranker_score",
            "relevance_score",
            "keyword_rank",
            "semantic_rank",
        ):
            value = getattr(hit, name, None)
            if value is not None:
                view[name] = round(float(value), 5)
        return view

    def hits(self, hits: Any) -> dict[str, Any]:
        items = [self.hit(hit, rank) for rank, hit in enumerate(hits, start=1)]
        gold_ranks = [item for item in items if item["gold"]]
        return {
            "count": len(items),
            "top": items[:TOP],
            "gold": gold_ranks[:5],
            "cut_chunks": [item["chunk"] for item in items],
        }


REC = Recorder()


def _wrap_async(obj: Any, name: str, after: Any) -> None:
    original = getattr(obj, name)

    @functools.wraps(original)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = await original(*args, **kwargs)
        after(result, args, kwargs)
        return result

    setattr(obj, name, wrapper)


def _wrap_sync(obj: Any, name: str, after: Any) -> None:
    original = getattr(obj, name)

    @functools.wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        after(result, args, kwargs)
        return result

    setattr(obj, name, wrapper)


def _caller() -> str:
    frame = inspect.currentframe()
    names = []
    while frame is not None and len(names) < 6:
        if frame.f_code.co_filename.endswith("grounded_answer_service.py"):
            names.append(f"{frame.f_code.co_name}:{frame.f_lineno}")
        frame = frame.f_back
    return " < ".join(names[:3])


def _patch_module() -> None:
    for name in FILTERS:

        def after(result: Any, args: Any, kwargs: Any, name: str = name) -> None:
            before = args[0] if args else next(iter(kwargs.values()))
            before_ids = {str(item[1].chunk_id) for item in before}
            after_ids = {str(item[1].chunk_id) for item in result}
            removed = before_ids - after_ids
            if removed:
                REC.trace["filters"].append(
                    {
                        "filter": name,
                        "before": len(before_ids),
                        "after": len(after_ids),
                        "gold_removed": sorted(removed & REC.gold),
                        "removed_codes": sorted(
                            {
                                REC.codes.get(str(item[1].document_id), "?")
                                for item in before
                                if str(item[1].chunk_id) in removed
                            }
                        ),
                    }
                )

        _wrap_sync(gas, name, after)

    _wrap_sync(
        gas,
        "_rank_hits_for_prompt",
        lambda result, args, kwargs: REC.trace["rank"].append(
            {
                "question": kwargs.get("question"),
                "input": REC.hits(args[0]),
                "output": REC.hits(result),
            }
        ),
    )

    def after_context(result: Any, args: Any, kwargs: Any) -> None:
        REC.trace["context_input"] = REC.hits(kwargs.get("hits", ()))
        REC.trace["information_needs"] = list(kwargs.get("information_needs") or ())
        REC.trace["context_selected_count"] = result.selected_chunk_count

    _wrap_sync(gas, "select_context_for_prompt", after_context)

    def after_registry(result: Any, args: Any, kwargs: Any) -> None:
        REC.trace["sources"] = [
            {
                "marker": source.marker,
                "chunk": str(source.chunk_id),
                "code": REC.codes.get(str(source.document_id), "?"),
                "pages": list(source.page_numbers),
                "gold": str(source.chunk_id) in REC.gold,
                "reranker_score": source.reranker_score,
                "preview": source.text[:240],
            }
            for source in result.sources
        ]

    _wrap_sync(gas, "build_prompt_source_registry", after_registry)
    _wrap_sync(
        gas,
        "_reason_evidence_is_missing",
        lambda result, args, kwargs: REC.trace.__setitem__("reason_evidence_missing", bool(result)),
    )
    _wrap_sync(
        gas,
        "_log_no_answer_diagnostics",
        lambda result, args, kwargs: REC.trace["no_answer_reasons"].append(kwargs.get("reason")),
    )
    _wrap_sync(
        gas,
        "_no_answer_draft",
        lambda result, args, kwargs: REC.trace["no_answer_calls"].append(_caller()),
    )
    for name in ("_should_retry_no_answer", "_should_retry_incomplete_answer"):

        def after_retry(result: Any, args: Any, kwargs: Any, name: str = name) -> None:
            REC.trace["retry_checks"].append({"check": name, "result": bool(result)})

        _wrap_sync(gas, name, after_retry)
    for name, value in list(vars(gas).items()):
        if name.startswith("_structured_") and name.endswith("_answer") and callable(value):

            def after_structured(result: Any, args: Any, kwargs: Any, name: str = name) -> None:
                if result is not None:
                    REC.trace["structured_hits"].append(
                        {"branch": name, "caller": _caller(), "answer": str(result)[:400]}
                    )

            _wrap_sync(gas, name, after_structured)


class TracedProvider:
    def __init__(self, inner: Any) -> None:
        self.inner = inner

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    async def generate(self, **kwargs: Any) -> Any:
        messages = kwargs.get("messages") or ()
        record: dict[str, Any] = {"message_chars": sum(len(m.content) for m in messages)}
        REC.trace["llm"].append(record)
        if REC.mode == "route":
            raise RouteStop
        started = perf_counter()
        result = await self.inner.generate(**kwargs)
        record.update(
            {
                "seconds": round(perf_counter() - started, 2),
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "content": result.content[:1500],
            }
        )
        return result


def _claim_view(result: Any, args: Any, kwargs: Any) -> None:
    feedback = getattr(result, "repair_feedback", None)
    REC.trace["claim_validation"].append(
        {
            "status": getattr(getattr(result, "status", None), "value", str(result)),
            "feedback": str(feedback)[:300] if feedback else None,
            "answer": str(kwargs.get("answer"))[:300],
        }
    )


def _wrap_validate(validator: Any) -> None:
    """Record each verdict, its evidence, and whether zero-padding a lone digit changes it."""
    original = validator.validate

    @functools.wraps(original)
    async def wrapper(**kwargs: Any) -> Any:
        result = await original(**kwargs)
        _claim_view(result, (), kwargs)
        record = REC.trace["claim_validation"][-1]
        registry = kwargs["source_registry"]
        labels = {label.strip("[]") for label in kwargs.get("cited_source_labels", ())}
        record["cited"] = sorted(labels)
        record["evidence"] = " || ".join(
            source.text[:900] for source in registry.sources if source.marker.strip("[]") in labels
        )
        if record["status"] != "SUPPORTED":
            padded = re.sub(r"(?<![\d.,])(\d)(?![\d.,])", r"0\1", kwargs["answer"])
            if padded != kwargs["answer"]:
                probe = await original(**{**kwargs, "answer": padded})
                record["zero_pad_probe"] = probe.status.value
        return result

    validator.validate = wrapper


class _ReasonHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if "reason=" in message and REC.trace:
            REC.trace.setdefault("log_reasons", []).append(message[:120])


def _patch_service(service: Any) -> None:
    hybrid = service.hybrid_retrieval_service

    def after_branch(key: str) -> Any:
        def after(result: Any, args: Any, kwargs: Any) -> None:
            REC.trace[key].append({"query": kwargs.get("query"), **REC.hits(result.hits)})

        return after

    _wrap_async(hybrid, "retrieve", after_branch("retrieve"))
    _wrap_async(hybrid.semantic_retrieval_service, "retrieve", after_branch("semantic"))
    _wrap_async(hybrid.keyword_retrieval_service, "retrieve", after_branch("keyword"))
    if service.retrieval_reranker is not None:
        _wrap_async(
            service.retrieval_reranker,
            "rerank",
            lambda result, args, kwargs: REC.trace["rerank"].append(
                {"query": kwargs.get("query"), "output": REC.hits(result)}
            ),
        )
    _wrap_async(
        service,
        "_prepare_prompt_retrieval_hits",
        lambda result, args, kwargs: REC.trace["prepared"].append(
            {"question": kwargs.get("question"), **REC.hits(result)}
        ),
    )

    def after_structured_draft(result: Any, args: Any, kwargs: Any) -> None:
        REC.trace["structured_value_draft"] = None if result is None else str(result.content)[:600]

    _wrap_async(service, "_structured_value_answer_draft", after_structured_draft)
    _wrap_async(
        service,
        "_draft_from_deterministic_repair",
        lambda result, args, kwargs: REC.trace["deterministic_repair"].append(
            None if result is None else str(result.content)[:400]
        ),
    )
    _wrap_validate(service.claim_validation_service)

    original_generation = service._draft_from_generation

    @functools.wraps(original_generation)
    async def traced_generation(*args: Any, **kwargs: Any) -> Any:
        try:
            return await original_generation(*args, **kwargs)
        except Exception as exc:
            REC.trace["generation_errors"].append(type(exc).__name__)
            raise

    service._draft_from_generation = traced_generation

    original_map = service.citation_validation_service.validate_and_map

    @functools.wraps(original_map)
    async def traced_map(*args: Any, **kwargs: Any) -> Any:
        try:
            return await original_map(*args, **kwargs)
        except Exception as exc:
            REC.trace["citation_errors"].append(type(exc).__name__)
            raise

    service.citation_validation_service.validate_and_map = traced_map


def _folded(text: str) -> str:
    return re.sub(r"\s+", " ", gas._fold_for_person_match(text)).strip()


async def _gold_chunks(session: Any, item: dict[str, Any], ids: dict[str, str]) -> dict[str, Any]:
    """Chunks holding a gold excerpt, else chunks on a gold page of a gold document."""
    excerpts = [
        (e["document"], e.get("page"), _folded(e["text"])) for e in item.get("excerpts", [])
    ]
    found: set[str] = set()
    page_only: set[str] = set()
    for citation in item.get("gold_citations", []):
        document_id = ids.get(citation["document"])
        if document_id is None:
            continue
        rows = await session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        pages = set(citation.get("pages", []))
        for chunk in rows.scalars():
            if pages & set(range(chunk.start_page, chunk.end_page + 1)):
                page_only.add(str(chunk.id))
                text = _folded(chunk.text)
                for document, _, excerpt in excerpts:
                    if document == citation["document"] and excerpt[:60] and excerpt[:60] in text:
                        found.add(str(chunk.id))
    return {
        "chunks": sorted(found or page_only),
        "method": "excerpt" if found else ("page" if page_only else "none"),
    }


async def _visibility(session: Any, user: Any, document_ids: set[str]) -> dict[str, bool]:
    if not document_ids:
        return {}
    rows = await session.execute(
        select(Document.id).where(gas.build_accessible_document_filter(user))
    )
    visible = {str(row) for row in rows.scalars()}
    return {document_id: document_id in visible for document_id in document_ids}


def _analysis_view(question: str) -> dict[str, Any]:
    analysis = analyze_question(question)
    view = dataclasses.asdict(analysis) if dataclasses.is_dataclass(analysis) else str(analysis)
    return {
        "analysis": view,
        "information_needs": list(gas.information_need_queries(question)),
        "is_overtime": gas._is_overtime_rate_question(question),
    }


async def _trace_item(service: Any, item: dict[str, Any], ids: dict[str, str]) -> dict[str, Any]:
    async with async_session_factory() as session:
        user = await get_by_email(session, ROLE_EMAIL.format(item["role"]))
        gold = await _gold_chunks(session, item, ids)
    REC.start(set(gold["chunks"]))
    question = item["question"]
    context = SimpleNamespace(resolved_question=SimpleNamespace(standalone_question=question))
    started = perf_counter()
    outcome: dict[str, Any]
    try:
        draft = await service._prepare_answer_draft(
            current_user=user, question=question, conversation_context=context
        )
        outcome = {
            "status": draft.grounding_status.value,
            "answer": draft.content[:1500],
            "citations": [
                {
                    "code": REC.codes.get(str(c.document_id), str(c.document_id)),
                    "document_id": str(c.document_id),
                    "chunk": str(c.chunk_id),
                    "page": c.page_number,
                    "gold": str(c.chunk_id) in REC.gold,
                    "excerpt": c.excerpt[:300],
                    "evidence_text": (c.evidence_text or "")[:300],
                }
                for c in draft.citations
            ],
            "citation_failure": dataclasses.asdict(draft.citation_failure)
            if draft.citation_failure
            else None,
        }
    except RouteStop:
        outcome = {"status": "ROUTE_STOP_AT_LLM", "answer": "", "citations": []}
    trace = REC.trace
    trace["cited_visibility"] = {}
    seen = {c["document_id"] for c in outcome.get("citations", [])}
    if seen:
        async with async_session_factory() as session:
            trace["cited_visibility"] = await _visibility(session, user, seen)
    route = "llm" if trace["llm"] else "no_llm_no_answer"
    if trace.get("structured_value_draft"):
        route = "deterministic"
    return {
        "id": item["id"],
        "role": item["role"],
        "group": item.get("group"),
        "gold_status": item.get("gold_status"),
        "question": question,
        "gold_chunks": gold,
        "route": route,
        "seconds": round(perf_counter() - started, 2),
        "outcome": outcome,
        "analysis": _analysis_view(question),
        "trace": trace,
    }


async def _embedding_pairs(service: Any, pairs: list[dict[str, Any]], ids: dict[str, str]) -> list:
    provider = service.hybrid_retrieval_service.semantic_retrieval_service.embedding_provider
    out = []
    for pair in pairs:
        async with async_session_factory() as session:
            gold = await _gold_chunks(session, pair, ids)
            rows = await session.execute(
                select(DocumentChunk.id, DocumentChunk.embedding).where(
                    DocumentChunk.id.in_(gold["chunks"])
                )
            )
            vectors = [list(map(float, row[1])) for row in rows.all()]
        scores: dict[str, Any] = {}
        for key in ("en", "vi"):
            query = list(map(float, provider.embed_query(pair[key]).values))
            cosines = [sum(a * b for a, b in zip(query, v, strict=True)) for v in vectors]
            scores[key] = {
                "best_cosine": round(max(cosines), 4) if cosines else None,
                "analysis": _analysis_view(pair[key]),
            }
        a = list(map(float, provider.embed_query(pair["en"]).values))
        b = list(map(float, provider.embed_query(pair["vi"]).values))
        out.append(
            {
                "id": pair["id"],
                "gold_method": gold["method"],
                "query_cosine": round(sum(x * y for x, y in zip(a, b, strict=True)), 4),
                **scores,
            }
        )
    return out


async def main_async(args: argparse.Namespace) -> None:
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    REC.mode = args.mode
    REC.codes = payload["codes"]
    ids = {code: document_id for document_id, code in payload["codes"].items()}
    base = get_settings()
    settings = base.model_copy(update={"rag_diagnostics_enabled": True})
    manager = LLMProviderManager(settings)
    service = gas.GroundedAnswerService(
        settings=settings,
        session_provider=async_session_factory,
        hybrid_retrieval_service=create_hybrid_retrieval_service(settings),
        retrieval_reranker=create_retrieval_reranker(settings)
        if settings.reranker_enabled
        else None,
        llm_provider_factory=lambda: TracedProvider(manager.get_provider()),
        close_llm_provider_after_generate=False,
        token_counter=TiktokenTokenCounter(settings.tokenizer_encoding_name),
    )
    _patch_module()
    _patch_service(service)
    output = Path(args.output)
    results: list[dict[str, Any]] = []
    extras: dict[str, Any] = {}
    for index, item in enumerate(payload["items"], start=1):
        results.append(await _trace_item(service, item, ids))
        print(f"{index}/{len(payload['items'])} {item['id']} {results[-1]['route']}", flush=True)
        output.write_text(
            json.dumps({"results": results, **extras}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
    if args.embedding_pairs:
        extras["embedding_pairs"] = await _embedding_pairs(service, payload["pairs"], ids)
    output.write_text(
        json.dumps({"results": results, **extras}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    reranker = service.retrieval_reranker
    print("reranker_model_load_failed", getattr(reranker, "_model_load_failed", None), flush=True)
    await manager.aclose()


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.CRITICAL)
    gas.logger.setLevel(logging.WARNING)
    gas.logger.propagate = False
    gas.logger.addHandler(_ReasonHandler())
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=("full", "route"), default="full")
    parser.add_argument("--embedding-pairs", action="store_true")
    asyncio.run(main_async(parser.parse_args()))
