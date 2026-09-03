Enterprise AI Knowledge Assistant — Markdown documentation update
Date: 2026-08-19

Files included:
- API_SPEC.md
- CHANGELOG.md
- CODEX_START_HERE.md
- DATABASE_DESIGN.md
- FRONTEND_SPEC.md
- PROJECT_STATUS.md
- RAG_DESIGN.md
- TASKS.md
- TESTING_STRATEGY.md

Purpose:
Capture the manual Exact Evidence / citation persistence work, the current Minimal Citation Selection checkpoint,
and the non-negotiable rule that regression/UAT questions are tests only and must never become runtime hard-coded answers.

Important:
These files were generated from the copies supplied in chat. Review/diff before replacing project files.
No application source code was modified by this documentation-generation step.


Latest checkpoint:
- Minimal Citation Selection: IMPLEMENTED + UNIT VERIFIED; live runtime verification pending
- Focused citation mapping: 17 passed in 0.19s
- Next active work: RAG Accuracy Hardening (general retrieval/reranking/validation; no hardcoded Q&A)
