# TASK-035.1 accepted-V2 baseline manifest

Manifest version: 1.0. Observation date: 2026-10-13 (Asia/Saigon). Scope: the isolated UAT Corpus v2 RAG-H5.2 candidate, **not** a production release candidate. This document records read-only observations made before adding TASK-035.1 documentation. SHA-256 values identify bytes; they do not establish that an image can be rebuilt or that a local artifact is backed up off-host.

## Source and runtime identity

| Component | Verified identity or observation | Qualification |
| --- | --- | --- |
| Git | Branch `main`; HEAD `04ebd73aae737414fb591fe2e8b2c286134cdcd8`; no staged changes. | HEAD alone excludes the accepted H5.2 changes. |
| Working tree | 22 modified tracked files and 15 individually untracked files (37 file paths); `git diff --stat`: 13,586 insertions, 566 deletions. The earlier “34 paths” grouped untracked directories. | File-byte inventory below is a pre-TASK-035.1-documentation snapshot. Do not reset/clean/checkout. |
| API | Container `9d510d8b8027c248cf83954d8f03bc6a696a96c3c4e5c20260d0e3e0bb3f34fd`; image `sha256:1f057785bd8cacb68aa8573e3aa12e29a23c37692e0ad045997770d4adf2648e`; healthy, restart 0, OOM false. | Exact final API image named in the H5.2 qualification report. All 216 `/app/app/**/*.py` files matched the working-tree counterparts byte-for-byte by SHA-256 at this observation. This does not cover every OS package or external model. |
| Worker | Container `2afc4af27fe5d25dc2929868d210cc6ef650c5a08e2fb1e6a06b4107ace5593e`; image `sha256:1e19725cdd8929d30311fd5dbf4605fe7279d22d3a4fe7823046e44ce13aa570`; healthy, restart 0, OOM false. | Older image, different from API. See skew assessment below. Image-ID recording is not an image export. |
| PostgreSQL | Active isolated project `enterprise-ai-uat-v2`: 9 documents, all `READY`; 143 chunks; 3 users; Alembic `20260822_0011`. | Read-only count/status and version queries. Not a full database byte comparison. |
| Redis | Active `/data` volume `enterprise-ai-uat-v2_redis_recovered_cutover_20261010`; recovery report says completed. Original, recovery, snapshot, diagnostic and isolated-test Redis volumes remain listed. | Historical Celery task accounting remains **UNKNOWN**. No task replay or Redis repair performed here. |
| Corpus | `uat/corpus-v2/manifest.json`, SHA-256 `a0c71bbcabc2df18af250c304fb5c0293e876ede9dc5d7fe44e13436f58dcd07`; runtime manifest SHA-256 `925d3f73bc6b5a8ff826a86064e0da476c5d72cc99d8fb490ee6a2e40483a683`. | Nine source PDFs were present and matched the manifest hashes below. Runtime document IDs, owner, visibility and grant details are in the ignored runtime manifest. |
| Model and configuration | Both containers report `LLM_PROVIDER=ollama`, `LLM_OLLAMA_MODEL=qwen2.5:3b`, enabled, context 8192, temperature 0, output cap 512, timeout 180 s; `intfloat/multilingual-e5-small`, 384 dimensions, chunk 500/75, Celery worker concurrency 1. | Non-secret allowlisted environment values. External Ollama model binary/digest and embedding-model revision/cache bytes were not independently frozen here. API `APP_DEBUG=false`; worker `APP_DEBUG=true`; both are UAT `APP_ENV=development`. |
| Build inputs | `Dockerfile` `eb0a5aeaaa350a4e93962b7407270477a9ae9f6f91ad3ffbe4419b1e341b56f7`; `compose.yaml` `b3fe02d118bb2e63f71bf5a06efc7245def34c38041e3b464f1f815f7384867c`; `compose.prod.yaml` `7f3eebadcfd743c986db8696ff56ddd0c24dfa1d8e77eeb538f85c61e079bc06`; `pyproject.toml` `989e79086047000b2b2864dcae747beca7e94f70fcb97e887abff39195065845`. | Dockerfile resolves version ranges with `pip install`; no backend dependency lockfile was found. `.env` and credential values are deliberately absent. |

## Dirty-source file inventory

Each row is `Git status | repository-relative path | SHA-256`. `M` means tracked modification; `??` means untracked. Nothing was staged or committed. Do not assume every untracked diagnostic file belongs in a future source commit.

```text
 M |CHANGELOG.md|cba236018dac2686eac172bd84a306f7383a377e436ee0482d32cb129352bcd1
 M |PROJECT_STATUS.md|ed39cfd39187d70484ef4dbc7eab355bded8ae4558ea6e243f111d0d79621385
 M |TASKS.md|6134e9e6e5d0d801a10d53b8605a28b9315aa7852e15a93bb48433b3bee339e2
 M |app/chat/context_builder.py|26b2daafcc7da2448ba8933e6702e12cd58d880edb92b054edefb7dfe8884ab8
 M |app/chat/prompt_builder.py|3e657e1e1ba08996eee123bc9d613c29f76d297ac8353f1ae33fd22c31aca69c
 M |app/citations/evidence.py|f46189b9b3f09d8bb2f87efa5fef1518aa1de2a522763c9dda01476d41e59bdf
 M |app/retrieval/question_analysis.py|ed8cdd729b7e2c1285d14e33056193c13fbd550d425b7237744a973681c40c8e
 M |app/retrieval/reranker.py|4fa1e470dfa097f3b881f9dfdaef3fb7771cd4953bfe99031c8b77dd882da8d0
 M |app/retrieval/structured.py|c2b5954d5cb95b93f5ed99227742fbd563d5236adae3746a703d4fe4cd366c9e
 M |app/retrieval/subclaims.py|a92aea0ad59d82c2a966ec9175bcead25feae2e0260668957c70c9550825bbfa
 M |app/scripts/seed_uat_data.py|bd33c7ceff1e6c898e32e885b547588439bc0d86703f1fa2964941449ed4f307
 M |app/services/claim_evidence_validation_service.py|d7e11c25b42d710b1a2ba4d325244adecb371c723dda9b3148b27bdc4f65b6e1
 M |app/services/document_service.py|aa2022d330df316d2fbc8e065fc1267a0dc89eec854a5ad37bdba58f70184206
 M |app/services/grounded_answer_service.py|4c9d4c648bbcef30a35c4e2ca01fad0093ed0e7a8aebb777dc78b478b345c919
 M |tests/acceptance/task_034_1_2_runtime_acceptance.py|55f0e294b8353f8b43f4765b6f59a1b9f3a46e9e4a971c24757d248e4e36693e
 M |tests/unit/test_chat_context_builder.py|a2fb97caf8685f388788e3f4ff5731922387a30eff3c3aae33e5cff9f69073d5
 M |tests/unit/test_citation_mapping.py|0b0e11faf20ab4422eb1365e43db9dde5c5db62542d6fff813271b07eacb3e65
 M |tests/unit/test_document_upload_enqueue.py|942cbee83996a3aafca0d392eb0d0dabf701c18e8f5813d12773853007caf700
 M |tests/unit/test_grounded_answer_service.py|0fd5de5c6c2a39e5daeb9655272522d71ef015647b0fd29387d4687e72abe059
 M |tests/unit/test_grounded_prompt_builder.py|443becfa0ae8fe5a5802846e8c82a703fd7c7ebe2283173057b3a7a248074a48
 M |tests/unit/test_rag_accuracy_components.py|06adf1e39b8cfd94f3239cf97c3be4beae499e22cbe8f8fc9ab65651b7b1d9c2
 M |tests/unit/test_retrieval_subclaims.py|d7f23e67bbc67e8ce0b73216f06c88b1693f03c1843c2007e3720c9c06b5bbd0
?? |.cache/huggingface/.agent_harnesses.json|2697b4b40d91f00ea0328ccaf0442d531d94d6f5228f306eccc1f88e6d24eda3
?? |app/retrieval/leave_relations.py|70083a0ab93e7bbd93400789880a2d57e301b4eec8a599e656375bb4df95b9ba
?? |compose.uat-corpus-v2-redis-cutover.yaml|0f4693a223350a4450fcfb3a7cc3498ff5cba1e48eeb91b2e51731c11f5d5980
?? |compose.uat-corpus-v2-redis-recovery.yaml|8cb1a440fb783332baa3cf96632a789972a7dd48390c335502c2e24fe1d148af
?? |compose.uat-corpus-v2-restore-check.yaml|752eb7ba1e819378fc9a37d11397b3d11bf6676261abf4b512e7ea82d1f690cf
?? |compose.uat-corpus-v2.yaml|932a45bb7223eb0d7e5455fefc1f6350a0036ca3aa5e3a49c526a961df634968
?? |scripts/uat/backup_corpus_v2.ps1|606da2eab6ccf6ce0d7d2634b3218c8a0d3e4a11fa89ed2110875afacd2b59d8
?? |scripts/uat/bootstrap_corpus_v2.ps1|183f395ac2a5f99a0ff6030866876745d25d9375fc02e8d265487c684023689c
?? |scripts/uat/finalize_corpus_v2_package.ps1|da9deec43fc561df5c168bc6159658e4de8c609ec8a58c515212e85e5c0f4fd6
?? |scripts/uat/smoke_corpus_v2.ps1|417f42609ff8adaa923fe6bbb20d3425e1b58e59d57993d07658d73fdd5750fe
?? |tests/acceptance/rag_h5_2_exact_100.py|c17991787e0bc6141432a6178542e889c0973f14cce0fef5cfee59e78ceaf958
?? |tmp_org_retrieval_trace.py|f6e85d64598c33cd070ea119991de887078e4a1b34dd1bfcaa821d98fbef01c7
?? |tmp_q085_retrieval_trace.py|f12f282a51b814e3eccfccb1403f383a4a5e3c2bb2c58be13a795a6c28ab09b2
?? |tmp_runtime_benefit_trace.py|ac416bea1889e44a08a019985417d65904891b858b2a33ffe503f07979130462
?? |uat/corpus-v2/README.md|4c1f2714447b055c90e31d104d713bfe93ff4e3a371db9b6da5f074961aa5bee
?? |uat/corpus-v2/manifest.json|a0c71bbcabc2df18af250c304fb5c0293e876ede9dc5d7fe44e13436f58dcd07
```

