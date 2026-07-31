from __future__ import annotations

from email_validator import EmailNotValidError, validate_email


def normalize_email_address(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid email address.")

    email = value.strip().lower()
    try:
        return validate_email(
            email,
            check_deliverability=False,
            test_environment=True,
        ).normalized
    except EmailNotValidError as exc:
        raise ValueError("Invalid email address.") from exc
