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

## 7. Validate Compose configuration

```powershell
docker compose config
```

## 8. Start infrastructure

```powershell
docker compose up -d
```

Current local infrastructure:

- `postgres`: PostgreSQL with pgvector image.
- `redis`: Redis with append-only persistence.

Backend, worker, and frontend containers are not part of the stack yet.

## 9. Check container status

```powershell
docker compose ps
```

PostgreSQL and Redis should become `healthy` after startup.

## 10. Check PostgreSQL

```powershell
docker compose exec postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Expected result includes:

```text
accepting connections
```

## 11. Check Redis

```powershell
docker compose exec redis redis-cli ping
```

Expected result:

```text
PONG
```

## 12. Run database migrations

Start PostgreSQL before running Alembic:

```powershell
docker compose up -d postgres
```

Apply schema migrations:

```powershell
alembic upgrade head
alembic current
```

Do not use `Base.metadata.create_all()` in this project. All schema changes must be added through Alembic migrations.

## 13. Create Development Admin

Configure local development values in `.env`:

```env
APP_ENV=development
DEV_ADMIN_EMAIL=admin@example.com
DEV_ADMIN_FULL_NAME=Development Admin
DEV_ADMIN_PASSWORD=<local-strong-password>
```

Then run:

```powershell
python -m app.scripts.seed_admin
```

Rules:

- The command is only for `development` and `test` environments.
- The password comes from `.env` or from hidden interactive terminal input.
- The password is hashed before it is stored.
- The command is idempotent.
- The command does not run automatically during backend startup.
- Do not commit `.env`.

## 14. Run backend

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Health checks:

```powershell
curl.exe -i http://127.0.0.1:8000/health/live
curl.exe -i http://127.0.0.1:8000/health/ready
```

## 15. Test authentication manually

### Login

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
```

Store tokens in variables without printing them:

```powershell
$accessToken = $login.data.access_token
$refreshToken = $login.data.refresh_token
```

### Current user

```powershell
$headers = @{
    Authorization = "Bearer $accessToken"
}

Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/v1/auth/me" `
    -Headers $headers
```

### Refresh

```powershell
$refreshBody = @{
    refresh_token = $refreshToken
} | ConvertTo-Json

$refreshed = Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/api/v1/auth/refresh" `
    -ContentType "application/json" `
    -Body $refreshBody

$newAccessToken = $refreshed.data.access_token
$newRefreshToken = $refreshed.data.refresh_token
```

Using `$refreshToken` again must return `HTTP 401` with `REFRESH_TOKEN_INVALID`.

### Logout

```powershell
$logoutHeaders = @{
    Authorization = "Bearer $newAccessToken"
}

$logoutBody = @{
    refresh_token = $newRefreshToken
} | ConvertTo-Json

Invoke-WebRequest `
    -Method Post `
    -Uri "http://127.0.0.1:8000/api/v1/auth/logout" `
    -Headers $logoutHeaders `
    -ContentType "application/json" `
    -Body $logoutBody
```

Expected result: `HTTP 204`. Using `$newRefreshToken` after logout must return `HTTP 401` with `REFRESH_TOKEN_INVALID`.

Do not put real tokens in screenshots, commits, or reports.

## 16. Check refresh token storage

Do not select or display token hashes directly. To verify only hash length:

```powershell
docker compose exec postgres psql -U app_user -d enterprise_ai -c "SELECT COUNT(*) AS total, MIN(LENGTH(token_hash)) AS min_hash_length, MAX(LENGTH(token_hash)) AS max_hash_length FROM refresh_tokens;"
```

Expected hash length is `64`.

## 17. Run tests

```powershell
python -m pytest -v
python -m pytest -m integration -v
```

Integration and API tests require a real local PostgreSQL database and migrated schema.

## 18. Run lint and format checks

```powershell
python -m ruff check .
python -m ruff format --check .
```

## 19. Run Celery worker

Start Redis and PostgreSQL:

```powershell
docker compose up -d redis postgres
```

Windows local development command:

```powershell
celery -A app.workers.celery_app:celery_app worker --loglevel=INFO --pool=solo --queues=default,documents
```

`solo` is for local development on Windows. It runs with practical concurrency `1` and must not be used for production performance evaluation. TASK-011 does not install eventlet or gevent.

Linux or production-like command:

```bash
celery \
  -A app.workers.celery_app:celery_app \
  worker \
  --loglevel=INFO \
  --queues=default,documents \
  --concurrency=2
```

TASK-011 does not add a worker service to Docker Compose.

Test worker ping from a second terminal:

```powershell
python -c "from app.workers.document_tasks import worker_ping; result = worker_ping.delay(); print(result.get(timeout=15))"
```

Expected safe result:

```text
{'status': 'ok', 'worker': 'enterprise-ai'}
```

Test Document task skeleton only on a disposable local Document:

```powershell
python -c "from app.workers.document_tasks import process_document; result = process_document.delay('<DOCUMENT_UUID>'); print(result.get(timeout=30))"
```

TASK-015 connects the Document worker to file loading, PDF extraction, chunking, embedding, chunk persistence, and READY/FAILED transitions. Upload now enqueues processing after commit.
## 20. Stop containers but keep data

```powershell
docker compose down
```

## 21. Remove local data

```powershell
docker compose down -v
```

Warning: `docker compose down -v` removes local PostgreSQL and Redis named volumes.

## 22. Suggested VS Code extensions

- Python.
- Pylance.
- Ruff.
- Docker.
- REST Client or Thunder Client.

## 23. Troubleshooting

- Check that `.venv` is selected in VS Code.
- Check that Docker Desktop is running.
- Check that PostgreSQL, Redis, and backend ports are free.
- Run `docker compose logs postgres` or `docker compose logs redis` if a container is not healthy.
- Do not manually change migration paths unless you understand the cause.
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
python -c "from app.core.config import get_settings; from app.embeddings.factory import create_embedding_provider; settings = get_settings(); provider = create_embedding_provider(settings); result = provider.embed_passages(['NhÃ¢n viÃªn Ä‘Æ°á»£c hÆ°á»Ÿng 12 ngÃ y nghá»‰ phÃ©p má»—i nÄƒm.', 'Há»‡ thá»‘ng sao lÆ°u dá»¯ liá»‡u vÃ o ban Ä‘Ãªm.']); print({'count': result.count, 'dimensions': result.dimensions, 'normalized': result.normalized, 'model_name': result.model_name})"
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
