# System Architecture

## 1. Kiáº¿n trÃºc tá»•ng thá»ƒ

```text
Web Client
    |
    v
FastAPI Application
    â”œâ”€â”€ Auth Module
    â”œâ”€â”€ User & Department Module
    â”œâ”€â”€ Document Module
    â”œâ”€â”€ Chat Module
    â”œâ”€â”€ Retrieval Module
    â”œâ”€â”€ Feedback Module
    â””â”€â”€ Audit Module
          |
          +--> PostgreSQL + pgvector
          +--> Redis
          +--> Celery Worker
          +--> File Storage
          +--> Embedding Provider
          +--> LLM Provider
```

## 2. Kiáº¿n trÃºc backend

```text
app/
â”œâ”€â”€ api/
â”‚   â”œâ”€â”€ dependencies.py
â”‚   â””â”€â”€ v1/
â”‚       â”œâ”€â”€ auth.py
â”‚       â”œâ”€â”€ users.py
â”‚       â”œâ”€â”€ departments.py
â”‚       â”œâ”€â”€ documents.py
â”‚       â”œâ”€â”€ chat.py
â”‚       â”œâ”€â”€ feedback.py
â”‚       â””â”€â”€ audit_logs.py
â”œâ”€â”€ core/
â”‚   â”œâ”€â”€ config.py
â”‚   â”œâ”€â”€ security.py
â”‚   â”œâ”€â”€ logging.py
â”‚   â””â”€â”€ exceptions.py
â”œâ”€â”€ db/
â”‚   â”œâ”€â”€ base.py
â”‚   â”œâ”€â”€ session.py
â”‚   â””â”€â”€ migrations/
â”œâ”€â”€ models/
â”œâ”€â”€ schemas/
â”œâ”€â”€ repositories/
â”œâ”€â”€ services/
â”œâ”€â”€ rag/
â”‚   â”œâ”€â”€ chunking.py
â”‚   â”œâ”€â”€ embeddings.py
â”‚   â”œâ”€â”€ retrieval.py
â”‚   â”œâ”€â”€ reranking.py
â”‚   â”œâ”€â”€ prompts.py
â”‚   â””â”€â”€ citations.py
â”œâ”€â”€ workers/
â”‚   â”œâ”€â”€ celery_app.py
â”‚   â””â”€â”€ document_tasks.py
â”œâ”€â”€ storage/
â”œâ”€â”€ tests/
â””â”€â”€ main.py
```

## 3. Layer responsibilities

### API layer

- Nháº­n request.
- Validate dá»¯ liá»‡u báº±ng schema.
- Gá»i service.
- Chuyá»ƒn exception thÃ nh HTTP response.
- KhÃ´ng chá»©a truy váº¥n database phá»©c táº¡p.

### Service layer

- Chá»©a business logic.
- Äiá»u phá»‘i repository, storage, RAG vÃ  audit.
- Quáº£n lÃ½ transaction khi cáº§n.

### Repository layer

- Truy váº¥n database.
- KhÃ´ng chá»©a logic HTTP.
- Ãp dá»¥ng filter permission á»Ÿ query phÃ¹ há»£p.

### RAG layer

- Chunking.
- Embedding.
- Retrieval.
- Reranking.
- Prompt building.
- Citation validation.

### Worker layer

- Xá»­ lÃ½ document báº¥t Ä‘á»“ng bá»™.
- Retry cÃ³ kiá»ƒm soÃ¡t.
- Cáº­p nháº­t tráº¡ng thÃ¡i vÃ  error message.

## 4. Dependency rules

```text
API â†’ Service â†’ Repository â†’ Database
               â†˜ RAG Provider
               â†˜ Storage Provider
               â†˜ Audit Service
```

KhÃ´ng cho phÃ©p:

- Model import router.
- Repository gá»i HTTP response.
- RAG module truy cáº­p global user mÃ  khÃ´ng truyá»n permission scope.
- Router gá»i trá»±c tiáº¿p Celery hoáº·c database ngoÃ i service.

## 5. Provider abstractions

NÃªn táº¡o interface hoáº·c protocol cho:

