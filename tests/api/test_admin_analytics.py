from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    AuditLog,
    ChatMessage,
    ChatMessageRole,
    ChatSession,
    CitationSourceType,
    Department,
    Document,
    DocumentAccessScope,
    DocumentStatus,
    Feedback,
    FeedbackRating,
    MessageCitation,
    User,
    UserRole,
)

pytestmark = pytest.mark.integration

SENSITIVE_QUESTION = "What is the secret payroll plan?"
SENSITIVE_ANSWER = "The confidential answer must not appear in analytics."
SENSITIVE_EXCERPT = "SECRET CITATION EXCERPT"
SENSITIVE_FEEDBACK_REASON = "private feedback reason with payroll detail"
SENSITIVE_STORAGE_KEY = "private/storage/secret-payroll.pdf"

ANALYTICS_ENDPOINTS = (
    "/api/v1/admin/analytics/overview",
    "/api/v1/admin/analytics/chat",
    "/api/v1/admin/analytics/users",
    "/api/v1/admin/analytics/search",
    "/api/v1/admin/analytics/ocr",
    "/api/v1/admin/analytics/llm",
    "/api/v1/admin/analytics/feedback",
    "/api/v1/admin/analytics/audit",
    "/api/v1/admin/reports/export?report=overview&format=json",
)


