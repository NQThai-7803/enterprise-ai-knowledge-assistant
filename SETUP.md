# Local Setup Guide

## 1. Requirements

- Windows 10/11.
- Visual Studio Code.
- Git.
- Python 3.12+.
- Docker Desktop.
- PostgreSQL and Redis run through Docker Compose.

## 2. Clone project

```powershell
git clone <repository-url>
cd enterprise-ai-knowledge-assistant
```

## 3. Create virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation scripts:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## 4. Install dependencies

The project uses `pyproject.toml` for dependencies and tool configuration.

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 5. Create environment file

```powershell
Copy-Item .env.example .env
```

Generate a local JWT secret and put it in `.env`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Required authentication settings:

```env
SECRET_KEY=<local-generated-secret>
JWT_ALGORITHM=HS256
JWT_ISSUER=enterprise-ai-knowledge-assistant
JWT_AUDIENCE=enterprise-ai-api
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Do not commit `.env`. Do not paste real secrets into documentation, screenshots, or reports.

## 6. Check Docker Desktop

```powershell
docker version
docker compose version
```

Open Docker Desktop before running Compose if the Docker daemon is not running.

## 7. Build and start the full backend stack

```powershell
docker compose config
docker compose build
docker compose up -d
docker compose ps
```

The default stack contains:

- `postgres`: PostgreSQL pgvector image on container port `5432`, bound to `127.0.0.1:55432` by default.
- `redis`: Redis 7 on container port `6379`, bound to `127.0.0.1:6379` by default.
- `migration`: one-shot `alembic upgrade head` service.
- `api`: FastAPI on `127.0.0.1:8000`.
- `worker`: Celery worker for `default` and `documents` queues.

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## 8. Logs and health

```powershell
docker compose logs migration --tail=100
docker compose logs api --tail=100
docker compose logs worker --tail=100
docker compose logs postgres --tail=100
docker compose logs redis --tail=100
curl.exe -i http://127.0.0.1:8000/health/live
curl.exe -i http://127.0.0.1:8000/health/ready
```

Expected steady state:

```text
postgres   healthy
redis      healthy
migration  exited (0)
api        running/healthy
worker     running/healthy
```

## 9. Migrations

Compose runs migrations through the `migration` service before API and worker start. Manual migration checks:

```powershell
docker compose run --rm migration
docker compose exec api alembic current
docker compose exec api alembic heads
```

Current Alembic source head after TASK-031 is `20260803_0010`. TASK-023 originally used `20260722_0009`. Do not use `Base.metadata.create_all()` in this project.

## 10. Python runtime checks

```powershell
docker compose exec api python --version
docker compose exec worker python --version
docker compose exec api id
docker compose exec worker id
```

API and worker must run Python 3.12.x as a non-root user.

## 11. Docker networking

Inside containers, Compose overrides application URLs to use service names:

```text
PostgreSQL: postgres:5432
Redis: redis:6379
```

Host tools may still use `127.0.0.1:55432` for PostgreSQL and `127.0.0.1:6379` for Redis.

## 12. Development admin

Configure local development values in `.env`:

```env
APP_ENV=development
DEV_ADMIN_EMAIL=admin@example.com
DEV_ADMIN_FULL_NAME=Development Admin
DEV_ADMIN_PASSWORD=<local-strong-password>
```

Then run either on host or in the API container:

```powershell
python -m app.scripts.seed_admin
docker compose exec api python -m app.scripts.seed_admin
```

The command is idempotent and does not run automatically during backend startup.

## 13. LLM during local Docker development

The default stack starts with:

```text
LLM_ENABLED=false
```

This allows API, worker, health checks, document upload, retrieval setup, feedback, and audit flows to run without an LLM. Chat requests with selected context return the existing safe `LLM_NOT_CONFIGURED` response until an enabled provider is configured.

OpenAI-compatible provider or enterprise gateway:

```text
LLM_ENABLED=true
LLM_PROVIDER=openai_compatible
LLM_OPENAI_BASE_URL=http://host.docker.internal:<port>/v1
LLM_OPENAI_API_KEY=
LLM_MODEL=<model>
```

Remote OpenAI-compatible endpoints must use HTTPS in production and set `LLM_OPENAI_API_KEY`; local OpenAI-compatible gateways on `localhost`, `127.0.0.1`, `::1`, or `host.docker.internal` may leave the key empty.

Ollama on the Windows host:

```text
LLM_ENABLED=true
LLM_PROVIDER=ollama
LLM_OLLAMA_BASE_URL=http://host.docker.internal:11434
LLM_OLLAMA_MODEL=<local-model>
```

LM Studio on the Windows host:

```text
LLM_ENABLED=true
LLM_PROVIDER=lm_studio
LLM_LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1
LLM_LM_STUDIO_MODEL=<local-model>
```

OpenRouter:

```text
LLM_ENABLED=true
LLM_PROVIDER=openrouter
LLM_OPENROUTER_API_KEY=<local-secret>
LLM_OPENROUTER_MODEL=<provider/model>
```

Azure OpenAI requires `LLM_AZURE_ENDPOINT`, `LLM_AZURE_API_KEY`, `LLM_AZURE_DEPLOYMENT`, and `LLM_AZURE_API_VERSION`. Gemini requires `LLM_GEMINI_API_KEY` and a model through `LLM_GEMINI_MODEL` or `LLM_MODEL`. Anthropic requires `LLM_ANTHROPIC_API_KEY`, a model through `LLM_ANTHROPIC_MODEL` or `LLM_MODEL`, and `LLM_ANTHROPIC_VERSION`.

Docker Desktop for Windows supports `host.docker.internal`. On Linux, that host name may require an explicit Docker host-gateway configuration outside the default TASK-026 Compose stack.

Do not add an LLM container, install Ollama, download a model, or call a real provider as part of the default backend startup or CI flow.

### UAT deterministic local LLM

The default development stack intentionally keeps `LLM_ENABLED=false`. For local UAT chat without a real provider key, use the UAT overlay:

```powershell
docker compose -f compose.yaml -f compose.uat.yaml up -d
```

If API or worker containers were already started without the overlay, recreate the UAT services without deleting volumes:

```powershell
docker compose -f compose.yaml -f compose.uat.yaml up -d --force-recreate uat-seed api worker uat-llm
```

The UAT overlay sets:

```text
LLM_ENABLED=true
LLM_PROVIDER=openai_compatible
LLM_MODEL=uat-deterministic-model
LLM_OPENAI_BASE_URL=http://uat-llm:18080/v1
```

No real OpenAI, Gemini, Anthropic, or OpenRouter key is required for the UAT provider. The overlay also runs the one-shot `uat-seed` service after migrations. It upserts `admin.uat@example.test`, `manager.uat@example.test`, and `staff.uat@example.test` with deterministic local-only passwords, updates stale hashes/roles/departments in place, and preserves unrelated users. Do not use `docker compose down -v` for UAT recovery unless you intentionally want to delete local UAT data.


## Web Search During Local Development

Web search is disabled by default:

```text
WEB_SEARCH_ENABLED=false
WEB_SEARCH_MODE=internal_only
WEB_SEARCH_PROVIDER=mock
WEB_SEARCH_ALLOW_EXTERNAL=false
```

For local backend tests without internet, keep `WEB_SEARCH_PROVIDER=mock`. To test a real provider, set `WEB_SEARCH_ENABLED=true`, choose `WEB_SEARCH_MODE=hybrid` or `web_only`, set `WEB_SEARCH_ALLOW_EXTERNAL=true`, and provide the selected provider credentials where required. Do not put real provider keys in committed files.

Admin-only configuration checks are available after login:

```text
GET  /api/v1/web-search/provider-status
POST /api/v1/web-search/test
```

The public Chat API body is unchanged; source mode is not a per-request client option in TASK-031.

## 14. Stop containers but keep data

```powershell
docker compose down
```

This keeps named volumes for PostgreSQL, Redis, uploads, and model cache.

## 15. Remove local data intentionally

```powershell
docker compose down -v
```

Warning: `docker compose down -v` removes local PostgreSQL, Redis, upload, and model-cache named volumes. Do not use it during normal TASK-023 verification.

## 16. Run backend outside Docker, optional

For host development, keep PostgreSQL and Redis running and start Uvicorn manually:

```powershell
docker compose up -d postgres redis
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`--reload` is only for host development. The default Docker API service does not use reload.

