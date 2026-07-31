import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RefreshTokenRequest


def test_login_request_normalizes_email() -> None:
    request = LoginRequest(email="  ADMIN@EXAMPLE.COM  ", password="not-printed-password")

    assert request.email == "admin@example.com"


def test_login_request_accepts_reserved_test_domain() -> None:
    request = LoginRequest(email="  ADMIN.UAT@EXAMPLE.TEST  ", password="not-printed-password")

    assert request.email == "admin.uat@example.test"


def test_login_request_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email="not-an-email", password="not-printed-password")


def test_login_request_repr_does_not_expose_password() -> None:
    request = LoginRequest(email="admin@example.com", password="not-printed-password")

    assert "not-printed-password" not in repr(request)


def test_refresh_token_request_repr_does_not_expose_token() -> None:
    request = RefreshTokenRequest(refresh_token="not-printed-refresh-token")

    assert "not-printed-refresh-token" not in repr(request)