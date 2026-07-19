# ADR 0001: Use FastAPI

## Status

Accepted.

## Context

Dự án cần API Python, validation schema, async I/O và tài liệu OpenAPI tự động.

## Decision

Use FastAPI as the backend web framework.

## Consequences

- Dễ xây REST API và Swagger.
- Cần quy ước rõ để tránh business logic nằm trong router.