## 17. Run Celery worker outside Docker, optional

Windows local development command:

```powershell
celery -A app.workers.celery_app:celery_app worker --loglevel=INFO --pool=solo --queues=default,documents
```

`solo` is for local Windows development only. The Linux Docker worker uses the default prefork pool with configured concurrency.

## 18. Run tests

Use the Docker test target for Python 3.12 verification:

```powershell
docker compose run --rm test
```

For integration tests, use a non-production test database URL. When running Celery integration tests against the Compose Redis instance, stop the application worker first or isolate queues, because those tests start their own worker on `default,documents`.

```powershell
docker compose stop worker
docker compose run --rm -e DATABASE_URL=postgresql+asyncpg://app_user:<password>@postgres:5432/<test_db> test python -m pytest -m integration -q
docker compose start worker
```

Host checks remain available:

```powershell
python -m pytest -v
python -m pytest -m integration -v
python -m ruff check .
python -m ruff format --check .
python -m compileall app
```

## 19. Troubleshooting

- If `docker version` or `docker info` fails, start or restart Docker Desktop before editing application code.
- If `docker compose config` fails, fix Compose syntax or missing environment defaults before building.
- If PostgreSQL is not healthy, inspect `docker compose logs postgres --tail=100` and verify port `55432` is free on the host.
- If Redis is not healthy, inspect `docker compose logs redis --tail=100` and verify port `6379` is free on the host.
- If API readiness fails, check PostgreSQL and Redis health first; liveness should not require either dependency.
- If the worker is not healthy, inspect `docker compose logs worker --tail=100` and verify the Celery app path is `app.workers.celery_app:celery_app`.
- If document processing stays `UPLOADED`, verify the API and worker share the `uploads_data` volume and the worker can reach Redis.
- If a local host LLM is enabled, use `host.docker.internal` from containers instead of `localhost`; Linux hosts may need explicit host-gateway configuration.

## 20. Suggested VS Code extensions

- Python.
- Pylance.
- Ruff.
- Docker.
- REST Client or Thunder Client.
## 24. TASK-007 User and Department API smoke test

Start PostgreSQL and apply migrations:

```powershell
docker compose up -d postgres
alembic upgrade head
alembic current
```

Create or update the development Admin:

```powershell
python -m app.scripts.seed_admin
```

Run the backend:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Login without printing tokens:

```powershell
$loginBody = @{
    email = "admin@example.com"
    password = $env:DEV_ADMIN_PASSWORD
} | ConvertTo-Json

$login = Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/api/v1/auth/login" `
    -ContentType "application/json" `
    -Body $loginBody

$accessToken = $login.data.access_token
$headers = @{ Authorization = "Bearer $accessToken" }
```

Do not use production passwords in demo commands. Do not commit `.env`.

Create a Department:

