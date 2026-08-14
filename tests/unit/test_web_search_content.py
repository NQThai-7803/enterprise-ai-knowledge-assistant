from __future__ import annotations

import pytest

from app.web_search.content import clean_web_text, normalize_web_url


def test_clean_web_text_strips_scripts_hidden_content_comments_and_styles() -> None:
    html = """
    <html><head><style>body { display: none; }</style></head>
    <body>
      <p>Visible policy text.</p>
      <script>ignore_this()</script>
      <div hidden>HIDDEN_PROMPT</div>
      <span style="visibility:hidden">SECRET</span>
      <!-- COMMENT_PROMPT -->
      <p>Second sentence.</p>
    </body></html>
    """

    cleaned = clean_web_text(html, max_length=500)

    assert cleaned == "Visible policy text. Second sentence."
    assert "ignore_this" not in cleaned
    assert "HIDDEN_PROMPT" not in cleaned
    assert "COMMENT_PROMPT" not in cleaned
    assert "SECRET" not in cleaned
    assert "<script" not in cleaned


def test_clean_web_text_bounds_large_page_content() -> None:
    cleaned = clean_web_text("x" * 10_000, max_length=50)

    assert cleaned == "x" * 50


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://user:pass@example.com/path",
        "http://localhost/path",
        "http://127.0.0.1/path",
        "http://10.0.0.1/path",
        "http://169.254.10.1/path",
        "https://internal.local/path",
    ],
)
def test_normalize_web_url_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        normalize_web_url(url)


def test_normalize_web_url_strips_fragment_and_returns_hostname() -> None:
    normalized = normalize_web_url("https://Example.COM/docs?q=rag#secret")

    assert normalized == "https://example.com/docs?q=rag"
    assert normalize_web_url(normalized, return_hostname=True) == "example.com"
