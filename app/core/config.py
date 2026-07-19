from functools import lru_cache
from math import isfinite
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.embeddings.constants import (
    EMBEDDING_PROVIDER_SENTENCE_TRANSFORMERS,
    EMBEDDING_SCHEMA_DIMENSIONS,
)

PLACEHOLDER_SECRET_KEYS = {
    "change-me",
    "change-me-for-local-development",
    "replace-with-a-long-random-secret-key",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Enterprise AI Knowledge Assistant"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"
    secret_key: str = Field(default="replace-with-a-long-random-secret-key", min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "enterprise-ai-knowledge-assistant"
    jwt_audience: str = "enterprise-ai-api"
    access_token_expire_minutes: int = Field(default=15, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)
    database_url: str = "postgresql+asyncpg:///enterprise_ai"
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
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_default_queue: str = Field(default="default", min_length=1)
    celery_document_queue: str = Field(default="documents", min_length=1)
    celery_task_track_started: bool = True
    celery_task_acks_late: bool = True
    celery_task_reject_on_worker_lost: bool = True
    celery_worker_prefetch_multiplier: int = Field(default=1, ge=1)
    celery_task_max_retries: int = Field(default=3, ge=0)
    celery_task_retry_backoff_seconds: int = Field(default=5, ge=0)
    celery_result_expires_seconds: int = Field(default=3600, ge=1)
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            msg = "DATABASE_URL must use the postgresql+asyncpg driver."
            raise ValueError(msg)
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
    )
    @classmethod
    def validate_embedding_string(cls, value: str) -> str:
        if not value.strip():
            msg = "Embedding string settings must not be empty."
            raise ValueError(msg)
        return value

    @field_validator("celery_broker_url", "celery_result_backend")
    @classmethod
    def validate_celery_redis_url(cls, value: str) -> str:
        if not value.startswith(("redis://", "rediss://")):
            msg = "Celery Redis URLs must use redis:// or rediss://."
            raise ValueError(msg)
        return value

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
    )
    @classmethod
    def validate_retrieval_float_settings(cls, value: float) -> float:
        if not isfinite(value):
            msg = "Retrieval float settings must be finite."
            raise ValueError(msg)
        return value

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
        return self

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env == "production" and (
            not self.secret_key.strip() or self.secret_key in PLACEHOLDER_SECRET_KEYS
        ):
            msg = "SECRET_KEY must be a non-placeholder value in production."
            raise ValueError(msg)
        if self.app_env == "production" and self.app_debug:
            msg = "APP_DEBUG must be false in production."
            raise ValueError(msg)
        if self.app_env == "production" and (
            "localhost" in self.celery_broker_url
            or "127.0.0.1" in self.celery_broker_url
            or "localhost" in self.celery_result_backend
            or "127.0.0.1" in self.celery_result_backend
        ):
            msg = "Celery Redis URLs must not use localhost in production."
            raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