```powershell
$departmentBody = @{
    name = "Information Technology"
    code = "it"
    description = "Internal IT department"
} | ConvertTo-Json

$department = Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/api/v1/departments" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $departmentBody

$departmentId = $department.data.id
```

Create a Staff User:

```powershell
$staffPassword = "StrongStaffPassword123!"
$userBody = @{
    email = "staff@example.com"
    full_name = "Staff User"
    password = $staffPassword
    role = "STAFF"
    department_id = $departmentId
} | ConvertTo-Json

$user = Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/api/v1/users" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $userBody

$userId = $user.data.id
```

List, update, deactivate, and delete:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/v1/users?page=1&page_size=20&role=STAFF" `
    -Headers $headers

$updateBody = @{ full_name = "Updated Staff User" } | ConvertTo-Json
Invoke-RestMethod `
    -Method Patch `
    -Uri "http://127.0.0.1:8000/api/v1/users/$userId" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $updateBody

Invoke-WebRequest `
    -Method Delete `
    -Uri "http://127.0.0.1:8000/api/v1/users/$userId" `
    -Headers $headers

Invoke-WebRequest `
    -Method Delete `
    -Uri "http://127.0.0.1:8000/api/v1/departments/$departmentId" `
    -Headers $headers
```

Check audit logs locally without selecting sensitive metadata:

```powershell
docker compose exec postgres psql `
    -U app_user `
    -d enterprise_ai `
    -c "SELECT action, entity_type, entity_id, created_at FROM audit_logs ORDER BY created_at DESC;"

docker compose exec postgres psql `
    -U app_user `
    -d enterprise_ai `
    -c "SELECT COUNT(*) FROM audit_logs WHERE metadata::text ~* 'password|token|authorization';"
```

The expected sensitive metadata count is `0`.


## 25. TASK-008 Document data model checks

Start PostgreSQL and apply migrations:

```powershell
docker compose up -d postgres
alembic upgrade head
alembic current
```

Run document model tests:

```powershell
python -m pytest tests/unit/test_document_models.py -v
python -m pytest tests/integration/test_document_database.py -m integration -v
python -m pytest -m integration -v
```

TASK-008 does not add upload commands, file storage, or Document API endpoints.
## 26. TASK-009 local PDF upload smoke test

Local storage defaults to `./data/uploads`. The application creates the directory when local storage is initialized. Do not commit uploaded files; `data/uploads/` is ignored by Git.

Start PostgreSQL and apply migrations:

```powershell
docker compose up -d postgres
alembic upgrade head
alembic current
```

Create or update the development Admin:

```powershell
python -m app.scripts.seed_admin
```

Run the backend:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Manual Swagger flow:

1. Call `POST /api/v1/auth/login`.
2. Store the returned access token without printing it in logs or screenshots.
3. Use `Authorize` with `Bearer <access-token>`.
4. Open `POST /api/v1/documents/upload`.
5. Select a non-sensitive sample PDF.
6. Enter a title and choose an access scope.
7. Submit the request.

Expected result:

```text
HTTP 202
status = UPLOADED
```

The response must not include `storage_key`, `checksum_sha256`, or a local absolute path.

PowerShell or curl upload example after login:

```powershell
$headers = @{
    Authorization = "Bearer $accessToken"
}

curl.exe `
    -X POST `
    "http://127.0.0.1:8000/api/v1/documents/upload" `
    -H "Authorization: Bearer $accessToken" `
    -F "file=@.\samples\sample.pdf;type=application/pdf" `
    -F "title=Sample Enterprise Policy" `
    -F "description=Local development upload test" `
    -F "access_scope=PRIVATE"
```

Check safe metadata without selecting storage keys or checksums for demos:

```powershell
docker compose exec postgres psql `
    -U app_user `
    -d enterprise_ai `
    -c "SELECT id, title, original_filename, mime_type, file_size, status, access_scope, department_id, uploaded_by, is_deleted FROM documents ORDER BY created_at DESC;"
```

Check local storage during development:

```powershell
Get-ChildItem -Recurse .\data\uploads
```

Stored filenames should be UUID-based PDF files under the storage root, not the original filename. Use only non-sensitive sample PDFs for demos.

Run upload tests:

```powershell
python -m pytest tests/unit/test_local_file_storage.py tests/unit/test_document_file_validation.py tests/unit/test_document_upload_schema.py -v
python -m pytest tests/integration/test_document_upload_service.py -m integration -v
python -m pytest tests/api/test_document_upload_api.py -m integration -v
```
## 27. TASK-010 Document access-control smoke test

Start PostgreSQL, apply migrations, seed an Admin, and run the backend:

```powershell
docker compose up -d postgres
alembic upgrade head
python -m app.scripts.seed_admin
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Use Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

Suggested manual flow with non-sensitive sample PDFs only:

1. Login as Admin and authorize Swagger.
2. Upload a PDF with `POST /api/v1/documents/upload`.
3. Call `GET /api/v1/documents` and verify pagination metadata.
4. Call `GET /api/v1/documents/{document_id}`.
5. Call `GET /api/v1/documents/{document_id}/status`.
6. Call `GET /api/v1/documents/{document_id}/download` and verify the response is an attachment.
7. Call `PATCH /api/v1/documents/{document_id}` to update title or description.
8. Create a direct User or Department grant with `POST /api/v1/documents/{document_id}/permissions`.
9. Login as a User in another Department and verify the grant takes effect without issuing a new token.
10. Delete the grant and verify access is removed unless Organization, same-Department, uploader, or Admin access still applies.
11. Soft delete the Document with `DELETE /api/v1/documents/{document_id}` and verify list/detail/status/download no longer return it.

