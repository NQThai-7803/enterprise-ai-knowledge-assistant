# TASK-035.3J disposition follow-up: root tmp trace scripts — 2026-10-30

This record follows up the dispositions in `TASK-035.3G-source-hygiene-inventory-20261014.md`,
`TASK-035.3I-source-hygiene-matrix-20261014.md` and
`TASK-035.3J-scratch-experimental-disposition-20261014.md`, which asked to preserve these scripts
as experiment evidence and archive them separately. Those documents are left unchanged.

## Decision

The owner approved option 1: archive the three root-level diagnostic scripts outside the
repository, then remove them from the working tree with `git rm`. They are one-off retrieval and
runtime traces against a live database. No application code, test, CI workflow, compose file or
Dockerfile imports or runs them. Removing them also clears the 24 Ruff findings that kept Backend
CI failing at the Lint step.

## Files

| File | SHA-256 | Content |
|---|---|---|
| `tmp_org_retrieval_trace.py` | `f6e85d64598c33cd070ea119991de887078e4a1b34dd1bfcaa821d98fbef01c7` | Traces each retrieval filter stage for two organization questions against fixed target chunk UUIDs |
| `tmp_q085_retrieval_trace.py` | `f12f282a51b814e3eccfccb1403f383a4a5e3c2bb2c58be13a795a6c28ab09b2` | Traces hybrid, keyword and prompt ranking for one ergonomic-allowance question |
| `tmp_runtime_benefit_trace.py` | `ac416bea1889e44a08a019985417d65904891b858b2a33ffe503f07979130462` | Replays prompt building, claim validation and structured repair for five benefit questions |

All three hashes match `TASK-035.1-baseline-manifest-20261013.md` lines 57-59, so the files were
unchanged since that baseline.

## Privacy scan

A regex scan of the three files found:

- 0 email addresses
- 0 password, secret, token, API key, private key, bearer or credential terms
- 0 connection strings (`postgresql://`, `redis://`, and similar). The database URL comes from
  the `TRACE_DATABASE_URL` environment variable or from application settings.
- 0 IPv4 or IPv6 addresses
- 0 personal names. The only capitalized multi-word phrase is "Nova Digital", the fictional
  company in the synthetic UAT corpus.

The files do contain synthetic UAT questions and chunk/document UUIDs from the local UAT corpus.

## Archive location

`C:\Users\_ASUS_\eaka-backups\tmp-traces-20261030\` holds the three files and a `SHA256SUMS`
file. `sha256sum -c SHA256SUMS` passed for the backup copies, and the copies also match the
TASK-035.1 manifest hashes. This archive lives on the same machine; an off-host copy has not
been made.

## Restore from Git

The last commit that still contains the files is `bd56fed5af41fb71288c9ffb46e123a06bff4845`,
the parent of the removal commit `chore: archive tmp trace scripts outside repo`.

```powershell
git show bd56fed:tmp_org_retrieval_trace.py > tmp_org_retrieval_trace.py
git show bd56fed:tmp_q085_retrieval_trace.py > tmp_q085_retrieval_trace.py
git show bd56fed:tmp_runtime_benefit_trace.py > tmp_runtime_benefit_trace.py
```

`git show <removal-commit>^:<file>` restores the same content.

## `vite-monorepo` Gitlink

### Decision

The owner approved removing the `vite-monorepo` Gitlink from the parent index with
`git rm --cached vite-monorepo` and adding `/vite-monorepo/` to `.gitignore`. The local nested
checkout, including its own `.git`, is kept unchanged on disk. This closes the open
decision in `TASK-035.3K-gitlink-decision-report-20261014.md`, which stays as it was.

### Reason

- No reachable URL exists for the nested commit. The parent has no `.gitmodules`, the nested
  repository has no remote, and the parent object store does not contain the commit
  (TASK-035.3J gitlink reproducibility report and TASK-035.3K). A fresh clone could never
  populate it.
- `actions/checkout` v7, used by Frontend CI, treats the unmapped Gitlink as fatal:
  `fatal: No url found for submodule path 'vite-monorepo' in .gitmodules` (run 41027432316).
  Backend CI (`actions/checkout@v4`) only logged `git failed with exit code 128`.
- No dependency on it was found: no reference in `frontend/package.json`,
  `frontend/package-lock.json`, `frontend/tsconfig*` or `frontend/vite.config.*`, and no Docker,
  compose or CI use. `.dockerignore` already excluded it. The TASK-035.3I/J release scripts only
  label the path while listing inventory and do not require it.

### Record

| Item | Value |
|---|---|
| Gitlink entry | `160000 commit 3becadbd1d46a68a61a173731a3c7b946fec024f vite-monorepo` |
| Last commit with the Gitlink | `833b2526674c07414ff1fc1fc13b7e909c098dcd` |
| Local copy | `vite-monorepo/` (nested repository, local only, not backed up off-host) |

To restore the Gitlink entry at the same commit:

```powershell
git update-index --add --cacheinfo 160000,3becadbd1d46a68a61a173731a3c7b946fec024f,vite-monorepo
```

Restoring it brings back the CI checkout failure until a reachable `.gitmodules` URL exists.
