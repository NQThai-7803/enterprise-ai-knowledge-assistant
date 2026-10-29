# TASK-035.3I — working-tree source inventory

Observed 2026-10-14 on `main`, HEAD
`04ebd73aae737414fb591fe2e8b2c286134cdcd8`. Root `AGENTS.md` and
root `DESIGN.md` are absent; `frontend/DESIGN.md` exists. The full per-path
working-tree inventory, including Git state, classification, byte count,
SHA-256 and snapshot decision, is
`artifacts/task-035-3i-20261014-a6b8f7f7/working-tree-inventory.json`
(SHA-256 `c12678dc7c7387f235ee35a87d7a6a549e8bf6360752f89170f4b0fc83322ea2`).
It records 586 tracked index entries (one is the `vite-monorepo` Gitlink),
68 untracked files, 495 source-copy inclusions and 159 exclusions. No path
was deleted, moved, staged or committed. A first, incomplete local snapshot
directory `artifacts/task-035-3i-20261014-bf3152c6/` was left intact after
the inventory discovered the Gitlink is a directory, not a regular file;
it is **not** a verified archive.

The 68-file untracked count is the **pre-report source freeze**; six new
035.3I report files were written afterward, making the final untracked-file
count 74. Those reports are checkpoint outputs, not unrecorded application
inputs. A final rehash found zero drift among all 495 included originals.

| Inventory class | Current disposition |
| --- | --- |
| Production backend source | `app/` (216 tracked Python modules plus untracked `app/retrieval/leave_relations.py`), all copied; modified tracked H5.2 modules are not in HEAD alone. |
| Production frontend source | `frontend/src/`, `server.mjs`, build configuration and untracked corrected-dialog test; copied. Generated `.js`, `.d.ts` and `*.tsbuildinfo` were not copied. |
| Production tests | Maintained `tests/unit/` and frontend component tests copied; known red safety contracts are retained, not erased to manufacture a pass. |
| Release qualification tests | Acceptance runners, mocked/live frontend test source, CI and release scripts reviewed for source inclusion. Historical runtime captures stay separate. |
| Experimental research harness | 035.3C.2E/2F evaluation scripts and 2F unit harness are retained in place but excluded from this proposed candidate source copy pending owner decision; their evidence remains available. |
| Diagnostic/scratch | Three root `tmp_*_trace.py` files and `.cache/huggingface/.agent_harnesses.json` remain in place; they are not candidate modules. |
| Authoritative project documentation | Tracked contracts and `PROJECT_STATUS.md`, `TASKS.md`, `CHANGELOG.md` remain in place. They are not silently replaced by current HEAD or repackaged as application code. |
| Historical release evidence | Untracked `docs/release/`, UAT/recovery overlays and ignored `artifacts/` are preserved separately. The 035.3B safety capture and H5.2 final broad capture rehash unchanged. |
| Generated build/cache | `frontend/node_modules/` (19,809 files), `frontend/dist/`, `frontend/test-results/`, `.venv/`, Python caches and local build outputs remain local, excluded from the archive. |
| Sensitive/potentially sensitive | `.env`, `.env.task035.production`, private `uat/`, `data/` (including model weights), `.backups/` (dumps/source recovery) and local corpus/runtime manifests were excluded. No decision to publish them is implied. |
| Unknown/review | The tracked `vite-monorepo` Gitlink (`3becadbd1d46a68a61a173731a3c7b946fec024f`), root `tore package.json package-lock.json`, legacy `files-for-chat/` and `frontend-stitch-reference/` are preserved outside the candidate copy pending relevance/provenance review. |

Relevant ignored evidence: `artifacts/uat-corpus-v2/` 109 files;
`artifacts/task-035-3a-20261013/` 613 files including an old generated source
stage; `artifacts/task-035-3b-20261013/` 11 files;
`artifacts/task-035-3h-20261014/` four files;
`.backups/uat-corpus-v2/` 14 files; `data/` 21 files. Counts are local
observations, not completeness or off-host backup proof. The untracked
`docs/release/` tree and ignored captures are **not disposable**.

Key identity hashes: accepted/frozen shared backend
`app/services/grounded_answer_service.py`
`4c9d4c648bbcef30a35c4e2ca01fad0093ed0e7a8aebb777dc78b478b345c919`;
035.3H `frontend/src/components/ui/ConfirmDialog.tsx`
`1f0f1ef7dc8ae7d1decaed33aec3e2d8bdd9e72d88800e4570c9fc42e20991c7`;
frontend lock `1fdf9b6d438cedc1f4027a43195407bcc1f2363f4acac50862f3403c6aa195d5`;
035.3B permission failure `b6e0f415dee409be55786fb4788cf9888d06890e0cfe684444013a5a1196714f`;
historical H5.2 broad capture `7fc3d5cb171aa09f17cfdf3b66e15def4b3332eec80dfdba95e32121836b5698`.