PowerShell examples after login and `$headers` setup:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/v1/documents?page=1&page_size=20" `
    -Headers $headers

Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/v1/documents/$documentId" `
    -Headers $headers

Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/v1/documents/$documentId/status" `
    -Headers $headers

Invoke-WebRequest `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/v1/documents/$documentId/download" `
    -Headers $headers `
    -OutFile ".\downloaded-document.pdf"

$updateBody = @{ title = "Updated Document Title" } | ConvertTo-Json
Invoke-RestMethod `
    -Method Patch `
    -Uri "http://127.0.0.1:8000/api/v1/documents/$documentId" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $updateBody

Invoke-WebRequest `
    -Method Delete `
    -Uri "http://127.0.0.1:8000/api/v1/documents/$documentId" `
    -Headers $headers
```

Run TASK-010 tests:

```powershell
python -m pytest tests/unit/test_document_access_policies.py tests/unit/test_document_permission_mapping.py -v
python -m pytest tests/integration/test_document_access_control.py -m integration -v
python -m pytest tests/api/test_documents_api.py -m integration -v
```

Do not use real enterprise documents in local demos. Do not print access tokens, storage keys, checksums, or local paths in screenshots.
## 28. TASK-012 PDF extraction checks

Check PyMuPDF import:

```powershell
python -c "import pymupdf; print('PyMuPDF OK')"
```

Run extraction tests:

```powershell
python -m pytest tests/unit/test_text_normalization.py -v
python -m pytest tests/unit/test_extraction_models.py -v
python -m pytest tests/unit/test_pymupdf_extractor.py -v
python -m pytest tests/integration/test_pdf_extraction_from_storage.py -v
```

Manual extraction for a non-sensitive local sample PDF should print only aggregate metadata:

```powershell
python -c "from pathlib import Path; from app.document_processing.extractors.pymupdf_extractor import PyMuPDFTextExtractor; data = Path('samples/sample.pdf').read_bytes(); result = PyMuPDFTextExtractor(max_pages=500, min_usable_characters=20, sort_text=True).extract(data); print({'page_count': result.page_count, 'pages_with_usable_text': result.pages_with_usable_text, 'total_usable_characters': result.total_usable_characters})"
```

Do not print page text, PDF bytes, storage keys, or absolute paths for sensitive documents.
## 29. TASK-013 chunking checks

Check tiktoken import:

```powershell
python -c "import tiktoken; print('tiktoken OK')"
```

Run chunking tests:

```powershell
python -m pytest tests/unit/test_tiktoken_counter.py -v
python -m pytest tests/unit/test_page_aware_chunker.py -v
python -m pytest tests/integration/test_pdf_extraction_and_chunking.py -v
```

Manual chunking for a non-sensitive sample PDF should print only aggregate metadata:

```powershell
python -c "from pathlib import Path; from app.document_processing.extractors.pymupdf_extractor import PyMuPDFTextExtractor; from app.document_processing.tokenization.tiktoken_counter import TiktokenTokenCounter; from app.document_processing.chunking.page_aware_chunker import PageAwareTokenChunker; pdf_bytes = Path('samples/sample.pdf').read_bytes(); extraction = PyMuPDFTextExtractor(max_pages=500, min_usable_characters=20, sort_text=True).extract(pdf_bytes); result = PageAwareTokenChunker(token_counter=TiktokenTokenCounter('cl100k_base'), target_tokens=500, max_tokens=700, overlap_tokens=75, min_tokens=50).chunk(extraction); print({'chunk_count': result.chunk_count, 'total_tokens': result.total_tokens, 'source_page_numbers': result.source_page_numbers})"
```

Do not print page text, chunk text, token IDs, PDF bytes, storage keys, or absolute paths when using sensitive documents.

## 30. TASK-014 pgvector and embedding checks

Check embedding dependencies:

```powershell
python -c "import sentence_transformers; import pgvector; print('Embedding dependencies OK')"
```

Check pgvector and apply migrations:

```powershell
docker compose up -d postgres
alembic upgrade head
alembic current
```

Check the real model the first time. The model is cached under `data/models` and must not be committed:

```powershell
python -m pytest -m embedding_model_integration -v
```

Run focused TASK-014 tests:

```powershell
python -m pytest tests/unit/test_sentence_transformer_provider.py -v
python -m pytest tests/integration/test_document_chunk_repository.py -m integration -v
python -m pytest tests/integration/test_document_embedding_persistence.py -m integration -v
```

Manual embedding smoke test with non-sensitive sample text should print only aggregate metadata:

```powershell
python -c "from app.core.config import get_settings; from app.embeddings.factory import create_embedding_provider; settings = get_settings(); provider = create_embedding_provider(settings); result = provider.embed_passages(['Nhân viên được hưởng 12 ngày nghỉ phép mỗi năm.', 'Hệ thống sao lưu dữ liệu vào ban đêm.']); print({'count': result.count, 'dimensions': result.dimensions, 'normalized': result.normalized, 'model_name': result.model_name})"
```

Do not print source text, vector values, storage keys, absolute paths, or model cache absolute paths in demos or logs.

## 31. TASK-015 manual end-to-end processing

Start infrastructure:

```powershell
docker compose up -d postgres redis
alembic upgrade head
python -m app.scripts.seed_admin
```

Terminal 1:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 on Windows:

```powershell
celery -A app.workers.celery_app:celery_app worker --loglevel=INFO --pool=solo --queues=default,documents
```

Upload a small text-based PDF through Swagger or API. The upload response is HTTP 202 and initially shows `UPLOADED`; processing happens asynchronously. Poll `GET /api/v1/documents/{document_id}/status` until the final status is `READY` or `FAILED`.

Check chunk count without printing chunk text or vectors:

```powershell
docker compose exec postgres psql `
    -U <POSTGRES_USER> `
    -d <POSTGRES_DB> `
    -c "SELECT COUNT(*) FROM document_chunks WHERE document_id = '<DOCUMENT_UUID>';"
```

