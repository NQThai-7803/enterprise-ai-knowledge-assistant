from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.embeddings.constants import (
    EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS,
    EMBEDDING_SCHEMA_DIMENSIONS,
)
from app.llm.provider_names import (
    ANTHROPIC_PROVIDER,
    AZURE_OPENAI_PROVIDER,
    GEMINI_PROVIDER,
    LM_STUDIO_PROVIDER,
    OLLAMA_PROVIDER,
    OPENAI_COMPATIBLE_PROVIDER,
    OPENROUTER_PROVIDER,
    SUPPORTED_PROVIDER_NAMES,
    normalize_provider_name,
)
from app.web_search.provider_names import (
    BING_PROVIDER,
    DUCKDUCKGO_PROVIDER,
    GOOGLE_CUSTOM_SEARCH_PROVIDER,
    MOCK_PROVIDER,
    SUPPORTED_WEB_SEARCH_PROVIDERS,
    normalize_web_search_provider_name,
)

PLACEHOLDER_SECRET_KEYS = {
    "",
    "change-me",
    "change-me-for-local-development",
    "changeme",
    "development-secret",
    "example",
    "replace-me",
    "replace-with-a-long-random-secret-key",
    "replace-with-production-postgres-password",
    "replace-with-production-secret-key",
    "secret",
    "your-secret-here",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "Enterprise AI Knowledge Assistant"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    debug: bool = Field(default=False, repr=False, validation_alias="DEBUG")
    api_v1_prefix: str = "/api/v1"
    api_docs_enabled: bool = True
    secret_key: str = Field(
        default="replace-with-a-long-random-secret-key",
        repr=False,
    )
    secret_key_file: str = Field(default="", repr=False)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "enterprise-ai-knowledge-assistant"
    jwt_audience: str = "enterprise-ai-api"
    access_token_expire_minutes: int = Field(default=15, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)
    database_url: str = Field(default="postgresql+asyncpg:///enterprise_ai", repr=False)
    database_url_file: str = Field(default="", repr=False)
    dev_admin_email: str = "admin@example.com"
    dev_admin_full_name: str = "Development Admin"
    dev_admin_password: str = ""
    storage_backend: Literal["local"] = "local"
    local_storage_path: str = Field(default="./data/uploads", min_length=1)
    max_upload_size_mb: int = Field(default=25, gt=0)
    upload_chunk_size_bytes: int = Field(default=1_048_576, gt=0)
    pdf_max_pages: int = Field(default=500, gt=0)
    pdf_min_usable_characters: int = Field(default=20, ge=0)
    pdf_text_sort: bool = True
    ocr_enabled: bool = True
    ocr_languages: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["vie", "eng"])
    ocr_max_pages: int = Field(default=100, ge=1, le=1000)
    ocr_render_dpi: int = Field(default=200, ge=72, le=400)
    ocr_max_image_pixels: int = Field(default=40_000_000, ge=1, le=200_000_000)
    ocr_max_image_width: int = Field(default=10_000, ge=1, le=20_000)
    ocr_max_image_height: int = Field(default=10_000, ge=1, le=20_000)
    ocr_page_timeout_seconds: int = Field(default=30, ge=1, le=600)
    ocr_document_timeout_seconds: int = Field(default=240, ge=1, le=3600)
    ocr_max_extracted_characters: int = Field(default=2_000_000, ge=1, le=10_000_000)
    ocr_native_text_min_characters_per_page: int = Field(default=40, ge=0, le=10_000)
    ocr_native_text_min_alnum_ratio: float = Field(default=0.35, ge=0.0, le=1.0)
    ocr_max_replacement_character_ratio: float = Field(default=0.05, ge=0.0, le=1.0)
    ocr_max_control_character_ratio: float = Field(default=0.02, ge=0.0, le=1.0)
    tokenizer_encoding_name: str = Field(default="cl100k_base", min_length=1)
    chunk_target_tokens: int = Field(default=500, gt=0)
    chunk_max_tokens: int = Field(default=700, gt=0)
    chunk_overlap_tokens: int = Field(default=75, ge=0)
    chunk_min_tokens: int = Field(default=50, ge=0)
    embedding_provider: Literal["sentence_transformers"] = EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS
    embedding_model_name: str = Field(default="intfloat/multilingual-e5-small", min_length=1)
    embedding_model_revision: str = ""
    embedding_dimensions: int = Field(default=EMBEDDING_SCHEMA_DIMENSIONS, gt=0)
    embedding_device: str = Field(default="cpu", min_length=1)
    embedding_batch_size: int = Field(default=16, gt=0)
    embedding_normalize: bool = True
    embedding_query_prefix: str = Field(default="query: ", min_length=1)
    embedding_passage_prefix: str = Field(default="passage: ", min_length=1)
    embedding_local_files_only: bool = False
    embedding_model_cache_path: str = Field(default="./data/models", min_length=1)
    retrieval_top_k: int = Field(default=10, gt=0)
    retrieval_max_top_k: int = Field(default=50, gt=0)
    min_relevance_score: float = Field(default=0.50, ge=0.0, le=1.0)
    retrieval_max_query_characters: int = Field(default=4000, gt=0)
    keyword_retrieval_top_k: int = Field(default=20, gt=0)
    keyword_retrieval_max_top_k: int = Field(default=100, gt=0)
    keyword_min_rank: float = Field(default=0.0, ge=0.0)
    hybrid_retrieval_top_k: int = Field(default=10, gt=0)
    hybrid_retrieval_max_top_k: int = Field(default=50, gt=0)
    hybrid_candidate_multiplier: int = Field(default=4, ge=1)
    hybrid_rrf_k: int = Field(default=60, gt=0)
    hybrid_semantic_weight: float = Field(default=1.0, ge=0.0)
    hybrid_keyword_weight: float = Field(default=1.0, ge=0.0)
    hybrid_semantic_min_relevance_score: float = Field(default=0.30, ge=0.0, le=1.0)
    reranker_enabled: bool = True
    reranker_provider: Literal["sentence_transformers", "heuristic"] = "sentence_transformers"
    reranker_model: str = Field(default="BAAI/bge-reranker-v2-m3", min_length=1)
    reranker_model_revision: str = ""
    reranker_device: str = Field(default="cpu", min_length=1)
    reranker_batch_size: int = Field(default=4, gt=0)
    reranker_top_k: int = Field(
        default=6,
        gt=0,
        validation_alias=AliasChoices("RERANKER_TOP_K", "RERANK_TOP_K"),
    )
    reranker_candidate_k: int = Field(default=50, gt=0)
    reranker_max_length: int = Field(default=512, gt=0)
    reranker_timeout_seconds: float = Field(default=10.0, gt=0.0, le=120.0)
    reranker_local_files_only: bool = True
    reranker_model_cache_path: str = Field(default="./data/models", min_length=1)
    claim_validation_enabled: bool = True
    rag_diagnostics_enabled: bool = False
    chat_session_title_max_characters: int = Field(default=200, gt=0)
    chat_session_list_page_size: int = Field(default=20, gt=0)
    chat_session_list_max_page_size: int = Field(default=100, gt=0)
    chat_history_page_size: int = Field(default=50, gt=0)
    chat_history_max_page_size: int = Field(default=100, gt=0)
    chat_message_max_characters: int = Field(default=12000, gt=0)
    llm_enabled: bool = False
    llm_provider: str = OPENAI_COMPATIBLE_PROVIDER
    llm_model: str = ""
    llm_timeout_seconds: float = Field(default=30.0, gt=0.0)
    llm_stream_heartbeat_seconds: float = Field(default=15.0, gt=0.0, le=300.0)
    llm_stream_max_duration_seconds: float = Field(default=120.0, gt=0.0, le=3600.0)
    llm_max_retries: int = Field(default=2, ge=0)
    llm_retry_backoff_seconds: float = Field(default=1.0, ge=0.0)
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_max_output_tokens: int = Field(default=1024, gt=0)
    llm_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_OPENAI_BASE_URL", "LLM_BASE_URL"),
    )
    llm_api_key: SecretStr = Field(
        default_factory=lambda: SecretStr(""),
        repr=False,
        validation_alias=AliasChoices("LLM_OPENAI_API_KEY", "LLM_API_KEY"),
    )
    llm_api_key_file: str = Field(default="", repr=False)
    llm_azure_endpoint: str = Field(default="", repr=False)
    llm_azure_api_key: SecretStr = Field(default_factory=lambda: SecretStr(""), repr=False)
    llm_azure_api_key_file: str = Field(default="", repr=False)
    llm_azure_deployment: str = ""
    llm_azure_api_version: str = ""
    llm_gemini_api_key: SecretStr = Field(default_factory=lambda: SecretStr(""), repr=False)
    llm_gemini_api_key_file: str = Field(default="", repr=False)
    llm_gemini_model: str = ""
    llm_gemini_base_url: str = Field(default="https://generativelanguage.googleapis.com")
    llm_anthropic_api_key: SecretStr = Field(default_factory=lambda: SecretStr(""), repr=False)
    llm_anthropic_api_key_file: str = Field(default="", repr=False)
    llm_anthropic_model: str = ""
    llm_anthropic_version: str = "2023-06-01"
    llm_anthropic_base_url: str = Field(default="https://api.anthropic.com")
    llm_ollama_base_url: str = Field(default="http://host.docker.internal:11434")
    llm_ollama_model: str = ""
    llm_ollama_reasoning_effort: Literal["", "none", "low", "medium", "high"] = "none"
    llm_ollama_num_ctx: int = Field(default=4096, ge=1024, le=32768)
    llm_ollama_keep_alive: str = "10m"
    llm_lm_studio_base_url: str = Field(default="http://host.docker.internal:1234/v1")
    llm_lm_studio_model: str = ""
    llm_openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    llm_openrouter_api_key: SecretStr = Field(default_factory=lambda: SecretStr(""), repr=False)
    llm_openrouter_api_key_file: str = Field(default="", repr=False)
    llm_openrouter_model: str = ""
    llm_no_answer_sentinel: str = Field(default="__NO_ANSWER__", min_length=1)
    chat_retrieval_top_k: int = Field(default=10, gt=0)
    chat_history_max_messages: int = Field(default=10, ge=0)
    chat_history_max_tokens: int = Field(default=1200, ge=0)
    chat_context_max_tokens: int = Field(default=6000, gt=0)
    chat_no_answer_message: str = Field(
        default=(
            "Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap "
            "de tra loi cau hoi nay."
        ),
        min_length=1,
    )
    web_search_enabled: bool = False
    web_search_mode: Literal["internal_only", "hybrid", "web_only"] = "internal_only"
    web_search_provider: str = MOCK_PROVIDER
    web_search_max_results: int = Field(default=3, gt=0, le=20)
    web_search_timeout_seconds: float = Field(default=5.0, gt=0.0, le=60.0)
    web_search_max_content_length: int = Field(default=2000, gt=0, le=20_000)
    web_search_allow_external: bool = False
    web_search_user_agent: str = Field(
        default="EnterpriseAIKnowledgeAssistant/1.0",
        min_length=1,
        max_length=200,
    )
    web_search_max_retries: int = Field(default=1, ge=0, le=5)
    web_search_retry_backoff_seconds: float = Field(default=0.5, ge=0.0, le=30.0)
    web_search_bing_endpoint: str = Field(
        default="https://api.bing.microsoft.com/v7.0/search",
        repr=False,
    )
    web_search_bing_api_key: SecretStr = Field(default_factory=lambda: SecretStr(""), repr=False)
    web_search_bing_api_key_file: str = Field(default="", repr=False)
    web_search_duckduckgo_endpoint: str = Field(
        default="https://api.duckduckgo.com/",
        repr=False,
    )
    web_search_google_endpoint: str = Field(
        default="https://www.googleapis.com/customsearch/v1",
        repr=False,
    )
    web_search_google_api_key: SecretStr = Field(
        default_factory=lambda: SecretStr(""),
        repr=False,
    )
    web_search_google_api_key_file: str = Field(default="", repr=False)
    web_search_google_cx: str = Field(default="", repr=False)
    citation_excerpt_max_characters: int = Field(default=500, gt=0)
    citation_max_sources_per_answer: int = Field(default=10, gt=0)
    feedback_reason_max_characters: int = Field(default=1000, ge=1, le=1000)
    feedback_report_page_size: int = Field(default=20, gt=0)
    feedback_report_max_page_size: int = Field(default=100, gt=0)
    audit_report_page_size: int = Field(default=50, gt=0)
    audit_report_max_page_size: int = Field(default=200, gt=0)
    audit_metadata_max_length: int = Field(default=2000, gt=0)
    audit_error_code_max_length: int = Field(default=100, gt=0)
    audit_target_type_max_length: int = Field(default=64, gt=0)
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"],
        validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS", "CORS_ORIGINS"),
    )
    cors_allow_credentials: bool = True
    cors_allowed_methods: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )
    cors_allowed_headers: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["Authorization", "Content-Type", "Accept", "Origin"]
    )
    trusted_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    max_request_body_bytes: int = Field(default=26_214_400, gt=0)
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=200)
    db_pool_timeout_seconds: int = Field(default=30, ge=1, le=300)
    db_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86_400)
    db_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)
    redis_url: str = Field(default="redis://localhost:6379/0", repr=False)
    redis_url_file: str = Field(default="", repr=False)
    redis_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    redis_socket_timeout_seconds: int = Field(default=5, ge=1, le=60)
    redis_health_check_interval_seconds: int = Field(default=30, ge=1, le=3600)
    rate_limit_enabled: bool = True
    rate_limit_login_requests: int = Field(default=5, ge=1, le=10_000)
    rate_limit_login_window_seconds: int = Field(default=60, ge=1, le=86_400)
    rate_limit_refresh_requests: int = Field(default=10, ge=1, le=10_000)
    rate_limit_refresh_window_seconds: int = Field(default=60, ge=1, le=86_400)
    rate_limit_chat_requests: int = Field(default=20, ge=1, le=10_000)
    rate_limit_chat_window_seconds: int = Field(default=60, ge=1, le=86_400)
    rate_limit_upload_requests: int = Field(default=10, ge=1, le=10_000)
    rate_limit_upload_window_seconds: int = Field(default=300, ge=1, le=86_400)
    rate_limit_feedback_requests: int = Field(default=30, ge=1, le=10_000)
    rate_limit_feedback_window_seconds: int = Field(default=60, ge=1, le=86_400)
    celery_broker_url: str = Field(default="redis://localhost:6379/1", repr=False)
    celery_broker_url_file: str = Field(default="", repr=False)
    celery_result_backend: str = Field(default="redis://localhost:6379/2", repr=False)
    celery_result_backend_file: str = Field(default="", repr=False)
    celery_task_default_queue: str = Field(default="default", min_length=1)
    celery_document_queue: str = Field(default="documents", min_length=1)
    celery_task_track_started: bool = True
    celery_task_acks_late: bool = True
    celery_task_reject_on_worker_lost: bool = True
    celery_worker_prefetch_multiplier: int = Field(default=1, ge=1)
    celery_task_max_retries: int = Field(default=3, ge=0)
    celery_task_retry_backoff_seconds: int = Field(default=5, ge=0)
    celery_task_soft_time_limit_seconds: int = Field(default=300, ge=1)
    celery_task_time_limit_seconds: int = Field(default=360, ge=1)
    celery_broker_connection_retry_on_startup: bool = True
    celery_result_expires_seconds: int = Field(default=3600, ge=1)
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"
    observability_enabled: bool = True
    request_log_enabled: bool = True
    metrics_enabled: bool = True
    metrics_include_subsystem_health: bool = True
    tracing_hooks_enabled: bool = True
    request_id_header: str = Field(default="X-Request-ID", min_length=1, max_length=64)
    traceparent_header: str = Field(default="traceparent", min_length=1, max_length=64)

    @field_validator(
        "cors_origins",
        "cors_allowed_methods",
        "cors_allowed_headers",
        "trusted_hosts",
        "ocr_languages",
        mode="before",
    )
    @classmethod
    def parse_csv_settings(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("llm_provider", mode="before")
    @classmethod
    def normalize_llm_provider(cls, value: object) -> object:
        if isinstance(value, str):
            if not value.strip():
                return OPENAI_COMPATIBLE_PROVIDER
            return normalize_provider_name(value)
        return value

    @field_validator("web_search_provider", mode="before")
    @classmethod
    def normalize_web_search_provider(cls, value: object) -> object:
        if isinstance(value, str):
            if not value.strip():
                return MOCK_PROVIDER
            return normalize_web_search_provider_name(value)
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        _validate_database_url_value(value)
        return value

    @field_validator("local_storage_path")
    @classmethod
    def validate_local_storage_path(cls, value: str) -> str:
        if not value.strip():
            msg = "LOCAL_STORAGE_PATH must not be empty."
            raise ValueError(msg)
        return value

    @field_validator("tokenizer_encoding_name")
    @classmethod
    def validate_tokenizer_encoding_name(cls, value: str) -> str:
        if not value.strip():
            msg = "TOKENIZER_ENCODING_NAME must not be empty."
            raise ValueError(msg)
        return value

    @field_validator(
        "embedding_model_name",
        "embedding_device",
        "embedding_query_prefix",
        "embedding_passage_prefix",
        "embedding_model_cache_path",
        "reranker_model",
        "reranker_device",
        "reranker_model_cache_path",
    )
    @classmethod
    def validate_embedding_string(cls, value: str) -> str:
        if not value.strip():
            msg = "Embedding string settings must not be empty."
            raise ValueError(msg)
        return value

    @field_validator("redis_url", "celery_broker_url", "celery_result_backend")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        _validate_redis_url_value(value)
        return value

    @field_validator(
        "max_request_body_bytes",
        "db_pool_size",
        "db_max_overflow",
        "db_pool_timeout_seconds",
        "db_pool_recycle_seconds",
        "db_connect_timeout_seconds",
        "redis_connect_timeout_seconds",
        "redis_socket_timeout_seconds",
        "redis_health_check_interval_seconds",
        "rate_limit_login_requests",
        "rate_limit_login_window_seconds",
        "rate_limit_refresh_requests",
        "rate_limit_refresh_window_seconds",
        "rate_limit_chat_requests",
        "rate_limit_chat_window_seconds",
        "rate_limit_upload_requests",
        "rate_limit_upload_window_seconds",
        "rate_limit_feedback_requests",
        "rate_limit_feedback_window_seconds",
        "celery_task_soft_time_limit_seconds",
        "celery_task_time_limit_seconds",
        mode="before",
    )
    @classmethod
    def reject_boolean_hardening_integer_settings(cls, value: object) -> object:
        if isinstance(value, bool):
            msg = "Hardening integer settings must not be boolean values."
            raise ValueError(msg)
        return value

    @field_validator("request_id_header", "traceparent_header")
    @classmethod
    def validate_http_header_name(cls, value: str) -> str:
        normalized = value.strip()
        allowed_characters = set("!#$%&'*+-.^_`|~")
        if not normalized or any(
            not (character.isalnum() or character in allowed_characters) for character in normalized
        ):
            msg = "HTTP header names must use valid token characters."
            raise ValueError(msg)
        return normalized

    @model_validator(mode="after")
    def load_secret_file_settings(self) -> "Settings":
        secret_key = _optional_secret_file_value(self.secret_key_file)
        if secret_key is not None:
            self.secret_key = secret_key

        database_url = _optional_secret_file_value(self.database_url_file)
        if database_url is not None:
            _validate_database_url_value(database_url)
            self.database_url = database_url

        for attr_name, file_attr_name in (
            ("redis_url", "redis_url_file"),
            ("celery_broker_url", "celery_broker_url_file"),
            ("celery_result_backend", "celery_result_backend_file"),
        ):
            url_value = _optional_secret_file_value(getattr(self, file_attr_name))
            if url_value is not None:
                _validate_redis_url_value(url_value)
                setattr(self, attr_name, url_value)

        for attr_name, file_attr_name in (
            ("llm_api_key", "llm_api_key_file"),
            ("llm_azure_api_key", "llm_azure_api_key_file"),
            ("llm_gemini_api_key", "llm_gemini_api_key_file"),
            ("llm_anthropic_api_key", "llm_anthropic_api_key_file"),
            ("llm_openrouter_api_key", "llm_openrouter_api_key_file"),
            ("web_search_bing_api_key", "web_search_bing_api_key_file"),
            ("web_search_google_api_key", "web_search_google_api_key_file"),
        ):
            secret_value = _optional_secret_file_value(getattr(self, file_attr_name))
            if secret_value is not None:
                setattr(self, attr_name, SecretStr(secret_value))
        return self

    @model_validator(mode="after")
    def validate_chunk_settings(self) -> "Settings":
        if self.chunk_max_tokens < self.chunk_target_tokens:
            msg = "CHUNK_MAX_TOKENS must be greater than or equal to CHUNK_TARGET_TOKENS."
            raise ValueError(msg)
        if self.chunk_overlap_tokens >= self.chunk_target_tokens:
            msg = "CHUNK_OVERLAP_TOKENS must be less than CHUNK_TARGET_TOKENS."
            raise ValueError(msg)
        if self.chunk_min_tokens > self.chunk_target_tokens:
            msg = "CHUNK_MIN_TOKENS must be less than or equal to CHUNK_TARGET_TOKENS."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_embedding_settings(self) -> "Settings":
        if self.embedding_provider != EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS:
            msg = "EMBEDDING_PROVIDER must be sentence_transformers."
            raise ValueError(msg)
        if self.embedding_dimensions != EMBEDDING_SCHEMA_DIMENSIONS:
            msg = "EMBEDDING_DIMENSIONS must match the document_chunks embedding schema."
            raise ValueError(msg)
        if self.embedding_query_prefix == self.embedding_passage_prefix:
            msg = "EMBEDDING_QUERY_PREFIX and EMBEDDING_PASSAGE_PREFIX must be different."
            raise ValueError(msg)
        return self

    @field_validator(
        "retrieval_top_k",
        "retrieval_max_top_k",
        "retrieval_max_query_characters",
        "keyword_retrieval_top_k",
        "keyword_retrieval_max_top_k",
        "hybrid_retrieval_top_k",
        "hybrid_retrieval_max_top_k",
        "hybrid_candidate_multiplier",
        "hybrid_rrf_k",
        "reranker_batch_size",
        "reranker_top_k",
        "reranker_candidate_k",
        "reranker_max_length",
        "ocr_max_pages",
        "ocr_render_dpi",
        "ocr_max_image_pixels",
        "ocr_max_image_width",
        "ocr_max_image_height",
        "ocr_page_timeout_seconds",
        "ocr_document_timeout_seconds",
        "ocr_max_extracted_characters",
        "ocr_native_text_min_characters_per_page",
        "chat_session_title_max_characters",
        "chat_session_list_page_size",
        "chat_session_list_max_page_size",
        "chat_history_page_size",
        "chat_history_max_page_size",
        "chat_message_max_characters",
        "llm_max_retries",
        "llm_max_output_tokens",
        "chat_retrieval_top_k",
        "chat_history_max_messages",
        "chat_history_max_tokens",
        "chat_context_max_tokens",
        "citation_excerpt_max_characters",
        "citation_max_sources_per_answer",
        "web_search_max_results",
        "web_search_max_content_length",
        "web_search_max_retries",
        "feedback_reason_max_characters",
        "feedback_report_page_size",
        "feedback_report_max_page_size",
        "audit_report_page_size",
        "audit_report_max_page_size",
        "audit_metadata_max_length",
        "audit_error_code_max_length",
        "audit_target_type_max_length",
        mode="before",
    )
    @classmethod
    def reject_boolean_retrieval_integer_settings(cls, value: object) -> object:
        if isinstance(value, bool):
            msg = "Retrieval integer settings must not be boolean values."
            raise ValueError(msg)
        return value

    @field_validator(
        "min_relevance_score",
        "keyword_min_rank",
        "hybrid_semantic_weight",
        "hybrid_keyword_weight",
        "hybrid_semantic_min_relevance_score",
        "reranker_timeout_seconds",
        "llm_timeout_seconds",
        "llm_stream_heartbeat_seconds",
        "llm_stream_max_duration_seconds",
        "llm_retry_backoff_seconds",
        "llm_temperature",
        "web_search_timeout_seconds",
        "web_search_retry_backoff_seconds",
        "ocr_native_text_min_alnum_ratio",
        "ocr_max_replacement_character_ratio",
        "ocr_max_control_character_ratio",
        mode="before",
    )
    @classmethod
    def reject_boolean_retrieval_float_settings(cls, value: object) -> object:
        if isinstance(value, bool):
            msg = "Retrieval float settings must not be boolean values."
            raise ValueError(msg)
        return value

    @field_validator(
        "min_relevance_score",
        "keyword_min_rank",
        "hybrid_semantic_weight",
        "hybrid_keyword_weight",
        "hybrid_semantic_min_relevance_score",
        "reranker_timeout_seconds",
        "llm_timeout_seconds",
        "llm_stream_heartbeat_seconds",
        "llm_stream_max_duration_seconds",
        "llm_retry_backoff_seconds",
        "llm_temperature",
        "web_search_timeout_seconds",
        "web_search_retry_backoff_seconds",
        "ocr_native_text_min_alnum_ratio",
        "ocr_max_replacement_character_ratio",
        "ocr_max_control_character_ratio",
    )
    @classmethod
    def validate_retrieval_float_settings(cls, value: float) -> float:
        if not isfinite(value):
            msg = "Retrieval float settings must be finite."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_ocr_settings(self) -> "Settings":
        allowed_languages = {"eng", "vie"}
        normalized_languages = tuple(
            dict.fromkeys(language.strip().lower() for language in self.ocr_languages)
        )
        if not normalized_languages:
            msg = "OCR_LANGUAGES must not be empty."
            raise ValueError(msg)
        if any(language not in allowed_languages for language in normalized_languages):
            msg = "OCR_LANGUAGES supports only eng and vie."
            raise ValueError(msg)
        self.ocr_languages = list(normalized_languages)
        if self.ocr_document_timeout_seconds < self.ocr_page_timeout_seconds:
            msg = "OCR_DOCUMENT_TIMEOUT_SECONDS must be >= OCR_PAGE_TIMEOUT_SECONDS."
            raise ValueError(msg)

        if self.ocr_document_timeout_seconds >= self.celery_task_soft_time_limit_seconds:
            msg = "OCR_DOCUMENT_TIMEOUT_SECONDS must be < CELERY_TASK_SOFT_TIME_LIMIT_SECONDS."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_retrieval_settings(self) -> "Settings":
        if self.retrieval_top_k > self.retrieval_max_top_k:
            msg = "RETRIEVAL_TOP_K must be less than or equal to RETRIEVAL_MAX_TOP_K."
            raise ValueError(msg)
        if self.keyword_retrieval_top_k > self.keyword_retrieval_max_top_k:
            msg = (
                "KEYWORD_RETRIEVAL_TOP_K must be less than or equal to KEYWORD_RETRIEVAL_MAX_TOP_K."
            )
            raise ValueError(msg)
        if self.hybrid_retrieval_top_k > self.hybrid_retrieval_max_top_k:
            msg = "HYBRID_RETRIEVAL_TOP_K must be less than or equal to HYBRID_RETRIEVAL_MAX_TOP_K."
            raise ValueError(msg)
        if self.hybrid_semantic_weight == 0.0 and self.hybrid_keyword_weight == 0.0:
            msg = "HYBRID_SEMANTIC_WEIGHT and HYBRID_KEYWORD_WEIGHT must not both be zero."
            raise ValueError(msg)
        if self.reranker_enabled and self.reranker_top_k > self.reranker_candidate_k:
            msg = "RERANKER_TOP_K must be less than or equal to RERANKER_CANDIDATE_K."
            raise ValueError(msg)
        if self.reranker_enabled and self.reranker_candidate_k > self.hybrid_retrieval_max_top_k:
            msg = "RERANKER_CANDIDATE_K must be less than or equal to HYBRID_RETRIEVAL_MAX_TOP_K."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_chat_settings(self) -> "Settings":
        if self.chat_session_list_page_size > self.chat_session_list_max_page_size:
            msg = (
                "CHAT_SESSION_LIST_PAGE_SIZE must be less than or equal to "
                "CHAT_SESSION_LIST_MAX_PAGE_SIZE."
            )
            raise ValueError(msg)
        if self.chat_history_page_size > self.chat_history_max_page_size:
            msg = "CHAT_HISTORY_PAGE_SIZE must be less than or equal to CHAT_HISTORY_MAX_PAGE_SIZE."
            raise ValueError(msg)
        if not self.llm_provider.strip():
            msg = "LLM_PROVIDER must not be empty."
            raise ValueError(msg)
        if not self.llm_no_answer_sentinel.strip():
            msg = "LLM_NO_ANSWER_SENTINEL must not be empty."
            raise ValueError(msg)
        if not self.chat_no_answer_message.strip():
            msg = "CHAT_NO_ANSWER_MESSAGE must not be empty."
            raise ValueError(msg)
        if self.citation_max_sources_per_answer > self.chat_retrieval_top_k:
            msg = "CITATION_MAX_SOURCES_PER_ANSWER must be <= CHAT_RETRIEVAL_TOP_K."
            raise ValueError(msg)
        if self.llm_enabled:
            _validate_selected_llm_provider_configuration(self)
        return self

    @model_validator(mode="after")
    def validate_web_search_settings(self) -> "Settings":
        if self.web_search_provider not in SUPPORTED_WEB_SEARCH_PROVIDERS:
            msg = "WEB_SEARCH_PROVIDER is not supported."
            raise ValueError(msg)
        if not self.web_search_user_agent.strip():
            msg = "WEB_SEARCH_USER_AGENT must not be empty."
            raise ValueError(msg)
        _validate_web_search_endpoint_url(self.web_search_bing_endpoint, settings=self)
        _validate_web_search_endpoint_url(self.web_search_duckduckgo_endpoint, settings=self)
        _validate_web_search_endpoint_url(self.web_search_google_endpoint, settings=self)
        if not self.web_search_enabled or self.web_search_mode == "internal_only":
            return self
        if (
            self.web_search_provider == BING_PROVIDER
            and self.web_search_allow_external
            and _secret_is_empty(self.web_search_bing_api_key)
        ):
            msg = "Selected web search provider is missing required configuration."
            raise ValueError(msg)
        if (
            self.web_search_provider == GOOGLE_CUSTOM_SEARCH_PROVIDER
            and self.web_search_allow_external
            and (
                _secret_is_empty(self.web_search_google_api_key)
                or not self.web_search_google_cx.strip()
            )
        ):
            msg = "Selected web search provider is missing required configuration."
            raise ValueError(msg)
        if self.web_search_provider == DUCKDUCKGO_PROVIDER:
            return self
        return self

    @model_validator(mode="after")
    def validate_feedback_settings(self) -> "Settings":
        if self.feedback_report_page_size > self.feedback_report_max_page_size:
            msg = (
                "FEEDBACK_REPORT_PAGE_SIZE must be less than or equal to "
                "FEEDBACK_REPORT_MAX_PAGE_SIZE."
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_audit_settings(self) -> "Settings":
        if self.audit_report_page_size > self.audit_report_max_page_size:
            msg = "AUDIT_REPORT_PAGE_SIZE must be less than or equal to AUDIT_REPORT_MAX_PAGE_SIZE."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_hardening_settings(self) -> "Settings":
        for origin in self.cors_origins:
            _validate_cors_origin(origin)
        if self.cors_allow_credentials and "*" in self.cors_origins:
            msg = "CORS wildcard origin cannot be used with credentials."
            raise ValueError(msg)
        if self.app_env == "production" and "*" in self.cors_origins:
            msg = "CORS wildcard origin is not allowed in production."
            raise ValueError(msg)
        if self.app_env == "production" and any(
            method == "*" for method in self.cors_allowed_methods
        ):
            msg = "CORS wildcard methods are not allowed in production."
            raise ValueError(msg)
        for host in self.trusted_hosts:
            _validate_trusted_host(host)
        if self.app_env == "production" and "*" in self.trusted_hosts:
            msg = "TRUSTED_HOSTS wildcard is not allowed in production."
            raise ValueError(msg)
        if self.celery_task_soft_time_limit_seconds > self.celery_task_time_limit_seconds:
            msg = "CELERY_TASK_SOFT_TIME_LIMIT_SECONDS must be <= CELERY_TASK_TIME_LIMIT_SECONDS."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.debug and not self.app_debug:
            self.app_debug = True
        if self.app_env != "production":
            return self
        if _is_placeholder_secret(self.secret_key) or len(self.secret_key.strip()) < 32:
            msg = "SECRET_KEY must be a non-placeholder value in production."
            raise ValueError(msg)
        if self.app_debug or self.debug:
            msg = "APP_DEBUG must be false in production."
            raise ValueError(msg)
        if _database_password_is_placeholder(self.database_url):
            msg = "DATABASE_URL must include a non-placeholder password in production."
            raise ValueError(msg)
        if (
            _uses_localhost(self.redis_url)
            or _uses_localhost(self.celery_broker_url)
            or _uses_localhost(self.celery_result_backend)
        ):
            msg = "Redis URLs must not use localhost in production."
            raise ValueError(msg)
        return self


def _is_placeholder_secret(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() in PLACEHOLDER_SECRET_KEYS


def _validate_database_url_value(value: str) -> None:
    if not value.startswith("postgresql+asyncpg://"):
        msg = "DATABASE_URL must use the postgresql+asyncpg driver."
        raise ValueError(msg)


def _validate_redis_url_value(value: str) -> None:
    if not value.startswith(("redis://", "rediss://")):
        msg = "Redis URLs must use redis:// or rediss://."
        raise ValueError(msg)


def _database_password_is_placeholder(database_url: str) -> bool:
    parsed = urlsplit(database_url)
    password = parsed.password
    if password is None:
        return True
    return _is_placeholder_secret(password)


def _uses_localhost(url: str) -> bool:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def _validate_cors_origin(origin: str) -> None:
    if origin == "*":
        return
    parsed = urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        msg = "CORS origins must be absolute http(s) origins."
        raise ValueError(msg)
    try:
        _ = parsed.port
    except ValueError as exc:
        msg = "CORS origins must use a valid optional port."
        raise ValueError(msg) from exc
    if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        msg = "CORS origins must not contain credentials, path, query, or fragment."
        raise ValueError(msg)


def _validate_trusted_host(host: str) -> None:
    if not host or "/" in host or "?" in host or "#" in host or "://" in host:
        msg = "TRUSTED_HOSTS entries must be hostnames, IPs, wildcard subdomains, or '*'."
        raise ValueError(msg)


def _secret_is_empty(value: SecretStr) -> bool:
    return not value.get_secret_value().strip()


def _optional_secret_file_value(path_value: str) -> str | None:
    normalized = path_value.strip()
    if not normalized:
        return None
    path = Path(normalized)
    try:
        if not path.is_file():
            msg = "Configured secret file is not readable."
            raise ValueError(msg)
        data = path.read_bytes()
    except OSError as exc:
        msg = "Configured secret file is not readable."
        raise ValueError(msg) from exc
    if len(data) > 65_536:
        msg = "Configured secret file is too large."
        raise ValueError(msg)
    try:
        value = data.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        msg = "Configured secret file must be UTF-8 text."
        raise ValueError(msg) from exc
    if not value:
        msg = "Configured secret file must not be empty."
        raise ValueError(msg)
    return value


def _model_or_default(provider_model: str, default_model: str) -> str:
    return provider_model.strip() or default_model.strip()


def _validate_selected_llm_provider_configuration(settings: Settings) -> None:
    provider = normalize_provider_name(settings.llm_provider)
    if provider not in SUPPORTED_PROVIDER_NAMES:
        msg = "LLM_PROVIDER is not supported."
        raise ValueError(msg)
    if provider == OPENAI_COMPATIBLE_PROVIDER:
        if not settings.llm_base_url.strip() or not settings.llm_model.strip():
            msg = "Selected LLM provider is missing required configuration."
            raise ValueError(msg)
        _validate_llm_url(settings.llm_base_url, settings=settings)
        if _secret_is_empty(settings.llm_api_key) and not _llm_url_is_local(settings.llm_base_url):
            msg = "Selected LLM provider is missing required configuration."
            raise ValueError(msg)
        return
    if provider == AZURE_OPENAI_PROVIDER:
        if (
            not settings.llm_azure_endpoint.strip()
            or _secret_is_empty(settings.llm_azure_api_key)
            or not settings.llm_azure_deployment.strip()
            or not settings.llm_azure_api_version.strip()
        ):
            msg = "Selected LLM provider is missing required configuration."
            raise ValueError(msg)
        _validate_llm_url(settings.llm_azure_endpoint, settings=settings, allow_http_local=False)
        return
    if provider == GEMINI_PROVIDER:
        if _secret_is_empty(settings.llm_gemini_api_key) or not _model_or_default(
            settings.llm_gemini_model,
            settings.llm_model,
        ):
            msg = "Selected LLM provider is missing required configuration."
            raise ValueError(msg)
        _validate_llm_url(settings.llm_gemini_base_url, settings=settings, allow_http_local=False)
        return
    if provider == ANTHROPIC_PROVIDER:
        if (
            _secret_is_empty(settings.llm_anthropic_api_key)
            or not _model_or_default(settings.llm_anthropic_model, settings.llm_model)
            or not settings.llm_anthropic_version.strip()
        ):
            msg = "Selected LLM provider is missing required configuration."
            raise ValueError(msg)
        _validate_llm_url(
            settings.llm_anthropic_base_url, settings=settings, allow_http_local=False
        )
        return
    if provider == OLLAMA_PROVIDER:
        if not settings.llm_ollama_base_url.strip() or not _model_or_default(
            settings.llm_ollama_model,
            settings.llm_model,
        ):
            msg = "Selected LLM provider is missing required configuration."
            raise ValueError(msg)
        _validate_llm_url(settings.llm_ollama_base_url, settings=settings)
        return
    if provider == LM_STUDIO_PROVIDER:
        if not settings.llm_lm_studio_base_url.strip() or not _model_or_default(
            settings.llm_lm_studio_model,
            settings.llm_model,
        ):
            msg = "Selected LLM provider is missing required configuration."
            raise ValueError(msg)
        _validate_llm_url(settings.llm_lm_studio_base_url, settings=settings)
        return
    if provider == OPENROUTER_PROVIDER:
        if (
            not settings.llm_openrouter_base_url.strip()
            or _secret_is_empty(settings.llm_openrouter_api_key)
            or not _model_or_default(settings.llm_openrouter_model, settings.llm_model)
        ):
            msg = "Selected LLM provider is missing required configuration."
            raise ValueError(msg)
        _validate_llm_url(
            settings.llm_openrouter_base_url, settings=settings, allow_http_local=False
        )


def _validate_llm_url(
    value: str,
    *,
    settings: Settings,
    allow_http_local: bool = True,
) -> None:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        msg = "Selected LLM provider URL is invalid."
        raise ValueError(msg)
    try:
        _ = parsed.port
    except ValueError as exc:
        msg = "Selected LLM provider URL is invalid."
        raise ValueError(msg) from exc
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        msg = "Selected LLM provider URL is invalid."
        raise ValueError(msg)
    if (
        parsed.scheme == "http"
        and settings.app_env == "production"
        and (not allow_http_local or not _is_local_provider_host(parsed.hostname))
    ):
        msg = "Remote LLM provider URLs must use HTTPS in production."
        raise ValueError(msg)


def _llm_url_is_local(value: str) -> bool:
    parsed = urlsplit(value.strip())
    return bool(parsed.hostname and _is_local_provider_host(parsed.hostname))


def _validate_web_search_endpoint_url(value: str, *, settings: Settings) -> None:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        msg = "Web search provider URL is invalid."
        raise ValueError(msg)
    try:
        _ = parsed.port
    except ValueError as exc:
        msg = "Web search provider URL is invalid."
        raise ValueError(msg) from exc
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        msg = "Web search provider URL is invalid."
        raise ValueError(msg)
    if (
        parsed.scheme == "http"
        and settings.app_env == "production"
        and not _is_local_provider_host(parsed.hostname)
    ):
        msg = "Remote web search provider URLs must use HTTPS in production."
        raise ValueError(msg)


def _is_local_provider_host(hostname: str) -> bool:
    normalized = hostname.strip().lower().strip("[]")
    return normalized in {"localhost", "127.0.0.1", "::1", "host.docker.internal"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
