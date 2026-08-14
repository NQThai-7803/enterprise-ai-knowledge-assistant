from __future__ import annotations

from math import inf, nan

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_default_retrieval_top_k() -> None:
    assert make_settings().retrieval_top_k == 10


def test_default_min_relevance_score() -> None:
    assert make_settings().min_relevance_score == 0.50


def test_top_k_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make_settings(retrieval_top_k=0)


def test_default_top_k_cannot_exceed_maximum() -> None:
    with pytest.raises(ValidationError):
        make_settings(retrieval_top_k=51, retrieval_max_top_k=50)


def test_min_relevance_score_must_be_in_range() -> None:
    with pytest.raises(ValidationError):
        make_settings(min_relevance_score=-0.01)
    with pytest.raises(ValidationError):
        make_settings(min_relevance_score=1.01)


def test_max_query_characters_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make_settings(retrieval_max_query_characters=0)


def test_nan_threshold_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(min_relevance_score=nan)


def test_infinite_threshold_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(min_relevance_score=inf)


def test_default_keyword_retrieval_settings() -> None:
    settings = make_settings()

    assert settings.keyword_retrieval_top_k == 20
    assert settings.keyword_retrieval_max_top_k == 100
    assert settings.keyword_min_rank == 0.0


def test_keyword_top_k_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make_settings(keyword_retrieval_top_k=0)


def test_default_keyword_top_k_cannot_exceed_maximum() -> None:
    with pytest.raises(ValidationError):
        make_settings(keyword_retrieval_top_k=101, keyword_retrieval_max_top_k=100)


def test_keyword_min_rank_must_be_non_negative_and_finite() -> None:
    with pytest.raises(ValidationError):
        make_settings(keyword_min_rank=-0.01)
    with pytest.raises(ValidationError):
        make_settings(keyword_min_rank=nan)
    with pytest.raises(ValidationError):
        make_settings(keyword_min_rank=inf)


def test_default_hybrid_retrieval_settings() -> None:
    settings = make_settings()

    assert settings.hybrid_retrieval_top_k == 10
    assert settings.hybrid_retrieval_max_top_k == 50
    assert settings.hybrid_candidate_multiplier == 4
    assert settings.hybrid_rrf_k == 60
    assert settings.hybrid_semantic_weight == 1.0
    assert settings.hybrid_keyword_weight == 1.0
    assert settings.hybrid_semantic_min_relevance_score == 0.30


def test_hybrid_top_k_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_retrieval_top_k=0)


def test_default_hybrid_top_k_cannot_exceed_maximum() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_retrieval_top_k=51, hybrid_retrieval_max_top_k=50)


def test_hybrid_candidate_multiplier_must_be_at_least_one() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_candidate_multiplier=0)


def test_hybrid_rrf_k_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_rrf_k=0)


def test_hybrid_weights_must_not_both_be_zero() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_semantic_weight=0.0, hybrid_keyword_weight=0.0)


def test_hybrid_semantic_min_relevance_score_must_be_in_range() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_semantic_min_relevance_score=-0.01)
    with pytest.raises(ValidationError):
        make_settings(hybrid_semantic_min_relevance_score=1.01)


def test_hybrid_float_settings_reject_nan_and_infinity() -> None:
    with pytest.raises(ValidationError):
        make_settings(hybrid_semantic_weight=nan)
    with pytest.raises(ValidationError):
        make_settings(hybrid_keyword_weight=inf)
    with pytest.raises(ValidationError):
        make_settings(hybrid_semantic_min_relevance_score=nan)


def test_default_chat_settings() -> None:
    settings = make_settings()

    assert settings.chat_session_title_max_characters == 200
    assert settings.chat_session_list_page_size == 20
    assert settings.chat_session_list_max_page_size == 100
    assert settings.chat_history_page_size == 50
    assert settings.chat_history_max_page_size == 100
    assert settings.chat_message_max_characters == 12000


