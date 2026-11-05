# Deployment Guide

## 1. Target architecture

```text
Nginx
├── Frontend static app
└── Reverse proxy /api
      └── FastAPI containers
            ├── PostgreSQL + pgvector
            ├── Redis
            ├── Celery workers
            └── Object storage
```

## 2. Containers

- backend
- worker
- postgres
- redis
- frontend
- nginx
- optional minio

## 3. Production requirements

- TLS.
- Strong secrets.
- Database backup.
- Persistent volumes.
- Health checks.
- Resource limits.
- Centralized logs.
- CORS restricted.
- Debug disabled.
- **Ollama context length set on the Ollama server (mandatory when `LLM_PROVIDER=ollama`).**

### 3.1 Ollama server context length (mandatory)

The app talks to Ollama through the OpenAI-compatible `/v1/chat/completions` endpoint. That endpoint
ignores `options`, so `LLM_OLLAMA_NUM_CTX` has no effect. The model runs with the context length of
the Ollama **server**, which is 4096 by default on Ollama 0.40.13.

When a prompt is longer than that context, Ollama drops the beginning without any error. The
system instructions go first, and `usage.prompt_tokens` then reports about half the context
(verified 2026-10-31: 2050 tokens at 4096, 4098 at 8192).

- Set `OLLAMA_CONTEXT_LENGTH` on the machine or container that runs Ollama, at least as large as
  `LLM_CONTEXT_WINDOW` (default 8192). Restart Ollama afterwards.
  - Windows desktop: set the user environment variable, then restart the Ollama tray app.
  - Linux service: set it in the systemd unit.
  - Container: set it in the Ollama container's environment.
- Verify after a request: `GET /api/ps` must report `context_length` equal to the configured value.
- None of the repository's compose files runs an Ollama service; the stacks call the host Ollama
  through `host.docker.internal`. There is no compose setting to change, but the host requirement
  above applies to every stack that uses Ollama.

## 4. Deployment flow

```text
Push to main
→ CI lint and test
→ Build images
→ Push registry
→ Pull on server
→ Run migration
→ Restart services
→ Readiness check
```

## 5. Migration safety

- Backup trước migration quan trọng.
- Không chạy destructive migration tự động nếu chưa review.
- App version và migration version phải tương thích.

## 6. Rollback

- Giữ image version trước.
- Có kế hoạch rollback database nếu migration không backward compatible.
- Không dùng `latest` làm tag duy nhất ở production.
