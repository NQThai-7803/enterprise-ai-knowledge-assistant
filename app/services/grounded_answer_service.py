from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit import AuditEventType, AuditTargetType
from app.chat.context_builder import select_context_for_prompt
from app.chat.models import ChatAnswerResult, GroundingStatus
from app.chat.prompt_builder import build_grounded_prompt, build_grounding_system_prompt
from app.citations.errors import (
    CitationMappingError,
    CitationPermissionRevalidationError,
    CitationValidationError,
)
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
from app.document_processing.tokenization.base import TokenCounter
from app.document_processing.tokenization.tiktoken_counter import TiktokenTokenCounter
from app.llm.base import LLMProvider
from app.llm.errors import LLMError, LLMFailureCode
from app.llm.models import LLMGenerationResult
from app.models import ChatMessage, ChatMessageRole, User
from app.repositories import (
    chat_message_repository,
    chat_session_repository,
    message_citation_repository,
)
from app.retrieval.base import HybridRetrievalService
from app.retrieval.errors import RetrievalError
from app.services.audit_service import AuditContext, AuditService
from app.services.chat_message_service import ChatMessageService, normalize_message_content
from app.services.citation_validation_service import CitationValidationService

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
        self.citation_validation_service = citation_validation_service or CitationValidationService(
            settings=self.settings,
            session_provider=session_provider,
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
            history_messages = await self.message_repository.list_recent_visible_owned_messages(
                session,
                session_id=session_id,
                owner_user_id=current_user.id,
                limit=self.settings.chat_history_max_messages,
            )

        draft = await self._prepare_answer_draft(
            current_user=current_user,
            question=normalized_question,
            history_messages=history_messages,
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
        history_messages: tuple[object, ...],
    ) -> _AnswerDraft:
        try:
            retrieval_result = await self.hybrid_retrieval_service.retrieve(
                query=question,
                current_user=current_user,
                top_k=self.settings.chat_retrieval_top_k,
            )
        except RetrievalError as exc:
            raise ChatRetrievalFailedError() from exc
        except Exception as exc:
            raise ChatRetrievalFailedError() from exc

        system_prompt = build_grounding_system_prompt(
            no_answer_sentinel=self.settings.llm_no_answer_sentinel,
        )
        selected_context = select_context_for_prompt(
            hits=retrieval_result.hits,
            history_messages=history_messages,
            question=question,
            system_prompt=system_prompt,
            token_counter=self.token_counter,
            max_tokens=self.settings.chat_context_max_tokens,
        )
        source_registry = build_prompt_source_registry(
            context_items=selected_context.items,
            max_sources=self.settings.citation_max_sources_per_answer,
        )
        if not source_registry.sources:
            return _no_answer_draft(self.settings.chat_no_answer_message)

        messages = build_grounded_prompt(
            question=question,
            context_items=selected_context.items,
            history_messages=history_messages,
            no_answer_sentinel=self.settings.llm_no_answer_sentinel,
            source_registry=source_registry,
        )
        provider = None
        try:
            provider = self.llm_provider_factory()
            generation = await provider.generate(
                messages=messages,
                temperature=self.settings.llm_temperature,
                max_output_tokens=self.settings.llm_max_output_tokens,
            )
        except LLMError as exc:
            raise _map_llm_error(exc) from exc
        except Exception as exc:
            raise LLMGenerationFailedApplicationError() from exc
        finally:
            close_provider = getattr(provider, "aclose", None)
            if self.close_llm_provider_after_generate and close_provider is not None:
                await close_provider()
        return await self._draft_from_generation(
            generation,
            source_registry=source_registry,
            current_user=current_user,
        )

    async def _draft_from_generation(
        self,
        generation: LLMGenerationResult,
        *,
        source_registry: object,
        current_user: User,
    ) -> _AnswerDraft:
        selected_chunk_count = len(source_registry.sources)
        if generation.content.strip() == self.settings.llm_no_answer_sentinel:
            return _no_answer_draft(
                self.settings.chat_no_answer_message,
                selected_chunk_count=selected_chunk_count,
                response_time_ms=generation.response_time_ms,
                prompt_tokens=generation.prompt_tokens,
                completion_tokens=generation.completion_tokens,
            )
        try:
            validated = await self.citation_validation_service.validate_and_map(
                answer=generation.content,
                source_registry=source_registry,
                current_user=current_user,
            )
        except CitationPermissionRevalidationError:
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
