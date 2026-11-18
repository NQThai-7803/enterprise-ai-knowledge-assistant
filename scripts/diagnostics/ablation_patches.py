"""PROMPT 6 ablations, applied inside the API process of an eval stack only. app/ is unchanged.

Loaded by scripts/diagnostics/ablation_site/sitecustomize.py when EVAL_ABLATION is set; one or
more names joined by "." select what is patched:

  low_alignment_off   _filter_low_alignment_documents keeps every document (mechanism A).
  deterministic_off   no deterministic answer or repair: _structured_value_repair_generation
                      and _structured_policy_clause_repair_generation return nothing, so every
                      answer comes from the LLM path.
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
  simple_trace        behavior unchanged: every LLM draft of the simple answer mode, accepted or
                      rejected, is appended to EVAL_SIMPLE_TRACE_FILE (default
                      /tmp/simple_trace.jsonl) with its sources, its outcome, and each sentence
                      with the markers it cites and the claim validator's status and deciding
                      rule for that sentence against its own cited sources.
  retrieval_oracle    no LLM (DEC-034 retrieval gate): the simple answer mode records the chunks
                      it would give the prompt (hybrid retrieval, then at most 5, at most 2 per
                      document) and which are gold (EVAL_ORACLE_FILE), to EVAL_SIMPLE_TRACE_FILE,
                      then answers NO_ANSWER without calling the LLM.

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

    known = {"low_alignment_off", "excerpt_off", "group5", "partial_compound", "oracle"}
    known.update({"simple_trace", "retrieval_oracle"})
    unknown = names - known - {"deterministic_off"}
    if unknown:
        raise RuntimeError(f"unknown ablation(s): {sorted(unknown)}")
    service = gas.GroundedAnswerService
    original_prepare_draft = service._prepare_answer_draft

    async def prepare_draft(self: Any, **kwargs: Any) -> Any:
        # The question as sent: the resolver rewrites first-person UAT wording before
        # standalone_question, and the oracle map is keyed on the sets' own text.
        token = _question.set(kwargs["question"])
        hit_token = _oracle_hit.set(False)
        try:
            return await original_prepare_draft(self, **kwargs)
        finally:
            _oracle_hit.reset(hit_token)
            _question.reset(token)

    service._prepare_answer_draft = prepare_draft

    if "low_alignment_off" in names:
        gas._filter_low_alignment_documents = lambda scored_hits: scored_hits
    if "deterministic_off" in names:
        gas._structured_value_repair_generation = lambda **_: None
        gas._structured_policy_clause_repair_generation = lambda **_: None
    if "excerpt_off" in names:
        import app.chat.context_builder as context_builder

        context_builder.query_focused_excerpt = lambda text, question, **_: text
    if "group5" in names or "oracle" in names:
        _patch_prepared_hits(gas, oracle="oracle" in names)
    if "partial_compound" in names:
        _patch_partial_compound(gas)
    if "simple_trace" in names:
        _patch_simple_trace(gas)
    if "retrieval_oracle" in names:
        _patch_retrieval_oracle(gas)
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


def _patch_retrieval_oracle(gas: Any) -> None:
    gold = _load_oracle()
    path = Path(os.environ.get("EVAL_SIMPLE_TRACE_FILE") or "/tmp/simple_trace.jsonl")

    async def simple_answer_draft(self: Any, *, current_user: Any, grounding_question: str) -> Any:
        # The retrieval and hit choice of _simple_answer_draft, without the prompt and the LLM.
        result = await self.hybrid_retrieval_service.retrieve(
            query=grounding_question,
            current_user=current_user,
            top_k=gas._chat_retrieval_candidate_top_k(
                settings=self.settings, reranker=self.retrieval_reranker
            ),
        )
        hits = gas._simple_select_hits(result.hits)
        codes = await _document_codes({hit.document_id for hit in hits})
        asked = _question.get() or ""
        entry = gold.get(question_key(asked))
        rows = [
            {
                "rank": rank,
                "code": codes.get(hit.document_id),
                "pages": list(hit.page_numbers),
                "row": hit.group_id is not None and hit.group_id != hit.chunk_id,
                "gold": bool(entry) and is_gold(hit, codes.get(hit.document_id), entry),
                "text": hit.text[:300],
            }
            for rank, hit in enumerate(hits, 1)
        ]
        record = {
            "asked": asked,
            "question": grounding_question,
            "has_gold": entry is not None,
            "gold_hit": any(row["gold"] for row in rows),
            "hits": rows,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + chr(10))
        return self._simple_no_answer("retrieval_oracle")

    gas.GroundedAnswerService._simple_answer_draft = simple_answer_draft


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


_rules: contextvars.ContextVar[list[tuple[str, str]] | None] = contextvars.ContextVar(
    "rules", default=None
)
_attempt: contextvars.ContextVar[list[int] | None] = contextvars.ContextVar("attempt", default=None)
_similarities: contextvars.ContextVar[list[dict[str, Any]] | None] = contextvars.ContextVar(
    "similarities", default=None
)
_bindings: contextvars.ContextVar[list[dict[str, Any]] | None] = contextvars.ContextVar(
    "bindings", default=None
)


def _patch_simple_trace(gas: Any) -> None:
    """Record every simple-mode draft. The rules of _validate_answer_against_evidence are
    wrapped only to note which one decided; every wrapper returns the original value."""
    import app.services.claim_evidence_validation_service as validation
    from app.citations.parser import parse_citation_markers
    from app.retrieval.evidence_quality import classify_evidence_context

    path = Path(os.environ.get("EVAL_SIMPLE_TRACE_FILE") or "/tmp/simple_trace.jsonl")
    for name in validation._validate_answer_against_evidence.__code__.co_names:
        rule = getattr(validation, name, None)
        if name.startswith("_") and callable(rule) and not isinstance(rule, type):
            setattr(validation, name, _noting(name, rule))

    def flags(self: Any) -> dict[str, bool]:
        return {
            "relaxed_rules": self.settings.rag_simple_relaxed_rules_enabled,
            "question_list_segments": self.settings.rag_simple_question_list_segments_enabled,
        }

    async def judged(self: Any, *, question: str, answer: str, registry: Any, labels: Any) -> dict:
        token = _rules.set([])
        try:
            with validation.simple_validation(**flags(self)):
                result = await self.claim_validation_service.validate(
                    question=question,
                    answer=answer,
                    source_registry=registry,
                    cited_source_labels=labels,
                )
            return {"status": result.status.value, "rule": deciding_rule(_rules.get() or [])}
        finally:
            _rules.reset(token)

    original = gas.GroundedAnswerService._simple_validate
    original_draft = gas.GroundedAnswerService._simple_answer_draft
    original_similarity = gas.GroundedAnswerService._simple_claim_similarity

    async def simple_answer_draft(self: Any, **kwargs: Any) -> Any:
        token = _attempt.set([0])  # LLM drafts of this question
        try:
            return await original_draft(self, **kwargs)
        finally:
            _attempt.reset(token)

    original_binding = gas.value_bound_to_subject

    def value_bound(**kwargs: Any) -> bool:
        bound = original_binding(**kwargs)
        noted = _bindings.get()
        if noted is not None:
            noted.append({"claim": kwargs["claim"], "bound": bound})
        return bound

    async def claim_similarity(self: Any, **kwargs: Any) -> Any:
        similarity = await original_similarity(self, **kwargs)
        noted = _similarities.get()
        if noted is not None:
            noted.append({"claim": kwargs["claim"], "similarity": similarity})
        return similarity

    def sentences_of(self: Any, text: str, question: str) -> list[tuple[str, bool]]:
        """(sentence, absence) as the service splits the draft."""
        if self.settings.rag_simple_absence_sentences_enabled:
            _, claims = gas._simple_split_absences(text, question=question)
            pieces = gas._simple_sentence_parts(text)[::2]
            return [(s, s not in claims) for s in pieces if s.strip()]
        return [
            (s, not gas._simple_claim_text(s)) for s in gas._SIMPLE_SENTENCE_BREAK.split(text)
            if s.strip()
        ]  # fmt: skip

    async def simple_validate(self: Any, generation: Any, **kwargs: Any) -> Any:
        counter = _attempt.get()
        if counter is not None:
            counter[0] += 1
        token = _similarities.set([])
        bindings_token = _bindings.set([])
        try:
            outcome = await original(self, generation, **kwargs)
            similarities = _similarities.get() or []
            bindings = _bindings.get() or []
        finally:
            _similarities.reset(token)
            _bindings.reset(bindings_token)
        registry, question = kwargs["source_registry"], kwargs["question"]
        text = gas.normalize_llm_citation_markers(
            generation.content.strip(), source_registry=registry
        )
        sentences = []
        for sentence, absence in sentences_of(self, text, question):
            labels = tuple(
                m.strip("[]") for m in parse_citation_markers(sentence).ordered_unique_markers
            )
            plain = "" if absence else gas._simple_claim_text(sentence)
            row: dict[str, Any] = {"text": sentence, "sources": labels, "absence": not plain}
            if plain and labels:
                row |= await judged(
                    self, question=question, answer=plain, registry=registry, labels=labels
                )
            sentences.append(row)
        claim_sentences = [s for s, absence in sentences_of(self, text, question) if not absence]
        labels = tuple(
            m.strip("[]")
            for m in parse_citation_markers(" ".join(claim_sentences)).ordered_unique_markers
        )
        plain = " ".join(filter(None, map(gas._simple_claim_text, claim_sentences)))
        whole = (
            await judged(self, question=question, answer=plain, registry=registry, labels=labels)
            if plain and labels
            else None
        )
        record = {
            "asked": _question.get(),
            "question": question,
            "oracle_hit": _oracle_hit.get(),
            "attempt": counter[0] if counter is not None else None,
            "draft": generation.content,
            "outcome": "answered" if not isinstance(outcome, tuple) else outcome[0],
            "final": not isinstance(outcome, tuple) or outcome[1] is None,
            "whole": whole,
            "sentences": sentences,
            "similarities": similarities,
            "bindings": bindings,
            "sources": [
                {
                    "label": source.marker.strip("[]"),
                    "title": source.document_title,
                    "pages": list(source.page_numbers),
                    "kind": classify_evidence_context(source.text).value,
                    "text": source.text,
                }
                for source in registry.sources
            ],
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return outcome

    gas.GroundedAnswerService._simple_validate = simple_validate
    gas.GroundedAnswerService._simple_answer_draft = simple_answer_draft
    gas.GroundedAnswerService._simple_claim_similarity = claim_similarity
    gas.value_bound_to_subject = value_bound


def _noting(name: str, rule: Any) -> Any:
    def noted(*args: Any, **kwargs: Any) -> Any:
        result = rule(*args, **kwargs)
        calls = _rules.get()
        status = getattr(result, "value", None)  # a ClaimEvidenceStatus; True for a predicate
        if calls is not None and (result is True or isinstance(status, str)):
            calls.append((name, status or "True"))
        return result

    return noted


def deciding_rule(calls: list[tuple[str, str]]) -> str:
    """The last rule that returned True or a status: the validator returns right after it.
    "fallthrough" when none did."""
    return "=".join(calls[-1]) if calls else "fallthrough"