- `EmbeddingProvider`
- `LLMProvider`
- `FileStorage`
- `TextExtractor`
- `Reranker`

Má»¥c tiÃªu lÃ  cÃ³ thá»ƒ thay provider mÃ  khÃ´ng sá»­a toÃ n bá»™ há»‡ thá»‘ng.

## 6. Async strategy

- FastAPI endpoint dÃ¹ng async khi thao tÃ¡c I/O phÃ¹ há»£p.
- Document processing cháº¡y báº±ng Celery worker.
- KhÃ´ng gá»i OCR hoáº·c embedding hÃ ng loáº¡t trá»±c tiáº¿p trong request upload.

## 7. Error handling

Error response thá»‘ng nháº¥t:

```json
{
  "error": {
    "code": "DOCUMENT_NOT_READY",
    "message": "Document is not ready for search.",
    "details": null,
    "request_id": "..."
  }
}
```

## 8. TASK-011 worker foundation

Implemented asynchronous processing foundation:

```text
FastAPI producer
    -> Redis broker
    -> Celery worker
    -> PostgreSQL
```

- Celery application name: `enterprise_ai`.
- Redis broker is configured by `CELERY_BROKER_URL`.
- Redis result backend is configured by `CELERY_RESULT_BACKEND` and stores only temporary task metadata.
- Document processing tasks are routed to the `documents` queue.
- Worker connectivity task `system.worker_ping` uses the default queue.
- Document task arguments contain only the Document UUID string.
- Worker database access uses a worker-specific async SQLAlchemy engine/session with `NullPool`.
- PostgreSQL remains the source of truth for Document processing status.
- TASK-011 does not implement PDF extraction, chunking, embeddings, or READY transition.
- Upload does not automatically enqueue Document processing in TASK-011.
## 9. TASK-012 PDF extraction foundation

Implemented PDF extraction flow:

```text
FileStorage
    -> bounded PDF bytes
    -> TextExtractor
    -> PyMuPDFTextExtractor
    -> ExtractionResult
```

- `TextExtractor` is a provider abstraction and does not depend on FastAPI, Celery, SQLAlchemy, or Document ORM models.
- `PyMuPDFTextExtractor` extracts plain text page by page from bounded PDF bytes.
- Page numbers in `ExtractionResult` are 1-based.
- Blank pages are preserved as empty `ExtractedPage` entries.
- Extracted text is normalized per page and held only in the in-memory result.
- Extracted text is not persisted to PostgreSQL or Redis in TASK-012.
- The extractor is not connected to the full Celery processing task yet.
- Upload still does not automatically enqueue processing.
- Chunking, embeddings, pgvector, retrieval, and READY transition are not implemented in TASK-012.
## 10. TASK-013 Chunking foundation

Implemented extraction-to-chunking in-memory flow:

```text
FileStorage
    -> PDF bytes
    -> PyMuPDFTextExtractor
    -> ExtractionResult
    -> PageAwareTokenChunker
    -> ChunkingResult
```

- `TokenCounter` is the tokenizer abstraction.
- `TiktokenTokenCounter` is the current token-counting implementation.
- `TextChunker` is the chunking abstraction.
- `PageAwareTokenChunker` chunks extracted page text with paragraph-first splitting, sentence fallback, and token-window fallback.
- Chunk metadata keeps stable chunk indexes, token counts, character counts, page numbers, overlap counts, and deterministic SHA-256 checksums.
- Chunking is deterministic for the same extraction result, configuration, and tokenizer encoding.
- Chunks are not persisted in TASK-013.
- Embeddings, pgvector storage, retrieval, and READY transition are not implemented in TASK-013.
- The full Celery document-processing pipeline is not connected yet.
- There is no API endpoint for viewing chunks.

## 11. TASK-014 Embeddings and vector storage

Implemented chunk embedding and vector persistence flow:

```text
FileStorage
    -> PyMuPDFTextExtractor
    -> ExtractionResult
    -> PageAwareTokenChunker
    -> ChunkingResult
    -> EmbeddingProvider
    -> SentenceTransformer provider
    -> PostgreSQL document_chunks + pgvector
```

