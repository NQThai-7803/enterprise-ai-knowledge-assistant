from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.session import async_session_factory, dispose_database_engine
from app.embeddings.constants import (
    EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS,
    EMBEDDING_SCHEMA_DIMENSIONS,
)
from app.models import (
    ChatMessage,
    ChatMessageRole,
    ChatSession,
    Department,
    Document,
    DocumentAccessScope,
    DocumentChunk,
    DocumentPermission,
    DocumentPermissionLevel,
    DocumentStatus,
    Feedback,
    FeedbackRating,
    MessageCitation,
    User,
    UserRole,
)

ALLOWED_ENVIRONMENTS = {"development", "test"}
UAT_ENABLED_VALUE = "true"
MIN_UAT_PASSWORD_LENGTH = 12

ADMIN_EMAIL = "admin.uat@example.test"
MANAGER_EMAIL = "manager.uat@example.test"
STAFF_EMAIL = "staff.uat@example.test"

KNOWLEDGE_DEPARTMENT_CODE = "UAT-KNOWLEDGE"
OPERATIONS_DEPARTMENT_CODE = "UAT-OPS"
GROUNDING_STORAGE_KEY = "uat/grounding-handbook.pdf"
SHARED_STORAGE_KEY = "uat/shared-policy.pdf"
PROCESSING_STORAGE_KEY = "uat/processing-placeholder.pdf"
FAILED_STORAGE_KEY = "uat/failed-placeholder.pdf"

GROUNDING_TEXT = (
    "UAT travel approval policy: staff must obtain manager approval before booking travel. "
    "Expense evidence must include the approved request, receipt, and trip purpose. "
    "This deterministic document is safe local UAT data for citation testing."
)

SHARED_TEXT = (
    "UAT shared knowledge policy: organization documents are visible to active users. "
    "Use document permissions only for direct grants on private documents."
)


class SeedUatDataError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class UatSeedResult:
    departments: dict[str, str]
    users: dict[str, str]
    documents: dict[str, str]
    permissions: dict[str, str]
    feedback: dict[str, str]