Run focused TASK-015 tests:

```powershell
python -m pytest tests/unit/test_document_tasks.py -v
python -m pytest tests/unit/test_document_upload_enqueue.py -v
python -m pytest tests/unit/test_end_to_end_document_processing_pipeline.py -v
python -m pytest tests/integration/test_end_to_end_document_processing_pipeline.py -m "integration and not processing_pipeline_model_integration" -v
python -m pytest -m processing_pipeline_model_integration -v
python -m pytest -m processing_pipeline_celery_integration -v
```

Use non-sensitive PDFs for local demos. The first real-model run can download and cache model files under `data/models`.
## Semantic Retrieval Tests

Run TASK-016 semantic retrieval tests:

```powershell
python -m pytest tests/unit/test_semantic_retrieval_service.py -v
python -m pytest tests/integration/test_permission_aware_retrieval.py -m integration -v
python -m pytest -m semantic_retrieval_model_integration -v
```

Test conditions:

- PostgreSQL must be running.
- Alembic must be at head.
- Retrieval integration fixtures create `READY` Documents and `DocumentChunk` embeddings.
- Real model tests require the Sentence Transformer model to be cached or available for first download.

Manual semantic retrieval smoke tests should call the internal service with a User loaded from PostgreSQL. For sensitive local data, print only metadata such as `hit_count`, `document_id`, `chunk_id`, `chunk_index`, `page_numbers`, and `relevance_score`; do not print query text, chunk text, Document title, vectors, storage keys, or local paths.

TASK-016 does not expose a Search API.

## TASK-017 Keyword and Hybrid Retrieval Tests

Run keyword retrieval tests:

```powershell
python -m pytest tests/integration/test_keyword_retrieval_repository.py -m integration -v
python -m pytest tests/integration/test_permission_aware_keyword_retrieval.py -m integration -v
```

Run hybrid retrieval tests:

```powershell
python -m pytest tests/unit/test_rrf_fusion.py -v
python -m pytest tests/integration/test_hybrid_retrieval.py -m integration -v
python -m pytest -m hybrid_retrieval_model_integration -v
```

Check the full-text index:

```powershell
docker compose exec postgres psql `
    -U <POSTGRES_USER> `
    -d <POSTGRES_DB> `
    -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'document_chunks' ORDER BY indexname;"
