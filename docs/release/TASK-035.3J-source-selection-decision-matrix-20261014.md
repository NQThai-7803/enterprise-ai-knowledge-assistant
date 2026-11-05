# TASK-035.3J — reviewed source-selection decision matrix

Date: 2026-10-14 (Asia/Saigon). **Decision package only; no Git staging or
production change.** Verified `main`/`04ebd73aae737414fb591fe2e8b2c286134cdcd8`,
23 modified tracked paths, 74 untracked paths before this report, and the
035.3I 495-file tar SHA-256
`a1a27f60efb1e8b3485343dcea3771985015de0fbda093ebb0fce59b5a26c518`.
All 495 selected originals still match the prior per-file manifest. Root
`AGENTS.md`, `.gitattributes`, and `.gitmodules` are absent. The current
`.gitignore`, Dockerfiles, Compose build contexts, CI and frontend package
scripts were read; no missing file contract was invented.

| Scope | Proposed selection | Build/test/historical role | Gate |
| --- | --- | --- | --- |
| A. Production backend and D. migrations | `app/**/*.py`, `app/db/migrations/**`, including untracked `app/retrieval/leave_relations.py`; root `Dockerfile`, `pyproject.toml`, `alembic.ini`, `README.md` | Docker copies `app`, plus the root four inputs; accepted H5.2 changes are dirty, not in HEAD. | Source-commit review; RAG safety remains open. |
| B. Production frontend | `frontend/src/**` production modules/styles/assets and `frontend/server.mjs`; `frontend/package*.json`, Dockerfile, index/build/style/type configs | Frontend Docker copies its context and builds with npm; 035.3H corrected dialog is part of this source, not a new broad RAG pass. | Source-commit review; live/prod delivery gaps remain. |
| C. Runtime templates and deployment | Root/frontend example env files, generic development/production Compose, `.dockerignore`, `.gitignore`, `deploy/**` | Required or relevant for documented build/deployment paths. Only example envs enter the proposed source set. | Manual configuration/privacy and production-origin/TLS review. |
| E. Application tests | Maintained `tests/**`, frontend component/mock/live test source; retain red answer-safety contracts | Testing source must reveal the blocker, not hide it. | Test/tooling-commit review; current full suite is not green. |
| F. Release qualification tooling | `.github/**`, tracked backup scripts, accepted/broad/safety runners, 035.3I source-inventory script | Reproduction and CI evidence; some tools can write when executed, but this checkpoint only inventories them. | Test/tooling-commit review; future execution needs separate scope. |
| G. Research harnesses | 035.3C.2E/2F evaluation runners and unit harnesses | Historical independent-method work, not a proven RC gate. | Keep as experimental evidence pending owner decision. |
| H. Scratch traces | Three root `tmp_*_trace.py` files | Retrieval/runtime diagnostics; not imported by build/CI. | Preserve separately after privacy review; do not delete or silently lint-exclude. |
| I. Historical acceptance evidence | H5.2 final capture, frozen 035.3B failure, 035.3H report, Redis/restore/backups | Different baseline identities. | Access-controlled immutable evidence; review reports before Git publication. |
| J. Generated output | `artifacts/`, `.venv/`, caches, `frontend/node_modules/`, `dist/`, test results, coverage | Local outputs, not source. | Exclude from source commits; preserve relevant historical evidence separately. |
| K. Sensitive/private | `.env`, `.env.task035.production`, `uat/`, `data/`, `.backups/`, private uploads/PDFs/model bytes | Required for some local runtime/recovery, but not ordinary Git source. | Access-controlled storage and manual privacy decision. |
| L. Gitlink/legacy | `vite-monorepo`, `tore package.json package-lock.json`, `files-for-chat/**`, `frontend/files-for-chat/**`, `frontend-stitch-reference/**`, old zip/7B Modelfile/design-tool assets | No direct active backend/frontend Docker or CI reference found; historical/design value may remain. | REVIEW_REQUIRED; inherited tracked files cannot be removed by merely omitting `git add`. |

The exact per-file proposed Git action, current hash, Git state, purpose,
build/test/history role, sensitivity and approval appears in
`TASK-035.3J-proposed-git-staging-manifest-20261014.json`. A prior 035.3I
source tar is **not** a clean-room build, and the 035.3B candidate **FAILED**
permission-aware unsupported-answer safety despite 98/98 supported broad
answers. The 035.3H frontend mock success is separately scoped. Source
selection is **READY_FOR_REVIEW**, not approved for staging/publication.
