# ADR 0002: Use PostgreSQL and pgvector

## Status

Accepted.

## Context

MVP cần relational data và vector search nhưng nên hạn chế số dịch vụ.

## Decision

Use PostgreSQL as the primary database and pgvector for embeddings.

## Consequences

- Transaction và relational data thống nhất.
- Cần quản lý vector dimension và index đúng với embedding model.