- Embedding runs locally through Sentence Transformers.
- The default model is `intfloat/multilingual-e5-small`.
- Passage chunks use the `passage: ` prefix only while embedding.
- Query verification uses the `query: ` prefix.
- Embedding vectors are normalized by default.
- The persisted vector dimension is fixed at 384 for this MVP schema.
- PostgreSQL stores vectors in `document_chunks.embedding` using pgvector `vector(384)`.
- A HNSW cosine index exists on chunk embeddings.
- The worker does not call extraction, chunking, embedding, or persistence yet.
- Upload does not automatically enqueue processing yet.
- There is no public semantic retrieval API in TASK-014.

## 12. TASK-015 end-to-end document processing pipeline

Implemented asynchronous ingestion flow:

```text
FastAPI Upload
    -> LocalFileStorage
    -> PostgreSQL Document: UPLOADED
    -> Celery/Redis queue
    -> Worker atomic claim: PROCESSING
    -> PyMuPDF extraction
    -> Page-aware chunking
    -> SentenceTransformer embedding
    -> document_chunks + pgvector
    -> Document: READY
```

Failure flow:

```text
PROCESSING -> FAILED
```

- Upload returns HTTP 202 before processing finishes.
- The upload service enqueues only after file save and database commit succeed.
- The Celery task receives only the Document UUID string.
- Redis does not carry PDF bytes, page text, chunk text, token IDs, vectors, storage keys, or user data.
- PostgreSQL remains the source of truth for status.
- The worker claims only `UPLOADED` and `FAILED` Documents atomically.
- Chunk replacement and the `READY` transition are committed in the same database transaction.
- Permanent processing failures store sanitized `FAILED` messages.
- There is no public search, chunk, embedding, chat, or citation API in TASK-015.
## 13. TASK-016 semantic retrieval foundation

Implemented internal semantic retrieval flow:

```text
User query
    -> query validation
    -> query embedding
    -> permission-aware pgvector query
    -> relevance threshold
    -> top-k RetrievalHit results
```

- Retrieval embeds user questions with the configured query embedding path.
- Retrieval joins `document_chunks` to `documents` and considers only `READY` Documents.
- Soft-deleted Documents and `ARCHIVED` Documents are excluded.
- The reusable TASK-010 Document access filter is applied inside the PostgreSQL vector query before ordering and `LIMIT`.
- Query embeddings are request-time values and are not persisted to PostgreSQL, Redis, Celery results, or logs.
- Semantic retrieval is an internal service only in TASK-016.
- There is no public Search API, keyword retrieval, hybrid retrieval, reranking, context assembly, Chat API, LLM answer generation, or citation response yet.

## 14. TASK-017 keyword and hybrid retrieval foundation

Implemented internal keyword and hybrid retrieval flow:

```text
User query
|-- Semantic retrieval
|   `-- query embedding + pgvector cosine
|-- Keyword retrieval
|   `-- PostgreSQL full-text search
`-- Weighted Reciprocal Rank Fusion
    `-- HybridRetrievalResult
```

- Semantic retrieval continues to use the TASK-016 pgvector cosine-distance path and the HNSW cosine index.
- Keyword retrieval uses PostgreSQL full-text search with the fixed `simple` text-search configuration.
- Keyword retrieval uses the `ix_document_chunks_text_fts_simple` GIN expression index on `to_tsvector('simple'::regconfig, text)`.
- Each retrieval branch joins `document_chunks` to `documents`, filters to `READY` Documents, excludes soft-deleted and archived Documents, and applies the shared permission filter in PostgreSQL.
- Permission filtering happens before branch ranking and branch `LIMIT`; unauthorized chunks are not loaded into application memory for later filtering.
- Hybrid retrieval fuses authorized semantic and keyword candidates with weighted Reciprocal Rank Fusion and deduplicates by `chunk_id`.
- Hybrid ranking is deterministic through stable tie-breaks on channel coverage, branch ranks, Document ID, chunk index, and chunk ID.
- Keyword and hybrid retrieval are internal services only.
- There is still no public Search API, Chat API, LLM answer generation, context assembly, reranking, or citation response.
