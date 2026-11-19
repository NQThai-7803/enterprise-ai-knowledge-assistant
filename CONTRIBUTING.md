# Contributing

## Before coding

1. Read `CODEX_START_HERE.md`.
2. Read the current task in `TASKS.md`.
3. Check `PROJECT_STATUS.md`.
4. Create a focused branch.

## Pull request requirements

- Clear description.
- Linked task.
- Test evidence.
- Migration note if schema changed.
- Security note if auth, permissions or files changed.
- Documentation updated.

## CI and verification (owner rule, 2026-11-19)

- Before reporting a change as verified, and before any merge, run `gh pr checks <PR>` on the PR's
  latest head and write its state in the report.
  - A green `eaka-verify` with a red CI is **red**.
  - CI installs from `pyproject.toml`, while the image installs from `requirements.lock`, so the two
    can disagree (PR #44: PyMuPDF 2.1 on CI, 1.28.2 in the image).
- After each `eaka-verify` run, keep only the `eaka-backend:verify-<sha>` image of the newest head.
  Remove the older verify images; never remove volumes, Ollama models or the protected stacks.

## Prohibited

- Commit `.env`.
- Commit generated uploads.
- Disable tests to make CI pass.
- Bypass permission checks.
- Add provider-specific code directly to business services without abstraction.
