from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.web_search.models import KnowledgeSourceMode

_CURRENT_INFORMATION_RE = re.compile(
    r"\b("
    r"latest|today|yesterday|tomorrow|current|recent|news|breaking|update|updated|"
    r"this week|this month|this year|now|online|internet|web|website|search web|"
    r"m[oơ]i nh[aấ]t|h[oô]m nay|hi[eệ]n t[aạ]i|g[aầ]n [dđ][aâ]y|tin t[uư]c|"
    r"tr[eê]n m[aạ]ng|internet|web"
    r")\b",
    flags=re.IGNORECASE,
)
_URL_OR_DOMAIN_RE = re.compile(r"(https?://|www\.|[A-Za-z0-9.-]+\.[A-Za-z]{2,})")


@dataclass(frozen=True, slots=True)
class SearchIntent:
    source_mode: KnowledgeSourceMode
    needs_web: bool
    use_internal: bool
    reason: str


class WebSearchIntentClassifier:
    def __init__(self, *, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def classify(self, *, question: str, internal_hit_count: int) -> SearchIntent:
        mode = KnowledgeSourceMode(self.settings.web_search_mode)
        if not self.settings.web_search_enabled or mode == KnowledgeSourceMode.INTERNAL_ONLY:
            return SearchIntent(
                source_mode=KnowledgeSourceMode.INTERNAL_ONLY,
                needs_web=False,
                use_internal=True,
                reason="internal_only",
            )
        if mode == KnowledgeSourceMode.WEB_ONLY:
            return SearchIntent(
                source_mode=mode,
                needs_web=True,
                use_internal=False,
                reason="web_only",
            )
        normalized_question = question.strip()
        if internal_hit_count <= 0:
            return SearchIntent(
                source_mode=mode,
                needs_web=True,
                use_internal=True,
                reason="no_internal_hits",
            )
        if _CURRENT_INFORMATION_RE.search(normalized_question) or _URL_OR_DOMAIN_RE.search(
            normalized_question
        ):
            return SearchIntent(
                source_mode=mode,
                needs_web=True,
                use_internal=True,
                reason="current_or_web_intent",
            )
        return SearchIntent(
            source_mode=mode,
            needs_web=False,
            use_internal=True,
            reason="internal_context_available",
        )
