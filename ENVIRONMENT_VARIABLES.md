# Environment Variables

## Application

```text
APP_NAME=Enterprise AI Knowledge Assistant
APP_ENV=development
APP_DEBUG=false
DEBUG=false
API_V1_PREFIX=/api/v1
API_DOCS_ENABLED=true
SECRET_KEY=replace-with-a-long-random-secret-key
JWT_ALGORITHM=HS256
JWT_ISSUER=enterprise-ai-knowledge-assistant
JWT_AUDIENCE=enterprise-ai-api
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Generate a local secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not commit generated secrets. `JWT_ALGORITHM` currently accepts only `HS256`.

## Development Admin

```text
DEV_ADMIN_EMAIL=admin@example.com
DEV_ADMIN_FULL_NAME=Development Admin
DEV_ADMIN_PASSWORD=
```

`DEV_ADMIN_PASSWORD` is intentionally empty in `.env.example`. Set it only in local `.env` or enter it through the hidden prompt when running `python -m app.scripts.seed_admin`.

## Database

```text
DATABASE_URL=postgresql+asyncpg://app_user:app_password@localhost:5432/enterprise_ai
```

## Redis and Celery

```text
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_TASK_DEFAULT_QUEUE=default
CELERY_DOCUMENT_QUEUE=documents
CELERY_TASK_TRACK_STARTED=true
CELERY_TASK_ACKS_LATE=true
CELERY_TASK_REJECT_ON_WORKER_LOST=true
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_TASK_MAX_RETRIES=3
CELERY_TASK_RETRY_BACKOFF_SECONDS=5
CELERY_RESULT_EXPIRES_SECONDS=3600
```

Celery rules:

- Broker and result backend must be Redis URLs and should use different Redis databases.
- Production deployments must not use `localhost` Redis URLs.
- `CELERY_DOCUMENT_QUEUE` routes `documents.process_document` work.
- Task serialization is JSON only; pickle is not accepted.
- Retry count is bounded by `CELERY_TASK_MAX_RETRIES`.
- Redis result backend stores temporary task execution metadata, not business source of truth.

## Storage

```text
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./data/uploads
MAX_UPLOAD_SIZE_MB=25
UPLOAD_CHUNK_SIZE_BYTES=1048576
```


Storage variable rules:

- `STORAGE_BACKEND` currently accepts only `local`.
- `LOCAL_STORAGE_PATH` must be a non-empty relative or absolute path. The default is relative and does not hard-code a developer machine path.
- `MAX_UPLOAD_SIZE_MB` must be greater than `0`.
- `UPLOAD_CHUNK_SIZE_BYTES` must be greater than `0`; default is 1 MiB.
- The storage root is never stored in the database and must not be logged or returned to clients.
- `data/uploads/` is ignored by Git and must not contain committed uploads.


## PDF Extraction

```text
PDF_MAX_PAGES=500
PDF_MIN_USABLE_CHARACTERS=20
PDF_TEXT_SORT=true
```

PDF extraction variable rules:

- `PDF_MAX_PAGES` is an integer greater than `0`.
- `PDF_MIN_USABLE_CHARACTERS` is an integer greater than or equal to `0`.
- `PDF_TEXT_SORT` is a boolean.
- These values are not secrets.
- No PDF password environment variable is supported in MVP.
## Chunking

```text
TOKENIZER_ENCODING_NAME=cl100k_base
CHUNK_TARGET_TOKENS=500
CHUNK_MAX_TOKENS=700
CHUNK_OVERLAP_TOKENS=75
CHUNK_MIN_TOKENS=50
```

Chunking variable rules:

- `TOKENIZER_ENCODING_NAME` is a non-empty string and is not a secret.
- `CHUNK_TARGET_TOKENS` is an integer greater than `0`.
- `CHUNK_MAX_TOKENS` is an integer greater than or equal to `CHUNK_TARGET_TOKENS`.
- `CHUNK_OVERLAP_TOKENS` is an integer greater than or equal to `0` and smaller than `CHUNK_TARGET_TOKENS`.
- `CHUNK_MIN_TOKENS` is an integer greater than or equal to `0` and less than or equal to `CHUNK_TARGET_TOKENS`.
- Tokenizer and chunking settings do not contain secrets.
- Runtime chunking does not require network access.
## Embeddings

```text
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-small
EMBEDDING_MODEL_REVISION=
EMBEDDING_DIMENSIONS=384
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=16
EMBEDDING_NORMALIZE=true
EMBEDDING_QUERY_PREFIX="query: "
EMBEDDING_PASSAGE_PREFIX="passage: "
EMBEDDING_LOCAL_FILES_ONLY=false
EMBEDDING_MODEL_CACHE_PATH=./data/models
```

Embedding variable rules:

- `EMBEDDING_PROVIDER` currently accepts only `sentence_transformers`.
- `EMBEDDING_MODEL_NAME` must be non-empty.
- `EMBEDDING_MODEL_REVISION` may be empty in the local MVP.
- `EMBEDDING_DIMENSIONS` must be the integer `384` to match the database schema.
- `EMBEDDING_DEVICE` must be non-empty; default is `cpu`.
- `EMBEDDING_BATCH_SIZE` must be an integer greater than `0`.
- `EMBEDDING_NORMALIZE` is a boolean; default is `true`.
- Query and passage prefixes must be non-empty and different.
- Quote prefix values in `.env` to preserve the trailing space.
- `EMBEDDING_LOCAL_FILES_ONLY=true` prevents model download attempts.
- `EMBEDDING_MODEL_CACHE_PATH` defaults to `./data/models` and must not be committed.
- These values are not secrets.
- If `EMBEDDING_MODEL_REVISION` is empty, a future model download may differ.

## Retrieval

```text
RETRIEVAL_TOP_K=10
RETRIEVAL_MAX_TOP_K=50
MIN_RELEVANCE_SCORE=0.50
RETRIEVAL_MAX_QUERY_CHARACTERS=4000
RERANK_TOP_K=5

