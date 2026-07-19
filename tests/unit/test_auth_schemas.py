from app.schemas.auth import LoginRequest, RefreshTokenRequest


def test_login_request_normalizes_email() -> None:
    request = LoginRequest(email="  ADMIN@EXAMPLE.COM  ", password="not-printed-password")

    assert str(request.email) == "admin@example.com"


def test_login_request_repr_does_not_expose_password() -> None:
    request = LoginRequest(email="admin@example.com", password="not-printed-password")

    assert "not-printed-password" not in repr(request)


def test_refresh_token_request_repr_does_not_expose_token() -> None:
    request = RefreshTokenRequest(refresh_token="not-printed-refresh-token")

    assert "not-printed-refresh-token" not in repr(request)