async def seed_analytics_rows(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    admin: User,
    staff: User,
    department: Department,
) -> None:
    _ = department
    now = datetime.now(UTC)
    sensitive_storage_key = f"{SENSITIVE_STORAGE_KEY}/{uuid.uuid4()}.pdf"
    async with session_factory() as session:
        knowledge_doc = Document(
            title="Analytics Knowledge Base",
            description="Safe title only.",
            original_filename="sensitive-name.pdf",
            storage_key=sensitive_storage_key,
            mime_type="application/pdf",
            file_size=256,
            checksum_sha256="1" * 64,
            status=DocumentStatus.READY,
            access_scope=DocumentAccessScope.PRIVATE,
            department_id=None,
            uploaded_by=admin.id,
            is_deleted=False,
            created_at=now - timedelta(hours=2),
        )
        ready_image = Document(
            title="Ready OCR Image",
            description=None,
            original_filename="ready-image.png",
            storage_key=f"tests/{uuid.uuid4()}.png",
            mime_type="image/png",
            file_size=128,
            checksum_sha256="2" * 64,
            status=DocumentStatus.READY,
            access_scope=DocumentAccessScope.PRIVATE,
            department_id=None,
            uploaded_by=admin.id,
            is_deleted=False,
            created_at=now - timedelta(hours=1),
        )
        failed_image = Document(
            title="Failed OCR Image",
            description=None,
            original_filename="failed-image.jpg",
            storage_key=f"tests/{uuid.uuid4()}.jpg",
            mime_type="image/jpeg",
            file_size=128,
            checksum_sha256="3" * 64,
            status=DocumentStatus.FAILED,
            access_scope=DocumentAccessScope.PRIVATE,
            department_id=None,
            uploaded_by=admin.id,
            error_message="OCR processing failed.",
            is_deleted=False,
            created_at=now - timedelta(minutes=45),
        )
        chat_session = ChatSession(
            user_id=staff.id,
            title="Sensitive analytics session",
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(minutes=10),
        )
        first_question = ChatMessage(
            session=chat_session,
            role=ChatMessageRole.USER,
            content=SENSITIVE_QUESTION,
            created_at=now - timedelta(hours=2),
        )
        first_answer = ChatMessage(
            session=chat_session,
            role=ChatMessageRole.ASSISTANT,
            content=SENSITIVE_ANSWER,
            retrieval_query=SENSITIVE_QUESTION,
            response_time_ms=1200,
            prompt_tokens=100,
            completion_tokens=50,
            created_at=now - timedelta(hours=2, microseconds=-1),
        )
        second_question = ChatMessage(
            session=chat_session,
            role=ChatMessageRole.USER,
            content=SENSITIVE_QUESTION,
            created_at=now - timedelta(minutes=30),
        )
        second_answer = ChatMessage(
            session=chat_session,
            role=ChatMessageRole.ASSISTANT,
            content="Another confidential answer.",
            retrieval_query=SENSITIVE_QUESTION,
            response_time_ms=800,
            prompt_tokens=80,
            completion_tokens=40,
            created_at=now - timedelta(minutes=29),
        )
        feedback = Feedback(
            message=first_answer,
            user_id=staff.id,
            rating=FeedbackRating.HELPFUL,
            reason=SENSITIVE_FEEDBACK_REASON,
            created_at=now - timedelta(minutes=20),
            updated_at=now - timedelta(minutes=20),
        )
        internal_citation = MessageCitation(
            message=first_answer,
            source_type=CitationSourceType.INTERNAL.value,
            document=knowledge_doc,
            page_number=1,
            excerpt=SENSITIVE_EXCERPT,
            citation_order=1,
        )
        web_citation = MessageCitation(
            message=first_answer,
            source_type=CitationSourceType.WEB.value,
            page_number=1,
            excerpt="WEB SECRET EXCERPT",
            citation_order=2,
            source_url="https://example.test/result",
            source_title="Sensitive web title",
        )
        second_internal_citation = MessageCitation(
            message=second_answer,
            source_type=CitationSourceType.INTERNAL.value,
            document=knowledge_doc,
            page_number=2,
            excerpt="SECOND SECRET EXCERPT",
            citation_order=1,
        )
        audit_logs = [
            AuditLog(
                user_id=admin.id,
                action="AUTH_LOGIN_SUCCEEDED",
                outcome="SUCCESS",
                entity_type="USER",
                metadata_json={},
                created_at=now - timedelta(minutes=50),
            ),
            AuditLog(
                user_id=admin.id,
                action="DOCUMENT_UPLOADED",
                outcome="SUCCESS",
                entity_type="DOCUMENT",
                metadata_json={"storage_key": sensitive_storage_key},
                created_at=now - timedelta(minutes=49),
            ),
            AuditLog(
                user_id=admin.id,
                action="DOCUMENT_DOWNLOADED",
                outcome="SUCCESS",
                entity_type="DOCUMENT",
                metadata_json={},
                created_at=now - timedelta(minutes=48),
            ),
            AuditLog(
                user_id=admin.id,
                action="DOCUMENT_DELETED",
                outcome="SUCCESS",
                entity_type="DOCUMENT",
                metadata_json={},
                created_at=now - timedelta(minutes=47),
            ),
            AuditLog(
                user_id=admin.id,
                action="DOCUMENT_PERMISSION_GRANTED",
                outcome="SUCCESS",
                entity_type="DOCUMENT_PERMISSION",
                metadata_json={},
                created_at=now - timedelta(minutes=46),
            ),
            AuditLog(
                user_id=admin.id,
                action="USER_CREATED",
                outcome="SUCCESS",
                entity_type="USER",
                metadata_json={},
                created_at=now - timedelta(minutes=45),
            ),
            AuditLog(
                user_id=staff.id,
                action="CHAT_ANSWER_GENERATED",
                outcome="FAILURE",
                entity_type="CHAT_MESSAGE",
                error_code="LLM_PROVIDER_TIMEOUT",
                metadata_json={},
                created_at=now - timedelta(minutes=44),
            ),
        ]
        session.add_all(
            [
                department,
                knowledge_doc,
                ready_image,
                failed_image,
                chat_session,
                first_question,
                first_answer,
                second_question,
                second_answer,
                feedback,
                internal_citation,
                web_citation,
                second_internal_citation,
                *audit_logs,
            ]
        )
        await session.commit()


def seed_rows(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    admin: User,
    staff: User,
    department: Department,
) -> None:
    asyncio.run(
        seed_analytics_rows(
            session_factory,
            admin=admin,
            staff=staff,
            department=department,
        )
    )