KEYWORD_RETRIEVAL_TOP_K=20
KEYWORD_RETRIEVAL_MAX_TOP_K=100
KEYWORD_MIN_RANK=0.0

HYBRID_RETRIEVAL_TOP_K=10
HYBRID_RETRIEVAL_MAX_TOP_K=50
HYBRID_CANDIDATE_MULTIPLIER=4
HYBRID_RRF_K=60
HYBRID_SEMANTIC_WEIGHT=1.0
HYBRID_KEYWORD_WEIGHT=1.0
HYBRID_SEMANTIC_MIN_RELEVANCE_SCORE=0.30
```

Retrieval variable rules:

- `RETRIEVAL_TOP_K` is an integer greater than `0`.
- `RETRIEVAL_MAX_TOP_K` is an integer greater than `0`.
- `RETRIEVAL_TOP_K` must be less than or equal to `RETRIEVAL_MAX_TOP_K`.
- `MIN_RELEVANCE_SCORE` is a finite number in `[0.0, 1.0]`.
- `MIN_RELEVANCE_SCORE` uses cosine similarity derived as `1 - cosine_distance`.
- `RETRIEVAL_MAX_QUERY_CHARACTERS` is an integer greater than `0` and is reused by semantic, keyword, and hybrid retrieval.
- `KEYWORD_RETRIEVAL_TOP_K` is an integer greater than `0`.
- `KEYWORD_RETRIEVAL_MAX_TOP_K` is an integer greater than `0`.
- `KEYWORD_RETRIEVAL_TOP_K` must be less than or equal to `KEYWORD_RETRIEVAL_MAX_TOP_K`.
- `KEYWORD_MIN_RANK` is a finite number greater than or equal to `0.0` and is compared to PostgreSQL `ts_rank_cd`.
- `HYBRID_RETRIEVAL_TOP_K` is an integer greater than `0`.
- `HYBRID_RETRIEVAL_MAX_TOP_K` is an integer greater than `0`.
- `HYBRID_RETRIEVAL_TOP_K` must be less than or equal to `HYBRID_RETRIEVAL_MAX_TOP_K`.
- `HYBRID_CANDIDATE_MULTIPLIER` is an integer greater than or equal to `1`.
- `HYBRID_RRF_K` is an integer greater than `0`.
- `HYBRID_SEMANTIC_WEIGHT` and `HYBRID_KEYWORD_WEIGHT` are finite numbers greater than or equal to `0.0`; they cannot both be `0.0`.
- `HYBRID_SEMANTIC_MIN_RELEVANCE_SCORE` is a finite number in `[0.0, 1.0]`.
- Hybrid RRF scores are ranking scores, not probabilities.
- These retrieval values are not secrets.
- `RERANK_TOP_K` is reserved for a future reranking task and is not used by TASK-016 or TASK-017.

## LLM

TASK-026 supports these provider names:

```text
openai_compatible
azure_openai
gemini
anthropic
ollama
lm_studio
openrouter
```

OpenAI-compatible providers share one adapter. This includes OpenAI, OpenRouter, Ollama's OpenAI endpoint, LM Studio's OpenAI endpoint, and custom enterprise gateways. Azure OpenAI, Gemini, and Anthropic use provider-specific adapters.

Common settings:

```text
LLM_ENABLED=false
LLM_PROVIDER=openai_compatible
LLM_MODEL=
LLM_TIMEOUT_SECONDS=30
LLM_STREAM_HEARTBEAT_SECONDS=15
LLM_STREAM_MAX_DURATION_SECONDS=120
LLM_MAX_RETRIES=2
LLM_RETRY_BACKOFF_SECONDS=1
LLM_TEMPERATURE=0.0
LLM_MAX_OUTPUT_TOKENS=1024
LLM_NO_ANSWER_SENTINEL=__NO_ANSWER__
```

OpenAI-compatible:

```text
LLM_OPENAI_BASE_URL=
LLM_OPENAI_API_KEY=
```

`LLM_BASE_URL` and `LLM_API_KEY` remain backward-compatible aliases for the OpenAI-compatible provider.

Remote OpenAI-compatible endpoints require `LLM_OPENAI_API_KEY`; local endpoints such as `localhost`, `127.0.0.1`, `::1`, and `host.docker.internal` may leave it empty.

Azure OpenAI:

```text
LLM_AZURE_ENDPOINT=
LLM_AZURE_API_KEY=
LLM_AZURE_DEPLOYMENT=
LLM_AZURE_API_VERSION=
```

Google Gemini:

```text
LLM_GEMINI_API_KEY=
LLM_GEMINI_MODEL=
LLM_GEMINI_BASE_URL=https://generativelanguage.googleapis.com
```

Anthropic Claude:

```text
LLM_ANTHROPIC_API_KEY=
LLM_ANTHROPIC_MODEL=
LLM_ANTHROPIC_VERSION=2023-06-01
LLM_ANTHROPIC_BASE_URL=https://api.anthropic.com
```

Local Ollama:

```text
LLM_PROVIDER=ollama
LLM_OLLAMA_BASE_URL=http://host.docker.internal:11434
LLM_OLLAMA_MODEL=<local-model>
```

Local LM Studio:

```text
LLM_PROVIDER=lm_studio
LLM_LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1
LLM_LM_STUDIO_MODEL=<local-model>
```

OpenRouter:

```text
LLM_PROVIDER=openrouter
LLM_OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM_OPENROUTER_API_KEY=
LLM_OPENROUTER_MODEL=<provider/model>
```

Validation rules:

- `LLM_ENABLED=false` requires no provider key, model, endpoint, or network access.
- Only the selected enabled provider requires its provider-specific configuration.
- Selected remote OpenAI-compatible providers require an API key; selected local OpenAI-compatible providers may omit it.
- Unselected provider settings may remain empty.
- Provider API keys are `SecretStr` values and are hidden from `repr`, logs, and validation errors.
- Base URLs must be absolute `http` or `https` URLs with no embedded credentials, query, fragment, or query-based API key.
- Remote production provider URLs must use `https`; `http` is allowed only for local development providers such as `localhost`, `127.0.0.1`, `::1`, and `host.docker.internal`.
- Provider calls use explicit connect/read/write/pool timeouts, a bounded connection pool, bounded retries, and retry backoff.
- Chat SSE uses `LLM_STREAM_HEARTBEAT_SECONDS` for empty heartbeat events and `LLM_STREAM_MAX_DURATION_SECONDS` as the total bounded stream duration. Heartbeats do not extend the maximum duration.
- The app does not call an LLM at import, migration, startup, liveness, or readiness by default.
- The app does not add an Ollama, LM Studio, or other LLM container to Compose in TASK-026.

Privacy and data residency:

- Enabling an external provider sends selected prompt messages and selected retrieved context to that provider.
- Configure providers only after approving data residency, contractual, and compliance requirements.
- Do not log prompts, retrieved context, user questions, provider responses, document text, citation excerpts, API keys, authorization headers, request bodies, or response bodies.
- Cost estimation is not implemented in TASK-026; analytics and cost dashboards belong to TASK-032.

Fallback policy:

- Runtime fallback is not implemented in TASK-026.
- No automatic provider failover occurs by default because it can duplicate cost, change data residency, and produce non-deterministic answers.
- Future fallback must be explicitly enabled and tested before sending data to another provider.

## CORS

```text
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOWED_METHODS=GET,POST,PUT,PATCH,DELETE,OPTIONS
CORS_ALLOWED_HEADERS=Authorization,Content-Type,Accept,Origin
```

## Logging

```text
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Rules

