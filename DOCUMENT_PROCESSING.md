# Document Processing Design

## 1. Supported file types

Current ingestion supports:

- `application/pdf` (`.pdf`).
- `image/png` (`.png`).
- `image/jpeg` (`.jpg`, `.jpeg`).

TASK-030 adds OCR for image documents and scanned/low-quality PDF pages through the asynchronous worker pipeline. Full TASK-030 completion is still blocked by Docker runtime verification.

## 2. Processing states```text
UPLOADED
→ PROCESSING
→ READY
       ↘ FAILED
```

`ARCHIVED` là trạng thái business, không phải processing failure.

## 3. Processing steps

1. Load document metadata.
2. Ensure document not deleted.
3. Set status PROCESSING.
4. Read file from storage.
5. Extract text page by page.
6. Normalize text.
7. Reject document with no usable text hoặc đánh dấu cần OCR.
8. Split chunks.
9. Generate embeddings theo batch.
10. Insert chunks trong transaction phù hợp.
11. Set status READY.
12. On failure, set FAILED và lưu error an toàn.

## 4. Text normalization

- Unicode normalization.
- Remove null characters.
- Collapse repeated spaces.
- Preserve paragraph breaks hợp lý.
- Detect repeated header/footer nếu có thể.
- Không tự sửa nội dung nghiệp vụ.

## 5. Idempotency

Reprocess phải:

- Không tạo chunk trùng.
- Xóa hoặc thay thế chunk cũ trong transaction.
- Có processing version.
- Có lock hoặc trạng thái ngăn hai worker xử lý cùng tài liệu.

## 6. Failure handling

- Retry lỗi network/provider tạm thời.
- Không retry vô hạn với file hỏng.
- Lưu error code riêng với message hiển thị.
- Log stack trace ở server nhưng không trả cho client.

## 7. Storage abstraction

```python
class FileStorage(Protocol):
    def save(...): ...
    def open(...): ...
    def delete(...): ...
    def exists(...): ...
