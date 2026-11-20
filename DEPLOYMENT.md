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
- **Ollama prompt cache capped with `LLAMA_ARG_CACHE_RAM=2048` (mandatory when `LLM_PROVIDER=ollama`, section 3.2).**
- Templates and drafts marked `lifecycle_status=DRAFT` by an admin. With `RAG_DRAFT_DOCUMENT_POLICY=exclude` (the default, DEC-036) they never answer. Documents uploaded before DEC-033 are `ACTIVE` until marked.

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

### 3.2 Ollama prompt cache (mandatory, every model)

Ollama 0.40 runs each model in llama-server. llama-server keeps the state of earlier prompts in
host RAM, **up to 8192 MiB by default**, and frees it only when the model unloads. A long-running
server therefore grows to the model's size plus 8 GiB once enough different prompts have passed.

- One prompt takes about 80 MiB with `qwen2.5:3b` and about 220 MiB with `qwen3.5:4b`.
- On a 16 GB CI runner the cache reached 6.6-8.0 GiB during a 50-question UAT run with
  `qwen3.5:4b`. One run lost its runner, and the others kept as little as 1.2 GB free (DEC-029).

This applies to every model, the default `qwen3.5-text:4b` and the rollback `qwen2.5:3b`:

- Set `LLAMA_ARG_CACHE_RAM=2048` (MiB) in the environment of the Ollama server, as for
  `OLLAMA_CONTEXT_LENGTH` above, and restart Ollama. Ollama passes the variable to llama-server.
- Verify in the Ollama server log after the first request:
  `prompt cache is enabled, size limit: 2048 MiB`.
  - Windows: `%LOCALAPPDATA%\Ollama\server.log`.
  - Linux service: `journalctl -u ollama`.
- With the cap, a UAT half kept 6.8 GB free on the same runner, at the same speed.
- `0` turns the cache off. Every request then re-reads its whole prompt.
- The eval workflows use the same 2048 MiB (`eval.yml` input `ollama_cache_ram`, `heldout-v2.yml`).

### 3.3 Default answer path and model (DEC-040)

Since DEC-040 (2026-11-20) the default is simple answer mode with the s1-s3 fixes and
`qwen3.5-text:4b`, with `RAG_DRAFT_DOCUMENT_POLICY=exclude`. Before it was `legacy` + `qwen2.5:3b`,
which stays available as the rollback below.

- **Hardware required: an NVIDIA GPU with at least 4 GB VRAM** (DEC-029 (c)).
  - Measured on a GTX 1650 4 GB: 2971 MiB of VRAM, 18.7-28.6 s of LLM time per question
    (median 20.7 s), the model 100% on the GPU.
  - A CPU-only host with 16 GB RAM works but is slow: about 77 s per question end to end (UAT
    median, 4 vCPU), about 2.5 times `legacy` + `qwen2.5:3b`. Set `LLM_TIMEOUT_SECONDS=600` there.
- **Build `qwen3.5-text:4b` once on the Ollama host.** It is `qwen3.5:4b` without its vision
  encoder, with every layer pinned to the GPU:

  ```bash
  python scripts/deploy/ollama_text_model.py qwen3.5:4b qwen3.5-text:4b --num-gpu 99
  ```

  - The Ollama library has no text-only tag, and the app cannot pass `num_gpu` (the `/v1`
    endpoint ignores options), so the model carries `PARAMETER num_gpu 99` itself.
  - Without it, Ollama keeps a VRAM reserve and leaves 36-52% of the layers on the CPU.
  - Verify after one request: `ollama ps` shows `100% GPU`.
  - On a CPU-only host, build it without `--num-gpu`.
- **Settings** (the application defaults, also in `.env.example`):
  - `RAG_ANSWER_MODE=simple`;
  - `RAG_SIMPLE_ABSENCE_SENTENCES_ENABLED`, `RAG_SIMPLE_SHORT_PROMPT_ENABLED` (s1),
    `RAG_SIMPLE_RELAXED_RULES_ENABLED`, `RAG_SIMPLE_CLAIM_RELEVANCE_ENABLED` (s2) and
    `RAG_SIMPLE_QUESTION_LIST_SEGMENTS_ENABLED` (s3) `=true`;
  - `LLM_OLLAMA_MODEL=qwen3.5-text:4b`, `LLM_OLLAMA_REASONING_EFFORT=none`;
  - `LLM_TIMEOUT_SECONDS=90` on the GPU (per call; about 3 times the longest question measured),
    600 on CPU;
  - the prompt cache cap of section 3.2.
- **Rollback to `legacy` + `qwen2.5:3b`** (no migration, no re-ingestion):
  1. `ollama pull qwen2.5:3b` on the Ollama host.
  2. Set `RAG_ANSWER_MODE=legacy` and `LLM_OLLAMA_MODEL=qwen2.5:3b`. The `RAG_SIMPLE_*` flags are
     read only in simple mode, so they can stay as they are.
  3. Restart the API: `docker compose up -d --force-recreate api` (production: the same with the
     production compose and env files).
  - Check: `docker compose exec api env | grep -E 'RAG_ANSWER_MODE|LLM_OLLAMA_MODEL'` shows the
    two rollback values.
  - Eval runs name the rollback configuration
    `legacy:EVAL_ANSWER_MODE=legacy,EVAL_LLM_MODEL=qwen2.5:3b` (`scripts/eval/README.md`).

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
