from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit import AuditEventType, AuditTargetType
from app.chat.context_builder import select_context_for_prompt
from app.chat.conversation_context_builder import ConversationContext, ConversationContextBuilder
from app.chat.models import ChatAnswerResult, GroundingStatus
from app.chat.prompt_builder import build_grounded_prompt, build_grounding_system_prompt
from app.citations.errors import (
    CitationMappingError,
    CitationPermissionRevalidationError,
    CitationValidationError,
)
from app.citations.grounded_output import GroundedLLMOutput, parse_grounded_llm_output
from app.citations.models import PromptSourceRegistry
from app.citations.registry import build_prompt_source_registry
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ApplicationError,
    ChatRetrievalFailedError,
    ChatSessionNotFoundError,
    CitationMappingFailedApplicationError,
    CitationPersistenceFailedApplicationError,
    CitationValidationFailedApplicationError,
    InternalServerError,
    LLMAuthenticationFailedApplicationError,
    LLMGenerationFailedApplicationError,
    LLMNotConfiguredApplicationError,
    LLMProviderAuthenticationFailedStandardApplicationError,
    LLMProviderBadResponseApplicationError,
    LLMProviderRateLimitedStandardApplicationError,
    LLMProviderTimeoutStandardApplicationError,
    LLMProviderUnavailableApplicationError,
    LLMProviderUnsupportedApplicationError,
    LLMRateLimitedApplicationError,
    LLMRequestRejectedApplicationError,
    LLMResponseInvalidApplicationError,
    LLMTimeoutApplicationError,
)
from app.core.permissions import build_accessible_document_filter
from app.document_processing.tokenization.base import TokenCounter
from app.document_processing.tokenization.tiktoken_counter import TiktokenTokenCounter
from app.llm.base import LLMProvider
from app.llm.errors import LLMError, LLMFailureCode
from app.llm.models import LLMGenerationResult, LLMMessage
from app.models import ChatMessage, ChatMessageRole, Document, DocumentChunk, DocumentStatus, User
from app.repositories import (
    chat_message_repository,
    chat_session_repository,
    message_citation_repository,
)
from app.retrieval.base import HybridRetrievalService
from app.retrieval.errors import RetrievalError
from app.retrieval.models import HybridRetrievalHit
from app.retrieval.question_analysis import QuestionAnalysis, analyze_question
from app.retrieval.reranker import RetrievalReranker
from app.retrieval.structured import has_explicit_not_specified
from app.services.audit_service import AuditContext, AuditService
from app.services.chat_message_service import ChatMessageService, normalize_message_content
from app.services.citation_validation_service import CitationValidationService
from app.services.claim_evidence_validation_service import (
    ClaimEvidenceStatus,
    ClaimEvidenceValidationService,
)
from app.web_search.errors import WebSearchError
from app.web_search.intent import WebSearchIntentClassifier
from app.web_search.models import KnowledgeSourceMode, WebSearchResult
from app.web_search.service import WebSearchService

logger = logging.getLogger(__name__)

_PROMPT_QUERY_TERM_PATTERN = re.compile(r"\w+", re.UNICODE)
_NAME_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)
_QUESTION_ACRONYM_PATTERN = re.compile(r"\b[A-Z][A-Z0-9&/+.-]{1,}\b")
_PUBLIC_CITATION_MARKER_PATTERN = re.compile(r"\[(?:SOURCE_[1-9][0-9]*|[1-9][0-9]*)\]")
_NUMBER_UNIT_PATTERN = re.compile(r"(?<!\d)(\d+)\s*(?:\([^)]{1,80}\)\s*)?([^\W\d_]+)", re.UNICODE)
_COUNT_VALUE_PATTERN = re.compile(
    r"(?<!\d)\d+(?:[.,]\d+)?\s*(?:nguoi|nhan\s+su|nhan\s+vien|employees?|people)\b"
)
_MONEY_VALUE_PATTERN = re.compile(
    r"(?<!\d)\d+(?:[.,]\d+)?(?:\s*(?:-|\u2013|\u2014)\s*\d+(?:[.,]\d+)?)?\s*"
    r"(?:trieu|dong|vnd|d|\u20ab)\b"
)
_PERCENT_VALUE_PATTERN = re.compile(r"(?<!\d)\d+(?:[.,]\d+)?\s*%")
_TIME_RANGE_VALUE_PATTERN = re.compile(
    r"(?<!\d)(?:[01]?\d|2[0-3])(?:[:h][0-5]\d)?\s*(?:-|\u2013|\u2014|den|to)\s*"
    r"(?:[01]?\d|2[0-3])(?:[:h][0-5]\d)?"
)
_CLOCK_VALUE_PATTERN = re.compile(r"(?<!\d)(?:[01]?\d|2[0-3])(?:[:h][0-5]\d)(?!\d)")
_DATE_VALUE_PATTERN = re.compile(r"\bngay\s+\d{1,2}(?:/\d{1,2}(?:/\d{2,4})?)?\b")
_DURATION_VALUE_PATTERN = re.compile(
    r"(?<!\d)\d+(?:[.,]\d+)?\s*(?:gio|ngay|tuan|thang|nam|hours?|days?|weeks?|months?|years?)\b"
)
_YEAR_VALUE_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
_FOUNDING_YEAR_VALUE_PATTERN = re.compile(
    r"(?:nam\s+thanh\s+lap|founded|established).{0,80}\b(?:19|20)\d{2}\b"
    r"|\b(?:19|20)\d{2}\b.{0,80}(?:nam\s+thanh\s+lap|founded|established)"
)
_PLANNING_YEAR_VALUE_PATTERN = re.compile(
    r"(?:den\s+nam|by\s+(?:the\s+)?year|by)\s+(?:19|20)\d{2}\b"
)
_PROMPT_MIN_QUERY_TERM_CHARACTERS = 3
_PROMPT_MAX_QUERY_TERMS = 32
_ADJACENT_CHUNK_SCORE_FACTOR = 0.98
_PROMPT_DOCUMENT_FILTER_MIN_BEST_SCORE = 40.0
_PROMPT_DOCUMENT_FILTER_MIN_RATIO = 0.75
_PROMPT_HIT_FILTER_MIN_RATIO = 0.75
_PROMPT_SPECIFIC_TERM_MIN_CHARACTERS = 8
_PROMPT_SPECIFIC_TERM_BONUS = 14.0
_PROMPT_PERSON_SOURCE_BONUS = 40.0
_PROMPT_NUMBER_MATCH_BONUS = 90.0
_PROMPT_NUMBER_UNIT_MATCH_BONUS = 70.0
_PROMPT_CHANGE_EVIDENCE_BONUS = 85.0
_PROMPT_PERSON_FOCUS_MATCH_BONUS = 35.0
_ROLE_PERSON_ASSOCIATION_MAX_CHARS = 320
_ROLE_PERSON_SUPPLEMENT_LIMIT = 12
_PROMPT_NON_ROLE_ACRONYMS = frozenset(
    {
        "ai",
        "api",
        "bhxh",
        "bhyt",
        "bhtn",
        "bi",
        "crm",
        "erp",
        "hrm",
        "mlops",
        "ot",
        "rag",
        "sla",
        "vpn",
    }
)
_QUESTION_LIST_CONTEXT_CUES = (
    "cau hoi goi y",
    "cau hoi kiem thu",
    "cau hoi tham khao",
    "tinh huong mau",
    "tinh huong",
    "sample scenario",
    "example scenario",
    "suggested question",
    "test question",
    "kiem thu rag",
    "testing rag",
    "no-answer test",
)
_REFERENCE_CONTEXT_CUES = (
    "muc luc",
    "danh muc tai lieu",
    "tai lieu lien quan",
    "lich su phien ban",
    "kiem soat tai lieu",
    "table of contents",
    "related documents",
    "version history",
)
_ANSWER_POLARITY_CUES = (
    "khong tu dong",
    "khong duoc",
    "khong phai",
    "duoc phep",
    "bat buoc",
    "phai",
    "tu dong",
    "not automatic",
    "not allowed",
    "required",
    "allowed",
    "must",
    "must not",
)
_ORGANIZATION_NAME_TOKENS = frozenset(
    {
        "an",
        "attt",
        "bao",
        "cao",
        "cap",
        "che",
        "chuong",
        "compliance",
        "contract",
        "customer",
        "data",
        "dieu",
        "dong",
        "du",
        "giam",
        "hang",
        "ho",
        "hoi",
        "hop",
        "ke",
        "kien",
        "khach",
        "kiem",
        "legal",
        "lieu",
        "mat",
        "noi",
        "phap",
        "pmo",
        "privacy",
        "product",
        "quyen",
        "rieng",
        "security",
        "service",
        "soc",
        "thu",
        "thong",
        "tin",
        "toan",
        "trinh",
        "truc",
        "tuan",
        "tu",
        "uy",
    }
)
_ORGANIZATION_NAME_START_TOKENS = frozenset(
    {"ban", "bo", "hoi", "khoi", "phong", "trung", "uy", "van"}
)
_PERSON_QUESTION_TERMS = frozenset({"ai", "who"})
_NON_PERSON_NAME_TOKENS = frozenset(
    {
        "ban",
        "bo",
        "business",
        "company",
        "cong",
        "corporation",
        "department",
        "chief",
        "chuyen",
        "co",
        "dieu",
        "director",
        "doc",
        "executive",
        "founder",
        "giam",
        "digital",
        "division",
        "gioi",
        "group",
        "hanh",
        "khoi",
        "kinh",
        "nghe",
        "office",
        "officer",
        "phu",
        "operations",
        "organization",
        "phong",
        "san",
        "strategy",
        "technology",
        "tong",
        "trach",
        "truong",
        "thieu",
        "to",
        "ty",
        "van",
    }
)
_CHANGE_QUESTION_CUES = (
    "thay \u0111\u1ed5i",
    "change",
)
_CHANGE_EVIDENCE_CUES = (
    "t\u0103ng",
    "th\u00eam",
    "gi\u1ea3m",
    "b\u1edbt",
    "\u0111i\u1ec1u ch\u1ec9nh",
    "increase",
    "additional",
    "extra",
    "decrease",
    "reduce",
    "adjust",
)
_REASON_QUESTION_PREFIXES = (
    "why ",
    "t\u1ea1i sao",
    "v\u00ec sao",
)
_REASON_EVIDENCE_CUES = (
    "because",
    "due to",
    "reason",
    "b\u1edfi v\u00ec",
    "l\u00fd do",
    "nguy\u00ean nh\u00e2n",
    "ly do",
    "nguyen nhan",
)
_PURPOSE_QUESTION_CUES = (
    "dung de",
    "lam gi",
    "dung lam gi",
    "used for",
    "what does",
    "purpose",
    "function",
)
_YES_NO_QUESTION_CUES = (
    "co phai",
    "dung khong",
    "phai khong",
    "is ",
    "are ",
    "do ",
    "does ",
)
_YES_NO_POLARITY_CUES = ("khong", "co", "dung", "phai", "yes", "no")
_LIMIT_QUESTION_CUES = ("toi da", "khong qua", "maximum", "limit")
_LIMIT_ANSWER_CUES = ("toi da", "khong qua", "maximum", "limit")
_PLACEHOLDER_ANSWER_CUES = (
    "complete answer",
    "actual answer",
    "answer text",
    "user-facing answer",
    "placeholder",
)
_QUANTITY_STOP_TERMS = frozenset({"bao", "nhieu", "how", "many", "cua", "duoc"})
_NO_ANSWER_LIKE_ANSWER_PHRASES = (
    "kh\u00f4ng c\u00f3 th\u00f4ng tin",
    "kh\u00f4ng cung c\u1ea5p th\u00f4ng tin",
    "kh\u00f4ng t\u00ecm th\u1ea5y",
    "kh\u00f4ng n\u00eau",
    "insufficient information",
    "not enough information",
    "does not provide",
    "do not provide",
    "does not state",
)

LLMProviderFactory = Callable[[], LLMProvider]


@dataclass(frozen=True, slots=True)
class _AnswerDraft:
    content: str
    grounding_status: GroundingStatus
    retrieved_chunk_count: int
    response_time_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    citations: tuple[object, ...] = ()