- `.env.example` contains keys but no real secrets.
- Production must not use placeholder secrets.
- Production must set `APP_DEBUG=false`.
- The application validates required config on startup.
- Do not log `SECRET_KEY`, passwords, access tokens, refresh tokens, or token hashes.

## TASK-015 environment groups

The end-to-end pipeline uses the existing environment variable groups:

- Storage: `STORAGE_BACKEND`, `LOCAL_STORAGE_PATH`, upload size and chunk-size limits.
- Celery: Redis broker/backend URLs, queue names, retry count, backoff, `acks_late`, and worker prefetch settings.
- PDF extraction: page limit, usable-character threshold, and text sorting.
- Chunking: tokenizer encoding, target/max/min tokens, and overlap.
- Embeddings: provider, model name, model revision, dimensions, device, batch size, normalization, prefixes, local-files-only, and model cache path.

TASK-015 adds no new secret variables and no search or LLM variables.

## TASK-020 citation settings

| Variable | Default | Type | Notes |
| --- | --- | --- | --- |
| `CITATION_EXCERPT_MAX_CHARACTERS` | `500` | positive integer | Maximum length of server-generated citation excerpts. Not a secret. |
| `CITATION_MAX_SOURCES_PER_ANSWER` | `8` | positive integer | Maximum number of source markers/citations accepted for one answer. Must be less than or equal to `CHAT_RETRIEVAL_TOP_K`. Not a secret. |