```

Expected indexes include:

```text
ix_document_chunks_embedding_hnsw_cosine
ix_document_chunks_text_fts_simple
```

Test conditions:

- PostgreSQL must be running.
- Alembic must be at head.
- Retrieval integration fixtures create `READY` Documents and `DocumentChunk` embeddings.
- Real hybrid tests require the Sentence Transformer model to be cached or available for first download.
- Keyword search uses PostgreSQL full-text search with the fixed `simple` configuration.

Manual keyword retrieval smoke tests should call the internal service with a User loaded from PostgreSQL. For sensitive local data, print only metadata such as `hit_count`, `document_id`, `chunk_id`, `chunk_index`, `page_numbers`, and `keyword_rank`; do not print the query, chunk text, Document title, vectors, storage keys, or local paths.

Manual hybrid retrieval smoke tests should call the internal service and print only metadata such as `hit_count`, `document_id`, `chunk_id`, `chunk_index`, `matched_by`, `semantic_rank`, `keyword_rank`, and `hybrid_score`; do not print text or vectors.

TASK-017 does not expose a Search API.

## TASK-020 citation validation setup

Run migrations:

```powershell
alembic upgrade head
```

Run citation tests:

```powershell
python -m pytest tests/unit -k "citation or marker or excerpt" -v
python -m pytest tests/integration -k "citation" -m integration -v
python -m pytest tests/api -k "chat and citation" -m integration -v
```

Manual validation checklist:

1. Start PostgreSQL and Redis.
2. Apply `alembic upgrade head`.
3. Configure a local or mock OpenAI-compatible provider.
4. Submit a Chat question where the provider returns a valid marker such as `[SOURCE_1]`.
5. Confirm the public answer uses `[1]` and returns matching citations.
6. Re-read Chat history and confirm Assistant citations load.
7. Test a duplicate marker and confirm only one citation is returned.
8. Test an unknown marker such as `[SOURCE_999]` and confirm a safe citation validation error with no persisted message pair.
9. Test permission revoke after retrieval and before validation; confirm NO_ANSWER and empty citations.

Do not print prompts, questions, answers, source registry entries, excerpts, chunk text, provider responses, API keys, vectors, storage keys, or absolute paths during manual checks.

## TASK-021 feedback setup

Run migrations:

```powershell
alembic upgrade head
```

Run Feedback tests:

```powershell
python -m pytest tests/unit -k "feedback" -v
python -m pytest tests/integration -k "feedback" -m integration -v
python -m pytest tests/api -k "feedback" -m integration -v
```

Manual validation checklist:

1. Login as Staff.
2. Create a ChatSession and get an ASSISTANT message.
3. PUT `/api/v1/messages/{assistant_message_id}/feedback` with `HELPFUL`.
4. PUT the same endpoint with `NOT_HELPFUL` and a changed reason; confirm only one Feedback row exists.
5. Confirm USER and SYSTEM messages return `404 FEEDBACK_TARGET_NOT_FOUND`.
6. Login as Manager in the same Department and confirm `GET /api/v1/feedback` returns only Department Feedback.
7. Login as Manager in another Department and confirm the Feedback is not returned.
8. Login as Admin and confirm global report access.
9. Confirm Staff receives `403 FEEDBACK_REPORT_FORBIDDEN` on `GET /api/v1/feedback`.

Do not use sensitive Chat content or real personal data in local manual feedback reasons.

## TASK-022 audit setup

Run migrations:

```powershell
alembic upgrade head
```

Run Audit tests:

```powershell
python -m pytest tests/unit -k "audit" -v
python -m pytest tests/integration -k "audit" -m integration -v
python -m pytest tests/api -k "audit" -m integration -v
```

Manual verification checklist:

1. Start PostgreSQL and Redis.
2. Apply `alembic upgrade head`.
3. Login as Admin.
4. Create a User or Department.
5. Upload a Document.
6. Change a Document permission.
7. Create a ChatSession.
8. Submit a Chat question.
9. Submit Feedback for an owned ASSISTANT message.
10. Call `GET /api/v1/audit-logs` as Admin and confirm events, safe actor/target IDs, filters, date filters, and pagination.
11. Login as Manager and Staff and confirm `GET /api/v1/audit-logs` returns `403 AUDIT_REPORT_FORBIDDEN`.

Do not print or store Chat questions, Assistant answers, prompts, retrieved context, citation excerpts, Feedback reasons, Document filenames, storage keys, passwords, tokens, or request/response bodies while checking audit logs.

## Backup and restore

Backups must keep PostgreSQL and the upload volume in sync. Model cache can be recreated and is optional to back up.

### PostgreSQL backup

```powershell
docker compose exec postgres pg_dump -U app_user -d enterprise_ai -Fc -f /tmp/enterprise_ai.dump
docker compose cp postgres:/tmp/enterprise_ai.dump .\backups\enterprise_ai.dump
```

Do not put real passwords in the command. Use the Compose environment or a local secret mechanism.

### PostgreSQL restore

Restore only into an isolated stack or verified empty target database first:

```powershell
docker compose cp .\backups\enterprise_ai.dump postgres:/tmp/enterprise_ai.dump
docker compose exec postgres pg_restore -U app_user -d enterprise_ai --clean --if-exists /tmp/enterprise_ai.dump
```

For plain SQL dumps, use:

```powershell
docker compose exec -T postgres psql -U app_user -d enterprise_ai < .\backups\enterprise_ai.sql
```

### Upload volume backup

```powershell
docker run --rm -v enterprise-ai-knowledge-assistant_uploads_data:/data -v ${PWD}\backups:/backup alpine sh -c "cd /data && tar czf /backup/uploads_data.tgz ."
```

### Upload volume restore

Restore to an isolated stack and verify Document download/processing before using the data:

```powershell
docker run --rm -v enterprise-ai-knowledge-assistant_uploads_data:/data -v ${PWD}\backups:/backup alpine sh -c "cd /data && tar xzf /backup/uploads_data.tgz"
```

### Restore verification

After restore, run migrations, readiness checks, document download checks, and a small upload/process/chat smoke test. Backups are not considered valid until a restore has been tested on an isolated stack.

## Data retention and deletion limitations

- Chat retention is not automated.
- Audit retention is not automated.
- Feedback deletion is not implemented.
- Uploaded-file cleanup is limited to upload failure compensation and soft-delete behavior; no scheduled orphan cleanup worker exists.
- Documents are soft-deleted by application flag.
- Historical Assistant answers and citation excerpts can remain visible to the chat owner after later permission changes.
- Chat messages, feedback reasons, citation excerpts, chunk text, and selected fields are plaintext in PostgreSQL.
- PII masking and malware scanning are not implemented.

## TASK-027 streaming chat checks

Run the streaming marker in Docker:

```powershell
docker compose --profile test run --rm test python -m pytest -m streaming_chat_integration -v
```

Run related regressions without collecting zero tests:

```powershell
docker compose --profile test run --rm test python -m pytest -m llm_provider_integration -v
docker compose --profile test run --rm test python -m pytest -m integration tests/api/test_chat_messages.py -v
docker compose --profile test run --rm test python -m pytest tests/unit/test_sse.py tests/unit/test_grounded_answer_service.py tests/unit/test_citation_validation_service.py -v
```

Manual SSE smoke test uses a normal bearer token and does not put the token in the URL:

```powershell
curl.exe -N `
  -X POST `
  "http://127.0.0.1:8000/api/v1/chat/sessions/<SESSION_ID>/messages/stream" `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -H "Accept: text/event-stream" `
  -d '{"content":"Synthetic SSE question"}'
```

Expected events for a successful no-answer or answered response are `stream.started`, `message.delta`, optional `citations.ready`, and `message.completed`. `stream.error` is terminal on failure. The default stack keeps `LLM_ENABLED=false`; do not enable live providers or add provider credentials for default verification.
## Frontend Setup

Install and run the frontend console:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

The default frontend API base URL is `http://127.0.0.1:8000`. Override it only with a browser-reachable API URL:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

Frontend quality checks:

```powershell
npm run lint
npm run typecheck
npm run test
npm run test:e2e
npm run build
```

Docker frontend profile:

```powershell
docker compose --profile frontend build frontend
docker compose --profile frontend up -d frontend
```

The frontend profile depends on the API health check and serves static assets on `127.0.0.1:${FRONTEND_PORT:-5173}`.
## TASK-028 live frontend UAT

For a local browser walkthrough, use the dedicated guide:

```text
docs/ui/USER_EXPERIENCE_GUIDE.md
```