class GroundedAnswerService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        session_provider: async_sessionmaker[AsyncSession],
        hybrid_retrieval_service: HybridRetrievalService,
        llm_provider_factory: LLMProviderFactory,
        token_counter: TokenCounter | None = None,
        session_repository=chat_session_repository,
        message_repository=chat_message_repository,
        citation_repository=message_citation_repository,
        message_service: ChatMessageService | None = None,
        citation_validation_service: CitationValidationService | None = None,
        claim_validation_service: ClaimEvidenceValidationService | None = None,
        retrieval_reranker: RetrievalReranker | None = None,
        conversation_context_builder: ConversationContextBuilder | None = None,
        web_search_service: WebSearchService | None = None,
        web_search_intent_classifier: WebSearchIntentClassifier | None = None,
        close_llm_provider_after_generate: bool = True,
    ) -> None:
        self.settings = settings or get_settings()
        self.session_provider = session_provider
        self.hybrid_retrieval_service = hybrid_retrieval_service
        self.llm_provider_factory = llm_provider_factory
        self.close_llm_provider_after_generate = close_llm_provider_after_generate
        self.token_counter = token_counter or TiktokenTokenCounter(
            self.settings.tokenizer_encoding_name
        )
        self.session_repository = session_repository
        self.message_repository = message_repository
        self.citation_repository = citation_repository
        self.message_service = message_service or ChatMessageService(settings=self.settings)
        self.conversation_context_builder = (
            conversation_context_builder
            or ConversationContextBuilder(
                settings=self.settings,
                token_counter=self.token_counter,
                message_repository=self.message_repository,
            )
        )
        self.citation_validation_service = citation_validation_service or CitationValidationService(
            settings=self.settings,
            session_provider=session_provider,
        )
        self.claim_validation_service = claim_validation_service or ClaimEvidenceValidationService()
        self.retrieval_reranker = retrieval_reranker
        self.web_search_service = web_search_service
        self.web_search_intent_classifier = (
            web_search_intent_classifier or WebSearchIntentClassifier(settings=self.settings)
        )

    async def answer_question(
        self,
        *,
        current_user: User,
        session_id: UUID,
        question: str,
        audit_context: AuditContext | None = None,
    ) -> ChatAnswerResult:
        normalized_question = normalize_message_content(
            question,
            max_characters=self.settings.chat_message_max_characters,
        )
        async with self.session_provider() as session:
            chat_session = await self.session_repository.get_owned_by_id(
                session,
                session_id=session_id,
                owner_user_id=current_user.id,
            )
            if chat_session is None:
                raise ChatSessionNotFoundError()
            conversation_context = await self.conversation_context_builder.build(
                session,
                session_id=session_id,
                owner_user_id=current_user.id,
                current_question=normalized_question,
            )

        draft = await self._prepare_answer_draft(
            current_user=current_user,
            question=normalized_question,
            conversation_context=conversation_context,
        )
        return await self._persist_message_pair(
            current_user=current_user,
            session_id=session_id,
            question=normalized_question,
            draft=draft,
            audit_context=audit_context,
        )

    async def _prepare_answer_draft(
        self,
        *,
        current_user: User,
        question: str,
        conversation_context: ConversationContext,
    ) -> _AnswerDraft:
        grounding_question = conversation_context.resolved_question.standalone_question
        retrieval_hits = ()
        if _should_retrieve_internal_context(self.settings):
            try:
                retrieval_result = await self.hybrid_retrieval_service.retrieve(
                    query=grounding_question,
                    current_user=current_user,
                    top_k=_chat_retrieval_candidate_top_k(
                        settings=self.settings,
                        reranker=self.retrieval_reranker,
                    ),
                )
            except RetrievalError as exc:
                raise ChatRetrievalFailedError() from exc
            except Exception as exc:
                raise ChatRetrievalFailedError() from exc
            retrieval_hits = await self._prepare_prompt_retrieval_hits(
                retrieval_result.hits,
                question=grounding_question,
                current_user=current_user,
            )

        search_intent = self.web_search_intent_classifier.classify(
            question=grounding_question,
            internal_hit_count=len(retrieval_hits),
        )
        if not search_intent.use_internal:
            retrieval_hits = ()
        web_results = (
            await self._search_web_for_prompt(question=grounding_question)
            if search_intent.needs_web
            else ()
        )

        system_prompt = build_grounding_system_prompt(
            no_answer_sentinel=self.settings.llm_no_answer_sentinel,
        )
        selected_context = select_context_for_prompt(
            hits=retrieval_hits,
            history_messages=(),
            web_results=web_results,
            conversation_history=None,
            question=grounding_question,
            system_prompt=system_prompt,
            token_counter=self.token_counter,
            max_tokens=self.settings.chat_context_max_tokens,
        )
        source_registry = build_prompt_source_registry(
            context_items=selected_context.items,
            max_sources=_prompt_source_limit(
                settings=self.settings,
                reranker=self.retrieval_reranker,
            ),
        )
        if self.settings.rag_diagnostics_enabled:
            _log_rag_diagnostics(
                question=grounding_question,
                source_registry=source_registry,
                selected_context_count=selected_context.selected_chunk_count,
            )
        if not source_registry.sources:
            if self.settings.rag_diagnostics_enabled:
                _log_no_answer_diagnostics(reason="no_selected_sources")
            return _no_answer_draft(self.settings.chat_no_answer_message)
        if _reason_evidence_is_missing(
            question=grounding_question,
            source_registry=source_registry,
        ):
            if self.settings.rag_diagnostics_enabled:
                _log_no_answer_diagnostics(reason="reason_evidence_missing")
            return _no_answer_draft(
                self.settings.chat_no_answer_message,
                selected_chunk_count=len(source_registry.sources),
            )
        structured_value_draft = await self._structured_value_answer_draft(
            question=grounding_question,
            source_registry=source_registry,
            current_user=current_user,
        )
        if structured_value_draft is not None:
            return structured_value_draft

        messages = build_grounded_prompt(
            question=grounding_question,
            context_items=selected_context.items,
            history_messages=(),
            no_answer_sentinel=self.settings.llm_no_answer_sentinel,
            source_registry=source_registry,
            conversation_history=None,
        )
        provider = None
        try:
            provider = self.llm_provider_factory()
            generation = await provider.generate(
                messages=messages,
                temperature=self.settings.llm_temperature,
                max_output_tokens=self.settings.llm_max_output_tokens,
            )
            try:
                draft = await self._draft_from_generation(
                    generation,
                    source_registry=source_registry,
                    current_user=current_user,
                )
                if draft.grounding_status == GroundingStatus.NO_ANSWER and _should_retry_no_answer(
                    question=grounding_question,
                    source_registry=source_registry,
                ):
                    retry_generation = await provider.generate(
                        messages=_no_answer_retry_messages(
                            messages,
                            no_answer_sentinel=self.settings.llm_no_answer_sentinel,
                            grounding_question=grounding_question,
                        ),
                        temperature=self.settings.llm_temperature,
                        max_output_tokens=self.settings.llm_max_output_tokens,
                    )
                    try:
                        retry_draft = await self._draft_from_generation_or_structured_repair(
                            retry_generation,
                            source_registry=source_registry,
                            current_user=current_user,
                            provider=provider,
                            messages=messages,
                            grounding_question=grounding_question,
                        )
                    except CitationValidationFailedApplicationError:
                        return _no_answer_draft(
                            self.settings.chat_no_answer_message,
                            selected_chunk_count=len(source_registry.sources),
                            response_time_ms=retry_generation.response_time_ms,
                            prompt_tokens=retry_generation.prompt_tokens,
                            completion_tokens=retry_generation.completion_tokens,
                        )
                    if _should_retry_incomplete_answer(
                        question=grounding_question,
                        answer=retry_draft.content,
                        source_registry=source_registry,
                    ):
                        return _no_answer_draft(
                            self.settings.chat_no_answer_message,
                            selected_chunk_count=len(source_registry.sources),
                            response_time_ms=retry_draft.response_time_ms,
                            prompt_tokens=retry_draft.prompt_tokens,
                            completion_tokens=retry_draft.completion_tokens,
                        )
                    return retry_draft
                if _should_retry_incomplete_answer(
                    question=grounding_question,
                    answer=draft.content,
                    source_registry=source_registry,
                ):
                    retry_generation = await provider.generate(
                        messages=_answer_quality_retry_messages(
                            messages,
                            no_answer_sentinel=self.settings.llm_no_answer_sentinel,
                            grounding_question=grounding_question,
                        ),
                        temperature=self.settings.llm_temperature,
                        max_output_tokens=self.settings.llm_max_output_tokens,
                    )
                    try:
                        retry_draft = await self._draft_from_generation_or_structured_repair(
                            retry_generation,
                            source_registry=source_registry,
                            current_user=current_user,
                            provider=provider,
                            messages=messages,
                            grounding_question=grounding_question,
                        )
                    except CitationValidationFailedApplicationError:
                        return _no_answer_draft(
                            self.settings.chat_no_answer_message,
                            selected_chunk_count=len(source_registry.sources),
                            response_time_ms=retry_generation.response_time_ms,
                            prompt_tokens=retry_generation.prompt_tokens,
                            completion_tokens=retry_generation.completion_tokens,
                        )
                    if _should_retry_incomplete_answer(
                        question=grounding_question,
                        answer=retry_draft.content,
                        source_registry=source_registry,
                    ):
                        repair_generation = await provider.generate(
                            messages=_answer_quality_repair_messages(
                                messages,
                                no_answer_sentinel=self.settings.llm_no_answer_sentinel,
                                grounding_question=grounding_question,
                            ),
                            temperature=self.settings.llm_temperature,
                            max_output_tokens=self.settings.llm_max_output_tokens,
                        )
                        try:
                            final_draft = await self._draft_from_generation_or_structured_repair(
                                repair_generation,
                                source_registry=source_registry,
                                current_user=current_user,
                                provider=provider,
                                messages=messages,
                                grounding_question=grounding_question,
                            )
                        except CitationValidationFailedApplicationError:
                            return _no_answer_draft(
                                self.settings.chat_no_answer_message,
                                selected_chunk_count=len(source_registry.sources),
                                response_time_ms=repair_generation.response_time_ms,
                                prompt_tokens=repair_generation.prompt_tokens,
                                completion_tokens=repair_generation.completion_tokens,
                            )
                        if _should_retry_incomplete_answer(
                            question=grounding_question,
                            answer=final_draft.content,
                            source_registry=source_registry,
                        ):
                            return _no_answer_draft(
                                self.settings.chat_no_answer_message,
                                selected_chunk_count=len(source_registry.sources),
                                response_time_ms=final_draft.response_time_ms,
                                prompt_tokens=final_draft.prompt_tokens,
                                completion_tokens=final_draft.completion_tokens,
                            )
                        return final_draft
                    return retry_draft
                return draft
            except CitationValidationFailedApplicationError:
                retry_generation = await provider.generate(
                    messages=_structured_output_retry_messages(
                        messages,
                        no_answer_sentinel=self.settings.llm_no_answer_sentinel,
                        previous_output=generation.content,
                    ),
                    temperature=self.settings.llm_temperature,
                    max_output_tokens=self.settings.llm_max_output_tokens,
                )
                try:
                    retry_draft = await self._draft_from_generation(
                        retry_generation,
                        source_registry=source_registry,
                        current_user=current_user,
                    )
                except CitationValidationFailedApplicationError:
                    structured_repair_generation = await provider.generate(
                        messages=_structured_output_repair_messages(
                            messages,
                            no_answer_sentinel=self.settings.llm_no_answer_sentinel,
                            grounding_question=grounding_question,
                            previous_output=retry_generation.content,
                        ),
                        temperature=self.settings.llm_temperature,
                        max_output_tokens=self.settings.llm_max_output_tokens,
                    )
                    try:
                        retry_draft = await self._draft_from_generation(
                            structured_repair_generation,
                            source_registry=source_registry,
                            current_user=current_user,
                        )
                    except CitationValidationFailedApplicationError:
                        return _no_answer_draft(
                            self.settings.chat_no_answer_message,
                            selected_chunk_count=len(source_registry.sources),
                            response_time_ms=structured_repair_generation.response_time_ms,
                            prompt_tokens=structured_repair_generation.prompt_tokens,
                            completion_tokens=structured_repair_generation.completion_tokens,
                        )
                if (
                    retry_draft.grounding_status == GroundingStatus.NO_ANSWER
                    and _should_retry_no_answer(
                        question=grounding_question,
                        source_registry=source_registry,
                    )
                ):
                    no_answer_retry_generation = await provider.generate(
                        messages=_no_answer_retry_messages(
                            messages,
                            no_answer_sentinel=self.settings.llm_no_answer_sentinel,
                            grounding_question=grounding_question,
                        ),
                        temperature=self.settings.llm_temperature,
                        max_output_tokens=self.settings.llm_max_output_tokens,
                    )
                    try:
                        no_answer_retry_draft = (
                            await self._draft_from_generation_or_structured_repair(
                                no_answer_retry_generation,
                                source_registry=source_registry,
                                current_user=current_user,
                                provider=provider,
                                messages=messages,
                                grounding_question=grounding_question,
                            )
                        )
                    except CitationValidationFailedApplicationError:
                        return _no_answer_draft(
                            self.settings.chat_no_answer_message,
                            selected_chunk_count=len(source_registry.sources),
                            response_time_ms=no_answer_retry_generation.response_time_ms,
                            prompt_tokens=no_answer_retry_generation.prompt_tokens,
                            completion_tokens=no_answer_retry_generation.completion_tokens,
                        )
                    if _should_retry_incomplete_answer(
                        question=grounding_question,
                        answer=no_answer_retry_draft.content,
                        source_registry=source_registry,
                    ):
                        return _no_answer_draft(
                            self.settings.chat_no_answer_message,
                            selected_chunk_count=len(source_registry.sources),
                            response_time_ms=no_answer_retry_draft.response_time_ms,
                            prompt_tokens=no_answer_retry_draft.prompt_tokens,
                            completion_tokens=no_answer_retry_draft.completion_tokens,
                        )
                    return no_answer_retry_draft
                if _should_retry_incomplete_answer(
                    question=grounding_question,
                    answer=retry_draft.content,
                    source_registry=source_registry,
                ):
                    quality_retry_generation = await provider.generate(
                        messages=_answer_quality_retry_messages(
                            messages,
                            no_answer_sentinel=self.settings.llm_no_answer_sentinel,
                            grounding_question=grounding_question,
                        ),
                        temperature=self.settings.llm_temperature,
                        max_output_tokens=self.settings.llm_max_output_tokens,
                    )
                    try:
                        quality_retry_draft = (
                            await self._draft_from_generation_or_structured_repair(
                                quality_retry_generation,
                                source_registry=source_registry,
                                current_user=current_user,
                                provider=provider,
                                messages=messages,
                                grounding_question=grounding_question,
                            )
                        )
                    except CitationValidationFailedApplicationError:
                        return _no_answer_draft(
                            self.settings.chat_no_answer_message,
                            selected_chunk_count=len(source_registry.sources),
                            response_time_ms=quality_retry_generation.response_time_ms,
                            prompt_tokens=quality_retry_generation.prompt_tokens,
                            completion_tokens=quality_retry_generation.completion_tokens,
                        )
                    if _should_retry_incomplete_answer(
                        question=grounding_question,
                        answer=quality_retry_draft.content,
                        source_registry=source_registry,
                    ):
                        return _no_answer_draft(
                            self.settings.chat_no_answer_message,
                            selected_chunk_count=len(source_registry.sources),
                            response_time_ms=quality_retry_draft.response_time_ms,
                            prompt_tokens=quality_retry_draft.prompt_tokens,
                            completion_tokens=quality_retry_draft.completion_tokens,
                        )
                    return quality_retry_draft
                return retry_draft
        except LLMError as exc:
            raise _map_llm_error(exc) from exc
        except ApplicationError:
            raise
        except Exception as exc:
            raise LLMGenerationFailedApplicationError() from exc
        finally:
            close_provider = getattr(provider, "aclose", None)
            if self.close_llm_provider_after_generate and close_provider is not None:
                await close_provider()

    async def _structured_value_answer_draft(
        self,
        *,
        question: str,
        source_registry: PromptSourceRegistry,
        current_user: User,
    ) -> _AnswerDraft | None:
        generation = _structured_value_repair_generation(
            question=question,
            source_registry=source_registry,
        )
        if generation is None:
            return None
        try:
            return await self._draft_from_generation(
                generation,
                source_registry=source_registry,
                current_user=current_user,
            )
        except CitationValidationFailedApplicationError:
            return None

    async def _draft_from_generation_or_structured_repair(
        self,
        generation: LLMGenerationResult,
        *,
        source_registry: PromptSourceRegistry,
        current_user: User,
        provider: LLMProvider,
        messages: tuple[LLMMessage, ...],
        grounding_question: str,
    ) -> _AnswerDraft:
        try:
            return await self._draft_from_generation(
                generation,
                source_registry=source_registry,
                current_user=current_user,
            )
        except CitationValidationFailedApplicationError:
            repair_generation = await provider.generate(
                messages=_answer_quality_repair_messages(
                    messages,
                    no_answer_sentinel=self.settings.llm_no_answer_sentinel,
                    grounding_question=grounding_question,
                ),
                temperature=self.settings.llm_temperature,
                max_output_tokens=self.settings.llm_max_output_tokens,
            )
            return await self._draft_from_generation(
                repair_generation,
                source_registry=source_registry,
                current_user=current_user,
            )

    async def _prepare_prompt_retrieval_hits(
        self,
        hits: tuple[HybridRetrievalHit, ...],
        *,
        question: str,
        current_user: User,
    ) -> tuple[HybridRetrievalHit, ...]:
        candidate_hits = await self._supplement_role_person_retrieval_hits(
            hits,
            question=question,
            current_user=current_user,
        )
        reranked_hits = candidate_hits
        if self.settings.reranker_enabled and self.retrieval_reranker is not None:
            try:
                reranked_hits = await self.retrieval_reranker.rerank(
                    query=question,
                    hits=candidate_hits,
                    top_k=min(self.settings.reranker_top_k, max(len(candidate_hits), 1)),
                )
            except Exception as exc:
                logger.warning(
                    "Retrieval reranking failed; using prompt ranking fallback.",
                    extra={"error_type": exc.__class__.__name__},
                )
        prompt_pool_hits = _merge_retrieval_hits(reranked_hits, candidate_hits)
        expanded_hits = await self._expand_adjacent_retrieval_hits(
            prompt_pool_hits,
            current_user=current_user,
        )
        ranked_hits = _rank_hits_for_prompt(expanded_hits, question=question)
        if self.settings.reranker_enabled and self.retrieval_reranker is not None:
            if _named_document_title_terms(question):
                return ranked_hits
            return _preserve_reranked_hit_order(reranked_hits, ranked_hits)
        return ranked_hits

    async def _supplement_role_person_retrieval_hits(
        self,
        hits: tuple[HybridRetrievalHit, ...],
        *,
        question: str,
        current_user: User,
    ) -> tuple[HybridRetrievalHit, ...]:
        analysis = analyze_question(question)
        if not analysis.asks_for_person:
            return hits
        role_terms = _role_terms_for_prompt_question(question)
        if not role_terms:
            return hits
        if any(_person_name_sequences_near_terms(hit.text, role_terms) for hit in hits):
            return hits

        raw_role_terms = tuple(dict.fromkeys(_QUESTION_ACRONYM_PATTERN.findall(question)))
        if not raw_role_terms:
            return hits
        conditions = tuple(
            DocumentChunk.text.ilike(_like_contains_pattern(term), escape="\\")
            for term in raw_role_terms
        )
        if not conditions:
            return hits

        existing_chunk_ids = {hit.chunk_id for hit in hits}
        supplements: list[HybridRetrievalHit] = []
        async with self.session_provider() as session:
            execute = getattr(session, "execute", None)
            if execute is None:
                return hits
            rows = await execute(
                select(DocumentChunk, Document)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(
                    Document.status == DocumentStatus.READY,
                    build_accessible_document_filter(current_user),
                    or_(*conditions),
                )
                .order_by(Document.created_at.desc(), DocumentChunk.chunk_index.asc())
                .limit(_ROLE_PERSON_SUPPLEMENT_LIMIT)
            )
        for chunk, document in rows.all():
            if chunk.id in existing_chunk_ids:
                continue
            hit = _role_person_hit_from_chunk(chunk=chunk, document=document)
            if not _person_name_sequences_near_terms(hit.text, role_terms):
                continue
            supplements.append(hit)
            existing_chunk_ids.add(chunk.id)
        if not supplements:
            return hits
        return (*hits, *tuple(supplements))

    async def _expand_adjacent_retrieval_hits(
        self,
        hits: tuple[HybridRetrievalHit, ...],
        *,
        current_user: User,
    ) -> tuple[HybridRetrievalHit, ...]:
        if not hits:
            return hits
        existing_keys = {(hit.document_id, hit.chunk_index) for hit in hits}
        parent_by_key: dict[tuple[UUID, int], HybridRetrievalHit] = {}
        for hit in hits:
            for adjacent_index in (
                hit.chunk_index - 2,
                hit.chunk_index - 1,
                hit.chunk_index + 1,
                hit.chunk_index + 2,
            ):
                if adjacent_index < 0:
                    continue
                key = (hit.document_id, adjacent_index)
                if key in existing_keys or key in parent_by_key:
                    continue
                parent_by_key[key] = hit
        if not parent_by_key:
            return hits

        conditions = tuple(
            and_(DocumentChunk.document_id == document_id, DocumentChunk.chunk_index == chunk_index)
            for document_id, chunk_index in parent_by_key
        )
        async with self.session_provider() as session:
            execute = getattr(session, "execute", None)
            if execute is None:
                return hits
            rows = await execute(
                select(DocumentChunk, Document)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(
                    Document.status == DocumentStatus.READY,
                    build_accessible_document_filter(current_user),
                    or_(*conditions),
                )
            )
        adjacent_by_key: dict[tuple[UUID, int], HybridRetrievalHit] = {}
        for chunk, document in rows.all():
            key = (chunk.document_id, chunk.chunk_index)
            parent = parent_by_key.get(key)
            if parent is None:
                continue
            adjacent_by_key[key] = _adjacent_hit_from_chunk(
                chunk=chunk,
                document=document,
                parent=parent,
            )

        merged_hits: list[HybridRetrievalHit] = []
        seen_chunk_ids: set[UUID] = set()
        for hit in hits:
            for offset in (2, 1):
                previous_key = (hit.document_id, hit.chunk_index - offset)
                previous = adjacent_by_key.get(previous_key)
                if previous is not None and previous.chunk_id not in seen_chunk_ids:
                    merged_hits.append(previous)
                    seen_chunk_ids.add(previous.chunk_id)
            if hit.chunk_id not in seen_chunk_ids:
                merged_hits.append(hit)
                seen_chunk_ids.add(hit.chunk_id)
            for offset in (1, 2):
                next_key = (hit.document_id, hit.chunk_index + offset)
                next_hit = adjacent_by_key.get(next_key)
                if next_hit is not None and next_hit.chunk_id not in seen_chunk_ids:
                    merged_hits.append(next_hit)
                    seen_chunk_ids.add(next_hit.chunk_id)
        return tuple(merged_hits)

    async def _search_web_for_prompt(self, *, question: str) -> tuple[WebSearchResult, ...]:
        if self.web_search_service is None:
            logger.warning(
                "Web search requested without a configured search service.",
                extra={"provider": self.settings.web_search_provider},
            )
            return ()
        try:
            results = await self.web_search_service.search(query=question)
        except WebSearchError as exc:
            logger.warning(
                "Web search failed during chat grounding.",
                extra={
                    "provider": self.settings.web_search_provider,
                    "error_code": exc.code.value,
                },
            )
            return ()
        except Exception:
            logger.exception(
                "Unexpected web search failure during chat grounding.",
                extra={"provider": self.settings.web_search_provider},
            )
            return ()
        return results.results

    async def _draft_from_generation(
        self,
        generation: LLMGenerationResult,
        *,
        source_registry: PromptSourceRegistry,
        current_user: User,
    ) -> _AnswerDraft:
        selected_chunk_count = len(source_registry.sources)
        raw_answer = generation.content.strip()
        if raw_answer == self.settings.llm_no_answer_sentinel:
            if self.settings.rag_diagnostics_enabled:
                _log_no_answer_diagnostics(reason="llm_no_answer_sentinel")
            return _no_answer_draft(
                self.settings.chat_no_answer_message,
                selected_chunk_count=selected_chunk_count,
                response_time_ms=generation.response_time_ms,
                prompt_tokens=generation.prompt_tokens,
                completion_tokens=generation.completion_tokens,
            )

        try:
            grounded_output = parse_grounded_llm_output(
                raw_answer,
                allowed_identifiers=_allowed_source_identifiers(source_registry),
            )
        except ValueError as exc:
            raise CitationValidationFailedApplicationError() from exc
        if grounded_output.answer.strip() == self.settings.llm_no_answer_sentinel:
            raise CitationValidationFailedApplicationError()
        if _is_no_answer_like_json_answer(grounded_output.answer):
            if self.settings.rag_diagnostics_enabled:
                _log_no_answer_diagnostics(reason="llm_no_answer_like_json")
            return _no_answer_draft(
                self.settings.chat_no_answer_message,
                selected_chunk_count=selected_chunk_count,
                response_time_ms=generation.response_time_ms,
                prompt_tokens=generation.prompt_tokens,
                completion_tokens=generation.completion_tokens,
            )
        if _is_placeholder_like_json_answer(grounded_output.answer):
            raise CitationValidationFailedApplicationError()

        answer = _canonical_answer_with_selected_markers(grounded_output)
        try:
            validated = await self.citation_validation_service.validate_and_map(
                answer=answer,
                source_registry=source_registry,
                current_user=current_user,
            )
        except CitationPermissionRevalidationError:
            if self.settings.rag_diagnostics_enabled:
                _log_no_answer_diagnostics(reason="citation_permission_revalidation_failed")
            return _no_answer_draft(
                self.settings.chat_no_answer_message,
                selected_chunk_count=selected_chunk_count,
                response_time_ms=generation.response_time_ms,
                prompt_tokens=generation.prompt_tokens,
                completion_tokens=generation.completion_tokens,
            )
        except CitationValidationError as exc:
            raise CitationValidationFailedApplicationError() from exc
        except CitationMappingError as exc:
            raise CitationMappingFailedApplicationError() from exc
        if not validated.citations:
            raise CitationValidationFailedApplicationError()
        if self.settings.claim_validation_enabled:
            claim_validation = await self.claim_validation_service.validate(
                answer=grounded_output.answer,
                source_registry=source_registry,
                cited_source_labels=tuple(grounded_output.citations),
            )
            if self.settings.rag_diagnostics_enabled:
                _log_claim_validation_diagnostics(status=claim_validation.status)
            if claim_validation.status != ClaimEvidenceStatus.SUPPORTED:
                if self.settings.rag_diagnostics_enabled:
                    _log_no_answer_diagnostics(
                        reason=f"claim_validation_{claim_validation.status.value.lower()}",
                    )
                raise CitationValidationFailedApplicationError()
        return _AnswerDraft(
            content=validated.answer,
            grounding_status=GroundingStatus.ANSWERED,
            retrieved_chunk_count=selected_chunk_count,
            response_time_ms=generation.response_time_ms,
            prompt_tokens=generation.prompt_tokens,
            completion_tokens=generation.completion_tokens,
            citations=validated.citations,
        )

    async def _persist_message_pair(
        self,
        *,
        current_user: User,
        session_id: UUID,
        question: str,
        draft: _AnswerDraft,
        audit_context: AuditContext | None = None,
    ) -> ChatAnswerResult:
        user_created_at = datetime.now(UTC)
        assistant_created_at = user_created_at + timedelta(microseconds=1)
        async with self.session_provider() as session:
            try:
                chat_session = await self.session_repository.get_owned_by_id_for_update(
                    session,
                    session_id=session_id,
                    owner_user_id=current_user.id,
                )
                if chat_session is None:
                    raise ChatSessionNotFoundError()
                user_message = await self.message_service.append_message(
                    session,
                    chat_session=chat_session,
                    role=ChatMessageRole.USER,
                    content=question,
                    retrieval_query=None,
                    response_time_ms=None,
                    prompt_tokens=None,
                    completion_tokens=None,
                    created_at=user_created_at,
                )
                assistant_message = await self.message_service.append_message(
                    session,
                    chat_session=chat_session,
                    role=ChatMessageRole.ASSISTANT,
                    content=draft.content,
                    retrieval_query=question,
                    response_time_ms=draft.response_time_ms,
                    prompt_tokens=draft.prompt_tokens,
                    completion_tokens=draft.completion_tokens,
                    created_at=assistant_created_at,
                )
                flush = getattr(session, "flush", None)
                if flush is not None:
                    await flush()
                if draft.citations:
                    try:
                        await self.citation_repository.create_many(
                            session,
                            assistant_message=assistant_message,
                            citations=draft.citations,
                        )
                    except ValueError as exc:
                        raise CitationPersistenceFailedApplicationError() from exc
                await self.session_repository.touch_updated_at(
                    chat_session,
                    updated_at=assistant_created_at,
                )
                await self._record_chat_audit_events(
                    session,
                    current_user=current_user,
                    user_message=user_message,
                    assistant_message=assistant_message,
                    draft=draft,
                    audit_context=audit_context,
                )
                await session.commit()
            except ApplicationError:
                await session.rollback()
                raise
            except SQLAlchemyError as exc:
                await session.rollback()
                raise InternalServerError() from exc
            except Exception as exc:
                await session.rollback()
                raise InternalServerError() from exc
        return ChatAnswerResult(
            session_id=session_id,
            user_message=_detach_message(user_message),
            assistant_message=_detach_message(assistant_message),
            grounding_status=draft.grounding_status,
            retrieved_chunk_count=draft.retrieved_chunk_count,
            assistant_citations=draft.citations,
        )

    async def _record_chat_audit_events(
        self,
        session: AsyncSession,
        *,
        current_user: User,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
        draft: _AnswerDraft,
        audit_context: AuditContext | None,
    ) -> None:
        audit_service = AuditService(session, settings=self.settings)
        grounding_status = draft.grounding_status.value
        await audit_service.record_success(
            actor_user_id=current_user.id,
            event_type=AuditEventType.CHAT_QUESTION_SUBMITTED,
            target_type=AuditTargetType.CHAT_MESSAGE,
            target_id=user_message.id,
            context=audit_context,
            metadata={"grounding_status": grounding_status},
        )
        answer_event_type = (
            AuditEventType.CHAT_ANSWER_GENERATED
            if draft.grounding_status == GroundingStatus.ANSWERED
            else AuditEventType.CHAT_NO_ANSWER_GENERATED
        )
        await audit_service.record_success(
            actor_user_id=current_user.id,
            event_type=answer_event_type,
            target_type=AuditTargetType.CHAT_MESSAGE,
            target_id=assistant_message.id,
            context=audit_context,
            metadata={
                "grounding_status": grounding_status,
                "citation_count": len(draft.citations),
            },
        )