Validation rules:

- `CITATION_EXCERPT_MAX_CHARACTERS > 0`.
- `CITATION_MAX_SOURCES_PER_ANSWER > 0`.
- `CITATION_MAX_SOURCES_PER_ANSWER <= CHAT_RETRIEVAL_TOP_K`.

## TASK-021 feedback settings

| Variable | Default | Type | Notes |
| --- | --- | --- | --- |
| `FEEDBACK_REASON_MAX_CHARACTERS` | `1000` | integer | Maximum accepted feedback reason length. Must be between `1` and `1000`. Not a secret. |
| `FEEDBACK_REPORT_PAGE_SIZE` | `20` | positive integer | Default page size for `GET /feedback`. Not a secret. |
| `FEEDBACK_REPORT_MAX_PAGE_SIZE` | `100` | positive integer | Maximum page size for `GET /feedback`. Must be greater than or equal to `FEEDBACK_REPORT_PAGE_SIZE`. Not a secret. |

Validation rules:

- `1 <= FEEDBACK_REASON_MAX_CHARACTERS <= 1000`.
- `FEEDBACK_REPORT_PAGE_SIZE > 0`.
- `FEEDBACK_REPORT_MAX_PAGE_SIZE > 0`.
- `FEEDBACK_REPORT_PAGE_SIZE <= FEEDBACK_REPORT_MAX_PAGE_SIZE`.

