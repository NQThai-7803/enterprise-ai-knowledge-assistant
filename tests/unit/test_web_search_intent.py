from __future__ import annotations

from app.core.config import Settings
from app.web_search.intent import WebSearchIntentClassifier
from app.web_search.models import KnowledgeSourceMode


def settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "web_search_provider": "mock",
        "chat_retrieval_top_k": 8,
        "citation_max_sources_per_answer": 8,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def classify(question: str, *, internal_hit_count: int, **overrides: object):
    return WebSearchIntentClassifier(settings=settings(**overrides)).classify(
        question=question,
        internal_hit_count=internal_hit_count,
    )


def test_disabled_web_search_forces_internal_only() -> None:
    intent = classify(
        "latest policy update",
        internal_hit_count=0,
        web_search_enabled=False,
        web_search_mode="hybrid",
    )

    assert intent.source_mode == KnowledgeSourceMode.INTERNAL_ONLY
    assert intent.needs_web is False
    assert intent.use_internal is True


def test_web_only_mode_skips_internal_sources() -> None:
    intent = classify(
        "company homepage",
        internal_hit_count=5,
        web_search_enabled=True,
        web_search_mode="web_only",
    )

    assert intent.source_mode == KnowledgeSourceMode.WEB_ONLY
    assert intent.needs_web is True
    assert intent.use_internal is False


def test_hybrid_uses_web_when_internal_has_no_hits() -> None:
    intent = classify(
        "What is the support policy?",
        internal_hit_count=0,
        web_search_enabled=True,
        web_search_mode="hybrid",
    )

    assert intent.needs_web is True
    assert intent.use_internal is True
    assert intent.reason == "no_internal_hits"


def test_hybrid_uses_web_for_current_or_url_intent() -> None:
    current = classify(
        "latest Microsoft Learn update",
        internal_hit_count=2,
        web_search_enabled=True,
        web_search_mode="hybrid",
    )
    url = classify(
        "Summarize example.com docs",
        internal_hit_count=2,
        web_search_enabled=True,
        web_search_mode="hybrid",
    )

    assert current.needs_web is True
    assert url.needs_web is True


def test_hybrid_stays_internal_when_internal_context_is_enough() -> None:
    intent = classify(
        "Explain the annual leave policy",
        internal_hit_count=3,
        web_search_enabled=True,
        web_search_mode="hybrid",
    )

    assert intent.needs_web is False
    assert intent.use_internal is True