def _structured_output_retry_messages(
    messages: tuple[LLMMessage, ...],
    *,
    no_answer_sentinel: str,
    previous_output: str | None = None,
) -> tuple[LLMMessage, ...]:
    previous_output_block = _format_previous_invalid_output(previous_output)
    retry_instruction = LLMMessage(
        role="user",
        content=(
            "Your previous output was invalid. Return only one of these two valid forms: "
            f"the exact string {no_answer_sentinel}, or one JSON object with keys "
            '"answer" and "citations". '
            "Use only SOURCE_n identifiers shown in Retrieved Context. The citations value "
            "must be an array of quoted string identifiers, not objects. For numeric "
            "answers, "
            "include the unit or noun attached to the number in Retrieved Context. Do not output "
            "markdown, bare citations, bracketed citations inside answer, explanations, "
            "or any text outside the JSON object. For all/every yes/no questions, if "
            "Retrieved Context contains a category list with multiple number-unit values, "
            "answer no and include every value with its matching condition; a bare "
            "Khong is invalid. Do not use the previous invalid output as "
            "evidence; use it only to repair formatting. If it contains a source-supported "
            "answer, convert it to valid JSON and put citation identifiers only in the "
            "citations array. If Retrieved Context directly corrects a false premise or "
            "states a product/tool role, purpose, description, function, or responsibility, "
            "answer with JSON instead of returning the no-answer sentinel.\n\n"
            f"{previous_output_block}"
        ),
    )
    return (*messages, retry_instruction)


def _structured_output_repair_messages(
    messages: tuple[LLMMessage, ...],
    *,
    no_answer_sentinel: str,
    grounding_question: str,
    previous_output: str | None = None,
) -> tuple[LLMMessage, ...]:
    previous_output_block = _format_previous_invalid_output(previous_output)
    repair_instruction = LLMMessage(
        role="user",
        content=(
            "Your previous JSON or output was still invalid. Return only valid JSON or "
            f"the exact string {no_answer_sentinel}. Put citation identifiers only in "
            "the citations array as quoted string identifiers, never objects. The "
            "answer string must not contain SOURCE_n, [SOURCE_n], "
            "[1], placeholder text, or schema descriptions. Return one JSON object with "
            'keys "answer" and "citations". Use only SOURCE_n identifiers shown in '
            "Retrieved Context. For all/every yes/no questions, if Retrieved Context "
            "contains a category list with multiple number-unit values, answer no and "
            "include every value with its matching condition; a bare Khong is invalid. "
            "Do not use background knowledge or the previous invalid "
            "output as evidence. If the previous invalid output contains a source-supported "
            "answer, convert it to the required JSON shape and choose citations from "
            "Retrieved Context. If a SOURCE_n directly corrects a false premise or states "
            "a product/tool role, purpose, description, function, or responsibility, answer "
            "with that correction or purpose using JSON.\n\n"
            f"{previous_output_block}"
            "Resolved grounding question:\n"
            f"{grounding_question}"
        ),
    )
    return (*messages, repair_instruction)


def _format_previous_invalid_output(previous_output: str | None) -> str:
    if not previous_output:
        return ""
    collapsed = " ".join(previous_output.split())[:800]
    if not collapsed:
        return ""
    return f"Previous invalid output, not evidence:\n{collapsed}\n\n"


def _answer_quality_retry_messages(
    messages: tuple[LLMMessage, ...],
    *,
    no_answer_sentinel: str,
    grounding_question: str,
) -> tuple[LLMMessage, ...]:
    instruction = (
        "The previous answer used retrieved citations but was incomplete. Complete it using only "
        "the displayed Retrieved Context. Return exactly one JSON object with keys "
        "answer and citations. "
        f"Return exactly {no_answer_sentinel} only if no displayed source directly "
        "supports the required values. The citations "
        "value must be an array of quoted SOURCE_n string identifiers, not objects. Do not put "
        "SOURCE_n, [SOURCE_n], or [1] inside the answer string. For yes/no questions, start "
        "with Co, Khong, Yes, or No and then include the source-stated correction. Do not answer "
        "only Co, Khong, Yes, or No. If the question asks whether everyone/all/"
        "every/moi/tat ca/deu "
        "share one value and Retrieved Context has bullet rows starting with number-unit values, "
        "copy every bullet row fact into the answer. Do not omit rows and do not merge rows into "
        "a range. For role/person false-premise questions, state the source-stated "
        "person or entity "
        "assigned to the requested role. For change questions, include the condition "
        "number and the "
        "source-stated increase, decrease, addition, reduction, adjustment, or extra amount."
    )
    return _focused_retry_messages(
        messages,
        no_answer_sentinel=no_answer_sentinel,
        grounding_question=grounding_question,
        instruction=instruction,
    )


def _answer_quality_repair_messages(
    messages: tuple[LLMMessage, ...],
    *,
    no_answer_sentinel: str,
    grounding_question: str,
) -> tuple[LLMMessage, ...]:
    instruction = (
        "The previous answer was still incomplete. Complete it from the displayed "
        "Retrieved Context. It is invalid unless it includes the exact "
        "source-stated values needed by the resolved question. Return "
        "exactly one JSON object with keys answer and citations. The citations value must be an "
        "array of quoted SOURCE_n string identifiers, not objects. Do not put source "
        "markers inside "
        "the answer string. For yes/no questions, start with Co, Khong, Yes, or "
        "No and then include "
        "the correction. If the question asks whether everyone/all/every/moi/tat ca/deu share one "
        "value and Retrieved Context has bullet rows starting with number-unit values, copy every "
        "bullet row fact into the answer. Do not omit rows and do not merge rows into a range. For "
        "who/person questions, copy the person or entity name assigned to the requested role. For "
        "change questions, copy the condition number, change direction, and changed amount/unit. "
        "If no source directly supports those required values, return exactly "
        f"{no_answer_sentinel}."
    )
    return _focused_retry_messages(
        messages,
        no_answer_sentinel=no_answer_sentinel,
        grounding_question=grounding_question,
        instruction=instruction,
    )


def _focused_retry_messages(
    messages: tuple[LLMMessage, ...],
    *,
    no_answer_sentinel: str,
    grounding_question: str,
    instruction: str,
) -> tuple[LLMMessage, ...]:
    context = _retrieved_context_from_messages(messages)
    requirements = _focused_retry_requirements(
        context=context,
        grounding_question=grounding_question,
    )
    if requirements:
        no_answer_rule = (
            "The completion requirements below were extracted from Retrieved Context. "
            "They are displayed source facts, so return JSON and do not return "
            f"{no_answer_sentinel}. "
            "A bare yes/no polarity is invalid."
        )
    else:
        no_answer_rule = (
            f"Return exactly {no_answer_sentinel} only when no displayed source directly "
            "supports the required values."
        )
    system = LLMMessage(
        role="system",
        content=(
            "You are an internal enterprise knowledge assistant. Use only Retrieved Context "
            "as evidence. Do not use conversation history or background knowledge. "
            f"{no_answer_rule}"
        ),
    )
    user = LLMMessage(
        role="user",
        content=(
            "Retrieved Context:\n"
            f"{context}\n\n"
            "Resolved question:\n"
            f"{grounding_question}\n\n"
            f"{requirements}"
            f"{instruction}"
        ),
    )
    return (system, user)


def _focused_retry_requirements(*, context: str, grounding_question: str) -> str:
    requirements: list[str] = []
    number_rows = tuple(
        dict.fromkeys(
            match.group(1).strip()
            for match in re.finditer(
                r"(?m)^-\s*((\d+\s*(?:\([^)]{1,80}\)\s*)?[^\W\d_]+)[^\n]*)",
                context,
            )
        )
    )
    if len(number_rows) >= 2:
        number_units = tuple(
            dict.fromkeys(
                match.group(1).strip()
                for row in number_rows
                if (match := re.match(r"(\d+\s*(?:\([^)]{1,80}\)\s*)?[^\W\d_]+)", row))
            )
        )
        example_answer = "; ".join(number_rows[:4])
        requirements.append(
            "Source-derived completion requirements:\n"
            "- Include every source row value and condition in the answer: "
            + " | ".join(number_rows[:4])
            + ".\n"
            "- Required number-unit strings that must appear exactly: "
            + "; ".join(number_units[:4])
            + ".\n"
            "- JSON shape to fill, using only displayed source rows and real source identifiers: "
            + '{"answer":"Khong. '
            + example_answer
            + '","citations":["SOURCE_n"]}. Replace SOURCE_n with the supporting '
            + "SOURCE identifier from Retrieved Context.\n"
        )
    if _question_mentions_change(grounding_question):
        change_requirement = _focused_change_retry_requirement(
            context=context,
            grounding_question=grounding_question,
        )
        if change_requirement:
            requirements.append(change_requirement)
    role_terms = tuple(_QUESTION_ACRONYM_PATTERN.findall(grounding_question))
    if role_terms:
        role_names = _person_name_sequences_near_terms(context, role_terms)
        if role_names:
            role_name = role_names[0]
            role_label = ", ".join(role_terms)
            if _is_yes_no_question(grounding_question):
                answer_shape = (
                    '{"answer":"Khong. '
                    + role_label
                    + " la "
                    + role_name
                    + ', khong phai nguoi duoc hoi.","citations":["SOURCE_n"]}'
                )
            else:
                answer_shape = (
                    '{"answer":"' + role_label + " la " + role_name + '.","citations":["SOURCE_n"]}'
                )
            requirements.append(
                "Source-derived completion requirements:\n"
                "- Include the source role-holder name for the requested role "
                + role_label
                + ": "
                + role_name
                + ".\n"
                "- JSON shape to fill, using only the displayed role record and real "
                "source identifiers: "
                + answer_shape
                + ". Replace SOURCE_n with the supporting SOURCE identifier from "
                + "Retrieved Context.\n"
            )
    if not requirements:
        return ""
    return "".join(requirements) + "\n"


def _focused_change_retry_requirement(*, context: str, grounding_question: str) -> str:
    folded_context_lines = tuple(_fold_for_person_match(line) for line in context.splitlines())
    source_lines = tuple(line.strip() for line in context.splitlines())
    cue_indexes: list[int] = []
    for index, folded_line in enumerate(folded_context_lines):
        if any(_fold_for_person_match(cue) in folded_line for cue in _CHANGE_EVIDENCE_CUES):
            cue_indexes.append(index)
    if not cue_indexes:
        return ""
    _, question_terms, _ = _prompt_query_needles(grounding_question)
    best_rule = ""
    best_score = -1
    for index in cue_indexes:
        selected = _change_rule_lines_around(
            source_lines=source_lines,
            folded_lines=folded_context_lines,
            index=index,
            question_terms=question_terms,
        )
        rule = " ".join(selected)
        folded_rule = _fold_for_person_match(rule)
        score = sum(1 for term in question_terms if term in folded_rule)
        score += 8 if _NUMBER_UNIT_PATTERN.search(folded_rule) else 0
        if score > best_score:
            best_rule = rule
            best_score = score
    if not best_rule:
        return ""
    folded_rule = _fold_for_person_match(best_rule)
    required_pairs = tuple(
        dict.fromkeys(
            f"{number} {unit}"
            for number, unit, _, _ in _source_number_unit_pair_spans(folded_rule)
            if unit not in {"thang", "month", "months"}
        )
    )
    required_text = "; ".join(required_pairs[:3])
    skeleton_answer = best_rule.replace('"', "'")[:260]
    return (
        "Source-derived completion requirements:\n"
        "- Use this source change rule, not adjacent table rows: "
        + best_rule
        + ".\n"
        + (
            "- Required change amount string(s) that must appear in the answer: "
            + required_text
            + ".\n"
            if required_text
            else ""
        )
        + "- JSON shape to fill, using only the displayed change rule and real source identifiers: "
        + '{"answer":"'
        + skeleton_answer
        + '","citations":["SOURCE_n"]}. Replace SOURCE_n with the supporting '
        + "SOURCE identifier from Retrieved Context.\n"
    )


def _change_rule_lines_around(
    *,
    source_lines: tuple[str, ...],
    folded_lines: tuple[str, ...],
    index: int,
    question_terms: tuple[str, ...],
) -> list[str]:
    selected_indexes: list[int] = []
    for line_index in range(max(0, index - 1), min(len(source_lines), index + 3)):
        line = source_lines[line_index]
        if not _is_change_rule_line_candidate(line):
            continue
        folded_line = folded_lines[line_index]
        has_change = any(
            _fold_for_person_match(cue) in folded_line for cue in _CHANGE_EVIDENCE_CUES
        )
        has_question_term = any(term in folded_line for term in question_terms)
        has_number_unit = _NUMBER_UNIT_PATTERN.search(folded_line) is not None
        is_current = line_index == index
        if is_current or has_change or (has_question_term and has_number_unit):
            selected_indexes.append(line_index)
            continue
        if selected_indexes and has_number_unit:
            selected_indexes.append(line_index)
    return [source_lines[line_index] for line_index in selected_indexes]


def _is_change_rule_line_candidate(line: str) -> bool:
    if not line:
        return False
    if (
        line.startswith("--- SOURCE_")
        or line.startswith("Document title:")
        or line.startswith("Page:")
    ):
        return False
    if line == "Content:":
        return False
    folded_line = _fold_for_person_match(line)
    metadata_cues = (
        "tai lieu mau",
        "trang ",
        "chinh sach nghi cua nguoi lao dong",
        "hr-pol",
        "internal",
    )
    return not any(cue in folded_line for cue in metadata_cues)


def _retrieved_context_from_messages(messages: tuple[LLMMessage, ...]) -> str:
    if len(messages) < 2:
        return "<retrieved_context>\n</retrieved_context>"
    content = messages[1].content
    start = content.find("<retrieved_context>")
    end = content.find("</retrieved_context>")
    if start < 0 or end < start:
        return "<retrieved_context>\n</retrieved_context>"
    end += len("</retrieved_context>")
    return content[start:end]


def _no_answer_retry_messages(
    messages: tuple[LLMMessage, ...],
    *,
    no_answer_sentinel: str,
    grounding_question: str,
) -> tuple[LLMMessage, ...]:
    retry_instruction = LLMMessage(
        role="user",
        content=(
            f"Your previous output was {no_answer_sentinel}. Re-check Retrieved Context. "
            "If no SOURCE_n directly supports the resolved grounding question below, "
            f"return the exact string {no_answer_sentinel}. If Retrieved Context directly "
            "supports an answer, return only one JSON object with keys "
            '"answer" and "citations". '
            "For yes/no questions, start with Co, Khong, Yes, or No and include "
            "the supported correction; never answer only Co, Khong, Yes, or No. "
            "when the premise is false; a false premise is not a reason for no-answer when "
            "Retrieved Context states the correction. If a question asks whether all/every "
            "items share one value and SOURCE_n lists different categories, conditions, or "
            "values, answer no and summarize those source-stated distinctions. For product, "
            "tool, purpose, function, or usage questions, a SOURCE_n that names the item and "
            "states its role, vai tro, description, mo ta, function, purpose, or "
            "responsibility directly supports an answer even if it does not use the user's "
            "exact wording. For questions asking how a "
            "value changes under "
            "a stated condition, a retrieved rule that states an increase, decrease, "
            "addition, reduction, adjustment, or extra amount is direct support for "
            "answering that change. Use only SOURCE_n identifiers shown in Retrieved "
            "Context and do not use background knowledge.\n\n"
            "Resolved grounding question:\n"
            f"{grounding_question}"
        ),
    )
    return (*messages, retry_instruction)