## TASK-022 audit settings

| Variable | Default | Type | Notes |
| --- | --- | --- | --- |
| `AUDIT_REPORT_PAGE_SIZE` | `50` | positive integer | Default page size for `GET /audit-logs`. Not a secret. |
| `AUDIT_REPORT_MAX_PAGE_SIZE` | `200` | positive integer | Maximum page size for `GET /audit-logs`. Must be greater than or equal to `AUDIT_REPORT_PAGE_SIZE`. Not a secret. |
| `AUDIT_METADATA_MAX_LENGTH` | `2000` | positive integer | Maximum serialized sanitized audit metadata length. Not a secret. |
| `AUDIT_ERROR_CODE_MAX_LENGTH` | `100` | positive integer | Maximum sanitized audit error-code length. Not a secret. |
| `AUDIT_TARGET_TYPE_MAX_LENGTH` | `64` | positive integer | Maximum audit target-type length. Not a secret. |

Validation rules:

- `AUDIT_REPORT_PAGE_SIZE > 0`.
- `AUDIT_REPORT_MAX_PAGE_SIZE > 0`.
- `AUDIT_REPORT_PAGE_SIZE <= AUDIT_REPORT_MAX_PAGE_SIZE`.
- `AUDIT_METADATA_MAX_LENGTH > 0`.
- `AUDIT_ERROR_CODE_MAX_LENGTH > 0`.
- `AUDIT_TARGET_TYPE_MAX_LENGTH > 0`.

TASK-022 does not add SIEM, export, signing, retention, Kafka, Redis, webhook, or Celery audit variables.


## TASK-023 Docker Compose overrides

The host `.env.example` keeps developer-friendly host values such as `localhost:55432` for PostgreSQL and `localhost:6379` for Redis. Compose overrides these inside application containers:

```text
DATABASE_URL=postgresql+asyncpg://<user>:<password>@postgres:5432/<db>
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
LOCAL_STORAGE_PATH=/app/data/uploads
EMBEDDING_MODEL_CACHE_PATH=/app/data/models
HF_HOME=/app/data/models/huggingface
SENTENCE_TRANSFORMERS_HOME=/app/data/models/sentence-transformers
LLM_ENABLED=false
```

Docker variable rules:

- Do not replace container service names with `localhost` inside API, worker, or migration containers.
- Do not put real production secrets in `.env.example`.
- Do not bake `.env`, uploads, or model cache into Docker images.
- API and worker must mount the same upload and model-cache named volumes.
- If a host OpenAI-compatible LLM is used during local development, set `LLM_OPENAI_BASE_URL=http://host.docker.internal:<port>/v1` in `.env` and set `LLM_ENABLED=true`. For Ollama or LM Studio, set `LLM_PROVIDER=ollama` or `LLM_PROVIDER=lm_studio` and use the provider-specific base URL/model variables.
- The default Compose stack does not run or depend on an LLM container.

## TASK-025 hardening settings

