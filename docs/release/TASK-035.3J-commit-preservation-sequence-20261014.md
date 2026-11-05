# TASK-035.3J — proposed source/evidence preservation sequence

No branch, index, commit, tag, push, image, service or database was changed.
These are **logical future boundaries**, not authorization to execute them.

1. **Engineering source checkpoint:** after owner decisions and exact-diff
   privacy review, version backend app/migrations, generic build/deployment
   inputs, dependency manifests and frontend production source from one
   reviewed source identity. Record the 035.3I per-file manifest and archive
   hash. This checkpoint must not be called an accepted RC; the current
   backend still carries the independent safety blocker.
2. **Tests and release tooling checkpoint:** version maintained backend and
   frontend tests, red safety contracts, CI, and reviewed verification/
   backup scripts. Preserve experimental 2E/2F and root traces separately
   unless engineering explicitly promotes and repairs them. Do not drop red
   tests to obtain a green commit.
3. **Release-documentation checkpoint:** version reviewed status/tasks and
   sanitized 035.1–3J decisions/manifest links. Review old release reports
   and binary/legacy material individually; do not put private PDF/DB/runtime
   manifests in Git merely because a document links to them.
4. **Access-controlled historical evidence:** retain immutable H5.2 V2
   98/98 broad result and original API image identity; keep the frozen 035.3B
   source/image/permission-safety failure distinct; preserve 035.3H dialog
   source/test/evidence hash, 035.3I snapshot, experiment outputs and local
   Redis/restore material with access controls. Link each prospective commit
   by manifest SHA-256, exact source hashes and image IDs, not a mutable tag.
5. **Future RC source freeze (not now):** only after generic answer-safety
   correction, Gitlink/privacy decisions, Python dependency lock and
   same-source API/worker/frontend build provenance. Run full reviewed-source
   lint/format, unit/integration and safety gates, then broad applicable V2
   acceptance, accessibility/live/security/recovery checks on that exact
   candidate. An RC tag/version requires separate release-owner approval
   after qualification; none is proposed as already approved.

Keep `.env` secrets, UAT source PDFs, database/Redis data, logs with personal
content, model caches and generated builds outside ordinary Git. Store
per-file manifests, nonsecret verification reports, dependency locks, image
digests/SBOM and model provenance in appropriately governed source or
artifact locations. The local 495-file archive is not off-host backup and
does not prove independent image/model reproducibility.

**Readiness:** source selection is READY_FOR_REVIEW; versioning approval is
**NO** until Gitlink/legacy, research-harness, privacy and exact-staged-diff
decisions. RAG safety OPEN/FAIL; active API/worker skew UNRESOLVED;
TASK-035 IN PROGRESS; RC NO-GO; approved deferrals zero.