The short path is:

```powershell
docker compose -f compose.yaml -f compose.uat.yaml up -d
docker compose -f compose.yaml -f compose.uat.yaml --profile frontend up -d frontend
```

The UAT overlay seeds these local-only deterministic login accounts: `admin.uat@example.test` / `LocalUatAdmin!2026`, `manager.uat@example.test` / `LocalUatManager!2026`, and `staff.uat@example.test` / `LocalUatStaff!2026`. To rerun the idempotent seed manually without deleting volumes, use `docker compose -f compose.yaml -f compose.uat.yaml run --rm uat-seed`. Open `http://localhost:5173`. Stop without deleting volumes using:

```powershell
docker compose -f compose.yaml -f compose.uat.yaml stop
```

## TASK-032 Admin Monitoring Checks

After starting the backend, login as an Admin and call the monitoring endpoints with a normal bearer token in the `Authorization` header:

```text
GET /api/v1/admin/system
GET /api/v1/admin/health
GET /api/v1/admin/providers
GET /api/v1/admin/workers
GET /api/v1/admin/statistics
GET /api/v1/admin/queues
GET /api/v1/admin/version
```

Manual checks should confirm:

- Manager and Staff receive `403 FORBIDDEN` for all `/api/v1/admin/*` endpoints.
- Health includes API, PostgreSQL, Redis, worker, OCR, embedding, LLM, Web Search, streaming, and conversation checks.
- Providers show enabled/disabled/configuration state without API keys or endpoint credentials.
- Queues reflect the existing Celery architecture: `documents` is the active document queue; OCR, embedding, retry, and dead-letter are not dedicated queues.
- Statistics are aggregate counts only and do not include chat text, prompts, context, citation excerpts, feedback reasons, filenames, storage keys, or vectors.

Host verification commands:

```powershell
python -m pytest tests/unit/test_admin_monitoring_service.py -v
python -m pytest tests/api/test_admin_monitoring.py -m integration -v
python -m ruff check app/api/v1/admin.py app/services/admin_monitoring_service.py app/schemas/admin_monitoring.py tests/unit/test_admin_monitoring_service.py tests/api/test_admin_monitoring.py
python -m compileall app tests
```

Docker verification remains the same stack flow:

```powershell
docker compose config
docker compose build
docker compose up -d
docker compose ps
curl.exe -i http://127.0.0.1:8000/health/live
curl.exe -i http://127.0.0.1:8000/health/ready
```


## TASK-033 Admin Analytics Checks

After starting the backend, login as an Admin and call the analytics endpoints with a bearer token in the `Authorization` header:

```text
GET /api/v1/admin/analytics/overview
GET /api/v1/admin/analytics/chat
GET /api/v1/admin/analytics/users
GET /api/v1/admin/analytics/search
GET /api/v1/admin/analytics/ocr
GET /api/v1/admin/analytics/llm
GET /api/v1/admin/analytics/feedback
GET /api/v1/admin/analytics/audit
GET /api/v1/admin/reports/export?report=overview&format=json
GET /api/v1/admin/reports/export?report=overview&format=csv
```

Supported date filters:

```text
period=today
period=7d
period=30d
period=90d
period=custom&date_from=2026-08-01T00:00:00Z&date_to=2026-08-04T23:59:59Z
```

Manual checks should confirm Manager and Staff receive `403 FORBIDDEN`, missing bearer tokens receive `401`, JSON/CSV exports omit sensitive content, and `format=pdf` returns `422 VALIDATION_ERROR` until a safe PDF export backend is added.

Focused verification commands:

```powershell
python -m pytest tests/unit/test_admin_analytics_service.py -v
python -m pytest tests/api/test_admin_analytics.py -m integration -v
python -m pytest tests/api/test_admin_analytics.py tests/api/test_admin_monitoring.py tests/api/test_web_search_admin.py tests/api/test_rbac_dependencies.py -m integration -v
python -m ruff check app/api/v1/admin_analytics.py app/services/admin_analytics_service.py app/schemas/admin_analytics.py tests/unit/test_admin_analytics_service.py tests/api/test_admin_analytics.py
python -m compileall app tests
```

Docker verification remains the same backend stack flow:

```powershell
docker compose config
docker compose build
docker compose up -d
docker compose ps
curl.exe -i http://127.0.0.1:8000/health/live
curl.exe -i http://127.0.0.1:8000/health/ready
curl.exe -i http://127.0.0.1:8000/api/v1/admin/analytics/overview
```

The final curl should return `401 ACCESS_TOKEN_INVALID` without a token, confirming the route exists and RBAC is enforced.

## TASK-034 production deployment and observability

The local development stack remains `compose.yaml`. Use `compose.prod.yaml` for production-oriented runtime checks.

1. Create a private production env file outside source control:

```powershell
Copy-Item .env.production.example .env.production
```

Replace every placeholder secret before starting containers. The example file is intentionally not production-safe.

2. Validate and start production runtime:

```powershell
docker compose --env-file .env.production -f compose.prod.yaml config
docker compose --env-file .env.production -f compose.prod.yaml build
docker compose --env-file .env.production -f compose.prod.yaml up -d
docker compose --env-file .env.production -f compose.prod.yaml ps
```

3. Verify reverse proxy and API health:

```powershell
curl.exe -i http://127.0.0.1:8080/health/live
curl.exe -i http://127.0.0.1:8080/health/ready
```

Production Nginx forwards `X-Forwarded-*` and `X-Request-ID`, applies security headers, enforces `client_max_body_size 25m`, and disables proxy buffering for the SSE stream route. The committed HTTPS file is disabled by extension and contains no certificate. Mount real certificates at runtime before enabling TLS.

