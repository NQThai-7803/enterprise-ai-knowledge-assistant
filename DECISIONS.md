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

## DEC-009 — Reranker deferred; RAM limits for eval

Stay on the lexical fallback for now. PROMPT 6 comes after the fixes to the deterministic route, the alignment filter and the validator. The 1000 MB Available limit applies only when loading or measuring a model alone, with Ollama not loaded. During eval runs the held-out validity rules apply: no INFRA_ERROR, no Ollama restart, no item above 120 s.

## DEC-010 — Rule for choosing RAG_DETERMINISTIC_ROUTE_MODE

Written before any measurement of `legacy`, `strict` or `off` (FIX 1, 2026-11-05).

The route is `_structured_condition_value_answer`. The other deterministic branches are not part of this choice.

Compare each mode with `legacy`, on the RBAC dev set:

1. `false_answer` must not increase.
2. The number of correct answers must increase. A correct answer is a control that passes `control_passed` (right status, right document cited, fact present).

Then:

3. Q001-Q100 only detects regressions and never picks a mode. A regression beyond the guard's tolerance of 1 question, a change of `false_answer_rate` beyond it, or any permission leak blocks the default change under `eaka-rag-change-guard`, and the owner is told.
4. Held-out v1 runs once at the end, as a diagnostic, and does not influence the choice or any further change.

If both `strict` and `off` pass, take the one with more correct answers, then fewer false answers, then `strict` because it keeps the route. (The owner set rules 1 to 4; this tie-break was added by the implementer before measuring.) If neither passes, the default stays `legacy`.
