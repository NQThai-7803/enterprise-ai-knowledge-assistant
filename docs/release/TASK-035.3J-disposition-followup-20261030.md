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