def test_admin_analytics_endpoints_are_admin_only(
    api_client: TestClient,
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    staff = make_user(role=UserRole.STAFF)
    admin = make_user(role=UserRole.ADMIN)

    for path in ANALYTICS_ENDPOINTS:
        forbidden = api_client.get(path, headers=make_auth_headers(staff))
        allowed = api_client.get(path, headers=make_auth_headers(admin))

        assert forbidden.status_code == 403
        assert allowed.status_code == 200


def test_admin_analytics_returns_expected_aggregates(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    department = make_department(name="Analytics", code="ANL")
    admin = make_user(role=UserRole.ADMIN)
    staff = make_user(role=UserRole.STAFF, department_id=department.id)
    seed_rows(
        async_session_factory_for_tests,
        admin=admin,
        staff=staff,
        department=department,
    )

    chat = api_client.get(
        "/api/v1/admin/analytics/chat",
        headers=make_auth_headers(admin),
    ).json()["data"]
    search = api_client.get(
        "/api/v1/admin/analytics/search",
        headers=make_auth_headers(admin),
    ).json()["data"]
    ocr = api_client.get(
        "/api/v1/admin/analytics/ocr",
        headers=make_auth_headers(admin),
    ).json()["data"]
    llm = api_client.get(
        "/api/v1/admin/analytics/llm",
        headers=make_auth_headers(admin),
    ).json()["data"]
    feedback = api_client.get(
        "/api/v1/admin/analytics/feedback",
        headers=make_auth_headers(admin),
    ).json()["data"]
    audit = api_client.get(
        "/api/v1/admin/analytics/audit",
        headers=make_auth_headers(admin),
    ).json()["data"]

    assert chat["questions"] == 2
    assert chat["sessions"] == 1
    assert chat["assistant_messages"] == 2
    assert chat["average_response_time_ms"] == 1000
    assert chat["average_retrieval_time_ms"]["available"] is False
    assert chat["average_streaming_usage"]["available"] is False
    assert chat["input_tokens"] == 180
    assert chat["output_tokens"] == 90
    assert chat["total_tokens"] == 270

    assert search["internal_searches"] == 1
    assert search["hybrid_searches"] == 1
    assert search["web_searches"] == 0
    assert search["uncategorized_questions"] == 0
    assert search["top_queries"][0]["count"] == 2
    assert search["top_queries"][0]["raw_query_available"] is False
    assert search["top_documents"][0]["title"] == "Analytics Knowledge Base"

    assert ocr["ocr_jobs"] == 2
    assert ocr["succeeded"] == 1
    assert ocr["failed"] == 1
    assert ocr["success_rate_percent"] == 50
    assert ocr["failure_rate_percent"] == 50
    assert ocr["average_ocr_time_ms"]["available"] is False

    assert llm["token_usage"]["input_tokens"] == 180
    assert llm["token_usage"]["output_tokens"] == 90
    assert llm["token_usage"]["total_tokens"] == 270
    assert llm["failures"] == 1
    assert llm["latency"]["value"] == 1000

    assert feedback["total_feedback"] == 1
    assert feedback["helpful"] == 1
    assert feedback["not_helpful"] == 0
    assert feedback["helpful_percent"] == 100

    assert audit["total_events"] == 7
    assert audit["login"] == 1
    assert audit["upload"] == 1
    assert audit["download"] == 1
    assert audit["delete"] == 1
    assert audit["permission"] == 1
    assert audit["admin_actions"] == 2
    assert audit["failures"] == 1


def test_admin_user_analytics_and_overview(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    department = make_department(name="Analytics Users", code="ANU")
    admin = make_user(role=UserRole.ADMIN)
    staff = make_user(role=UserRole.STAFF, department_id=department.id)
    seed_rows(
        async_session_factory_for_tests,
        admin=admin,
        staff=staff,
        department=department,
    )

    users = api_client.get(
        "/api/v1/admin/analytics/users",
        headers=make_auth_headers(admin),
    ).json()["data"]
    overview = api_client.get(
        "/api/v1/admin/analytics/overview",
        headers=make_auth_headers(admin),
    ).json()["data"]

    assert users["active_users"] == 2
    assert users["total_active_accounts"] == 2
    assert users["new_users"] == 2
    assert users["top_users"][0]["user_id"] == str(staff.id)
    assert users["top_users"][0]["question_count"] == 2
    assert users["top_departments"][0]["department_code"] == "ANU"
    assert users["top_departments"][0]["question_count"] == 2

    assert overview["questions"] == 2
    assert overview["active_users"] == 2
    assert overview["documents"] == 3
    assert overview["feedback"] == 1
    assert overview["audit_events"] == 7
    assert overview["total_tokens"] == 270


def test_admin_analytics_does_not_expose_sensitive_content(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    department = make_department(name="Analytics Security", code="ANS")
    admin = make_user(role=UserRole.ADMIN)
    staff = make_user(role=UserRole.STAFF, department_id=department.id)
    seed_rows(
        async_session_factory_for_tests,
        admin=admin,
        staff=staff,
        department=department,
    )

    for path in (
        "/api/v1/admin/analytics/overview",
        "/api/v1/admin/analytics/search",
        "/api/v1/admin/analytics/feedback",
        "/api/v1/admin/analytics/audit",
        "/api/v1/admin/reports/export?report=search&format=json",
        "/api/v1/admin/reports/export?report=search&format=csv",
    ):
        response = api_client.get(path, headers=make_auth_headers(admin))
        assert response.status_code == 200
        payload = response.text
        assert SENSITIVE_QUESTION not in payload
        assert SENSITIVE_ANSWER not in payload
        assert SENSITIVE_EXCERPT not in payload
        assert SENSITIVE_FEEDBACK_REASON not in payload
        assert SENSITIVE_STORAGE_KEY not in payload
        assert "retrieval_query" not in payload
        assert "storage_key" not in payload
        assert "feedback reason" not in payload.lower()
        assert "citation excerpt" not in payload.lower()
        assert "prompt" not in payload.lower()
        assert "context" not in payload.lower()


def test_admin_report_export_supports_json_and_csv_but_not_pdf(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    department = make_department(name="Analytics Export", code="ANX")
    admin = make_user(role=UserRole.ADMIN)
    staff = make_user(role=UserRole.STAFF, department_id=department.id)
    seed_rows(
        async_session_factory_for_tests,
        admin=admin,
        staff=staff,
        department=department,
    )

    json_response = api_client.get(
        "/api/v1/admin/reports/export?report=feedback&format=json",
        headers=make_auth_headers(admin),
    )
    csv_response = api_client.get(
        "/api/v1/admin/reports/export?report=feedback&format=csv",
        headers=make_auth_headers(admin),
    )
    pdf_response = api_client.get(
        "/api/v1/admin/reports/export?report=feedback&format=pdf",
        headers=make_auth_headers(admin),
    )

    assert json_response.status_code == 200
    assert json_response.json()["data"]["report"] == "feedback"
    assert json_response.headers["content-disposition"].endswith(
        'filename="admin-feedback-analytics.json"'
    )
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "data.total_feedback,1" in csv_response.text
    assert pdf_response.status_code == 422
    assert pdf_response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_admin_analytics_custom_range_and_performance_smoke(
    api_client: TestClient,
    async_session_factory_for_tests: async_sessionmaker[AsyncSession],
    make_department: Callable[..., Department],
    make_user: Callable[..., User],
    make_auth_headers: Callable[[User], dict[str, str]],
) -> None:
    department = make_department(name="Analytics Perf", code="ANP")
    admin = make_user(role=UserRole.ADMIN)
    staff = make_user(role=UserRole.STAFF, department_id=department.id)
    seed_rows(
        async_session_factory_for_tests,
        admin=admin,
        staff=staff,
        department=department,
    )
    start = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()

    started = time.perf_counter()
    response = api_client.get(
        "/api/v1/admin/analytics/overview",
        params={"period": "custom", "date_from": start, "date_to": end},
        headers=make_auth_headers(admin),
    )
    elapsed = time.perf_counter() - started
    invalid_response = api_client.get(
        "/api/v1/admin/analytics/overview?period=custom",
        headers=make_auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["data"]["questions"] == 2
    assert elapsed < 5
    assert invalid_response.status_code == 422
