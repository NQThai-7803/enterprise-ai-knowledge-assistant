from __future__ import annotations

import logging
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

SECURITY_RESPONSE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cache-Control": "no-store",
}


class ApplicationError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


class InvalidCredentialsError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_CREDENTIALS",
            message="Email or password is incorrect.",
        )


class AccessTokenInvalidError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="ACCESS_TOKEN_INVALID",
            message="Access token is invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpiredError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="TOKEN_EXPIRED",
            message="Access token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class RefreshTokenInvalidError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="REFRESH_TOKEN_INVALID",
            message="Refresh token is invalid.",
        )


class UserInactiveError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="USER_INACTIVE",
            message="User account is inactive.",
        )


class PermissionDeniedError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message="You do not have permission to perform this action.",
        )


class ResourceNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Resource does not exist or should not be revealed.",
        )


class BusinessValidationError(ApplicationError):
    def __init__(self, message: str = "Request is invalid.") -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="VALIDATION_ERROR",
            message=message,
        )


class InvalidFileTypeError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="DOCUMENT_FILE_TYPE_INVALID",
            message="File type is not supported.",
        )


class FileTooLargeError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=413,
            code="DOCUMENT_FILE_TOO_LARGE",
            message="File exceeds size limit.",
        )


class EmptyFileError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="DOCUMENT_FILE_EMPTY",
            message="File is empty.",
        )


class DocumentFileSignatureInvalidError(InvalidFileTypeError):
    def __init__(self) -> None:
        ApplicationError.__init__(
            self,
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="DOCUMENT_FILE_SIGNATURE_INVALID",
            message="File signature is invalid.",
        )


class DocumentFilenameInvalidError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="DOCUMENT_FILENAME_INVALID",
            message="Filename is invalid.",
        )


class RequestTooLargeError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            code="REQUEST_TOO_LARGE",
            message="Request body is too large.",
        )


class RateLimitExceededError(ApplicationError):
    def __init__(self, *, retry_after_seconds: int) -> None:
        retry_after = max(1, retry_after_seconds)
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests.",
            headers={"Retry-After": str(retry_after)},
        )


class DuplicateDocumentError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_DOCUMENT",
            message="Duplicate document upload is not allowed.",
        )


class InternalServerError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_ERROR",
            message="Unexpected error.",
        )


class ChatSessionNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="CHAT_SESSION_NOT_FOUND",
            message="Chat session does not exist or should not be revealed.",
        )


class ChatSessionTitleTooLongError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="CHAT_SESSION_TITLE_TOO_LONG",
            message="Chat session title is too long.",
        )


class ChatMessageContentInvalidError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="CHAT_MESSAGE_CONTENT_INVALID",
            message="Chat message content is invalid.",
        )


class ChatMessageContentTooLongError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="CHAT_MESSAGE_CONTENT_TOO_LONG",
            message="Chat message content is too long.",
        )


class ChatMessageMetricsInvalidError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="CHAT_MESSAGE_METRICS_INVALID",
            message="Chat message metrics are invalid.",
        )


class ChatRetrievalFailedError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="CHAT_RETRIEVAL_FAILED",
            message="Chat retrieval failed.",
        )


class LLMNotConfiguredApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="LLM_NOT_CONFIGURED",
            message="The LLM provider is not configured.",
        )


class LLMProviderUnsupportedApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="LLM_PROVIDER_UNSUPPORTED",
            message="The LLM provider is not supported.",
        )


class LLMProviderAuthenticationFailedStandardApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="LLM_PROVIDER_AUTHENTICATION_FAILED",
            message="The LLM provider authentication failed.",
        )


class LLMProviderRateLimitedStandardApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="LLM_PROVIDER_RATE_LIMITED",
            message="The LLM provider is rate limited.",
        )


class LLMProviderTimeoutStandardApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            code="LLM_PROVIDER_TIMEOUT",
            message="The LLM provider timed out.",
        )


class LLMProviderBadResponseApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="LLM_PROVIDER_BAD_RESPONSE",
            message="The LLM provider returned an invalid response.",
        )


class LLMRequestRejectedApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="LLM_REQUEST_REJECTED",
            message="The LLM request was rejected by the provider.",
        )


class LLMProviderUnavailableApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="LLM_PROVIDER_UNAVAILABLE",
            message="The LLM provider is unavailable.",
        )


class LLMTimeoutApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            code="LLM_TIMEOUT",
            message="The LLM provider timed out.",
        )


class LLMAuthenticationFailedApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="LLM_AUTHENTICATION_FAILED",
            message="The LLM provider authentication failed.",
        )


class LLMRateLimitedApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="LLM_RATE_LIMITED",
            message="The LLM provider is rate limited.",
        )


class LLMResponseInvalidApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="LLM_RESPONSE_INVALID",
            message="The LLM provider returned an invalid response.",
        )


class LLMGenerationFailedApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="LLM_GENERATION_FAILED",
            message="The LLM generation operation failed.",
        )


class CitationValidationFailedApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="CITATION_VALIDATION_FAILED",
            message="The LLM provider returned invalid citation markers.",
        )


class CitationMappingFailedApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="CITATION_MAPPING_FAILED",
            message="The generated citation markers could not be mapped safely.",
        )


class CitationPersistenceFailedApplicationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="CITATION_PERSISTENCE_FAILED",
            message="Citations could not be persisted.",
        )


class FeedbackTargetNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FEEDBACK_TARGET_NOT_FOUND",
            message="Feedback target does not exist or should not be revealed.",
        )


class FeedbackRatingInvalidError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="FEEDBACK_RATING_INVALID",
            message="Feedback rating is invalid.",
        )


class FeedbackReasonTooLongError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="FEEDBACK_REASON_TOO_LONG",
            message="Feedback reason is too long.",
        )


class FeedbackDateRangeInvalidError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="FEEDBACK_DATE_RANGE_INVALID",
            message="Feedback report date range is invalid.",
        )


class FeedbackReportForbiddenError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FEEDBACK_REPORT_FORBIDDEN",
            message="You do not have permission to view feedback reports.",
        )


class FeedbackReportScopeUnavailableError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FEEDBACK_REPORT_SCOPE_UNAVAILABLE",
            message="Feedback report scope is unavailable for this user.",
        )


class FeedbackOperationFailedError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="FEEDBACK_OPERATION_FAILED",
            message="Feedback operation failed.",
        )


class AuditReportForbiddenError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="AUDIT_REPORT_FORBIDDEN",
            message="You do not have permission to view audit logs.",
        )


class AuditDateRangeInvalidError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="AUDIT_DATE_RANGE_INVALID",
            message="Audit report date range is invalid.",
        )


class AuditFilterInvalidError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="AUDIT_FILTER_INVALID",
            message="Audit report filter is invalid.",
        )


class AuditEventInvalidError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="AUDIT_EVENT_INVALID",
            message="Audit event is invalid.",
        )


class AuditMetadataInvalidError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="AUDIT_METADATA_INVALID",
            message="Audit metadata is invalid.",
        )


class AuditOperationFailedError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="AUDIT_OPERATION_FAILED",
            message="Audit operation failed.",
        )


class DocumentFileUnavailableError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_410_GONE,
            code="DOCUMENT_FILE_UNAVAILABLE",
            message="Document file is unavailable.",
        )


class DocumentPermissionAlreadyExistsError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="DOCUMENT_PERMISSION_ALREADY_EXISTS",
            message="Document permission already exists.",
        )


class DepartmentHasDocumentsError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="DEPARTMENT_HAS_DOCUMENTS",
            message="Department has scoped documents.",
        )


class UserEmailAlreadyExistsError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="USER_EMAIL_ALREADY_EXISTS",
            message="Email is already in use.",
        )


class DepartmentNameAlreadyExistsError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="DEPARTMENT_NAME_ALREADY_EXISTS",
            message="Department name already exists.",
        )


class DepartmentCodeAlreadyExistsError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="DEPARTMENT_CODE_ALREADY_EXISTS",
            message="Department code already exists.",
        )


class DepartmentInUseError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="DEPARTMENT_IN_USE",
            message="Department still has active users.",
        )


class LastActiveAdminError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="LAST_ACTIVE_ADMIN",
            message="Cannot remove the last active Admin.",
        )


class SelfModificationNotAllowedError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="SELF_MODIFICATION_NOT_ALLOWED",
            message="Admins cannot change their own role or active status with this API.",
        )


async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        headers=_security_headers(exc.headers),
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": None,
            }
        },
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "Unhandled API error.",
        extra={"error_type": exc.__class__.__name__, "method": request.method},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers=_security_headers(),
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error.",
                "details": None,
                "request_id": None,
            }
        },
    )


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    code, message = (
        _audit_validation_error_code(request, exc)
        or _feedback_validation_error_code(request, exc)
        or (
            "VALIDATION_ERROR",
            "Request is invalid.",
        )
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        headers=_security_headers(),
        content={
            "error": {
                "code": code,
                "message": message,
                "details": None,
                "request_id": None,
            }
        },
    )


def _security_headers(headers: dict[str, str] | None = None) -> dict[str, str]:
    merged = dict(SECURITY_RESPONSE_HEADERS)
    if headers:
        merged.update(headers)
    return merged


def _feedback_validation_error_code(
    request: Request,
    exc: RequestValidationError,
) -> tuple[str, str] | None:
    if "/feedback" not in request.url.path:
        return None
    for error in exc.errors():
        loc = tuple(str(part) for part in error.get("loc", ()))
        field = loc[-1] if loc else ""
        if field == "rating":
            return "FEEDBACK_RATING_INVALID", "Feedback rating is invalid."
        if field == "reason" and error.get("type") == "string_too_long":
            return "FEEDBACK_REASON_TOO_LONG", "Feedback reason is too long."
    return None


def _audit_validation_error_code(
    request: Request,
    exc: RequestValidationError,
) -> tuple[str, str] | None:
    if "/audit-logs" not in request.url.path:
        return None
    for error in exc.errors():
        loc = tuple(str(part) for part in error.get("loc", ()))
        field = loc[-1] if loc else ""
        if field in {"date_from", "date_to"}:
            return "AUDIT_DATE_RANGE_INVALID", "Audit report date range is invalid."
    return "AUDIT_FILTER_INVALID", "Audit report filter is invalid."
