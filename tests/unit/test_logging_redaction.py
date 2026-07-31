from __future__ import annotations

import logging

from app.core.logging import REDACTED, SensitiveDataRedactionFilter


def test_logging_redacts_secrets_and_business_content(caplog) -> None:  # noqa: ANN001
    logger = logging.getLogger("tests.redaction")
    logger.addFilter(SensitiveDataRedactionFilter())

    with caplog.at_level(logging.INFO, logger="tests.redaction"):
        logger.info(
            (
                "password=s3cr3t access_token=access-secret "
                "refresh_token=refresh-secret question=WhereIsPayroll "
                "assistant_answer=PayrollAnswer prompt=SensitivePrompt"
            ),
            extra={
                "api_key": "api-secret-value",
                "authorization": "Bearer hidden-token",
                "database_url": "postgresql://hidden-db",
                "redis_url": "redis://hidden-redis",
                "document_content": "confidential document content",
                "document_text": "confidential document text",
                "feedback_reason": "confidential feedback",
                "citation_excerpt": "confidential excerpt",
                "chat_question": "confidential chat question",
            },
        )

    confidential_markers = [
        "s3cr3t",
        "access-secret",
        "refresh-secret",
        "WhereIsPayroll",
        "PayrollAnswer",
        "SensitivePrompt",
        "api-secret-value",
        "Bearer hidden-token",
        "postgresql://hidden-db",
        "redis://hidden-redis",
        "confidential document content",
        "confidential document text",
        "confidential feedback",
        "confidential excerpt",
        "confidential chat question",
    ]
    for marker in confidential_markers:
        assert marker not in caplog.text
    assert REDACTED in caplog.text
    record = caplog.records[-1]
    assert record.api_key == REDACTED
    assert record.authorization == REDACTED
    assert record.database_url == REDACTED
    assert record.redis_url == REDACTED
    assert record.document_content == REDACTED
    assert record.document_text == REDACTED
    assert record.feedback_reason == REDACTED
    assert record.citation_excerpt == REDACTED
    assert record.chat_question == REDACTED