```text
TRUSTED_HOSTS=localhost,127.0.0.1
MAX_REQUEST_BODY_BYTES=26214400
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT_SECONDS=30
DB_POOL_RECYCLE_SECONDS=1800
DB_CONNECT_TIMEOUT_SECONDS=10
REDIS_CONNECT_TIMEOUT_SECONDS=5
REDIS_SOCKET_TIMEOUT_SECONDS=5
REDIS_HEALTH_CHECK_INTERVAL_SECONDS=30
RATE_LIMIT_ENABLED=true
RATE_LIMIT_LOGIN_REQUESTS=5
RATE_LIMIT_LOGIN_WINDOW_SECONDS=60
RATE_LIMIT_REFRESH_REQUESTS=10
RATE_LIMIT_REFRESH_WINDOW_SECONDS=60
RATE_LIMIT_CHAT_REQUESTS=20
RATE_LIMIT_CHAT_WINDOW_SECONDS=60
RATE_LIMIT_UPLOAD_REQUESTS=10
RATE_LIMIT_UPLOAD_WINDOW_SECONDS=300
RATE_LIMIT_FEEDBACK_REQUESTS=30
RATE_LIMIT_FEEDBACK_WINDOW_SECONDS=60
CELERY_TASK_SOFT_TIME_LIMIT_SECONDS=300
CELERY_TASK_TIME_LIMIT_SECONDS=360
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP=true
```

Production rules:

- `APP_ENV` must be one of `development`, `test`, or `production`.
- Production rejects `APP_DEBUG=true` or `DEBUG=true`.
- Production rejects placeholder `SECRET_KEY` values such as `changeme`, `secret`, `development-secret`, `replace-me`, and `.env.example` placeholders.
- Production `DATABASE_URL` must include a non-placeholder password. Error messages do not print the URL or password.
- Production rejects wildcard trusted hosts and wildcard CORS origins with credentials.
- `CORS_ALLOWED_ORIGINS` entries must be http(s) origins only, without path, query, fragment, or credentials.
- `TRUSTED_HOSTS` entries are hostnames/IPs only; forwarded host headers are not trusted.
- LLM API key is required only when the selected enabled provider requires one. The local OpenAI-compatible provider may be used without a key.
- `API_DOCS_ENABLED=false` disables `/docs`, `/redoc`, and `/openapi.json` while health and API routes stay available.



## Frontend

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_APP_NAME=Enterprise AI Knowledge Assistant
FRONTEND_PORT=5173
```

Frontend variable rules:

- `VITE_API_BASE_URL` is the browser-visible API origin and must point to the public API URL reachable from the user's browser.
- `VITE_APP_NAME` is display-only and is not a secret.
- `FRONTEND_PORT` controls the optional Docker Compose frontend host port.
- Do not add LLM API keys, database credentials, Redis credentials, JWT signing secrets, or provider secrets to frontend environment variables.
- Do not use internal Docker service hostnames such as `api:8000` for browser builds unless the browser can resolve that hostname.
## TASK-028 live UAT

These variables are for local UAT only and must not be committed with real values:

```text
UAT_SEED_ENABLED=false
UAT_ADMIN_PASSWORD=
UAT_MANAGER_PASSWORD=
UAT_STAFF_PASSWORD=
E2E_LIVE=false
E2E_API_BASE_URL=http://127.0.0.1:8000
PLAYWRIGHT_BASE_URL=http://localhost:5173
UAT_LLM_PORT=18080
FAKE_LLM_DELAY_MS=250
```

Rules:

- `UAT_SEED_ENABLED=true` is required before `python -m app.scripts.seed_uat_data` creates or updates UAT data.
- UAT passwords are read from the local shell environment and are not baked into Docker images or the frontend bundle.
- `compose.uat.yaml` enables a local deterministic OpenAI-compatible provider for acceptance testing without external LLM calls or provider API keys.
- Use `http://localhost:5173` as the browser frontend origin unless CORS is explicitly expanded for another local origin.