def test_chat_title_max_characters_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make_settings(chat_session_title_max_characters=0)


def test_chat_session_default_page_size_cannot_exceed_maximum() -> None:
    with pytest.raises(ValidationError):
        make_settings(chat_session_list_page_size=101, chat_session_list_max_page_size=100)


def test_chat_history_default_page_size_cannot_exceed_maximum() -> None:
    with pytest.raises(ValidationError):
        make_settings(chat_history_page_size=101, chat_history_max_page_size=100)


def test_chat_message_max_characters_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make_settings(chat_message_max_characters=0)


def test_chat_integer_settings_reject_boolean_values() -> None:
    with pytest.raises(ValidationError):
        make_settings(chat_history_page_size=True)


def test_default_llm_and_chat_answer_settings() -> None:
    settings = make_settings()

    assert settings.llm_enabled is False
    assert settings.llm_provider == "openai_compatible"
    assert settings.llm_base_url == ""
    assert settings.llm_api_key.get_secret_value() == ""
    assert settings.llm_model == ""
    assert settings.llm_timeout_seconds == 30.0
    assert settings.llm_max_retries == 2
    assert settings.llm_retry_backoff_seconds == 1.0
    assert settings.llm_temperature == 0.0
    assert settings.llm_max_output_tokens == 1024
    assert settings.llm_no_answer_sentinel == "__NO_ANSWER__"
    assert settings.chat_retrieval_top_k == 10
    assert settings.chat_history_max_messages == 10
    assert settings.chat_history_max_tokens == 1200
    assert settings.chat_context_max_tokens == 6000
    assert settings.chat_no_answer_message.strip()


def test_llm_selected_provider_config_required_only_when_enabled() -> None:
    make_settings(llm_enabled=False, llm_model="")
    with pytest.raises(ValidationError):
        make_settings(llm_enabled=True, llm_model="", llm_base_url="")
    make_settings(
        llm_enabled=True,
        llm_model="fake",
        llm_base_url="http://localhost:11434/v1",
    )


def test_llm_timing_and_generation_settings_validation() -> None:
    with pytest.raises(ValidationError):
        make_settings(llm_timeout_seconds=0)
    with pytest.raises(ValidationError):
        make_settings(llm_max_retries=-1)
    with pytest.raises(ValidationError):
        make_settings(llm_retry_backoff_seconds=-0.1)
    with pytest.raises(ValidationError):
        make_settings(llm_temperature=-0.1)
    with pytest.raises(ValidationError):
        make_settings(llm_temperature=2.1)
    with pytest.raises(ValidationError):
        make_settings(llm_max_output_tokens=0)


def test_llm_float_settings_reject_nan_and_infinity() -> None:
    with pytest.raises(ValidationError):
        make_settings(llm_timeout_seconds=nan)
    with pytest.raises(ValidationError):
        make_settings(llm_retry_backoff_seconds=inf)
    with pytest.raises(ValidationError):
        make_settings(llm_temperature=nan)


def test_chat_answer_settings_validation() -> None:
    with pytest.raises(ValidationError):
        make_settings(llm_no_answer_sentinel="")
    with pytest.raises(ValidationError):
        make_settings(chat_retrieval_top_k=0)
    with pytest.raises(ValidationError):
        make_settings(chat_history_max_messages=-1)
    with pytest.raises(ValidationError):
        make_settings(chat_history_max_tokens=-1)
    with pytest.raises(ValidationError):
        make_settings(chat_context_max_tokens=0)
    with pytest.raises(ValidationError):
        make_settings(chat_no_answer_message="")


def test_default_citation_settings() -> None:
    settings = make_settings()

    assert settings.citation_excerpt_max_characters == 500
    assert settings.citation_max_sources_per_answer == 10


