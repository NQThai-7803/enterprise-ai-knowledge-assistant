from app.core.security import generate_refresh_token, hash_refresh_token


def test_generate_refresh_token_returns_non_empty_token() -> None:
    assert generate_refresh_token()


def test_generate_refresh_token_returns_unique_values() -> None:
    assert generate_refresh_token() != generate_refresh_token()


def test_hash_refresh_token_is_deterministic() -> None:
    token = generate_refresh_token()

    assert hash_refresh_token(token) == hash_refresh_token(token)


def test_hash_refresh_token_is_not_raw_token() -> None:
    token = generate_refresh_token()

    assert hash_refresh_token(token) != token


def test_hash_refresh_token_has_sha256_hex_length() -> None:
    token_hash = hash_refresh_token(generate_refresh_token())

    assert len(token_hash) == 64
    int(token_hash, 16)
