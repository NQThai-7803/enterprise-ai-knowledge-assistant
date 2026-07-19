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