```

MVP dùng local storage; production có thể chuyển sang S3/MinIO.

## 8. TASK-008 database status model

`DocumentStatus` is implemented in the database model with PostgreSQL enum `document_status`:

```text
UPLOADED
PROCESSING
READY
FAILED
ARCHIVED
```

The intended lifecycle remains:

```text
UPLOADED -> PROCESSING -> READY
PROCESSING -> FAILED
FAILED -> PROCESSING
READY -> PROCESSING
UPLOADED | READY | FAILED -> ARCHIVED
```

TASK-008 only stores status and sanitized error metadata. The processing pipeline, worker, storage reader, PDF extraction, chunking, embedding, retry logic, and state-transition service are not implemented yet. There is no database trigger enforcing status transitions.

`documents.error_message` is nullable and must contain only sanitized user-safe processing errors. It must not contain stack traces, absolute file-system paths, API keys, database URLs, or full document content.
## 9. TASK-011 Celery worker foundation

Implemented in TASK-011:

- Celery app configured with Redis broker and Redis result backend.
- Worker ping task `system.worker_ping` verifies client -> Redis broker -> worker -> Redis result backend.
- Document task skeleton `documents.process_document` is routed to the `documents` queue.
- Task messages carry only `document_id` as a string UUID.
- Worker uses its own async database session and does not reuse FastAPI request sessions.
- Atomic claim moves non-deleted Documents from `UPLOADED` or `FAILED` to `PROCESSING`.
- `PROCESSING`, `READY`, `ARCHIVED`, deleted, and missing Documents are not claimed.
- TASK-015 replaces the earlier placeholder with the real extraction, chunking, embedding, persistence, and READY/FAILED pipeline.
- Retry reset can move `PROCESSING` back to `UPLOADED` for bounded retry attempts.
- Final retry failure marks the Document `FAILED` with a sanitized message.

Not implemented in TASK-011:

- PDF extraction.
- Text normalization implementation.
- Document chunks.
- Embeddings.
- READY transition.
- Automatic enqueue from upload.
- Worker crash recovery or watchdog for Documents left in `PROCESSING`.
## 10. TASK-012 PDF extraction foundation

Implemented in TASK-012:

- `TextExtractor` abstraction.
- PyMuPDF-based PDF text extractor using `import pymupdf`.
- Page-level plain text extraction.
- 1-based page numbering.
- Blank-page preservation.
- Unicode NFC normalization.
- Line-ending, null-character, and whitespace normalization.
- Usable-character counting.
- Encrypted/password-protected PDF detection.
- Invalid or corrupted PDF detection.
- Maximum page-count validation before page extraction.
- No-usable-text detection for blank and image-only PDFs.
- Typed internal PDF extraction failure codes.
- Storage helper that reads bounded bytes through `FileStorage`.

Not implemented in TASK-012:

- Header/footer removal.
- Table reconstruction.
- OCR.
- Chunking.
- Token counting.
- Embeddings.
- Persistence of extracted pages.
- READY transition.
- Full worker pipeline.

`page.get_text("text", sort=True)` is used when configured. Sorting can improve common reading order, but it does not guarantee perfect order for multi-column PDFs, complex tables, text boxes, rotated text, overlapping elements, or unusual PDF encodings.
## 11. TASK-013 Chunking foundation

### Da trien khai

- Token counting.
- Page-aware chunking.
- Target token size as a soft limit.
- Hard maximum token size.
- Configurable token overlap.
- Paragraph-first splitting.
- Sentence fallback using a deterministic heuristic.
- Token-window fallback for oversized sentences or long words.
- Stable zero-based chunk indexes.
- Page metadata on each chunk.
- Deterministic SHA-256 chunk checksum.
- Safe small-final-chunk merge behavior.
- Chunking security tests for repr, errors, logs, and result metadata.

### Chua trien khai

- Chunk persistence.
- Embeddings.
- pgvector.
- Semantic search.
- Hybrid retrieval.
- Full Celery pipeline.
- READY transition.
- Citation rendering.

Chunk target size is a soft limit. Chunk maximum size is a hard limit. Sentence splitting uses a small heuristic and is not full NLP sentence segmentation. Header/footer removal is not implemented. Text tables are preserved as extracted text, but table structure is not reconstructed.

## 12. TASK-014 embeddings and vector storage

### Da trien khai

- Chunk embedding.
- Query embedding for internal verification.
- Batch embedding.
- Vector normalization.
- Embedding dimension and finite-value validation.
- Chunk persistence.
- Atomic chunk replacement.
- PostgreSQL pgvector extension.
- `document_chunks` table.
- HNSW cosine index.
- Real Vietnamese embedding model tests.

### Chua trien khai

- Full worker integration.
- Upload enqueue.
- READY transition.
- Search API.
- Permission-aware retrieval.
- Hybrid retrieval.
- Chat/citations.

TASK-014 persists chunk text and embeddings through the internal service. TASK-015 connects Celery `documents.process_document` to extraction, chunking, embeddings, atomic persistence, and READY/FAILED transitions.

## 13. TASK-015 processing pipeline

### Implemented

- Upload auto enqueue after database commit.
- Celery document-processing pipeline.
- File loading through `FileStorage`.
- PDF extraction through `PyMuPDFTextExtractor`.
- Page-aware chunking.
- Local passage embedding.
- Chunk and vector persistence in `document_chunks`.
- Atomic chunk replacement.
- `PROCESSING -> READY` transition after successful persistence.
- Sanitized `PROCESSING -> FAILED` transition for permanent failures.
- Bounded retry handling for classified transient failures.
- Idempotent handling for duplicate deliveries.
- Concurrent-claim protection.

### Not implemented

- Reprocess API.
- PROCESSING watchdog or recovery scheduler.
- Dead-letter queue.
- OCR.
- Semantic retrieval API.
- Hybrid search.
- Chat.
- Citation rendering.

The worker materializes bounded PDF bytes, generated chunks, and embedding vectors in memory during processing. Chunk text is persisted in PostgreSQL but is not returned through API responses, Celery results, or Redis messages.

## 14. TASK-030 OCR and Document Image Understanding

Recovery implementation status: In Progress until Docker/API/integration acceptance can be verified.

Implemented OCR path:

```text
Upload PDF/PNG/JPEG
    -> validate extension, MIME, and signature
    -> save through FileStorage
    -> enqueue documents.process_document
    -> worker loads stored bytes and MIME metadata
    -> ExtractionRouter
       -> native PDF text when usable
       -> Tesseract OCR for scanned/low-quality PDF pages
       -> Tesseract OCR for standalone PNG/JPEG images
    -> page-aware chunking
    -> embeddings
    -> document_chunks
    -> READY or FAILED with sanitized error
```

OCR safety limits are controlled by `OCR_ENABLED`, `OCR_LANGUAGES`, `OCR_MAX_PAGES`, `OCR_RENDER_DPI`, `OCR_MAX_IMAGE_PIXELS`, `OCR_MAX_IMAGE_WIDTH`, `OCR_MAX_IMAGE_HEIGHT`, `OCR_PAGE_TIMEOUT_SECONDS`, `OCR_DOCUMENT_TIMEOUT_SECONDS`, `OCR_MAX_EXTRACTED_CHARACTERS`, and OCR text-quality thresholds.

The OCR engine is Tesseract through `app.document_processing.ocr.tesseract_provider.TesseractOCRProvider`. The Docker runtime image installs English and Vietnamese language packs. The provider is lazy and subprocess based; it does not download models or call external services at import/startup.

Page metadata includes page number, extraction method, source type, optional confidence, image width/height, and warnings. Retrieval and citation code continue to use existing chunk/page metadata and source-marker mapping; no Chat API, streaming, conversation memory, citation architecture, or database schema change was introduced.

Known limitations until TASK-030 completion:

- Docker runtime Tesseract, API, worker, Redis, Postgres, and migration verification is blocked by the local Docker Desktop daemon state.
- OCR quality is best-effort plain text extraction; table reconstruction, handwriting understanding, layout analysis, and visual question answering are not implemented.
- Host Tesseract is not required for unit tests and was not available on this machine; runtime OCR is expected inside the Docker image once Docker is healthy.