def _reason_evidence_is_missing(
    *,
    question: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    if _named_entity_evidence_is_missing(question=question, source_registry=source_registry):
        return True
    folded_question = _fold_for_person_match(question).strip()
    folded_prefixes = tuple(_fold_for_person_match(prefix) for prefix in _REASON_QUESTION_PREFIXES)
    if not folded_question.startswith(folded_prefixes):
        return False
    source_text = _fold_for_person_match(
        "\n".join(f"{source.document_title}\n{source.text}" for source in source_registry.sources)
    )
    folded_cues = tuple(_fold_for_person_match(cue) for cue in _REASON_EVIDENCE_CUES)
    if not any(_contains_folded_phrase(source_text, cue) for cue in folded_cues):
        return True
    _, terms, _ = _prompt_query_needles(question)
    focus_terms = tuple(
        term
        for term in terms
        if term not in {"tai", "sao", "why", "chon", "lam", "ceo", "cto"}
        and len(term) >= _PROMPT_MIN_QUERY_TERM_CHARACTERS
    )
    if not focus_terms:
        return False
    for cue in folded_cues:
        start = 0
        while True:
            position = source_text.find(cue, start)
            if position < 0:
                break
            window = source_text[max(0, position - 220) : min(len(source_text), position + 220)]
            if any(term in window for term in focus_terms):
                return False
            start = position + len(cue)
    return True


def _named_entity_evidence_is_missing(
    *,
    question: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    if not _QUESTION_ACRONYM_PATTERN.search(question):
        return False
    if not (_is_person_lookup_question(question) or _is_yes_no_question(question)):
        return False
    entity_terms = _question_named_entity_terms(question)
    if not entity_terms:
        return False
    source_text = _fold_for_person_match(
        "\n".join(f"{source.document_title}\n{source.text}" for source in source_registry.sources)
    )
    return not all(_contains_folded_phrase(source_text, term) for term in entity_terms)


def _is_person_lookup_question(question: str) -> bool:
    folded_question = _fold_for_person_match(question).strip()
    return (
        " la ai" in folded_question
        or folded_question.endswith(" ai")
        or " who " in f" {folded_question} "
    )


def _question_named_entity_terms(question: str) -> tuple[str, ...]:
    terms: list[str] = []
    for match in _NAME_TOKEN_PATTERN.finditer(question):
        token = match.group(0)
        if token.isupper() or not token[:1].isupper():
            continue
        folded = _fold_for_person_match(token).strip("_ ")
        if folded in _NON_PERSON_NAME_TOKENS or folded in _PERSON_QUESTION_TERMS:
            continue
        if folded not in terms:
            terms.append(folded)
    return tuple(terms)


def _contains_folded_phrase(text: str, phrase: str) -> bool:
    if not phrase:
        return False
    pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
    return re.search(pattern, text) is not None


def _should_retry_incomplete_answer(
    *,
    question: str,
    answer: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    clean_answer = _strip_public_citation_markers(answer)
    if _is_placeholder_like_json_answer(clean_answer):
        return True
    if _yes_no_answer_missing_polarity(question=question, answer=clean_answer):
        return True
    if _yes_no_answer_missing_supported_correction(
        question=question,
        answer=clean_answer,
        source_registry=source_registry,
    ):
        return True
    if _limit_answer_missing_limit_cue(
        question=question,
        answer=clean_answer,
        source_registry=source_registry,
    ):
        return True
    if _multi_value_answer_missing_source_distinctions(
        question=question,
        answer=clean_answer,
        source_registry=source_registry,
    ):
        return True
    if _open_person_answer_has_negative_polarity(
        question=question,
        answer=clean_answer,
        source_registry=source_registry,
    ):
        return True
    if _person_answer_missing_source_name(
        question=question,
        answer=clean_answer,
        source_registry=source_registry,
    ):
        return True
    if _quantity_answer_missing_source_number(
        question=question,
        answer=clean_answer,
        source_registry=source_registry,
    ):
        return True
    if _time_answer_missing_source_time_range(
        question=question,
        answer=clean_answer,
        source_registry=source_registry,
    ):
        return True
    if _numeric_answer_missing_source_unit(
        answer=clean_answer,
        source_registry=source_registry,
    ):
        return True
    return _change_answer_missing_source_change(
        question=question,
        answer=clean_answer,
        source_registry=source_registry,
    )


def _yes_no_answer_missing_polarity(*, question: str, answer: str) -> bool:
    if not _is_yes_no_question(question):
        return False
    folded_answer = _fold_for_person_match(answer)
    return not any(_contains_folded_phrase(folded_answer, cue) for cue in _YES_NO_POLARITY_CUES)


def _is_yes_no_question(question: str) -> bool:
    folded_question = _fold_for_person_match(question).strip()
    if any(cue in folded_question for cue in ("co phai", "dung khong", "phai khong")):
        return True
    if folded_question.startswith(("is ", "are ", "do ", "does ")):
        return True
    return folded_question.endswith(" khong") or folded_question.endswith(" khong?")


def _yes_no_answer_missing_supported_correction(
    *,
    question: str,
    answer: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    if not _is_yes_no_question(question):
        return False
    role_terms = tuple(_QUESTION_ACRONYM_PATTERN.findall(question))
    if not role_terms:
        return False
    candidates = _source_person_name_candidates(
        question=question,
        source_registry=source_registry,
    )
    if not candidates:
        return False
    return not _answer_contains_source_person_name(answer, candidates)


def _limit_answer_missing_limit_cue(
    *,
    question: str,
    answer: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    folded_question = _fold_for_person_match(question)
    if not any(cue in folded_question for cue in _LIMIT_QUESTION_CUES):
        return False
    source_text = _fold_for_person_match(
        "\n".join(source.text for source in source_registry.sources)
    )
    if not any(cue in source_text for cue in _LIMIT_QUESTION_CUES):
        return False
    folded_answer = _fold_for_person_match(answer)
    if any(cue in folded_answer for cue in _LIMIT_ANSWER_CUES):
        return False
    pairs = _question_focused_source_number_unit_pairs(
        question=question,
        source_registry=source_registry,
    )
    return not any(
        _number_occurs_in_source(number, folded_answer) and unit in folded_answer
        for number, unit in pairs
    )


def _multi_value_answer_missing_source_distinctions(
    *,
    question: str,
    answer: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    if not _is_multi_value_yes_no_question(question):
        return False
    pairs = _multi_value_source_number_unit_pairs(
        question=question,
        source_registry=source_registry,
    )
    if len(pairs) < 2:
        return False
    folded_answer = _fold_for_person_match(answer)
    return not all(
        _number_occurs_in_source(number, folded_answer) and unit in folded_answer
        for number, unit in pairs[:4]
    )


def _is_multi_value_yes_no_question(question: str) -> bool:
    folded_question = _fold_for_person_match(question)
    if not _is_yes_no_question(question):
        return False
    return any(cue in folded_question for cue in ("moi", "tat ca", "deu", "all", "every"))


def _multi_value_source_number_unit_pairs(
    *,
    question: str,
    source_registry: PromptSourceRegistry,
) -> tuple[tuple[str, str], ...]:
    _, terms, _ = _prompt_query_needles(question)
    source_text = _fold_for_person_match(
        "\n".join(source.text for source in source_registry.sources[:1])
    )
    spans = _source_number_unit_pair_spans(source_text)
    if not spans:
        return ()
    question_units = {unit for _, unit, _, _ in spans if unit in terms}
    if question_units:
        spans = tuple(span for span in spans if span[1] in question_units)
    filtered_spans: list[tuple[str, str, int, int]] = []
    for number, unit, start, end in spans:
        window = source_text[max(0, start - 80) : min(len(source_text), end + 140)]
        if any(_fold_for_person_match(cue) in window for cue in _CHANGE_EVIDENCE_CUES):
            continue
        filtered_spans.append((number, unit, start, end))
    pairs: list[tuple[str, str]] = []
    for number, unit, _, _ in filtered_spans or list(spans):
        pair = (number, unit)
        if pair not in pairs:
            pairs.append(pair)
    return tuple(pairs)


def _open_person_answer_has_negative_polarity(
    *,
    question: str,
    answer: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    if _is_yes_no_question(question):
        return False
    _, terms, _ = _prompt_query_needles(question)
    if not (_asks_for_person(terms) or _QUESTION_ACRONYM_PATTERN.search(question)):
        return False
    candidates = _source_person_name_candidates(
        question=question,
        source_registry=source_registry,
    )
    if not candidates:
        return False
    folded_answer = _fold_for_person_match(answer).strip()
    return folded_answer.startswith(("khong", "no"))


def _person_answer_missing_source_name(
    *,
    question: str,
    answer: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    _, terms, _ = _prompt_query_needles(question)
    if not _asks_for_person(terms):
        return False
    candidates = _source_person_name_candidates(
        question=question,
        source_registry=source_registry,
    )
    if not candidates:
        return False
    return not _answer_contains_source_person_name(answer, candidates)


def _source_person_name_candidates(
    *,
    question: str,
    source_registry: PromptSourceRegistry,
) -> tuple[str, ...]:
    focus_terms = tuple(_QUESTION_ACRONYM_PATTERN.findall(question))
    if focus_terms:
        focused_candidates: list[str] = []
        for source in source_registry.sources:
            focused_candidates.extend(_person_name_sequences_near_terms(source.text, focus_terms))
        if focused_candidates:
            return tuple(dict.fromkeys(focused_candidates))
    candidates: list[str] = []
    for source in source_registry.sources:
        candidates.extend(_person_name_sequences(source.text))
    return tuple(dict.fromkeys(candidates))


def _person_name_sequences_near_terms(
    text: str,
    terms: tuple[str, ...],
) -> tuple[str, ...]:
    role_record_names = _role_record_names_for_terms(text, terms)
    if role_record_names:
        return role_record_names
    spans = _person_name_sequence_spans(text)
    if not spans:
        return ()
    folded_text = text.casefold()
    record_candidates: list[str] = []
    candidates_by_distance: dict[str, int] = {}
    for term in terms:
        folded_term = term.casefold()
        start = 0
        while True:
            position = folded_text.find(folded_term, start)
            if position < 0:
                break
            term_end = position + len(folded_term)
            record_candidate = _person_name_for_role_occurrence(
                text,
                spans=spans,
                term_start=position,
                term_end=term_end,
            )
            if record_candidate is not None:
                record_candidates.append(record_candidate)
            for candidate, candidate_start, candidate_end in spans:
                distance = _span_distance(
                    first_start=position,
                    first_end=term_end,
                    second_start=candidate_start,
                    second_end=candidate_end,
                )
                candidates_by_distance[candidate] = min(
                    distance,
                    candidates_by_distance.get(candidate, distance),
                )
            start = term_end
    if record_candidates:
        return tuple(dict.fromkeys(record_candidates))
    if not candidates_by_distance:
        return ()
    closest_distance = min(candidates_by_distance.values())
    return tuple(
        candidate
        for candidate, distance in candidates_by_distance.items()
        if distance == closest_distance
    )


def _role_record_names_for_terms(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    folded_terms = tuple(_fold_for_person_match(term) for term in terms)
    names: list[str] = []
    for line in text.splitlines():
        if " - " not in line:
            continue
        folded_line = _fold_for_person_match(line)
        if not any(_contains_folded_phrase(folded_line, term) for term in folded_terms):
            continue
        name_part = line.split(" - ", 1)[0]
        for name, _, _ in _person_name_sequence_spans(name_part):
            if name not in names:
                names.append(name)
    return tuple(names)


def _person_name_for_role_occurrence(
    text: str,
    *,
    spans: tuple[tuple[str, int, int], ...],
    term_start: int,
    term_end: int,
) -> str | None:
    line_start = text.rfind("\n", 0, term_start) + 1
    line_end = text.find("\n", term_end)
    if line_end < 0:
        line_end = len(text)

    same_line_following = tuple(
        (candidate, candidate_start)
        for candidate, candidate_start, _ in spans
        if term_end <= candidate_start <= line_end
        and candidate_start - term_end <= _ROLE_PERSON_ASSOCIATION_MAX_CHARS
    )
    if same_line_following:
        return min(same_line_following, key=lambda row: row[1])[0]

    same_line_preceding = tuple(
        (candidate, candidate_end)
        for candidate, _, candidate_end in spans
        if line_start <= candidate_end <= term_start
        and term_start - candidate_end <= _ROLE_PERSON_ASSOCIATION_MAX_CHARS
    )
    if same_line_preceding:
        return max(same_line_preceding, key=lambda row: row[1])[0]

    preceding = tuple(
        (candidate, candidate_end)
        for candidate, _, candidate_end in spans
        if candidate_end <= term_start
        and term_start - candidate_end <= _ROLE_PERSON_ASSOCIATION_MAX_CHARS
    )
    if preceding:
        return max(preceding, key=lambda row: row[1])[0]

    following = tuple(
        (candidate, candidate_start)
        for candidate, candidate_start, _ in spans
        if candidate_start >= term_end
        and candidate_start - term_end <= _ROLE_PERSON_ASSOCIATION_MAX_CHARS
    )
    if following:
        return min(following, key=lambda row: row[1])[0]
    return None


def _person_name_sequences(text: str) -> tuple[str, ...]:
    return tuple(sequence for sequence, _, _ in _person_name_sequence_spans(text))


def _person_name_sequence_spans(text: str) -> tuple[tuple[str, int, int], ...]:
    sequences: list[tuple[str, int, int]] = []
    current: list[str] = []
    current_start: int | None = None
    current_end = 0
    for match in _NAME_TOKEN_PATTERN.finditer(text):
        token = match.group(0)
        separator = text[current_end : match.start()] if current else ""
        if current and _has_name_sequence_separator(separator):
            if current_start is not None and _looks_like_person_name_sequence(current):
                sequences.append((" ".join(current), current_start, current_end))
            current = []
            current_start = None
            current_end = 0
        if _is_name_token_candidate(token):
            if not current:
                current_start = match.start()
            current.append(token)
            current_end = match.end()
            continue
        if current_start is not None and _looks_like_person_name_sequence(current):
            sequences.append((" ".join(current), current_start, current_end))
        current = []
        current_start = None
        current_end = 0
    if current_start is not None and _looks_like_person_name_sequence(current):
        sequences.append((" ".join(current), current_start, current_end))
    return tuple(sequences)


def _span_distance(
    *,
    first_start: int,
    first_end: int,
    second_start: int,
    second_end: int,
) -> int:
    if first_start <= second_end and second_start <= first_end:
        return 0
    return min(abs(first_start - second_end), abs(second_start - first_end))


def _has_name_sequence_separator(text: str) -> bool:
    return any(character in text for character in "-:;()[]{}|/")


def _looks_like_person_name_sequence(tokens: list[str]) -> bool:
    if len(tokens) < 3:
        return False
    folded_tokens = tuple(_fold_for_person_match(token).strip("_ ") for token in tokens)
    if any(token in _NON_PERSON_NAME_TOKENS for token in folded_tokens):
        return False
    if folded_tokens and folded_tokens[0] in _ORGANIZATION_NAME_START_TOKENS:
        return False
    organization_token_count = sum(
        1 for token in folded_tokens if token in _ORGANIZATION_NAME_TOKENS
    )
    return organization_token_count < 2


def _answer_contains_source_person_name(answer: str, candidates: tuple[str, ...]) -> bool:
    folded_answer = _fold_for_person_match(answer)
    return any(_fold_for_person_match(candidate) in folded_answer for candidate in candidates)


def _fold_for_person_match(text: str) -> str:
    normalized = unicodedata.normalize(
        "NFKD",
        text.casefold().replace("\u0111", "d").replace("\u0110", "d"),
    )
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _quantity_answer_missing_source_number(
    *,
    question: str,
    answer: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    if not _asks_for_quantity(question):
        return False
    pairs = _question_focused_source_number_unit_pairs(
        question=question,
        source_registry=source_registry,
    )
    if not pairs:
        return False
    folded_answer = _fold_for_person_match(answer)
    all_source_pairs = _source_number_unit_pairs(source_registry)
    if _question_has_negated_condition(question) and any(
        _number_occurs_in_source(number, folded_answer) and unit in folded_answer
        for number, unit in all_source_pairs
    ):
        return False
    return not any(
        _number_occurs_in_source(number, folded_answer) and unit in folded_answer
        for number, unit in pairs
    )


def _question_has_negated_condition(question: str) -> bool:
    folded_question = _fold_for_person_match(question)
    return any(
        cue in folded_question for cue in ("khong thuoc", "khong phai", "khong", "not ", "except")
    )


def _asks_for_quantity(question: str) -> bool:
    folded_question = _fold_for_person_match(question)
    return "bao nhieu" in folded_question or "how many" in folded_question


def _question_mentions_change(question: str) -> bool:
    folded_question = _fold_for_person_match(question)
    return any(_fold_for_person_match(cue) in folded_question for cue in _CHANGE_QUESTION_CUES)


def _time_answer_missing_source_time_range(
    *,
    question: str,
    answer: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    analysis = analyze_question(question)
    if not (analysis.asks_for_time_range or analysis.answer_type == "TIME"):
        return False
    required_ranges = _question_focused_source_time_ranges(
        question=question,
        source_registry=source_registry,
    )
    if not required_ranges:
        return False
    folded_answer = _fold_for_person_match(answer)
    return not any(
        _time_range_occurs_in_answer(time_range, folded_answer) for time_range in required_ranges
    )


def _question_focused_source_time_ranges(
    *,
    question: str,
    source_registry: PromptSourceRegistry,
) -> tuple[str, ...]:
    _, terms, _ = _prompt_query_needles(question)
    focus_terms = tuple(
        term
        for term in terms
        if len(term) >= 3
        and term not in _QUANTITY_STOP_TERMS
        and term not in {"cua", "theo", "chinh", "sach", "co", "duoc", "moi"}
    )
    ranges: list[str] = []
    source_text = _fold_for_person_match(
        "\n".join(source.text for source in source_registry.sources)
    )
    for match in _TIME_RANGE_VALUE_PATTERN.finditer(source_text):
        window = source_text[max(0, match.start() - 180) : min(len(source_text), match.end() + 180)]
        if focus_terms and not any(term in window for term in focus_terms):
            continue
        value = match.group(0)
        if value not in ranges:
            ranges.append(value)
    return tuple(ranges[:4])


def _time_range_occurs_in_answer(time_range: str, folded_answer: str) -> bool:
    clocks = tuple(match.group(0) for match in _CLOCK_VALUE_PATTERN.finditer(time_range))
    if not clocks:
        return time_range in folded_answer
    return all(clock in folded_answer for clock in clocks)


def _numeric_answer_missing_source_unit(
    *,
    answer: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    folded_answer = answer.casefold()
    for match in re.finditer(r"\d+", folded_answer):
        number = match.group(0)
        if _looks_like_year_number(number) or _number_match_is_time_or_date_component(
            folded_answer,
            match,
        ):
            continue
        units = _source_units_for_number(number, source_registry)
        if units and not any(unit in folded_answer for unit in units):
            return True
    return False


def _looks_like_year_number(number: str) -> bool:
    return bool(_YEAR_VALUE_PATTERN.fullmatch(number))


def _number_match_is_time_or_date_component(text: str, match: re.Match[str]) -> bool:
    start, end = match.span()
    before = text[start - 1 : start] if start > 0 else ""
    after = text[end : end + 1]
    return before in {":", "/", "h"} or after in {":", "/", "h"}


def _change_answer_missing_source_change(
    *,
    question: str,
    answer: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    folded_question = _fold_for_person_match(question)
    if not any(_fold_for_person_match(cue) in folded_question for cue in _CHANGE_QUESTION_CUES):
        return False
    source_text = _fold_for_person_match(
        "\n".join(source.text for source in source_registry.sources)
    )
    if not any(_fold_for_person_match(cue) in source_text for cue in _CHANGE_EVIDENCE_CUES):
        return False
    folded_answer = _fold_for_person_match(answer)
    _, terms, numbers = _prompt_query_needles(question)
    for number in numbers:
        if _number_occurs_with_question_unit(
            number,
            source_text,
            terms,
        ) and not _number_occurs_with_question_unit(
            number,
            folded_answer,
            terms,
        ):
            return True
    if not any(_fold_for_person_match(cue) in folded_answer for cue in _CHANGE_EVIDENCE_CUES):
        return True
    focused_pairs = _question_focused_source_number_unit_pairs(
        question=question,
        source_registry=source_registry,
    )
    if focused_pairs:
        return not any(
            _number_occurs_in_source(number, folded_answer) and unit in folded_answer
            for number, unit in focused_pairs
        )
    change_pairs = _source_change_amount_pairs(source_registry)
    if change_pairs:
        return not any(
            _number_occurs_in_source(number, folded_answer) and unit in folded_answer
            for number, unit in change_pairs
        )
    if not _source_units_for_any_number(source_registry):
        return False
    return not any(unit in folded_answer for unit in _source_units_for_any_number(source_registry))


def _question_focused_source_number_unit_pairs(
    *,
    question: str,
    source_registry: PromptSourceRegistry,
) -> tuple[tuple[str, str], ...]:
    if not source_registry.sources:
        return ()
    phrases, terms, _ = _prompt_query_needles(question)
    source_text = _fold_for_person_match(source_registry.sources[0].text)
    spans = _source_number_unit_pair_spans(source_text)
    if not spans:
        return ()
    question_units = {unit for _, unit, _, _ in spans if unit in terms}
    if question_units:
        spans = tuple(span for span in spans if span[1] in question_units)
    if not spans:
        return ()

    question_is_change = _question_mentions_change(question)
    negated_terms = _negated_question_terms(question=question, terms=terms)
    focused_terms = tuple(
        term
        for term in terms
        if term not in _QUANTITY_STOP_TERMS
        and term not in question_units
        and term not in negated_terms
    )
    scored: list[tuple[tuple[str, str], int, bool]] = []
    for number, unit, start, end in spans:
        window = source_text[max(0, start - 80) : min(len(source_text), end + 140)]
        score = sum(1 for term in focused_terms if term in window)
        score += sum(3 for phrase in phrases if phrase in window)
        if _number_span_followed_by_question_term(source_text, end=end, terms=terms):
            score += 40
        if negated_terms and all(term in window for term in negated_terms):
            score -= 8
        has_change_evidence = any(
            _fold_for_person_match(cue) in window for cue in _CHANGE_EVIDENCE_CUES
        )
        scored.append(((number, unit), score, has_change_evidence))
    if not question_is_change and any(not has_change for _, _, has_change in scored):
        scored = [row for row in scored if not row[2]]
    best_score = max(score for _, score, _ in scored)
    minimum_score = best_score - 2
    return tuple(dict.fromkeys(pair for pair, score, _ in scored if score >= minimum_score))


def _number_span_followed_by_question_term(
    source_text: str,
    *,
    end: int,
    terms: tuple[str, ...],
) -> bool:
    period_terms = {
        "ngay",
        "tuan",
        "thang",
        "nam",
        "day",
        "week",
        "month",
        "year",
    }
    relevant_terms = tuple(term for term in terms if term in period_terms)
    if not relevant_terms:
        return False
    tail = source_text[end : min(len(source_text), end + 32)]
    tail_before_next_number = re.split(r"\d", tail, maxsplit=1)[0]
    return any(
        f"/{term}" in tail_before_next_number or f" {term}" in tail_before_next_number
        for term in relevant_terms
    )


def _negated_question_terms(*, question: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    folded_question = _fold_for_person_match(question)
    tokens = [token.strip("_ ") for token in _PROMPT_QUERY_TERM_PATTERN.findall(folded_question)]
    negated: list[str] = []
    for index, token in enumerate(tokens):
        if token not in {"khong", "not", "without"}:
            continue
        window = tokens[index + 1 : index + 8]
        if "loai" in window:
            loai_index = window.index("loai")
            for term in window[loai_index + 1 : loai_index + 3]:
                if term in terms and term not in negated:
                    negated.append(term)
        if "dac" in window and "biet" in window:
            for term in ("dac", "biet"):
                if term in terms and term not in negated:
                    negated.append(term)
    return tuple(negated)


def _looks_like_section_number_span(text: str, *, start: int, end: int) -> bool:
    line_start = text.rfind("\n", 0, start) + 1
    prefix = text[line_start:start]
    suffix = text[end : min(len(text), end + 80)]
    marker_context = text[line_start : min(len(text), end + 24)]
    if re.match(r"\s*\d+(?:\.\d+)+\s+", marker_context) is None:
        return False
    return bool(prefix.strip() == "" or "." in prefix) and (
        "\n" in suffix or " muc " in suffix or " doi tuong " in suffix
    )


def _source_number_unit_pair_spans(text: str) -> tuple[tuple[str, str, int, int], ...]:
    pairs: list[tuple[str, str, int, int]] = []
    for match in _NUMBER_UNIT_PATTERN.finditer(text):
        if _looks_like_section_number_span(text, start=match.start(), end=match.end()):
            continue
        number = str(int(match.group(1)))
        unit = match.group(2).strip("_ ")
        if len(unit) >= 2:
            pairs.append((number, unit, match.start(), match.end()))
    return tuple(pairs)


def _source_number_unit_pairs(
    source_registry: PromptSourceRegistry,
) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    source_text = _fold_for_person_match(
        "\n".join(source.text for source in source_registry.sources)
    )
    for match in _NUMBER_UNIT_PATTERN.finditer(source_text):
        number = str(int(match.group(1)))
        unit = match.group(2).strip("_ ")
        pair = (number, unit)
        if len(unit) >= 2 and pair not in pairs:
            pairs.append(pair)
    return tuple(pairs)


def _source_change_amount_pairs(
    source_registry: PromptSourceRegistry,
) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for source in source_registry.sources:
        source_text = _fold_for_person_match(source.text)
        spans = _source_number_unit_pair_spans(source_text)
        if not spans:
            continue
        for cue in _CHANGE_EVIDENCE_CUES:
            folded_cue = _fold_for_person_match(cue)
            start = 0
            while True:
                cue_position = source_text.find(folded_cue, start)
                if cue_position < 0:
                    break
                for number, unit, span_start, _ in spans:
                    if span_start < cue_position:
                        continue
                    if span_start - cue_position > 180:
                        continue
                    pair = (number, unit)
                    if pair not in pairs:
                        pairs.append(pair)
                start = cue_position + len(folded_cue)
    return tuple(pairs)


def _source_units_for_any_number(source_registry: PromptSourceRegistry) -> tuple[str, ...]:
    units: list[str] = []
    source_text = "\n".join(source.text for source in source_registry.sources).casefold()
    for match in _NUMBER_UNIT_PATTERN.finditer(source_text):
        unit = match.group(2).strip("_ ")
        if len(unit) >= 2 and unit not in units:
            units.append(unit)
    return tuple(units)


def _source_units_for_number(
    number: str,
    source_registry: PromptSourceRegistry,
) -> tuple[str, ...]:
    if not number.isdecimal():
        return ()
    normalized = str(int(number))
    units: list[str] = []
    source_text = "\n".join(source.text for source in source_registry.sources).casefold()
    for match in _NUMBER_UNIT_PATTERN.finditer(source_text):
        if str(int(match.group(1))) != normalized:
            continue
        unit = match.group(2).strip("_ ")
        if len(unit) >= 2 and unit not in units:
            units.append(unit)
    return tuple(units)


def _contains_person_name_sequence(text: str) -> bool:
    return bool(_person_name_sequence_spans(text))


def _strip_public_citation_markers(answer: str) -> str:
    return _PUBLIC_CITATION_MARKER_PATTERN.sub(" ", answer)


def _should_retry_no_answer(
    *,
    question: str,
    source_registry: PromptSourceRegistry,
) -> bool:
    if not source_registry.sources:
        return False
    folded_question = _fold_for_person_match(question)
    if "tai sao" in folded_question or folded_question.strip().startswith("why "):
        return False
    phrases, terms, numbers = _prompt_query_needles(question)
    source_text = _fold_for_person_match(
        "\n".join(f"{source.document_title}\n{source.text}" for source in source_registry.sources)
    )
    if any(phrase in source_text for phrase in phrases):
        return True
    if any(_number_occurs_in_source(number, source_text) for number in numbers):
        return True
    matched_terms = {term for term in terms if term in source_text and term not in {"ai", "who"}}
    if _asks_about_purpose(question) and any(
        len(term) >= _PROMPT_SPECIFIC_TERM_MIN_CHARACTERS for term in matched_terms
    ):
        return True
    return len(matched_terms) >= 2


def _asks_about_purpose(question: str) -> bool:
    folded_question = _fold_for_person_match(question)
    return any(cue in folded_question for cue in _PURPOSE_QUESTION_CUES)


def _number_occurs_with_question_unit(
    number: str,
    source_text: str,
    terms: tuple[str, ...],
) -> bool:
    if not number.isdecimal():
        return False
    normalized = str(int(number))
    spans = _source_number_unit_pair_spans(source_text)
    question_units = _question_value_units(terms)
    if not question_units:
        return _number_occurs_in_source(number, source_text)
    return any(
        number_value == normalized and _unit_matches_question(unit, question_units)
        for number_value, unit, _, _ in spans
    )


def _question_value_units(terms: tuple[str, ...]) -> frozenset[str]:
    units: set[str] = set()
    for term in terms:
        if term in {"gio", "hour", "hours"}:
            units.update({"gio", "h", "hour", "hours"})
        elif term in {"ngay", "day", "days"}:
            units.update({"ngay", "day", "days"})
        elif term in {"tuan", "week", "weeks"}:
            units.update({"tuan", "week", "weeks"})
        elif term in {"thang", "month", "months"}:
            units.update({"thang", "month", "months"})
        elif term in {"nam", "year", "years"}:
            units.update({"nam", "year", "years"})
        elif term in {"nguoi", "nhan", "employee", "employees", "people"}:
            units.update({"nguoi", "nhan", "employee", "employees", "people"})
        elif term in {"dong", "trieu", "vnd"}:
            units.update({"dong", "trieu", "vnd", "d"})
    return frozenset(units)


def _unit_matches_question(unit: str, question_units: frozenset[str]) -> bool:
    if unit in question_units:
        return True
    return any(unit.startswith(f"{question_unit}/") for question_unit in question_units)


def _number_occurs_in_source(number: str, source_text: str) -> bool:
    if not number.isdecimal():
        return False
    normalized = str(int(number))
    return any(str(int(match.group(0))) == normalized for match in re.finditer(r"\d+", source_text))


def _merge_retrieval_hits(
    *hit_groups: tuple[HybridRetrievalHit, ...],
) -> tuple[HybridRetrievalHit, ...]:
    merged: list[HybridRetrievalHit] = []
    seen: set[UUID] = set()
    for hit_group in hit_groups:
        for hit in hit_group:
            if hit.chunk_id in seen:
                continue
            merged.append(hit)
            seen.add(hit.chunk_id)
    return tuple(merged)


def _preserve_reranked_hit_order(
    reranked_hits: tuple[HybridRetrievalHit, ...],
    ranked_hits: tuple[HybridRetrievalHit, ...],
) -> tuple[HybridRetrievalHit, ...]:
    ordered: list[HybridRetrievalHit] = []
    seen: set[UUID] = set()
    for hit in (*ranked_hits, *reranked_hits):
        if hit.chunk_id in seen:
            continue
        ordered.append(hit)
        seen.add(hit.chunk_id)
    return tuple(ordered)


def _rank_hits_for_prompt(
    hits: tuple[HybridRetrievalHit, ...],
    *,
    question: str,
) -> tuple[HybridRetrievalHit, ...]:
    phrases, terms, numbers = _prompt_query_needles(question)
    if not phrases and not terms and not numbers:
        return hits
    analysis = analyze_question(question)
    quantity_question = _asks_for_quantity(question)
    change_question = _question_mentions_change(question)
    role_terms = _role_terms_for_prompt_question(question)
    scored_hits = tuple(
        (
            index,
            hit,
            _prompt_hit_alignment_score(
                hit,
                phrases=phrases,
                terms=terms,
                numbers=numbers,
                question=question,
                analysis=analysis,
                quantity_question=quantity_question,
                change_question=change_question,
                role_terms=role_terms,
            ),
        )
        for index, hit in enumerate(hits)
    )
    filtered_hits = _filter_to_role_person_hits(scored_hits, role_terms=role_terms)
    filtered_hits = _filter_to_named_document_title_hits(filtered_hits, question=question)
    filtered_hits = _filter_low_alignment_documents(filtered_hits)
    filtered_hits = _filter_to_specific_term_hits(filtered_hits, terms=terms)
    return tuple(
        hit
        for index, hit, alignment_score in sorted(
            filtered_hits,
            key=lambda scored_hit: _prompt_hit_sort_key(
                scored_hit[1],
                index=scored_hit[0],
                phrases=phrases,
                terms=terms,
                numbers=numbers,
                question=question,
                analysis=analysis,
                quantity_question=quantity_question,
                change_question=change_question,
                role_terms=role_terms,
                alignment_score=scored_hit[2],
            ),
        )
    )


def _filter_to_role_person_hits(
    scored_hits: tuple[tuple[int, HybridRetrievalHit, float], ...],
    *,
    role_terms: tuple[str, ...],
) -> tuple[tuple[int, HybridRetrievalHit, float], ...]:
    if not role_terms:
        return scored_hits
    role_person_hits = tuple(
        (index, hit, score)
        for index, hit, score in scored_hits
        if _person_name_sequences_near_terms(hit.text, role_terms)
    )
    return role_person_hits or scored_hits


def _filter_to_named_document_title_hits(
    scored_hits: tuple[tuple[int, HybridRetrievalHit, float], ...],
    *,
    question: str,
) -> tuple[tuple[int, HybridRetrievalHit, float], ...]:
    title_terms = _named_document_title_terms(question)
    if not title_terms:
        return scored_hits
    title_hits = tuple(
        (index, hit, score)
        for index, hit, score in scored_hits
        if all(term in _fold_for_person_match(hit.document_title) for term in title_terms)
    )
    if not title_hits:
        return scored_hits
    direct_title_hits = tuple(
        (index, hit, score)
        for index, hit, score in title_hits
        if not _is_reference_or_question_list_hit(hit)
    )
    return direct_title_hits or title_hits


def _is_reference_or_question_list_hit(hit: HybridRetrievalHit) -> bool:
    text = _fold_for_person_match(f"{hit.document_title}\n{hit.text}")
    return any(cue in text for cue in (*_QUESTION_LIST_CONTEXT_CUES, *_REFERENCE_CONTEXT_CUES))


def _named_document_title_terms(question: str) -> tuple[str, ...]:
    folded_question = f" {_fold_for_person_match(question)} "
    for prefix in (" chinh sach ", " noi quy ", " quy che ", " policy ", " procedure "):
        start = folded_question.find(prefix)
        if start < 0:
            continue
        candidate = folded_question[start + len(prefix) : start + len(prefix) + 120]
        stop_positions = tuple(
            position
            for cue in (
                " nhan vien ",
                " nguoi lao dong ",
                " employee ",
                " employees ",
                " co the ",
                " duoc ",
                " bao nhieu ",
                " may gio ",
                " trong khoang ",
                " la ",
                " neu ",
                " thi ",
            )
            if (position := candidate.find(cue)) >= 0
        )
        if stop_positions:
            candidate = candidate[: min(stop_positions)]
        ignored_terms = {
            "chinh",
            "sach",
            "noi",
            "quy",
            "che",
            "policy",
            "procedure",
            "theo",
            "cua",
            "va",
        }
        terms = tuple(
            term
            for term in _PROMPT_QUERY_TERM_PATTERN.findall(candidate)
            if len(term) >= 3 and term not in ignored_terms
        )
        if len(terms) >= 2:
            return terms[:6]
    return ()


def _filter_to_specific_term_hits(
    scored_hits: tuple[tuple[int, HybridRetrievalHit, float], ...],
    *,
    terms: tuple[str, ...],
) -> tuple[tuple[int, HybridRetrievalHit, float], ...]:
    specific_terms = tuple(
        term for term in terms if len(term) >= _PROMPT_SPECIFIC_TERM_MIN_CHARACTERS
    )
    if not specific_terms:
        return scored_hits
    specific_hits = tuple(
        (index, hit, score)
        for index, hit, score in scored_hits
        if any(
            term in _fold_for_person_match(f"{hit.document_title}\n{hit.text}")
            for term in specific_terms
        )
    )
    return specific_hits or scored_hits


def _filter_low_alignment_documents(
    scored_hits: tuple[tuple[int, HybridRetrievalHit, float], ...],
) -> tuple[tuple[int, HybridRetrievalHit, float], ...]:
    if not scored_hits:
        return scored_hits
    best_score = max(score for _, _, score in scored_hits)
    if best_score < _PROMPT_DOCUMENT_FILTER_MIN_BEST_SCORE:
        return scored_hits

    document_best_scores: dict[UUID, float] = {}
    for _, hit, score in scored_hits:
        document_best_scores[hit.document_id] = max(
            score,
            document_best_scores.get(hit.document_id, 0.0),
        )
    minimum_document_score = best_score * _PROMPT_DOCUMENT_FILTER_MIN_RATIO
    allowed_document_ids = {
        document_id
        for document_id, score in document_best_scores.items()
        if score >= minimum_document_score
    }
    filtered_hits = tuple(
        (index, hit, score)
        for index, hit, score in scored_hits
        if hit.document_id in allowed_document_ids
    )
    minimum_hit_scores = {
        document_id: score * _PROMPT_HIT_FILTER_MIN_RATIO
        for document_id, score in document_best_scores.items()
        if document_id in allowed_document_ids
    }
    tightly_matched_hits = tuple(
        (index, hit, score)
        for index, hit, score in filtered_hits
        if score >= minimum_hit_scores[hit.document_id]
    )
    return tightly_matched_hits or filtered_hits


def _role_terms_for_prompt_question(question: str) -> tuple[str, ...]:
    analysis = analyze_question(question)
    if not analysis.asks_for_person and not _asks_role_assignment_question(question):
        return ()
    return tuple(
        term
        for term in dict.fromkeys(
            _fold_for_person_match(term) for term in _QUESTION_ACRONYM_PATTERN.findall(question)
        )
        if term not in _PROMPT_NON_ROLE_ACRONYMS
    )


def _asks_role_assignment_question(question: str) -> bool:
    if not _QUESTION_ACRONYM_PATTERN.search(question):
        return False
    folded_question = _fold_for_person_match(question)
    return any(
        cue in folded_question
        for cue in (
            " la ",
            "co phai",
            "dung khong",
            "phai khong",
            " is ",
            " are ",
        )
    )


def _like_contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _prompt_hit_sort_key(
    hit: HybridRetrievalHit,
    *,
    index: int,
    phrases: tuple[str, ...],
    terms: tuple[str, ...],
    numbers: tuple[str, ...],
    question: str,
    analysis: QuestionAnalysis,
    quantity_question: bool,
    change_question: bool,
    role_terms: tuple[str, ...],
    alignment_score: float | None = None,
) -> tuple[float, float, float, float, int]:
    if alignment_score is None:
        alignment_score = _prompt_hit_alignment_score(
            hit,
            phrases=phrases,
            terms=terms,
            numbers=numbers,
            question=question,
            analysis=analysis,
            quantity_question=quantity_question,
            change_question=change_question,
            role_terms=role_terms,
        )
    text = _fold_for_person_match(hit.text)
    has_change_evidence = any(_fold_for_person_match(cue) in text for cue in _CHANGE_EVIDENCE_CUES)
    return (
        -alignment_score,
        0 if not change_question or has_change_evidence else 1,
        -(hit.keyword_score or 0.0),
        -(hit.semantic_score or 0.0),
        -hit.hybrid_score,
        index,
    )


def _prompt_hit_alignment_score(
    hit: HybridRetrievalHit,
    *,
    phrases: tuple[str, ...],
    terms: tuple[str, ...],
    numbers: tuple[str, ...],
    question: str,
    analysis: QuestionAnalysis,
    quantity_question: bool,
    change_question: bool,
    role_terms: tuple[str, ...],
) -> float:
    text = _fold_for_person_match(f"{hit.document_title}\n{hit.text}")
    alignment_score = 0.0
    for phrase in phrases:
        if phrase in text:
            alignment_score += 8.0 + len(phrase.split())
    for number in numbers:
        if _number_occurs_with_question_unit(number, text, terms):
            alignment_score += _PROMPT_NUMBER_MATCH_BONUS
            if any(_fold_for_person_match(cue) in text for cue in _CHANGE_EVIDENCE_CUES):
                alignment_score += _PROMPT_NUMBER_UNIT_MATCH_BONUS
    for term in terms:
        if term in text:
            alignment_score += _prompt_term_match_score(term)
        if quantity_question and _contains_number_unit(text, term):
            alignment_score += _PROMPT_NUMBER_UNIT_MATCH_BONUS
    if change_question and any(
        _fold_for_person_match(cue) in text for cue in _CHANGE_EVIDENCE_CUES
    ):
        alignment_score += _PROMPT_CHANGE_EVIDENCE_BONUS
    if _asks_for_person(terms) and _contains_person_name_sequence(hit.text):
        alignment_score += _PROMPT_PERSON_SOURCE_BONUS
        focus_terms = tuple(term for term in terms if term not in _PERSON_QUESTION_TERMS)
        if any(term in text for term in focus_terms):
            alignment_score += _PROMPT_PERSON_FOCUS_MATCH_BONUS
    if role_terms and _contains_person_name_sequence(hit.text):
        matched_role_terms = tuple(
            term for term in role_terms if _contains_folded_phrase(text, term)
        )
        if matched_role_terms:
            alignment_score += _PROMPT_PERSON_SOURCE_BONUS
            alignment_score += len(matched_role_terms) * _PROMPT_PERSON_FOCUS_MATCH_BONUS
    evidence_score = _prompt_answer_type_evidence_score(
        text,
        analysis=analysis,
        terms=terms,
    )
    alignment_score += evidence_score
    alignment_score -= _prompt_non_answer_context_penalty(
        text=text,
        question=question,
        evidence_score=evidence_score,
    )
    return alignment_score


def _asks_founding_year(terms: tuple[str, ...]) -> bool:
    term_set = frozenset(terms)
    return {"thanh", "lap"} <= term_set or bool(term_set.intersection({"founded", "established"}))


def _prompt_answer_type_evidence_score(
    text: str,
    *,
    analysis: QuestionAnalysis,
    terms: tuple[str, ...],
) -> float:
    score = 0.0
    if analysis.answer_type == "YEAR" and _YEAR_VALUE_PATTERN.search(text):
        score += 95.0
        if _asks_founding_year(terms):
            if _FOUNDING_YEAR_VALUE_PATTERN.search(text):
                score += 190.0
            else:
                score -= 85.0
            if _PLANNING_YEAR_VALUE_PATTERN.search(text):
                score -= 130.0
        elif any(cue in text for cue in ("founded", "established", "nam thanh lap")):
            score += 45.0
    if analysis.asks_for_count and _COUNT_VALUE_PATTERN.search(text):
        score += 135.0
        if any(cue in text for cue in ("khoang", "approximately", "around", "about")):
            score += 55.0
        if any(cue in text for cue in ("quy mo", "headcount", "workforce", "personnel")):
            score += 70.0
        has_customer_target_cue = any(
            cue in text for cue in ("khach hang muc tieu", "target customer", "customer target")
        )
        asks_about_customer = any(term in terms for term in ("khach", "customer", "client"))
        if has_customer_target_cue and not asks_about_customer:
            score -= 120.0
    if analysis.asks_for_amount and _MONEY_VALUE_PATTERN.search(text):
        score += 130.0
        if any(term in text for term in terms if len(term) >= 6):
            score += 25.0
    if analysis.asks_for_percentage:
        if _PERCENT_VALUE_PATTERN.search(text):
            score += 130.0
        if has_explicit_not_specified(text):
            score += 150.0
    if analysis.answer_type == "DATE" and _DATE_VALUE_PATTERN.search(text):
        score += 85.0
        if any(term in text for term in ("tra", "luong", "salary", "payroll", "payment")):
            score += 55.0
    if analysis.asks_for_time_range:
        if _TIME_RANGE_VALUE_PATTERN.search(text):
            score += 130.0
        elif _CLOCK_VALUE_PATTERN.search(text):
            score += 80.0
    elif analysis.answer_type == "TIME" and _CLOCK_VALUE_PATTERN.search(text):
        score += 110.0
    if analysis.asks_for_duration and _DURATION_VALUE_PATTERN.search(text):
        score += 120.0
        if any(term in text for term in terms if len(term) >= 5):
            score += 25.0
        if any(cue in text for cue in ("toi da", "maximum", "limit", "khong qua")):
            score += 60.0
    if analysis.is_yes_no and any(cue in text for cue in _ANSWER_POLARITY_CUES):
        score += 105.0
        if _polarity_near_focus_terms(text, terms=terms):
            score += 95.0
    if analysis.asks_for_explicit_value and _has_generic_value_expression(text):
        score += 35.0
    score += _direct_answer_window_score(text, analysis=analysis, terms=terms)
    return score


def _direct_answer_window_score(
    text: str,
    *,
    analysis: QuestionAnalysis,
    terms: tuple[str, ...],
) -> float:
    anchors = _direct_answer_anchor_spans(text, analysis=analysis, terms=terms)
    if not anchors:
        return 0.0
    focus_terms = tuple(
        term
        for term in terms
        if len(term) >= 3
        and term not in _QUANTITY_STOP_TERMS
        and term not in {"cua", "theo", "chinh", "sach", "co", "duoc", "moi"}
    )
    if not focus_terms:
        return 0.0
    best_score = 0.0
    for start, end in anchors:
        window = text[max(0, start - 220) : min(len(text), end + 220)]
        matched_terms = {term for term in focus_terms if term in window}
        score = len(matched_terms) * 35.0
        if analysis.asks_for_duration:
            if "toi" in terms and any(cue in window for cue in ("toi da", "maximum", "limit")):
                score += 140.0
            if {"ngay", "tuan"}.issubset(set(terms)) and (
                "ngay/tuan" in window or ("ngay" in window and "tuan" in window)
            ):
                score += 100.0
        if analysis.is_yes_no:
            if _terms_ask_about_automatic(terms) and any(
                cue in window for cue in ("tu dong", "automatic")
            ):
                score += 160.0
            if "call" in terms and "call" in window:
                score += 90.0
        best_score = max(best_score, score)
    return best_score


def _terms_ask_about_automatic(terms: tuple[str, ...]) -> bool:
    return "automatic" in terms or ("dong" in terms and ("tinh" in terms or "toan" in terms))


def _direct_answer_anchor_spans(
    text: str,
    *,
    analysis: QuestionAnalysis,
    terms: tuple[str, ...],
) -> tuple[tuple[int, int], ...]:
    spans: list[tuple[int, int]] = []
    patterns: tuple[re.Pattern[str], ...] = ()
    if analysis.asks_for_count:
        patterns = (_COUNT_VALUE_PATTERN,)
    elif analysis.asks_for_amount:
        patterns = (_MONEY_VALUE_PATTERN,)
    elif analysis.asks_for_percentage:
        patterns = (_PERCENT_VALUE_PATTERN,)
    elif analysis.asks_for_duration:
        patterns = (_DURATION_VALUE_PATTERN,)
    elif analysis.asks_for_time_range:
        patterns = (_TIME_RANGE_VALUE_PATTERN, _CLOCK_VALUE_PATTERN)
    elif analysis.answer_type == "DATE":
        patterns = (_DATE_VALUE_PATTERN,)
    elif analysis.answer_type == "YEAR":
        patterns = (_YEAR_VALUE_PATTERN,)
    elif analysis.answer_type == "TIME":
        patterns = (_CLOCK_VALUE_PATTERN,)
    for pattern in patterns:
        spans.extend((match.start(), match.end()) for match in pattern.finditer(text))
    if analysis.asks_for_percentage and has_explicit_not_specified(text):
        spans.extend(_cue_spans(text, ("khong co dinh", "khong quy dinh", "not fixed", "no fixed")))
    if analysis.is_yes_no:
        automatic_question = _terms_ask_about_automatic(terms)
        if automatic_question:
            spans.extend(
                _cue_spans(
                    text,
                    ("khong tu dong", "tu dong", "not automatic", "automatic"),
                )
            )
        else:
            spans.extend(_cue_spans(text, _ANSWER_POLARITY_CUES))
    return tuple(spans)


def _cue_spans(text: str, cues: tuple[str, ...]) -> tuple[tuple[int, int], ...]:
    spans: list[tuple[int, int]] = []
    for cue in cues:
        start = 0
        while True:
            position = text.find(cue, start)
            if position < 0:
                break
            spans.append((position, position + len(cue)))
            start = position + len(cue)
    return tuple(spans)


def _polarity_near_focus_terms(text: str, *, terms: tuple[str, ...]) -> bool:
    focus_terms = tuple(
        term for term in terms if len(term) >= 5 and term not in _QUANTITY_STOP_TERMS
    )
    if not focus_terms:
        return False
    polarity_positions = tuple(
        position for cue in _ANSWER_POLARITY_CUES if (position := text.find(cue)) >= 0
    )
    if not polarity_positions:
        return False
    for term in focus_terms:
        start = 0
        while True:
            position = text.find(term, start)
            if position < 0:
                break
            close_to_polarity = any(
                abs(position - polarity_position) <= 180 for polarity_position in polarity_positions
            )
            if close_to_polarity:
                return True
            start = position + len(term)
    return False


def _has_generic_value_expression(text: str) -> bool:
    return any(
        pattern.search(text)
        for pattern in (
            _COUNT_VALUE_PATTERN,
            _MONEY_VALUE_PATTERN,
            _PERCENT_VALUE_PATTERN,
            _TIME_RANGE_VALUE_PATTERN,
            _CLOCK_VALUE_PATTERN,
            _DATE_VALUE_PATTERN,
            _DURATION_VALUE_PATTERN,
            _YEAR_VALUE_PATTERN,
        )
    ) or has_explicit_not_specified(text)


def _prompt_non_answer_context_penalty(
    *,
    text: str,
    question: str,
    evidence_score: float,
) -> float:
    penalty = 0.0
    folded_question = _fold_for_person_match(question).strip(" ?.!")
    repeats_question = bool(folded_question) and folded_question in text
    has_question_list_cue = any(cue in text for cue in _QUESTION_LIST_CONTEXT_CUES)
    has_reference_cue = any(cue in text for cue in _REFERENCE_CONTEXT_CUES)
    asks_for_limit = any(cue in folded_question for cue in _LIMIT_QUESTION_CUES)
    asks_about_automatic = "tu dong" in folded_question or "automatic" in folded_question
    if repeats_question:
        if has_explicit_not_specified(text):
            penalty += 35.0
        elif evidence_score < 60.0:
            penalty += 180.0
        else:
            penalty += 650.0
    if asks_for_limit and not any(cue in text for cue in _LIMIT_ANSWER_CUES):
        penalty += 180.0
    if asks_about_automatic and not any(cue in text for cue in ("tu dong", "automatic")):
        penalty += 500.0
    if has_question_list_cue:
        if asks_about_automatic and not any(
            cue in text for cue in ("khong tu dong", "not automatic")
        ):
            penalty += 500.0
        elif evidence_score < 80.0:
            penalty += 160.0
        elif evidence_score < 220.0:
            penalty += 115.0
        else:
            penalty += 35.0
    if has_reference_cue:
        if asks_about_automatic and not ("call" in text and "khong tu dong" in text):
            penalty += 500.0
        else:
            penalty += 170.0 if evidence_score < 220.0 else 60.0
    return penalty


def _prompt_term_match_score(term: str) -> float:
    if len(term) >= _PROMPT_SPECIFIC_TERM_MIN_CHARACTERS:
        return 1.0 + _PROMPT_SPECIFIC_TERM_BONUS
    return 1.0


def _contains_number_unit(text: str, term: str) -> bool:
    if not term or term.isdecimal():
        return False
    pattern = rf"\d+\s*(?:\([^)]{{1,80}}\)\s*)?{re.escape(term)}\b"
    return re.search(pattern, text) is not None


def _asks_for_person(terms: tuple[str, ...]) -> bool:
    return any(term in _PERSON_QUESTION_TERMS for term in terms)


def _contains_person_name_candidate(text: str) -> bool:
    candidate_start: int | None = None
    consecutive_candidates = 0
    for match in _NAME_TOKEN_PATTERN.finditer(text):
        token = match.group(0)
        if _is_name_token_candidate(token):
            if consecutive_candidates == 0:
                candidate_start = match.start()
            consecutive_candidates += 1
            if consecutive_candidates >= 3 and candidate_start is not None:
                window = text[candidate_start : min(len(text), match.end() + 80)].casefold()
                if "-" in window or "ceo" in window or "director" in window:
                    return True
        else:
            candidate_start = None
            consecutive_candidates = 0
    return False


def _is_name_token_candidate(token: str) -> bool:
    return len(token) >= 2 and token[:1].isupper() and not token.isupper()


def _prompt_query_needles(
    question: str,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    terms = tuple(
        dict.fromkeys(
            term.strip("_")
            for term in _PROMPT_QUERY_TERM_PATTERN.findall(_fold_for_person_match(question))
            if _is_prompt_query_term(term.strip("_"))
        )
    )[:_PROMPT_MAX_QUERY_TERMS]
    numbers = tuple(term for term in terms if term.isdecimal())
    non_numeric_terms = tuple(term for term in terms if not term.isdecimal())
    phrases: list[str] = []
    for size in (4, 3, 2):
        if len(non_numeric_terms) < size:
            continue
        for index in range(len(non_numeric_terms) - size + 1):
            phrase = " ".join(non_numeric_terms[index : index + size])
            if len(phrase) >= 8:
                phrases.append(phrase)
    return tuple(dict.fromkeys(phrases)), non_numeric_terms, numbers


def _is_prompt_query_term(term: str) -> bool:
    return bool(term) and (
        term in _PERSON_QUESTION_TERMS
        or term.isdecimal()
        or len(term) >= _PROMPT_MIN_QUERY_TERM_CHARACTERS
    )


def _role_person_hit_from_chunk(
    *,
    chunk: DocumentChunk,
    document: Document,
) -> HybridRetrievalHit:
    return HybridRetrievalHit(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        document_title=document.title,
        chunk_index=chunk.chunk_index,
        text=chunk.text,
        page_numbers=tuple(chunk.page_numbers),
        start_page=chunk.start_page,
        end_page=chunk.end_page,
        token_count=chunk.token_count,
        hybrid_score=0.0,
        semantic_score=None,
        semantic_rank=None,
        keyword_score=0.0,
        keyword_rank=1,
        matched_by=("keyword",),
    )


def _adjacent_hit_from_chunk(
    *,
    chunk: DocumentChunk,
    document: Document,
    parent: HybridRetrievalHit,
) -> HybridRetrievalHit:
    return HybridRetrievalHit(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        document_title=document.title,
        chunk_index=chunk.chunk_index,
        text=chunk.text,
        page_numbers=tuple(chunk.page_numbers),
        start_page=chunk.start_page,
        end_page=chunk.end_page,
        token_count=chunk.token_count,
        hybrid_score=parent.hybrid_score * _ADJACENT_CHUNK_SCORE_FACTOR,
        semantic_score=parent.semantic_score,
        semantic_rank=parent.semantic_rank,
        keyword_score=parent.keyword_score,
        keyword_rank=parent.keyword_rank,
        matched_by=parent.matched_by,
    )


def _chat_retrieval_candidate_top_k(
    *,
    settings: Settings,
    reranker: RetrievalReranker | None,
) -> int:
    if settings.reranker_enabled and reranker is not None:
        return min(settings.reranker_candidate_k, settings.hybrid_retrieval_max_top_k)
    return settings.chat_retrieval_top_k


def _prompt_source_limit(
    *,
    settings: Settings,
    reranker: RetrievalReranker | None,
) -> int:
    if settings.reranker_enabled and reranker is not None:
        return min(settings.citation_max_sources_per_answer, settings.reranker_top_k)
    return settings.citation_max_sources_per_answer


def _should_retrieve_internal_context(settings: Settings) -> bool:
    mode = KnowledgeSourceMode(settings.web_search_mode)
    return not (settings.web_search_enabled and mode == KnowledgeSourceMode.WEB_ONLY)


def _is_no_answer_like_json_answer(answer: str) -> bool:
    folded_answer = answer.casefold()
    phrase_positions = tuple(
        position
        for phrase in _NO_ANSWER_LIKE_ANSWER_PHRASES
        if (position := folded_answer.find(phrase)) >= 0
    )
    if not phrase_positions:
        return False
    if min(phrase_positions) <= 40:
        return True
    return not _answer_has_grounded_substance(answer)


def _answer_has_grounded_substance(answer: str) -> bool:
    folded_answer = _fold_for_person_match(answer)
    if _NUMBER_UNIT_PATTERN.search(folded_answer):
        return True
    return _contains_person_name_sequence(answer)


def _is_placeholder_like_json_answer(answer: str) -> bool:
    stripped_answer = answer.strip()
    folded_answer = _fold_for_person_match(stripped_answer)
    if stripped_answer.startswith("<") and stripped_answer.endswith(">"):
        return True
    return any(cue in folded_answer for cue in _PLACEHOLDER_ANSWER_CUES)


def _allowed_source_identifiers(source_registry: PromptSourceRegistry) -> frozenset[str]:
    return frozenset(source.marker[1:-1] for source in source_registry.sources)


def _canonical_answer_with_selected_markers(output: GroundedLLMOutput) -> str:
    citation_markers = " ".join(f"[{citation}]" for citation in output.citations)
    return f"{output.answer} {citation_markers}"


def _log_rag_diagnostics(
    *,
    question: str,
    source_registry: PromptSourceRegistry,
    selected_context_count: int,
) -> None:
    analysis = analyze_question(question)
    logger.info(
        "RAG diagnostics.",
        extra={
            "answer_type": analysis.answer_type,
            "selected_context_count": selected_context_count,
            "source_count": len(source_registry.sources),
            "selected_sources": [
                {
                    "source": source.label,
                    "document_title": source.document_title,
                    "chunk_id": str(source.chunk_id) if source.chunk_id is not None else None,
                    "document_id": (
                        str(source.document_id) if source.document_id is not None else None
                    ),
                    "start_page": source.start_page,
                    "end_page": source.end_page,
                    "hybrid_score": source.hybrid_score,
                    "reranker_score": source.reranker_score,
                    "excerpt_length": len(source.text),
                }
                for source in source_registry.sources
            ],
        },
    )


def _log_claim_validation_diagnostics(*, status: ClaimEvidenceStatus) -> None:
    logger.info(
        "RAG claim validation diagnostics.",
        extra={"claim_validation_result": status.value},
    )


def _log_no_answer_diagnostics(*, reason: str) -> None:
    logger.info(
        "RAG no-answer diagnostics.",
        extra={"no_answer_reason": reason},
    )


def _structured_value_repair_generation(
    *,
    question: str,
    source_registry: PromptSourceRegistry,
) -> LLMGenerationResult | None:
    structured_answer = _structured_time_range_answer(
        question=question,
        source_registry=source_registry,
    )
    if structured_answer is None:
        structured_answer = _structured_direct_value_answer(
            question=question,
            source_registry=source_registry,
        )
    if structured_answer is None:
        return None
    answer, source_label = structured_answer
    return LLMGenerationResult(
        content=json.dumps(
            {"answer": answer, "citations": [source_label]},
            ensure_ascii=False,
        ),
        model="local-structured-value-repair",
        finish_reason="stop",
        prompt_tokens=0,
        completion_tokens=0,
        response_time_ms=0,
        provider="local",
    )


def _structured_time_range_answer(
    *,
    question: str,
    source_registry: PromptSourceRegistry,
) -> tuple[str, str] | None:
    analysis = analyze_question(question)
    if not (analysis.asks_for_time_range or analysis.answer_type == "TIME"):
        return None
    for source in source_registry.sources:
        ranges = _question_focused_time_ranges_from_text(
            question=question,
            source_text=source.text,
        )
        if ranges:
            return _render_time_range_answer(ranges), source.label
    return None


def _structured_direct_value_answer(
    *,
    question: str,
    source_registry: PromptSourceRegistry,
) -> tuple[str, str] | None:
    analysis = analyze_question(question)
    if analysis.asks_for_time_range or analysis.answer_type == "TIME":
        return None
    if not (
        analysis.answer_type in {"DATE", "DURATION", "PERCENTAGE"}
        or analysis.asks_for_duration
        or analysis.asks_for_percentage
    ):
        return None
    if analysis.asks_for_duration and not _paid_leave_duration_repair_allowed(question):
        return None
    for source in source_registry.sources:
        if analysis.asks_for_percentage and has_explicit_not_specified(source.text):
            continue
        value = _question_focused_direct_value_from_text(
            question=question,
            source_text=source.text,
            analysis=analysis,
        )
        if value:
            return _render_direct_value_answer(value=value, analysis=analysis), source.label
    return None


def _paid_leave_duration_repair_allowed(question: str) -> bool:
    folded_question = _fold_for_person_match(question)
    return " paid leave" in folded_question or (
        "nghi" in folded_question and "huong" in folded_question and "luong" in folded_question
    )


def _render_direct_value_answer(*, value: str, analysis: QuestionAnalysis) -> str:
    if analysis.answer_type == "DATE":
        return f"Ng\u00e0y l\u00e0 {value}."
    if analysis.asks_for_percentage:
        return f"T\u1ef7 l\u1ec7 l\u00e0 {value}."
    if analysis.asks_for_duration:
        return f"Th\u1eddi l\u01b0\u1ee3ng l\u00e0 {value}."
    return f"Gi\u00e1 tr\u1ecb l\u00e0 {value}."


def _question_focused_direct_value_from_text(
    *,
    question: str,
    source_text: str,
    analysis: QuestionAnalysis,
) -> str | None:
    pattern = _direct_value_pattern_for_analysis(analysis)
    if pattern is None:
        return None
    folded_question = _fold_for_person_match(question)
    asks_minimum = any(
        cue in folded_question for cue in ("it nhat", "toi thieu", "minimum", "at least")
    )
    _, terms, _ = _prompt_query_needles(question)
    term_set = set(terms)
    focus_terms = tuple(
        term
        for term in terms
        if len(term) >= 3
        and term not in _QUANTITY_STOP_TERMS
        and term
        not in {
            "cua",
            "theo",
            "chinh",
            "sach",
            "co",
            "duoc",
            "moi",
            "nhan",
            "vien",
            "trong",
            "khoang",
            "nao",
        }
    )
    folded_source_text = _fold_for_person_match(source_text)
    matches = tuple(pattern.finditer(folded_source_text))
    if not matches:
        return None

    best_value = ""
    best_score = 0.0
    for index, match in enumerate(matches):
        line_start = folded_source_text.rfind("\n", 0, match.start()) + 1
        next_value_start = (
            matches[index + 1].start() if index + 1 < len(matches) else len(folded_source_text)
        )
        local_before = folded_source_text[max(line_start, match.start() - 140) : match.start()]
        line_end = folded_source_text.find("\n", match.end())
        if line_end < 0:
            line_end = len(folded_source_text)
        local_after = folded_source_text[match.end() : min(line_end, match.end() + 180)]
        if line_end < len(folded_source_text):
            next_line_start = line_end + 1
            while (
                next_line_start < len(folded_source_text)
                and folded_source_text[next_line_start] == "\n"
            ):
                next_line_start += 1
            next_line_end = folded_source_text.find("\n", next_line_start)
            if next_line_end < 0:
                next_line_end = len(folded_source_text)
            next_line = folded_source_text[next_line_start:next_line_end].strip()
            if next_line and len(next_line) <= 140 and pattern.search(next_line) is None:
                local_after = f"{local_after} {next_line}"
        broad_window = folded_source_text[
            max(0, match.start() - 220) : min(
                len(folded_source_text), min(next_value_start, match.end() + 260)
            )
        ]
        score = sum(
            2.0 for term in focus_terms if term in local_before or term in local_after[:160]
        )
        if focus_terms and score == 0:
            score += sum(0.25 for term in focus_terms if term in broad_window)

        if analysis.answer_type == "DATE":
            if any(cue in broad_window for cue in ("tra luong", "payroll", "salary", "payment")):
                score += 90.0
            if "ngay" in term_set:
                score += 20.0
        if analysis.asks_for_duration:
            if any(unit in match.group(0) for unit in ("gio", "ngay", "tuan", "thang", "nam")):
                score += 45.0
            if "nghi" in term_set and "nghi" in broad_window:
                score += 55.0
            if "huong" in term_set and "huong luong" in broad_window:
                score += 70.0
            if (
                {"ket", "hon"}.issubset(term_set)
                and "ket" in broad_window
                and "hon" in broad_window
            ):
                score += 90.0
            if "toi" in term_set and any(
                cue in broad_window for cue in ("toi da", "maximum", "limit", "khong qua")
            ):
                score += 70.0
            if {"ngay", "tuan"}.issubset(term_set) and (
                "ngay/tuan" in broad_window or ("ngay" in broad_window and "tuan" in broad_window)
            ):
                score += 65.0
        if analysis.asks_for_percentage:
            if asks_minimum and "it nhat" in broad_window:
                score += 75.0
            if {"lam", "viec", "ban", "dem"}.issubset(term_set):
                if "lam viec ban dem" in local_after[:160] or "lam viec ban dem" in local_before:
                    score += 150.0
                if "lam them vao ban dem" in local_after[:160]:
                    score -= 130.0
            if {"nghi", "hang", "tuan"}.issubset(
                term_set
            ) and "ngay nghi hang tuan" in broad_window:
                score += 140.0

        value = _structured_direct_value_for_match(
            folded_source_text=folded_source_text,
            match=match,
            analysis=analysis,
        )
        if score > best_score:
            best_score = score
            best_value = value
    if best_score < 50.0:
        return None
    return best_value


def _direct_value_pattern_for_analysis(analysis: QuestionAnalysis) -> re.Pattern[str] | None:
    if analysis.answer_type == "DATE":
        return _DATE_VALUE_PATTERN
    if analysis.asks_for_percentage:
        return _PERCENT_VALUE_PATTERN
    if analysis.asks_for_duration:
        return _DURATION_VALUE_PATTERN
    return None


def _structured_direct_value_for_match(
    *,
    folded_source_text: str,
    match: re.Match[str],
    analysis: QuestionAnalysis,
) -> str:
    value = match.group(0)
    if analysis.answer_type == "DATE":
        suffix = folded_source_text[match.end() : min(len(folded_source_text), match.end() + 80)]
        suffix_match = re.match(r"\s+(?:cua\s+)?(?:thang|month)\s+[a-z0-9 ]{1,30}", suffix)
        if suffix_match is not None:
            value = folded_source_text[match.start() : match.end() + suffix_match.end()]
    return re.sub(r"\s+", " ", value).strip(" .;,:")


def _render_time_range_answer(ranges: tuple[str, ...]) -> str:
    if len(ranges) == 1:
        return f"Kho\u1ea3ng th\u1eddi gian l\u00e0 {ranges[0]}."
    return f"C\u00e1c kho\u1ea3ng th\u1eddi gian l\u00e0 {_join_vietnamese_list(ranges)}."


def _join_vietnamese_list(values: tuple[str, ...]) -> str:
    if len(values) <= 1:
        return "".join(values)
    return f"{', '.join(values[:-1])} v\u00e0 {values[-1]}"


def _question_focused_time_ranges_from_text(
    *,
    question: str,
    source_text: str,
) -> tuple[str, ...]:
    _, terms, _ = _prompt_query_needles(question)
    term_set = set(terms)
    focus_terms = tuple(
        term
        for term in terms
        if len(term) >= 3
        and term not in _QUANTITY_STOP_TERMS
        and term
        not in {
            "cua",
            "theo",
            "chinh",
            "sach",
            "co",
            "duoc",
            "moi",
            "nhan",
            "vien",
            "trong",
            "khoang",
            "nao",
        }
    )
    start_intent = bool(term_set & {"bat", "dau", "start", "begin", "begins"})
    end_intent = bool(term_set & {"ket", "thuc", "end", "finish", "finishes"})
    core_intent = bool(term_set & {"cot", "loi", "core"})
    has_direct_intent = start_intent or end_intent or core_intent

    folded_source_text = _fold_for_person_match(source_text)
    matches = tuple(_TIME_RANGE_VALUE_PATTERN.finditer(folded_source_text))
    if not matches:
        return ()

    ranges: list[str] = []
    previous_value_end = 0
    previous_direct_score = 0.0
    for match in matches:
        line_start = folded_source_text.rfind("\n", 0, match.start()) + 1
        label_start = max(line_start, previous_value_end)
        label_context = folded_source_text[label_start : match.start()].strip()
        if len(label_context) > 120:
            label_context = label_context[-120:]
        trailing_context = folded_source_text[
            match.end() : min(len(folded_source_text), match.end() + 80)
        ]
        broad_window = folded_source_text[
            max(0, match.start() - 180) : min(len(folded_source_text), match.end() + 180)
        ]

        connector_only = bool(
            label_context and re.fullmatch(r"(?:[,;/+&]|\bva\b|\band\b|\s)+", label_context)
        )
        score = 0.0
        score += sum(
            2.0 for term in focus_terms if term in label_context or term in trailing_context[:40]
        )
        if focus_terms and score == 0:
            score += sum(0.25 for term in focus_terms if term in broad_window)

        label_has_start = ("bat" in label_context and "dau" in label_context) or any(
            term in label_context for term in ("start", "begin")
        )
        label_has_end = ("ket" in label_context and "thuc" in label_context) or any(
            term in label_context for term in ("end", "finish")
        )
        label_has_core = (
            "cot" in label_context and "loi" in label_context
        ) or "core" in label_context

        if start_intent:
            if label_has_start:
                score += 120.0
            elif connector_only and previous_direct_score >= 80.0:
                score += 85.0
            else:
                score -= 60.0
            if label_has_end or label_has_core:
                score -= 140.0
        if end_intent:
            if label_has_end:
                score += 120.0
            elif connector_only and previous_direct_score >= 80.0:
                score += 85.0
            else:
                score -= 60.0
            if label_has_start or label_has_core:
                score -= 140.0
        if core_intent:
            if label_has_core:
                score += 120.0
            elif connector_only and previous_direct_score >= 80.0:
                score += 85.0
            else:
                score -= 60.0
            if label_has_start or label_has_end:
                score -= 140.0

        value = match.group(0)
        include = score >= 50.0 if has_direct_intent else score > 0.0
        if include and value not in ranges:
            ranges.append(value)
            previous_direct_score = score if has_direct_intent else 0.0
        else:
            previous_direct_score = 0.0
        previous_value_end = match.end()

    if ranges:
        return tuple(ranges[:4])

    fallback_ranges: list[str] = []
    for match in matches:
        window = folded_source_text[
            max(0, match.start() - 180) : min(len(folded_source_text), match.end() + 180)
        ]
        if focus_terms and not any(term in window for term in focus_terms):
            continue
        value = match.group(0)
        if value not in fallback_ranges:
            fallback_ranges.append(value)
    return tuple(fallback_ranges[:4])


def _no_answer_draft(
    content: str,
    *,
    selected_chunk_count: int = 0,
    response_time_ms: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> _AnswerDraft:
    return _AnswerDraft(
        content=content,
        grounding_status=GroundingStatus.NO_ANSWER,
        retrieved_chunk_count=selected_chunk_count,
        response_time_ms=response_time_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        citations=(),
    )


def _detach_message(message: ChatMessage) -> ChatMessage:
    return message


def _map_llm_error(error: LLMError) -> ApplicationError:
    if error.code == LLMFailureCode.LLM_NOT_CONFIGURED:
        return LLMNotConfiguredApplicationError()
    if error.code == LLMFailureCode.LLM_PROVIDER_UNSUPPORTED:
        return LLMProviderUnsupportedApplicationError()
    if error.code == LLMFailureCode.LLM_PROVIDER_UNAVAILABLE:
        return LLMProviderUnavailableApplicationError()
    if error.code == LLMFailureCode.LLM_PROVIDER_TIMEOUT:
        return LLMProviderTimeoutStandardApplicationError()
    if error.code == LLMFailureCode.LLM_PROVIDER_AUTHENTICATION_FAILED:
        return LLMProviderAuthenticationFailedStandardApplicationError()
    if error.code == LLMFailureCode.LLM_PROVIDER_RATE_LIMITED:
        return LLMProviderRateLimitedStandardApplicationError()
    if error.code == LLMFailureCode.LLM_PROVIDER_BAD_RESPONSE:
        return LLMProviderBadResponseApplicationError()
    if error.code == LLMFailureCode.LLM_REQUEST_REJECTED:
        return LLMRequestRejectedApplicationError()
    if error.code == LLMFailureCode.LLM_TIMEOUT:
        return LLMTimeoutApplicationError()
    if error.code == LLMFailureCode.LLM_AUTHENTICATION_FAILED:
        return LLMAuthenticationFailedApplicationError()
    if error.code == LLMFailureCode.LLM_RATE_LIMITED:
        return LLMRateLimitedApplicationError()
    if error.code == LLMFailureCode.LLM_RESPONSE_INVALID:
        return LLMResponseInvalidApplicationError()
    return LLMGenerationFailedApplicationError()
