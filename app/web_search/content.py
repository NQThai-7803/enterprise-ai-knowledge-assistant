from __future__ import annotations

import ipaddress
import re
import unicodedata
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit

_WHITESPACE_RE = re.compile(r"\s+")
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript|template)\b[^>]*>.*?</\1>",
    flags=re.IGNORECASE | re.DOTALL,
)
_COMMENT_RE = re.compile(r"<!--.*?-->", flags=re.DOTALL)
_BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}
_HIDDEN_STYLE_MARKERS = (
    "display:none",
    "visibility:hidden",
    "opacity:0",
    "font-size:0",
)
_MAX_URL_LENGTH = 2048


class _VisibleTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        attrs_by_name = {name.lower(): (value or "") for name, value in attrs}
        if normalized_tag in {"script", "style", "noscript", "template"} or _is_hidden(
            attrs_by_name
        ):
            self.hidden_depth += 1
            return
        if self.hidden_depth == 0 and normalized_tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if self.hidden_depth > 0 and normalized_tag in {
            "script",
            "style",
            "noscript",
            "template",
            "span",
            "div",
            "p",
        }:
            self.hidden_depth -= 1
            return
        if self.hidden_depth == 0 and normalized_tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self.hidden_depth == 0:
            self.parts.append(data)

    def text(self) -> str:
        return " ".join(self.parts)


def clean_web_text(value: str | None, *, max_length: int) -> str:
    if max_length <= 0:
        msg = "max_length must be positive."
        raise ValueError(msg)
    if value is None:
        return ""
    bounded = str(value)[: max_length * 4]
    without_blocks = _SCRIPT_STYLE_RE.sub(" ", bounded)
    without_comments = _COMMENT_RE.sub(" ", without_blocks)
    parser = _VisibleTextExtractor()
    try:
        parser.feed(without_comments)
        parser.close()
        extracted = parser.text()
    except Exception:
        extracted = without_comments
    decoded = unescape(extracted)
    visible = "".join(_visible_character(char) for char in decoded)
    normalized = _WHITESPACE_RE.sub(" ", visible).strip()
    return normalized[:max_length].strip()


def normalize_web_url(value: str, *, return_hostname: bool = False) -> str:
    if not isinstance(value, str):
        msg = "Web URL is invalid."
        raise ValueError(msg)
    candidate = value.strip()
    if not candidate or len(candidate) > _MAX_URL_LENGTH:
        msg = "Web URL is invalid."
        raise ValueError(msg)
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        msg = "Web URL is invalid."
        raise ValueError(msg)
    try:
        _ = parsed.port
    except ValueError as exc:
        msg = "Web URL is invalid."
        raise ValueError(msg) from exc
    if parsed.username or parsed.password:
        msg = "Web URL is invalid."
        raise ValueError(msg)
    hostname = parsed.hostname.strip().lower().strip("[]")
    if _is_blocked_hostname(hostname):
        msg = "Web URL host is not allowed."
        raise ValueError(msg)
    if return_hostname:
        return hostname
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path or "",
            parsed.query or "",
            "",
        )
    )


def _visible_character(char: str) -> str:
    if char in {"\n", "\r", "\t"}:
        return " "
    category = unicodedata.category(char)
    if category in {"Cf", "Cc", "Cs", "Co", "Cn"}:
        return ""
    return char


def _is_hidden(attrs: dict[str, str]) -> bool:
    if "hidden" in attrs or attrs.get("aria-hidden", "").strip().lower() == "true":
        return True
    normalized_style = re.sub(r"\s+", "", attrs.get("style", "").lower())
    return any(marker in normalized_style for marker in _HIDDEN_STYLE_MARKERS)


def _is_blocked_hostname(hostname: str) -> bool:
    if hostname in {"localhost", "host.docker.internal"} or hostname.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )
