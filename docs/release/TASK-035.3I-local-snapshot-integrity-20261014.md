# TASK-035.3I — local snapshot integrity and bounded checks

Verified archive:
`artifacts/task-035-3i-20261014-a6b8f7f7/reviewed-source.tar`, SHA-256
`a1a27f60efb1e8b3485343dcea3771985015de0fbda093ebb0fce59b5a26c518`.
Unique source copy and separate extraction are alongside it. Copy-time
source/destination hashes matched for 495 files; after archive creation, all
495 extracted files matched the manifest and extracted file count matched.
A subsequent 495-file source rehash found zero drift in the originals.
Post-verification tools generated caches/`.pyc` in staging/extraction **after**
the archive; they are not among the 495 manifest entries or tar contents.
An earlier unique local directory ending `bf3152c6` is an **incomplete,
unverified attempt**, preserved without deletion after encountering a
tracked Gitlink. Only `a6b8f7f7` is the verified archive.

| Check | Result and limit |
| --- | --- |
| Full original Ruff lint / format | **FAIL**: 24 findings in three scratch traces / three unformatted files (two traces, 2F eval harness). |
| Extracted candidate-source Ruff lint / format | **PASS**: all checks; 394 Python files formatted. This is filtered-source evidence, not full-repo cleanliness. |
| Extracted Python compile | **PASS** for `app`, `tests`, `.github/scripts` under host Python 3.11; candidate requires Python >=3.12. |
| Extracted non-mutating units | **49 PASS** in context-builder and retrieval-subclaims modules with plugin autoload disabled. A broader two-module attempt produced no output for ~90 seconds and was interrupted; **not** a pass or a diagnosed test failure. No active V2 DB was targeted. |
| Frontend current-source typecheck / ESLint | **PASS** / **PASS with seven existing warnings**. Source hashes matched the archived copy. |
| Frontend Vitest | First sandbox attempt failed before collection (`EPERM` temp rename); authorized local rerun **40/40 PASS**. |
| Mocked Chromium | **15/15 PASS**; local Vite mock only, no V2 backend. |
| Isolated frontend build | **PASS** in this checkpoint's ignored artifact directory; 1,978 modules, JS 412.49 kB, CSS 23.83 kB, source map 1,618.90 kB. Built from matching current frontend source, not a clean-room extraction install. |
| Dependency/config consistency | Host `pip check` **PASS** on Python 3.11; `npm ls --depth=0` **PASS** on installed local tree. Python ranges are not a resolved lock, and neither result is a vulnerability audit. |
| Offline source security check | Custom `.github/scripts/security_scan.py` **PASS** on staged copy; narrow scan only. No private-key/AWS/GitHub/OpenAI token marker hit in scanned app/frontend/tests/CI/deploy/templates. Manifest includes only three intentional example `.env` files; the secret/password entries inspected there are empty or explicit example/local placeholders, and production-example Redis URLs have no embedded userinfo. No PDF/dump/model/executable/cache is in the tar. Manual/private-data and comprehensive secret review remain open. |

The archive is a **local source-preservation success** only. It does not
verify an independently repeatable backend/frontend image, exact dependency
resolution, model bytes, current safety behavior, or off-host recovery.
