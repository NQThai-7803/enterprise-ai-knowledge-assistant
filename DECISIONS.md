# Architecture Decisions

This file lists accepted project-level decisions. Detailed records may be added under `adr/`.

## DEC-001 — Backend framework

Use FastAPI for the Python backend.

## DEC-002 — Primary database

Use PostgreSQL with pgvector.

## DEC-003 — Async document processing

Use Celery with Redis for background processing.

## DEC-004 — MVP document type

Support text-based PDF first. OCR and other formats come later.

## DEC-005 — Authorization model

Use role plus document access scope and optional direct grants.

## DEC-006 — RAG safety

Permission filtering occurs before context is sent to the LLM. Citations are validated by backend.

## DEC-007 — Provider abstraction

Embedding, LLM and storage providers must be replaceable through interfaces.

## DEC-008 — Held-out v1 is used for diagnosis

Since the official score (2026-11-05, `docs/eval/runs/heldout-v1-f3cdbf3/score.md`), held-out v1 is used for diagnosis and is no longer a test set. A new held-out v2 is required before release. Dev stays Q001-Q100.