async def seed_uat_data(
    *,
    settings: Settings | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> UatSeedResult:
    settings = settings or get_settings()
    session_factory = session_factory or async_session_factory
    _validate_uat_enabled(settings)

    passwords = _load_passwords()
    async with session_factory() as session:
        try:
            knowledge_department = await _upsert_department(
                session,
                code=KNOWLEDGE_DEPARTMENT_CODE,
                name="UAT Knowledge Operations",
                description="Local UAT department for document and chat acceptance testing.",
            )
            operations_department = await _upsert_department(
                session,
                code=OPERATIONS_DEPARTMENT_CODE,
                name="UAT Field Operations",
                description="Local UAT department used for role separation checks.",
            )
            await session.flush()

            admin = await _upsert_user(
                session,
                email=ADMIN_EMAIL,
                full_name="UAT Admin",
                password=passwords["admin"],
                role=UserRole.ADMIN,
                department_id=None,
            )
            manager = await _upsert_user(
                session,
                email=MANAGER_EMAIL,
                full_name="UAT Manager",
                password=passwords["manager"],
                role=UserRole.MANAGER,
                department_id=knowledge_department.id,
            )
            staff = await _upsert_user(
                session,
                email=STAFF_EMAIL,
                full_name="UAT Staff",
                password=passwords["staff"],
                role=UserRole.STAFF,
                department_id=knowledge_department.id,
            )
            await session.flush()

            grounding_document = await _upsert_document_with_chunk(
                session,
                settings=settings,
                storage_key=GROUNDING_STORAGE_KEY,
                title="UAT Grounding Handbook",
                text=GROUNDING_TEXT,
                uploaded_by=staff.id,
                access_scope=DocumentAccessScope.PRIVATE,
                department_id=None,
                status=DocumentStatus.READY,
            )
            shared_document = await _upsert_document_with_chunk(
                session,
                settings=settings,
                storage_key=SHARED_STORAGE_KEY,
                title="UAT Shared Knowledge Policy",
                text=SHARED_TEXT,
                uploaded_by=admin.id,
                access_scope=DocumentAccessScope.ORGANIZATION,
                department_id=None,
                status=DocumentStatus.READY,
            )
            processing_document = await _upsert_placeholder_document(
                session,
                settings=settings,
                storage_key=PROCESSING_STORAGE_KEY,
                title="UAT Processing Placeholder",
                text="UAT placeholder document currently marked as processing.",
                uploaded_by=manager.id,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=knowledge_department.id,
                status=DocumentStatus.PROCESSING,
                error_message=None,
            )
            failed_document = await _upsert_placeholder_document(
                session,
                settings=settings,
                storage_key=FAILED_STORAGE_KEY,
                title="UAT Failed Processing Fixture",
                text="UAT placeholder document with a sanitized processing failure.",
                uploaded_by=manager.id,
                access_scope=DocumentAccessScope.DEPARTMENT,
                department_id=knowledge_department.id,
                status=DocumentStatus.FAILED,
                error_message="UAT fixture processing failure.",
            )
            permission = await _upsert_direct_permission(
                session,
                document=grounding_document,
                grantee_user=manager,
                created_by=admin,
                permission=DocumentPermissionLevel.VIEW,
            )
            feedback = await _upsert_feedback_fixture(
                session,
                staff=staff,
                cited_document=grounding_document,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    return UatSeedResult(
        departments={
            KNOWLEDGE_DEPARTMENT_CODE: str(knowledge_department.id),
            OPERATIONS_DEPARTMENT_CODE: str(operations_department.id),
        },
        users={
            "admin": str(admin.id),
            "manager": str(manager.id),
            "staff": str(staff.id),
        },
        documents={
            "grounding": str(grounding_document.id),
            "shared": str(shared_document.id),
            "processing": str(processing_document.id),
            "failed": str(failed_document.id),
        },
        permissions={"manager_grounding_view": str(permission.id)},
        feedback={"staff_grounding_feedback": str(feedback.id)},
    )


def _validate_uat_enabled(settings: Settings) -> None:
    if settings.app_env not in ALLOWED_ENVIRONMENTS:
        msg = "UAT seed can only run in development or test environments."
        raise SeedUatDataError(msg)
    if os.getenv("UAT_SEED_ENABLED", "").strip().lower() != UAT_ENABLED_VALUE:
        msg = "Set UAT_SEED_ENABLED=true to run the UAT seed."
        raise SeedUatDataError(msg)


def _load_passwords() -> dict[str, str]:
    passwords = {
        "admin": os.getenv("UAT_ADMIN_PASSWORD", ""),
        "manager": os.getenv("UAT_MANAGER_PASSWORD", ""),
        "staff": os.getenv("UAT_STAFF_PASSWORD", ""),
    }
    missing = [name for name, value in passwords.items() if not value]
    if missing:
        msg = "Missing UAT password variables: " + ", ".join(
            f"UAT_{name.upper()}_PASSWORD" for name in missing
        )
        raise SeedUatDataError(msg)
    short = [name for name, value in passwords.items() if len(value) < MIN_UAT_PASSWORD_LENGTH]
    if short:
        msg = "UAT passwords must be at least 12 characters."
        raise SeedUatDataError(msg)
    return passwords


async def _upsert_department(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    description: str,
) -> Department:
    department = await session.scalar(select(Department).where(Department.code == code))
    if department is None:
        department = Department(code=code, name=name, description=description)
        session.add(department)
    else:
        department.name = name
        department.description = description
    return department


async def _upsert_user(
    session: AsyncSession,
    *,
    email: str,
    full_name: str,
    password: str,
    role: UserRole,
    department_id: object | None,
) -> User:
    normalized_email = email.strip().lower()
    user = await session.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        user = User(
            email=normalized_email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role,
            department_id=department_id,
            is_active=True,
        )
        session.add(user)
    else:
        user.full_name = full_name
        user.hashed_password = hash_password(password)
        user.role = role
        user.department_id = department_id
        user.is_active = True
    return user


async def _upsert_document_with_chunk(
    session: AsyncSession,
    *,
    settings: Settings,
    storage_key: str,
    title: str,
    text: str,
    uploaded_by: object,
    access_scope: DocumentAccessScope,
    department_id: object | None,
    status: DocumentStatus,
) -> Document:
    document = await _upsert_placeholder_document(
        session,
        settings=settings,
        storage_key=storage_key,
        title=title,
        text=text,
        uploaded_by=uploaded_by,
        access_scope=access_scope,
        department_id=department_id,
        status=status,
        error_message=None,
    )
    await session.flush()
    await _replace_seeded_chunk(session, document=document, text=text)
    return document


async def _upsert_placeholder_document(
    session: AsyncSession,
    *,
    settings: Settings,
    storage_key: str,
    title: str,
    text: str,
    uploaded_by: object,
    access_scope: DocumentAccessScope,
    department_id: object | None,
    status: DocumentStatus,
    error_message: str | None,
) -> Document:
    pdf_bytes = _minimal_pdf_bytes(text)
    _write_seed_file(settings=settings, storage_key=storage_key, content=pdf_bytes)
    checksum = hashlib.sha256(pdf_bytes).hexdigest()
    document = await session.scalar(select(Document).where(Document.storage_key == storage_key))
    if document is None:
        document = Document(
            title=title,
            description="UAT local test data.",
            original_filename=Path(storage_key).name,
            storage_key=storage_key,
            mime_type="application/pdf",
            file_size=len(pdf_bytes),
            checksum_sha256=checksum,
            status=status,
            access_scope=access_scope,
            department_id=department_id,
            uploaded_by=uploaded_by,
            error_message=error_message,
            is_deleted=False,
        )
        session.add(document)
    else:
        document.title = title
        document.description = "UAT local test data."
        document.original_filename = Path(storage_key).name
        document.mime_type = "application/pdf"
        document.file_size = len(pdf_bytes)
        document.checksum_sha256 = checksum
        document.status = status
        document.access_scope = access_scope
        document.department_id = department_id
        document.uploaded_by = uploaded_by
        document.error_message = error_message
        document.is_deleted = False
    return document


async def _replace_seeded_chunk(
    session: AsyncSession,
    *,
    document: Document,
    text: str,
) -> DocumentChunk:
    await session.execute(
        DocumentChunk.__table__.delete().where(DocumentChunk.document_id == document.id)
    )
    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=0,
        text=text,
        token_count=max(1, len(text.split())),
        character_count=len(text),
        page_numbers=[1],
        start_page=1,
        end_page=1,
        overlap_token_count=0,
        content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        embedding=[1.0, *([0.0] * (EMBEDDING_SCHEMA_DIMENSIONS - 1))],
        embedding_provider=EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS,
        embedding_model="uat-seeded-vector",
        embedding_dimensions=EMBEDDING_SCHEMA_DIMENSIONS,
    )
    session.add(chunk)
    return chunk


async def _upsert_direct_permission(
    session: AsyncSession,
    *,
    document: Document,
    grantee_user: User,
    created_by: User,
    permission: DocumentPermissionLevel,
) -> DocumentPermission:
    existing = await session.scalar(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document.id,
            DocumentPermission.user_id == grantee_user.id,
        )
    )
    if existing is not None:
        existing.permission = permission
        existing.created_by = created_by.id
        return existing
    row = DocumentPermission(
        document_id=document.id,
        user_id=grantee_user.id,
        department_id=None,
        permission=permission,
        created_by=created_by.id,
    )
    session.add(row)
    return row