def test_citation_settings_validation() -> None:
    with pytest.raises(ValidationError):
        make_settings(citation_excerpt_max_characters=0)
    with pytest.raises(ValidationError):
        make_settings(citation_max_sources_per_answer=0)
    with pytest.raises(ValidationError):
        make_settings(chat_retrieval_top_k=2, citation_max_sources_per_answer=3)
    with pytest.raises(ValidationError):
        make_settings(citation_excerpt_max_characters=True)


def test_llm_integer_settings_reject_boolean_values() -> None:
    with pytest.raises(ValidationError):
        make_settings(llm_max_retries=True)
    with pytest.raises(ValidationError):
        make_settings(chat_retrieval_top_k=True)
    with pytest.raises(ValidationError):
        make_settings(chat_history_max_tokens=True)


def test_default_ocr_settings() -> None:
    settings = make_settings()

    assert settings.ocr_enabled is True
    assert settings.ocr_languages == ["vie", "eng"]
    assert settings.ocr_max_pages == 100
    assert settings.ocr_render_dpi == 200
    assert settings.ocr_max_image_pixels == 40_000_000
    assert settings.ocr_page_timeout_seconds == 30
    assert settings.ocr_document_timeout_seconds == 240
    assert settings.ocr_max_extracted_characters == 2_000_000


def test_ocr_languages_are_normalized_and_deduplicated() -> None:
    settings = make_settings(ocr_languages=" ENG, vie,eng ")

    assert settings.ocr_languages == ["eng", "vie"]


def test_ocr_rejects_unsupported_language() -> None:
    with pytest.raises(ValidationError):
        make_settings(ocr_languages="eng,fra")


def test_ocr_document_timeout_must_fit_worker_soft_time_limit() -> None:
    with pytest.raises(ValidationError):
        make_settings(ocr_document_timeout_seconds=30, celery_task_soft_time_limit_seconds=30)


def test_ocr_dimension_and_pixel_limits_are_independent() -> None:
    settings = make_settings(ocr_max_image_width=3, ocr_max_image_height=10)

    assert settings.ocr_max_image_width == 3
    assert settings.ocr_max_image_pixels == 40_000_000


def test_ocr_integer_and_float_settings_reject_invalid_values() -> None:
    with pytest.raises(ValidationError):
        make_settings(ocr_max_pages=True)
    with pytest.raises(ValidationError):
        make_settings(ocr_native_text_min_alnum_ratio=nan)
    with pytest.raises(ValidationError):
        make_settings(ocr_max_replacement_character_ratio=inf)


def test_default_web_search_settings() -> None:
    settings = make_settings()

    assert settings.web_search_enabled is False
    assert settings.web_search_mode == "internal_only"
    assert settings.web_search_provider == "mock"
    assert settings.web_search_max_results == 3
    assert settings.web_search_timeout_seconds == 5.0
    assert settings.web_search_max_content_length == 2000
    assert settings.web_search_allow_external is False
    assert settings.web_search_user_agent.strip()


def test_web_search_numeric_settings_validation() -> None:
    with pytest.raises(ValidationError):
        make_settings(web_search_max_results=0)
    with pytest.raises(ValidationError):
        make_settings(web_search_timeout_seconds=0)
    with pytest.raises(ValidationError):
        make_settings(web_search_max_content_length=0)
    with pytest.raises(ValidationError):
        make_settings(web_search_max_retries=-1)
    with pytest.raises(ValidationError):
        make_settings(web_search_retry_backoff_seconds=-0.1)
    with pytest.raises(ValidationError):
        make_settings(web_search_timeout_seconds=nan)


def test_web_search_endpoint_urls_must_be_safe() -> None:
    with pytest.raises(ValidationError):
        make_settings(web_search_bing_endpoint="javascript:alert(1)")
    with pytest.raises(ValidationError):
        make_settings(web_search_google_endpoint="https://user:pass@example.com/search")


def test_web_search_provider_names_are_normalized() -> None:
    settings = make_settings(web_search_provider="DuckDuckGo")

    assert settings.web_search_provider == "duckduckgo"
