# TASK-035.3K — source versioning approval package

**035.3K analysis complete; READY_FOR_VERSIONING_APPROVAL: NO.** This is an owner decision package, not Git staging approval or an RC. The exact prior proposed inclusion is [`TASK-035.3J-proposed-git-staging-manifest-20261014.json`](TASK-035.3J-proposed-git-staging-manifest-20261014.json), SHA-256 `0d814286beb193f791f8a6196938aa79c710fbc4330f41e758ee0a5bc9acefb6`: 290 source, 207 tests/tooling, 56 release docs, 103 review-required and 10 other dispositions = 666 listed paths. The JSON's own path is self-referenced without a recorded hash, so it is not a complete current Git-visible inventory; these 035.3K reports are also post-freeze. Do not silently alter the prior manifest/hash. A future exact-path refresh and review are required.

At entry, all 665 listed file hashes and the recorded Gitlink identity matched. After this checkpoint's authorized `TASKS.md` and `PROJECT_STATUS.md` updates, those two documentation hashes differ from the frozen 035.3J manifest by design; all production-source and historical-evidence identities remain unchanged. The new 035.3K reports likewise lie outside the prior inventory.

The [103-path appendix](TASK-035.3K-owner-review-path-appendix-20261014.json) and [grouped decision matrix](TASK-035.3K-owner-review-resolution-matrix-20261014.md) leave every owner path unresolved. The [Gitlink options](TASK-035.3K-gitlink-decision-report-20261014.md) remain unselected. The [isolated simulation](TASK-035.3K-isolated-staging-simulation-20261014.md) staged exactly 497 source/test files outside the parent, but its whitespace gate failed on eight paths; the original index was unchanged. Automated high-signal security/size/path checks found no matches among the 553 proposed inclusion paths, but manual privacy, rights, binary, exact-diff and comprehensive secret review have not been completed. The 56 release docs especially cannot be equated with cleared publication material.

## Future preservation boundaries (planning only)

1. **Backend/application source:** freeze reviewed `app/**`, migrations, generic backend Docker/dependency/deployment inputs and examples as one coherent identity, including the still-red safety implementation state. Do not label it accepted H5.2 or RC.
2. **Frontend application/accessibility:** freeze the matching frontend runtime/build inputs, ConfirmDialog correction and source map/origin decisions with dependency identity. Do not infer live accessibility from mocked tests.
3. **Tests/tooling:** include maintained backend/frontend tests, red safety contracts, CI and vetted release/backup tooling for the same source state. Preserve research harnesses separately until their owner decision; never hide failing tests to manufacture green quality.
4. **Release documentation:** review/sanitize status, task history and each of the 56 proposed reports, plus a refreshed inclusion manifest, before any documentation commit. Keep historical H5.2 acceptance, frozen 035.3B failure and later local checks explicitly separate.
5. **Evidence references/integrity:** version only approved nonsecret hashes/links/manifests; retain private corpus, DB/Redis recovery data, runtime logs, dumps, uploads, model caches and source PDFs in access-controlled artifact storage. Link immutable accepted and failed artifacts to exact source/image identities, not mutable tags.

No commit boundary above is authorized. An engineering preservation checkpoint would only record a reviewed source tree; it would **not** inherit the H5.2 98/98 accepted runtime result or cure the frozen 035.3B safety failure. A future RC freeze requires a new same-source API/worker/frontend build, lock/digest provenance, current safety and broad gates, operational/security/accessibility qualification, and release-owner approval.

## Approval prerequisites and stop conditions

- Owner decisions for all 103 review-required paths and Gitlink option A/B/C, including licensing/provenance; explicit treatment of already-tracked legacy content.
- Refreshed exact-path manifest including the 035.3J self-reference gap and post-freeze files; reviewed exact original-repository staged diff **only after separate staging authorization**.
- Resolve or explicitly adjudicate the eight-path staged whitespace failure and full-tree Ruff failures without changing lint exclusions or weakening red safety tests.
- Manual privacy and secrets review of all proposed source/docs and binaries; preserve private evidence outside Git. The bounded automated scan is not publication clearance.
- Verified local and off-host encrypted backup with transferred hashes and independent restore; current 495-file local tar is not off-host recovery proof.
- Reproducible source/dependency/image/model inputs, independent clean build/clone including chosen Gitlink arrangement, and same-source API/worker skew resolution. Neither off-host backup nor reproducible build was independently verified in 035.3K.
- Stop before any original Git staging/commit/tag/push, Gitlink edit, source deletion, release deferral or RC sign-off until separately authorized. If sensitive contents, unavailable upstream objects, or identity drift appears, preserve evidence and request owner direction.

Historical H5.2 supported-case acceptance remains 98/98 **for its isolated V2 baseline**; the frozen 035.3B candidate remains **FAILED**. RAG unsupported-answer safety B19/B21/R18 is **OPEN**, active API/worker skew **UNRESOLVED**, TASK-035 **IN PROGRESS**, RC **NO-GO**. No release deferral was approved.