async def _upsert_feedback_fixture(
    session: AsyncSession,
    *,
    staff: User,
    cited_document: Document,
) -> Feedback:
    chat_session = await session.scalar(
        select(ChatSession).where(
            ChatSession.user_id == staff.id,
            ChatSession.title == "UAT Seeded Feedback Session",
        )
    )
    if chat_session is None:
        chat_session = ChatSession(user_id=staff.id, title="UAT Seeded Feedback Session")
        session.add(chat_session)
        await session.flush()

    assistant_message = await session.scalar(
        select(ChatMessage).where(
            ChatMessage.session_id == chat_session.id,
            ChatMessage.role == ChatMessageRole.ASSISTANT,
            ChatMessage.content == (
                "Seeded UAT answer for feedback reporting with validated source [SOURCE_1]."
            ),
        )
    )
    if assistant_message is None:
        user_message = ChatMessage(
            session_id=chat_session.id,
            role=ChatMessageRole.USER,
            content="Seed a UAT feedback example.",
        )
        assistant_message = ChatMessage(
            session_id=chat_session.id,
            role=ChatMessageRole.ASSISTANT,
            content="Seeded UAT answer for feedback reporting with validated source [SOURCE_1].",
            retrieval_query="Seed a UAT feedback example.",
            response_time_ms=1,
            prompt_tokens=1,
            completion_tokens=1,
        )
        session.add_all([user_message, assistant_message])
        await session.flush()
        citation = MessageCitation(
            message_id=assistant_message.id,
            document_id=cited_document.id,
            chunk_id=None,
            page_number=1,
            excerpt="Seeded UAT feedback citation excerpt.",
            relevance_score="1.0",
            citation_order=1,
        )
        session.add(citation)
    else:
        await session.flush()

    feedback = await session.scalar(
        select(Feedback).where(
            Feedback.message_id == assistant_message.id,
            Feedback.user_id == staff.id,
        )
    )
    if feedback is None:
        feedback = Feedback(
            message_id=assistant_message.id,
            user_id=staff.id,
            rating=FeedbackRating.HELPFUL,
            reason="UAT seeded feedback record.",
        )
        session.add(feedback)
    else:
        feedback.rating = FeedbackRating.HELPFUL
        feedback.reason = "UAT seeded feedback record."
    return feedback


def _write_seed_file(*, settings: Settings, storage_key: str, content: bytes) -> None:
    root = Path(settings.local_storage_path)
    target = root / storage_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def _minimal_pdf_bytes(text: str) -> bytes:
    safe_text = (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )[:900]
    return f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length {len(safe_text) + 64} >>
stream
BT
/F1 12 Tf
72 720 Td
({safe_text}) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000059 00000 n 
0000000116 00000 n 
0000000243 00000 n 
0000000313 00000 n 
trailer
<< /Root 1 0 R /Size 6 >>
startxref
430
%%EOF
""".encode("utf-8")


async def run_seed_command() -> int:
    try:
        result = await seed_uat_data()
    except SeedUatDataError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        await dispose_database_engine()

    print("UAT seed completed.")
    for label, values in (
        ("departments", result.departments),
        ("users", result.users),
        ("documents", result.documents),
        ("permissions", result.permissions),
        ("feedback", result.feedback),
    ):
        print(f"{label}:")
        for key, value in values.items():
            print(f"  {key}: {value}")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run_seed_command()))


if __name__ == "__main__":
    main()
