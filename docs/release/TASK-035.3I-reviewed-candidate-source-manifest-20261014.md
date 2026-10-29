# TASK-035.3I — reviewed future-source inventory

This is a **proposed input set**, not a qualified RC. The exact 495-file
allowlist and per-file SHA-256 values are in
`artifacts/task-035-3i-20261014-a6b8f7f7/source-manifest.json`
(SHA-256 `232e6da563ac5e696940dc4f1d31154e0533c170bff1fa669dddffb7c50a22c2`).
The manifest also names every excluded tracked/untracked path. Its source is
the current dirty working tree, not Git HEAD and not the frozen failed image.

Included: all `app/` Python/migration source including untracked
`leave_relations.py`; maintained backend tests and acceptance runner including
untracked safety contracts; frontend `src/`, mocked/live test source,
`ConfirmDialog.tsx` and new 035.3H tests; frontend package/lock and build/
test configuration; `pyproject.toml`, backend Dockerfile, Compose development/
production inputs, Alembic config, nonsecret `.env.example` templates,
deployment templates, CI workflow/security script, and reviewed release
verification scripts. This permits frontend and backend bytes to be sourced
from **one local reviewed archive**. It does not prove a unified image build.

Excluded but preserved: `.env` and non-example `.env.*`, UAT private
documents/manifests, `data/` uploads/model cache, `.backups/`, Docker and
PostgreSQL volumes, historical benchmark/restore captures, generated
node_modules/dist/cache/coverage, root scratch traces, experimental 2E/2F
harnesses, legacy/reference content, and the `vite-monorepo` Gitlink. UAT
recovery overlays and scripts are evidence/operations inputs needing separate
privacy and deployment review, not silently promoted into a public source
archive. No original is classified disposable.

Across paths shared with the 035.3A source manifest, **zero SHA-256 drifts**
were found. The present copy has 96 additional included paths, mostly frontend
(73), plus release/verification material. The accepted V2 API app source had
matched host app bytes at the 035.1 observation; the 035.3A same-source
candidate then passed focused compatibility but the frozen 035.3B broad
candidate **failed independent answer-safety** despite 98/98 supported V2
cases. Today's 035.3H change is frontend-only. No new broad/safety result is
transferred to this archive; no unexplained shared-source drift was found.

Missing reproducibility/build decisions: no reviewed Git commit, backend
fresh-resolution lock with wheel hashes, pinned base/OS artifacts, verified
frontend clean-room `npm ci`, current CI run on this tree, image export,
embedding-model revision bytes, end-to-end model execution pin, or off-host
restorable evidence copy. The 035.3A 92-package lock is a historical
accepted-API image inventory, **not** a fresh-source resolution for this
frontend-inclusive copy. `vite-monorepo` Gitlink/reference relevance and
the malformed-name tracked root file require owner review before any
source-control cleanup or publication.
