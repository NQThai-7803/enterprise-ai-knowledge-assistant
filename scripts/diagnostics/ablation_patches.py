"""PROMPT 6 ablations, applied inside the API process of an eval stack only. app/ is unchanged.

Loaded by scripts/diagnostics/ablation_site/sitecustomize.py when EVAL_ABLATION is set; one or
more names joined by "." select what is patched:

  low_alignment_off   _filter_low_alignment_documents keeps every document (mechanism A).
  excerpt_off         each prompt source is its whole chunk, not query_focused_excerpt's
                      lexically chosen lines ("oracle.excerpt_off" is the full oracle).
  group5              the per-question cut of prepared hits keeps 5 instead of 2 (group_hits[:2]).
  partial_compound    a two-part question whose claims are only partly validated answers the
                      validated parts and says, in a fixed server-side sentence, which parts the
                      permitted documents do not mention, instead of refusing it all (mechanism C).
  oracle              the prompt gets the gold chunks of the question (EVAL_ORACLE_FILE), found
                      in the permission-filtered retrieval (widened to the service's maximum
                      top_k), past ranking and filters; questions
                      without gold, or whose gold the user cannot retrieve, run unchanged.

Diagnostic only: per-request state lives in context variables, and every patch logs one
"ABLATION ..." line per decision so a run can be audited from the stack log.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import unicodedata
from pathlib import Path
from typing import Any

logger = logging.getLogger("eaka.ablation")

PARTIAL_SENTENCE = "Tài liệu bạn được phép truy cập không đề cập: {need}"

_question: contextvars.ContextVar[str | None] = contextvars.ContextVar("question", default=None)
_oracle_hit: contextvars.ContextVar[bool] = contextvars.ContextVar("oracle_hit", default=False)
_claims: contextvars.ContextVar[list[dict[str, Any]] | None] = contextvars.ContextVar(
    "claims", default=None
)


class _WideCut(tuple):
    """A tuple whose [:2] reads as [:5], so the fixed cut in _prepare_answer_draft widens."""

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, slice) and (key.start, key.stop, key.step) == (None, 2, None):
            key = slice(None, 5)
        return super().__getitem__(key)


def question_key(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def selected() -> frozenset[str]:
    return frozenset(name for name in os.environ.get("EVAL_ABLATION", "").split(".") if name)


def apply(names: frozenset[str]) -> None:
    import app.services.grounded_answer_service as gas

    unknown = names - {"low_alignment_off", "excerpt_off", "group5", "partial_compound", "oracle"}
    if unknown:
        raise RuntimeError(f"unknown ablation(s): {sorted(unknown)}")
    service = gas.GroundedAnswerService
    original_prepare_draft = service._prepare_answer_draft

    async def prepare_draft(self: Any, **kwargs: Any) -> Any:
        token = _question.set(kwargs["conversation_context"].resolved_question.standalone_question)
        hit_token = _oracle_hit.set(False)
        try:
            return await original_prepare_draft(self, **kwargs)
        finally:
            _oracle_hit.reset(hit_token)
            _question.reset(token)

    service._prepare_answer_draft = prepare_draft

    if "low_alignment_off" in names:
        gas._filter_low_alignment_documents = lambda scored_hits: scored_hits
    if "excerpt_off" in names:
        import app.chat.context_builder as context_builder

        context_builder.query_focused_excerpt = lambda text, question, **_: text
    if "group5" in names or "oracle" in names:
        _patch_prepared_hits(gas, oracle="oracle" in names)
    if "partial_compound" in names:
        _patch_partial_compound(gas)
    logger.warning("ABLATION applied %s", ",".join(sorted(names)))


def _patch_prepared_hits(gas: Any, *, oracle: bool) -> None:
    from app.retrieval.hybrid_service import HybridRetrievalService

    gold = _load_oracle() if oracle else {}
    original_retrieve = HybridRetrievalService.retrieve
    original_prepare = gas.GroundedAnswerService._prepare_prompt_retrieval_hits

    async def retrieve(self: Any, *, query: str, current_user: Any, top_k: int) -> Any:
        entry = gold.get(question_key(_question.get() or ""))
        if entry is None:
            return await original_retrieve(
                self, query=query, current_user=current_user, top_k=top_k
            )
        # The widest retrieval the service allows; a larger top_k is INVALID_RETRIEVAL_TOP_K.
        widest = self.settings.hybrid_retrieval_max_top_k
        result = await original_retrieve(
            self, query=query, current_user=current_user, top_k=max(top_k, widest)
        )
        codes = await _document_codes({hit.document_id for hit in result.hits})
        hits = tuple(hit for hit in result.hits if is_gold(hit, codes.get(hit.document_id), entry))
        logger.warning("ABLATION oracle %s gold_hits=%d", "hit" if hits else "miss", len(hits))
        if not hits:
            return result
        _oracle_hit.set(True)
        return type(result)(**{**vars_of(result), "hits": hits, "hit_count": len(hits)})

    async def prepare(self: Any, hits: Any, **kwargs: Any) -> Any:
        if _oracle_hit.get() and hits:
            return _WideCut(hits)  # gold hits only: skip supplements, ranking and filters
        return _WideCut(await original_prepare(self, hits, **kwargs))

    if oracle:
        HybridRetrievalService.retrieve = retrieve
    gas.GroundedAnswerService._prepare_prompt_retrieval_hits = prepare


def vars_of(result: Any) -> dict[str, Any]:
    import dataclasses

    return {field.name: getattr(result, field.name) for field in dataclasses.fields(result)}


def is_gold(hit: Any, code: str | None, entry: list[dict[str, Any]]) -> bool:
    """A hit is gold when it is in a gold document and on a gold page or holds a gold fact."""
    from app.retrieval.question_analysis import fold_text

    text = fold_text(hit.text)
    for gold in entry:
        if code != gold["document"]:
            continue
        if set(gold.get("pages", ())) & set(hit.page_numbers):
            return True
        if any(fold_text(fact) in text for fact in gold.get("facts", ())):
            return True
    return False


async def _document_codes(document_ids: set[Any]) -> dict[Any, str]:
    from sqlalchemy import select

    from app.db.session import async_session_factory
    from app.models.document import Document

    if not document_ids:
        return {}
    async with async_session_factory() as session:
        rows = await session.execute(
            select(Document.id, Document.document_code).where(Document.id.in_(document_ids))
        )
        return {row[0]: row[1] for row in rows.all()}


def _load_oracle() -> dict[str, list[dict[str, Any]]]:
    path = os.environ.get("EVAL_ORACLE_FILE", "")
    if not path:
        raise RuntimeError("the oracle ablation needs EVAL_ORACLE_FILE")
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return {question_key(question): entry for question, entry in raw.items()}


def _patch_partial_compound(gas: Any) -> None:
    service = gas.GroundedAnswerService
    original_validated = service._validated_structured_claims
    original_compound = service._compound_draft_with_claim_repair

    async def validated(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = await original_validated(self, *args, **kwargs)
        stash = _claims.get()
        if stash is not None and not stash:
            stash.append(result)  # the first call returns the dict the repair later updates
        return result

    async def compound(self: Any, generation: Any, **kwargs: Any) -> Any:
        token = _claims.set([])
        try:
            return await original_compound(self, generation, **kwargs)
        except gas.CitationValidationFailedApplicationError:
            stash = _claims.get() or [{}]
            draft = await partial_draft(self, gas, generation, stash[0], **kwargs)
            if draft is None:
                raise
            return draft
        finally:
            _claims.reset(token)

    service._validated_structured_claims = validated
    service._compound_draft_with_claim_repair = compound


async def partial_draft(
    self: Any, gas: Any, generation: Any, claims: dict[str, Any], **kwargs: Any
) -> Any:
    needs = kwargs["information_needs"]
    ids = tuple(f"CLAIM_{index}" for index in range(1, len(needs) + 1))
    if not claims or len(claims) >= len(needs):
        logger.warning("ABLATION partial none validated=%d needs=%d", len(claims), len(needs))
        return None
    parts = [claims[claim_id].answer for claim_id in ids if claim_id in claims]
    parts += [
        PARTIAL_SENTENCE.format(need=need.rstrip(" ?"))
        for claim_id, need in zip(ids, needs, strict=True)
        if claim_id not in claims
    ]
    citations = list(dict.fromkeys(c for claim in claims.values() for c in claim.citations))
    content = json.dumps({"answer": " ".join(parts), "citations": citations}, ensure_ascii=False)
    logger.warning("ABLATION partial answered=%d needs=%d", len(claims), len(needs))
    return await self._draft_from_generation(
        gas.LLMGenerationResult(
            content=content,
            model=generation.model,
            finish_reason=generation.finish_reason,
            prompt_tokens=generation.prompt_tokens,
            completion_tokens=generation.completion_tokens,
            response_time_ms=generation.response_time_ms,
            provider=generation.provider,
        ),
        source_registry=kwargs["source_registry"],
        current_user=kwargs["current_user"],
        grounding_question=kwargs["grounding_question"],
        claims_already_validated=True,
    )