## Source-document manifest verification

The nine locally present source PDFs matched the SHA-256 values in `uat/corpus-v2/manifest.json` during this checkpoint. These are isolated UAT corpus sources, including recovered policy documents; this list is not permission to put their bytes into Git or a public artifact store.

| Code | Source SHA-256 | Visibility |
| --- | --- | --- |
| ND-CORP-001 | `593156f8b218e95ff5519000e95b8391b3338e9d4ee4e4742ae1bc327b9f7962` | ORGANIZATION |
| ND-HR-002 | `3d92ef98c6e1dfd2723cea1f3740404f7d707ba27033b43a17101c9de6d5942a` | ORGANIZATION |
| ND-HR-003 | `75b949e101288bfae6d11b70abeb42a212807666f48b82824ecf9e59d64d8652` | ORGANIZATION |
| ND-HR-004 | `efcc573cf4aded7fcce81953a50727ef8aaeaa812e82069d31f62fc612440413` | ORGANIZATION |
| ND-HR-005 | `e243fed816c48f66b400c1cf50f81ab701ecb68600af535bb398729d53a1198c` | ORGANIZATION |
| ND-HR-006 | `75aedd6f49fee99f585d7ecad2d5f5968a8883b646840453c10bdbbe552f8874` | ORGANIZATION |
| UAT-LEAVE-AUTHORITY-001 | `24178db420422e474326986672b6c15cc67373ee6adbe1489ba5e8addf95f4f4` | ORGANIZATION |
| UAT-GROUNDING-001 | `43a4d9f1661b38f0e3245afd824849ba33d9fe87aa063873c11fdc01b3601040` | PRIVATE; manager VIEW grant |
| UAT-SHARED-001 | `d6a93cb8db7620166ce9764a289ad83598c2fc3d657c8ef51f1adbf8b492080b` | ORGANIZATION |

## Acceptance and recovery evidence inventory

`artifacts/uat-corpus-v2/` is Git-ignored and currently has 109 files, including historical failing/intermediate captures. The following are the **superseding final/current evidence**, not every historical capture. SHA-256 is of the local file at this checkpoint.

| Evidence | SHA-256 | Recorded result/limit |
| --- | --- | --- |
| `h5-2-qualification-20261013.md` | `4ebd7d1eef42d8154aebf440e4ad469f32a01d1d580821bedaa2a3a9fdb36e0a` | V2 H5.2 decision and limits. |
| `h5-2-broad-v2-final-20261013.json` | `7fc3d5cb171aa09f17cfdf3b66e15def4b3332eec80dfdba95e32121836b5698` | 100/100 transport, 98/98 supported material answers per separate manual review; Q018/Q100 abstain. |
| `h5-2-supported-failure-ledger-20261013.md` | `144cfd9d4dc86a5d8d7d544ee1fa66aebe450fe6f3b24612e50ddd15e513be6a` | Case adjudication. |
| `h5-2-negation-targeted-20261013.json` | `e419c60f44de72ee5c07fc72ced0179f7580926c83745a2d795da68713cf6699` | Final targeted capture. |
| `h5-2-final-image-safety-smoke-20261013.json` | `7ac776d8dcab58943ac968878f6a00220deb77bbdf567170702bc79359550487` | 6/6. |
| `h5-2-final-image-repeat-20261013.json` | `d18210dd71ba5cbbccd41cfa1e911c3339c6f3170eea0c2be382c3e8e5dda8a7` | 9/9. |
| `h5-2-final-image-independent-restore-smoke-20261013.json` | `6cf538faf808d8d29c385a905e184d7f0f675e00a3cc687fb50cde93bbc8f7c7` | 6/6 on prior separate restored corpus; not a fresh dump restore on 2026-10-13. |
| `runtime-manifest.json` | `925d3f73bc6b5a8ff826a86064e0da476c5d72cc99d8fb490ee6a2e40483a683` | Actual document IDs, owners, scopes, grants and SHA-256. |
| `redis-recovery-20261010/postreboot-cutover-integrity-20261011.md` | `1a5fc220c7521d4f2a1623c7ecdd0eba5a3acf63797ddaa80c66566a25ebd62b` | Infrastructure recovery complete; historical Celery unknown. Its older RAG/TASK-035 status statements are superseded. |
| `.backups/uat-corpus-v2/20260930-010258/SHA256SUMS.json` | `529933812d61ccbf27e46f01da8329e0979a680a58359ba9fbcc7fbe3be5069e` | Local 13-file recovery-package inventory. Previous qualification verified package checksums and separate structural restore; no off-host copy is proven. |

