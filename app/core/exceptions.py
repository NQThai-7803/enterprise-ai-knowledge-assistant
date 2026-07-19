from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


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
            code="INVALID_FILE_TYPE",
            message="File type is not supported.",
        )


class FileTooLargeError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=413,
            code="FILE_TOO_LARGE",
            message="File exceeds size limit.",
        )


class EmptyFileError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="EMPTY_FILE",
            message="File is empty.",
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
        headers=exc.headers,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": None,
            }
        },
    )


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request is invalid.",
                "details": None,
                "request_id": None,
            }
        },
    )
