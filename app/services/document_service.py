from __future__ import annotations

import hashlib
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import AuditEventType, AuditTargetType
from app.core.exceptions import (
    ApplicationError,
    BusinessValidationError,
    DocumentFilenameInvalidError,
    DocumentFileSignatureInvalidError,
    DocumentFileUnavailableError,
    DuplicateDocumentError,
    EmptyFileError,
    FileTooLargeError,
    InternalServerError,
    InvalidFileTypeError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.core.permissions import can_edit_document, can_manage_document, can_view_document
from app.models import (
    Document,
    DocumentAccessScope,
    DocumentPermissionLevel,
    DocumentStatus,
    User,
    UserRole,
)
from app.repositories import department_repository, document_repository
from app.schemas.common import PaginationMeta, build_pagination_meta, calculate_offset
from app.schemas.document import DocumentUpdate
from app.services.audit_service import AuditContext, AuditService
from app.storage.base import FileStorage
from app.storage.local import StorageError

PDF_SIGNATURE = b"%PDF-"
PDF_MIME_TYPE = "application/pdf"
PDF_EXTENSION = ".pdf"
MAX_TITLE_LENGTH = 255
MAX_ORIGINAL_FILENAME_LENGTH = 255
MAX_SEARCH_LENGTH = 200

EnqueueDocumentProcessing = Callable[[UUID], bool]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentUploadLimits:
    max_upload_size_bytes: int
    upload_chunk_size_bytes: int


@dataclass(frozen=True)
class DocumentDownload:
    filename: str
    file_size: int
    media_type: str
    chunks: AsyncIterator[bytes]


class UploadFileProcessor:
    def __init__(
        self,
        file: UploadFile,
        *,
        max_upload_size_bytes: int,
        upload_chunk_size_bytes: int,
    ) -> None:
        if max_upload_size_bytes <= 0:
            msg = "max_upload_size_bytes must be greater than zero."
            raise ValueError(msg)
        if upload_chunk_size_bytes <= 0:
            msg = "upload_chunk_size_bytes must be greater than zero."
            raise ValueError(msg)
        self.file = file
        self.max_upload_size_bytes = max_upload_size_bytes
        self.upload_chunk_size_bytes = upload_chunk_size_bytes
        self.total_size = 0
        self._hasher = hashlib.sha256()
        self._signature_prefix = bytearray()
        self._signature_checked = False

    @property
    def checksum_sha256(self) -> str:
        return self._hasher.hexdigest()

    async def iter_chunks(self) -> AsyncIterator[bytes]:
        while True:
            chunk = await self.file.read(self.upload_chunk_size_bytes)
            if not chunk:
                break
            self._validate_signature_chunk(chunk)
            self.total_size += len(chunk)
            if self.total_size > self.max_upload_size_bytes:
                raise FileTooLargeError()
            self._hasher.update(chunk)
            yield chunk

        if self.total_size == 0:
            raise EmptyFileError()
        if not self._signature_checked:
            raise DocumentFileSignatureInvalidError()

    def _validate_signature_chunk(self, chunk: bytes) -> None:
        if self._signature_checked:
            return
        bytes_needed = len(PDF_SIGNATURE) - len(self._signature_prefix)
        self._signature_prefix.extend(chunk[:bytes_needed])
        if len(self._signature_prefix) < len(PDF_SIGNATURE):
            return
        self._signature_checked = True
        if bytes(self._signature_prefix) != PDF_SIGNATURE:
            raise DocumentFileSignatureInvalidError()


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: FileStorage | None = None,
        upload_limits: DocumentUploadLimits | None = None,
        enqueue_processing: EnqueueDocumentProcessing | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.upload_limits = upload_limits
        self.enqueue_processing = enqueue_processing

    async def upload_document(
        self,
        *,
        file: UploadFile,
        title: str,
        description: str | None,
        access_scope: DocumentAccessScope,
        department_id: UUID | None,
        current_user: User,
        audit_context: AuditContext | None = None,
    ) -> Document:
        storage = self._require_storage()
        upload_limits = self._require_upload_limits()
        normalized_title = normalize_title(title)
        normalized_description = normalize_description(description)
        original_filename = sanitize_original_filename(file.filename)
        validate_pdf_extension(original_filename)
        validate_pdf_mime_type(file.content_type)
        validated_department_id = await self._validate_upload_scope(
            current_user=current_user,
            access_scope=access_scope,
            department_id=department_id,
        )
        storage_key = generate_document_storage_key()
        processor = UploadFileProcessor(
            file,
            max_upload_size_bytes=upload_limits.max_upload_size_bytes,
            upload_chunk_size_bytes=upload_limits.upload_chunk_size_bytes,
        )
        file_saved = False

        try:
            await storage.save(storage_key, processor.iter_chunks())
            file_saved = True

            duplicate = await document_repository.get_active_duplicate_by_uploader_and_checksum(
                self.session,
                uploaded_by=current_user.id,
                checksum_sha256=processor.checksum_sha256,
            )
            if duplicate is not None:
                raise DuplicateDocumentError()

            document = await document_repository.create(
                self.session,
                title=normalized_title,
                description=normalized_description,
                original_filename=original_filename,
                storage_key=storage_key,
                mime_type=PDF_MIME_TYPE,
                file_size=processor.total_size,
                checksum_sha256=processor.checksum_sha256,
                access_scope=access_scope,
                department_id=validated_department_id,
                uploaded_by=current_user.id,
            )
            await self.session.flush()
            await AuditService(self.session).record_success(
                actor_user_id=current_user.id,
                event_type=AuditEventType.DOCUMENT_UPLOADED,
                target_type=AuditTargetType.DOCUMENT,
                target_id=document.id,
                context=audit_context,
                metadata={
                    "document_status": document.status,
                    "access_scope": document.access_scope,
                },
            )
            await self.session.commit()
            await self.session.refresh(document)
            file_saved = False
            self._try_enqueue_processing(document.id)
        except ApplicationError as exc:
            await self.session.rollback()
            if file_saved:
                await self._cleanup_saved_file(storage_key, exc)
            raise
        except StorageError as exc:
            await self.session.rollback()
            raise InternalServerError() from exc
        except IntegrityError as exc:
            await self.session.rollback()
            if file_saved:
                await self._cleanup_saved_file(storage_key, exc)
            raise InternalServerError() from exc
        except Exception as exc:
            await self.session.rollback()
            if file_saved:
                await self._cleanup_saved_file(storage_key, exc)
            raise InternalServerError() from exc

        return document

    async def list_documents(
        self,
        *,
        current_user: User,
        page: int,
        page_size: int,
        search: str | None,
        status: DocumentStatus | None,
        access_scope: DocumentAccessScope | None,
        department_id: UUID | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Document], PaginationMeta]:
        _validate_document_sort(sort_by, sort_order)
        normalized_search = normalize_search(search)
        total = await document_repository.count_accessible_documents(
            self.session,
            current_user=current_user,
            search=normalized_search,
            status=status,
            access_scope=access_scope,
            department_id=department_id,
        )
        documents = await document_repository.list_accessible_documents(
            self.session,
            current_user=current_user,
            limit=page_size,
            offset=calculate_offset(page, page_size),
            search=normalized_search,
            status=status,
            access_scope=access_scope,
            department_id=department_id,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return documents, build_pagination_meta(page=page, page_size=page_size, total=total)

    async def get_document_detail(
        self,
        *,
        document_id: UUID,
        current_user: User,
    ) -> Document:
        document = await document_repository.get_accessible_by_id(
            self.session,
            document_id=document_id,
            current_user=current_user,
        )
        if document is None:
            raise ResourceNotFoundError()
        return document

    async def get_document_status(
        self,
        *,
        document_id: UUID,
        current_user: User,
    ) -> Document:
        return await self.get_document_detail(document_id=document_id, current_user=current_user)

    async def get_document_download(
        self,
        *,
        document_id: UUID,
        current_user: User,
        audit_context: AuditContext | None = None,
    ) -> DocumentDownload:
        storage = self._require_storage()
        upload_limits = self._require_upload_limits()
        document = await self.get_document_detail(
            document_id=document_id,
            current_user=current_user,
        )
        storage_key = document.storage_key
        filename = safe_download_filename(document.original_filename)
        file_size = document.file_size
        try:
            file_exists = await storage.exists(storage_key)
        except StorageError as exc:
            raise DocumentFileUnavailableError() from exc
        if not file_exists:
            raise DocumentFileUnavailableError()
        await AuditService(self.session).record_success(
            actor_user_id=current_user.id,
            event_type=AuditEventType.DOCUMENT_DOWNLOADED,
            target_type=AuditTargetType.DOCUMENT,
            target_id=document.id,
            context=audit_context,
            metadata={},
        )
        await self.session.commit()
        return DocumentDownload(
            filename=filename,
            file_size=file_size,
            media_type=PDF_MIME_TYPE,
            chunks=storage.iter_chunks(storage_key, upload_limits.upload_chunk_size_bytes),
        )

    async def update_document(
        self,
        *,
        document_id: UUID,
        payload: DocumentUpdate,
        current_user: User,
        audit_context: AuditContext | None = None,
    ) -> Document:
        try:
            document = await self._get_viewable_document_or_404(
                document_id=document_id,
                current_user=current_user,
            )
            direct_permission = await self._get_effective_direct_permission(
                document=document,
                current_user=current_user,
            )
            changes_metadata = bool({"title", "description"} & payload.model_fields_set)
            changes_scope = bool({"access_scope", "department_id"} & payload.model_fields_set)
            if changes_metadata and not can_edit_document(
                current_user,
                document,
                direct_permission,
            ):
                raise PermissionDeniedError()
            if changes_scope and not can_manage_document(
                current_user,
                document,
                direct_permission,
            ):
                raise PermissionDeniedError()
            self._reject_null_update_fields(payload)
            final_scope, final_department_id = await self._validate_update_scope(
                document=document,
                payload=payload,
                current_user=current_user,
            )
            self._apply_document_update(
                document,
                payload,
                final_scope=final_scope,
                final_department_id=final_department_id,
            )
            await self.session.flush()
            metadata: dict[str, object] = {}
            if changes_scope:
                metadata["access_scope"] = document.access_scope
            await AuditService(self.session).record_success(
                actor_user_id=current_user.id,
                event_type=AuditEventType.DOCUMENT_UPDATED,
                target_type=AuditTargetType.DOCUMENT,
                target_id=document.id,
                context=audit_context,
                metadata=metadata,
            )
            await self.session.commit()
            await self.session.refresh(document)
        except IntegrityError as exc:
            await self.session.rollback()
            raise InternalServerError() from exc
        except Exception:
            await self.session.rollback()
            raise
        return document

    async def soft_delete_document(
        self,
        *,
        document_id: UUID,
        current_user: User,
        audit_context: AuditContext | None = None,
    ) -> None:
        try:
            document = await document_repository.get_by_id_including_deleted(
                self.session,
                document_id,
            )
            if document is None:
                raise ResourceNotFoundError()
            direct_permission = await self._get_effective_direct_permission(
                document=document,
                current_user=current_user,
            )
            if document.is_deleted:
                if not self._can_manage_deleted_document(
                    current_user=current_user,
                    document=document,
                    direct_permission=direct_permission,
                ):
                    raise ResourceNotFoundError()
                await self.session.commit()
                return
            if not can_view_document(current_user, document, direct_permission):
                raise ResourceNotFoundError()
            if not can_manage_document(current_user, document, direct_permission):
                raise PermissionDeniedError()
            status_before = document.status
            document.is_deleted = True
            await self.session.flush()
            await AuditService(self.session).record_success(
                actor_user_id=current_user.id,
                event_type=AuditEventType.DOCUMENT_DELETED,
                target_type=AuditTargetType.DOCUMENT,
                target_id=document.id,
                context=audit_context,
                metadata={"status_before": status_before},
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def _validate_upload_scope(
        self,
        *,
        current_user: User,
        access_scope: DocumentAccessScope,
        department_id: UUID | None,
    ) -> UUID | None:
        if current_user.role == UserRole.STAFF:
            raise PermissionDeniedError()

        if access_scope == DocumentAccessScope.ORGANIZATION:
            if department_id is not None:
                raise BusinessValidationError("Organization documents must not have a Department.")
            if current_user.role == UserRole.MANAGER:
                raise PermissionDeniedError()
            return None

        if access_scope == DocumentAccessScope.PRIVATE:
            if department_id is not None:
                raise BusinessValidationError("Private documents must not have a Department.")
            return None

        if department_id is None:
            raise BusinessValidationError("Department documents require a Department.")

        if current_user.role == UserRole.MANAGER:
            if current_user.department_id is None:
                raise PermissionDeniedError()
            if current_user.department_id != department_id:
                raise PermissionDeniedError()

        department = await department_repository.get_by_id(self.session, department_id)
        if department is None:
            raise ResourceNotFoundError()
        return department.id

    async def _validate_update_scope(
        self,
        *,
        document: Document,
        payload: DocumentUpdate,
        current_user: User,
    ) -> tuple[DocumentAccessScope, UUID | None]:
        final_scope = document.access_scope
        if "access_scope" in payload.model_fields_set:
            if payload.access_scope is None:
                raise BusinessValidationError("Access scope must not be null.")
            final_scope = payload.access_scope

        if "department_id" in payload.model_fields_set:
            final_department_id = payload.department_id
        elif "access_scope" in payload.model_fields_set and final_scope in {
            DocumentAccessScope.PRIVATE,
            DocumentAccessScope.ORGANIZATION,
        }:
            final_department_id = None
        else:
            final_department_id = document.department_id

        if final_scope == DocumentAccessScope.ORGANIZATION:
            if current_user.role == UserRole.MANAGER:
                raise PermissionDeniedError()
            if final_department_id is not None:
                raise BusinessValidationError("Organization documents must not have a Department.")
            return final_scope, None

        if final_scope == DocumentAccessScope.PRIVATE:
            if final_department_id is not None:
                raise BusinessValidationError("Private documents must not have a Department.")
            return final_scope, None

        if final_department_id is None:
            raise BusinessValidationError("Department documents require a Department.")
        if current_user.role == UserRole.MANAGER:
            if current_user.department_id is None:
                raise PermissionDeniedError()
            if current_user.department_id != final_department_id:
                raise PermissionDeniedError()
        department = await department_repository.get_by_id(self.session, final_department_id)
        if department is None:
            raise ResourceNotFoundError()
        return final_scope, department.id

    async def _get_viewable_document_or_404(
        self,
        *,
        document_id: UUID,
        current_user: User,
    ) -> Document:
        document = await document_repository.get_by_id_including_deleted(
            self.session,
            document_id,
        )
        if document is None or document.is_deleted:
            raise ResourceNotFoundError()
        direct_permission = await self._get_effective_direct_permission(
            document=document,
            current_user=current_user,
        )
        if not can_view_document(current_user, document, direct_permission):
            raise ResourceNotFoundError()
        return document

    async def _get_effective_direct_permission(
        self,
        *,
        document: Document,
        current_user: User,
    ):
        return await document_repository.get_effective_direct_permission(
            self.session,
            document_id=document.id,
            user_id=current_user.id,
            department_id=current_user.department_id,
        )

    def _reject_null_update_fields(self, payload: DocumentUpdate) -> None:
        if "title" in payload.model_fields_set and payload.title is None:
            raise BusinessValidationError("Document title must not be null.")

    def _apply_document_update(
        self,
        document: Document,
        payload: DocumentUpdate,
        *,
        final_scope: DocumentAccessScope,
        final_department_id: UUID | None,
    ) -> None:
        if "title" in payload.model_fields_set:
            document.title = normalize_title(payload.title or "")
        if "description" in payload.model_fields_set:
            document.description = normalize_description(payload.description)
        if {"access_scope", "department_id"} & payload.model_fields_set:
            document.access_scope = final_scope
            document.department_id = final_department_id

    def _can_manage_deleted_document(
        self,
        *,
        current_user: User,
        document: Document,
        direct_permission: DocumentPermissionLevel | None,
    ) -> bool:
        was_deleted = document.is_deleted
        document.is_deleted = False
        try:
            return can_manage_document(current_user, document, direct_permission)
        finally:
            document.is_deleted = was_deleted

    def _try_enqueue_processing(self, document_id: UUID) -> None:
        if self.enqueue_processing is None:
            return
        try:
            enqueued = self.enqueue_processing(document_id)
        except Exception as exc:  # noqa: BLE001 - upload result must not leak broker details.
            logger.warning(
                "Document processing enqueue failed after upload commit.",
                extra={"document_id": str(document_id), "error_type": exc.__class__.__name__},
            )
            return
        if not enqueued:
            logger.warning(
                "Document processing enqueue failed after upload commit.",
                extra={"document_id": str(document_id)},
            )

    async def _cleanup_saved_file(self, storage_key: str, original_error: BaseException) -> None:
        storage = self._require_storage()
        try:
            await storage.delete(storage_key)
        except StorageError as exc:
            logger.warning(
                "Stored upload cleanup failed.",
                extra={"error_type": exc.__class__.__name__},
            )
            raise InternalServerError() from original_error

    def _require_storage(self) -> FileStorage:
        if self.storage is None:
            msg = "Document storage dependency is required."
            raise RuntimeError(msg)
        return self.storage

    def _require_upload_limits(self) -> DocumentUploadLimits:
        if self.upload_limits is None:
            msg = "Document upload limits dependency is required."
            raise RuntimeError(msg)
        return self.upload_limits


def normalize_title(title: str) -> str:
    normalized = title.strip()
    if not normalized:
        raise BusinessValidationError("Document title must not be empty.")
    if len(normalized) > MAX_TITLE_LENGTH:
        raise BusinessValidationError("Document title is too long.")
    return normalized


def normalize_description(description: str | None) -> str | None:
    if description is None:
        return None
    normalized = description.strip()
    return normalized or None


def normalize_search(search: str | None) -> str | None:
    if search is None:
        return None
    normalized = search.strip()
    if not normalized:
        return None
    if len(normalized) > MAX_SEARCH_LENGTH:
        raise BusinessValidationError("Search is too long.")
    return normalized


def sanitize_original_filename(filename: str | None) -> str:
    if filename is None:
        raise DocumentFilenameInvalidError()
    normalized = filename.replace("\\", "/").split("/")[-1].strip()
    normalized = "".join(
        character for character in normalized if character >= " " and character != "\x7f"
    )
    if not normalized:
        raise DocumentFilenameInvalidError()
    if len(normalized) > MAX_ORIGINAL_FILENAME_LENGTH:
        raise DocumentFilenameInvalidError()
    return normalized


def safe_download_filename(filename: str | None) -> str:
    try:
        sanitized = sanitize_original_filename(filename)
    except ApplicationError:
        sanitized = "document.pdf"
    sanitized = sanitized.replace('"', "_").replace("\\", "_").replace(";", "_")
    if not sanitized.lower().endswith(PDF_EXTENSION):
        sanitized = "document.pdf"
    return sanitized[:MAX_ORIGINAL_FILENAME_LENGTH] or "document.pdf"


def validate_pdf_extension(filename: str) -> None:
    if not filename.lower().endswith(PDF_EXTENSION):
        raise InvalidFileTypeError()


def validate_pdf_mime_type(content_type: str | None) -> None:
    if content_type != PDF_MIME_TYPE:
        raise InvalidFileTypeError()


def generate_document_storage_key(
    *,
    now: datetime | None = None,
    document_uuid: uuid.UUID | None = None,
) -> str:
    current_time = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    storage_uuid = document_uuid or uuid.uuid4()
    return f"documents/{current_time:%Y}/{current_time:%m}/{storage_uuid}.pdf"


def _validate_document_sort(sort_by: str, sort_order: str) -> None:
    if sort_by not in document_repository.DOCUMENT_SORT_FIELDS:
        raise BusinessValidationError("Invalid sort field.")
    if sort_order not in {"asc", "desc"}:
        raise BusinessValidationError("Invalid sort order.")