The qualification report also records 101/101 persisted citation identities, 467 focused unit tests, Ruff/compile checks, broad p95 23.75 s without a repo-defined ceiling, and the independent restore-check API stop anomaly. Those are report claims linked to the frozen API image, **not** a TASK-035 release sign-off.

## API/worker skew assessment

SHA-256 comparison of all 216 Python application files found **zero host–API differences** and **eight host/API–worker differences**. The eight differing files are `app/chat/context_builder.py`, `app/citations/evidence.py`, `app/retrieval/leave_relations.py`, `app/retrieval/question_analysis.py`, `app/retrieval/reranker.py`, `app/retrieval/structured.py`, `app/services/claim_evidence_validation_service.py`, and `app/services/grounded_answer_service.py`. The last file is `4c9d4c648bbcef30a35c4e2ca01fad0093ed0e7a8aebb777dc78b478b345c919` in host/API and `7ad6dc69fa39a55b13dd3ed0141feed8e67d12a592d8148420f4bcf01ad04548` in worker.

`app/workers/document_tasks.py`, `app/workers/celery_app.py`, `app/services/document_processing_pipeline.py`, and `app/services/document_service.py` are identical among host/API/worker within the 216-file comparison. The Celery include/route invokes `documents.process_document` through the document pipeline; direct imports from that path do not reference the eight differing RAG/chat/citation files. Thus no **direct source-path** ingestion or task-contract difference was found. This does **not** prove full transitive/runtime equivalence or future task behavior.

Both containers' `/app/README.md`, `/app/alembic.ini`, and `/app/pyproject.toml` hashes match each other and the working tree. However, `pip freeze` returned 92 packages per container with **22 package-version differences** (including FastAPI, SQLAlchemy, asyncpg, pgvector, NumPy, transformers, tokenizers, amqp and billiard). UAT runtime environment differed at `APP_DEBUG` and API-only rate-limit overrides; model, embedding, chunk and Celery concurrency values listed above matched. The source comparison plus package skew means **API/WORKER SKEW IS AN RC BLOCKER pending a separately approved same-candidate image/runtime reconciliation or explicit release-authority decision**. No service was rebuilt or recreated.

## Protection and reproducibility plan — not executed

1. Preserve the dirty tree and all ignored evidence in place. Review each untracked file before any future commit; exclude cache/temporary traces unless they are deliberately selected and secret-scanned. Never use `git clean`, reset, or checkout to “prepare” this baseline.
2. With separate approval, create a reviewable source commit from selected H5.2 source/tests/config/manifests **after** secret/sensitive-data checks, then attach an immutable release-candidate tag only after all TASK-035 gates and authorized sign-off. Neither action occurred here.
3. With separate approval, make an access-controlled, encrypted, **off-host** evidence/recovery copy of the ignored final captures, nine source PDFs, corpus/runtime manifests, Redis recovery report, and existing local PostgreSQL/uploads/source package. Verify transfer checksums and an independent restore. Hash lists alone and the existing local package are not off-host DR.
4. Preserve/pin the exact API and worker OCI images or an authorized reproducible build recipe plus resolved dependency lock/SBOM. Record image digests, model binary/revision, non-secret config, migration and corpus identities together. Do not rely on mutable `latest` or a container ID as a distribution artifact.

**Missing reproducibility material:** committed H5.2 changes; a reviewed selection of untracked scripts/config/runner; durable off-host final evidence and backup; exported/pinned API and worker images; backend resolved dependency lock/SBOM; independently frozen Ollama and embedding-model bytes; resolution of API/worker version skew; and an authorized RC acceptance/deferral decision. Some local source and recovery checks are verified, but end-to-end reproducibility and production readiness are **not** established.
