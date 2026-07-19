# Environment Variables

## Application

```text
APP_NAME=Enterprise AI Knowledge Assistant
APP_ENV=development
APP_DEBUG=true
API_V1_PREFIX=/api/v1
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

```text
LLM_PROVIDER=<provider>
LLM_MODEL_NAME=<model>
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=60
```

## CORS

```text
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
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