4. Verify internal metrics from the API container or Prometheus:

```powershell
docker compose --env-file .env.production -f compose.prod.yaml exec api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/metrics', timeout=5).read().decode()[:500])"
```

The reverse proxy intentionally returns `404` for external `/metrics`.

5. Optional Prometheus/Grafana provisioning check:

```powershell
docker compose --profile observability --env-file .env.production -f compose.prod.yaml config
```

Starting the observability profile may require pulling Prometheus and Grafana images if they are not already present.

### TASK-034 backup and restore helpers

PostgreSQL backup:

```powershell
.\scripts\backup\postgres_backup.ps1 -ComposeFile compose.prod.yaml -BackupDir .backups
```

PostgreSQL restore verification into an isolated database:

```powershell
.\scripts\backup\postgres_restore.ps1 -DumpPath .\.backups\enterprise_ai_postgres_YYYYMMDD-HHMMSS.dump -TargetDatabase enterprise_ai_restore_check
```

Uploads volume backup:

```powershell
.\scripts\backup\uploads_backup.ps1 -BackupDir .backups
```

Uploads restore verification into an isolated volume:

```powershell
.\scripts\backup\uploads_restore.ps1 -ArchivePath .\.backups\enterprise_ai_uploads_YYYYMMDD-HHMMSS.tgz -TargetVolumeName enterprise-ai-knowledge-assistant-prod_uploads_restore_check
```

Restore scripts refuse production overwrite unless the explicit overwrite switch is provided. Backups are not valid until an isolated restore has been tested.

### TASK-034 failure recovery smoke

Use controlled stops/restarts only in a non-production verification environment:

```powershell
docker compose --env-file .env.production -f compose.prod.yaml restart api
docker compose --env-file .env.production -f compose.prod.yaml restart worker
docker compose --env-file .env.production -f compose.prod.yaml stop redis
docker compose --env-file .env.production -f compose.prod.yaml start redis
docker compose --env-file .env.production -f compose.prod.yaml stop postgres
docker compose --env-file .env.production -f compose.prod.yaml start postgres
```

After each restart, verify `docker compose ps`, `/health/ready`, Celery worker ping, and migration state.

## TASK-035 Final Acceptance

TASK-035 -- Final Acceptance Test & Release Candidate is not started by the UAT UX + LLM configuration fix. Do not treat focused UAT selector, fake-provider, Docker, or chat verification as release-candidate sign-off.
## TASK-034.1 Local Real LLM Acceptance Setup

TASK-034.1 requires a real local or explicitly configured external provider. Do not use `compose.uat.yaml` or `fake-openai-provider.mjs` for real answer-quality acceptance.

Current recommended local path on Docker Desktop:

1. Install and start Ollama on the host.
2. Pull the selected model deliberately, for example:

```powershell
ollama pull qwen3:4b
```

If the machine cannot run that model comfortably, choose a smaller multilingual instruct model such as `qwen2.5:3b`. Do not download a multi-GB model without operator approval.

3. Configure `.env` with actual settings names read by `app.core.config.Settings`:

```env
LLM_ENABLED=true
LLM_PROVIDER=ollama
LLM_OLLAMA_BASE_URL=http://host.docker.internal:11434
LLM_OLLAMA_MODEL=qwen3:4b
LLM_OLLAMA_REASONING_EFFORT=none
LLM_TIMEOUT_SECONDS=180
LLM_STREAM_HEARTBEAT_SECONDS=15
LLM_STREAM_MAX_DURATION_SECONDS=300
LLM_TEMPERATURE=0.0
LLM_MAX_OUTPUT_TOKENS=1024
WEB_SEARCH_ENABLED=false
WEB_SEARCH_MODE=internal_only
```

`LLM_MODEL_NAME` is not read by the backend. Use `LLM_MODEL` or provider-specific model variables such as `LLM_OLLAMA_MODEL` and `LLM_LM_STUDIO_MODEL`.

Optional warm-up before live acceptance:

```powershell
$body = @{ model = "qwen3:4b"; messages = @(@{ role = "user"; content = "Reply OK." }); stream = $false; reasoning_effort = "none"; max_tokens = 16; temperature = 0 } | ConvertTo-Json -Depth 8 -Compress
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:11434/v1/chat/completions" -ContentType "application/json" -Body $body
```

This loads the local model before acceptance. Backend readiness must remain independent of Ollama availability.

4. Start the normal development stack, not the UAT overlay:

```powershell
docker compose up -d
```

5. Verify the API container can reach the host provider by using `host.docker.internal`. Then upload the new local acceptance PDFs from `artifacts/task-034-1/` through the normal document upload workflow and wait for `READY`.

6. Run the required strict grounded acceptance questions manually through both non-streaming and streaming chat. Record each answer, citation number, document title, page, excerpt, and claim support in `artifacts/task-034-1/real-llm-acceptance-report.json`.

7. Validate the completed report explicitly:

```powershell
$env:RUN_REAL_LLM_ACCEPTANCE="true"
$env:REAL_LLM_ACCEPTANCE_REPORT="artifacts/task-034-1/real-llm-acceptance-report.json"
python -m pytest tests/integration/test_real_llm_strict_grounded_acceptance.py -m real_llm_acceptance -q
```

Local status for TASK-034.1 follow-up: Ollama `qwen3:4b` connectivity and buffer-after-validation SSE have been verified for the Nova Digital CEO, CTO, and NovaAssist live questions with no `STREAM_TIMEOUT`. TASK-034.1 still requires the full strict matrix and manual claim report before completion.
