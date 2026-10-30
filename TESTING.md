# Running the tests

This page covers how to run the backend test suite. For test design and scope, see
`TESTING_STRATEGY.md`.

## Reference environment

The reference environment is the test image built from `requirements.lock`. Its packages match
the accepted dependency lock exactly. A host virtualenv installed with `pip install -e ".[dev]"`
resolves the latest versions instead, so its results are useful for development but are not the
reference.

## Unit suite in the test image

```powershell
docker build --target test -t eaka-backend:<tag> .
docker run --rm --network=none eaka-backend:<tag> python -m pytest -q
```

- `pyproject.toml` (`[tool.pytest.ini_options]`) is the pytest config inside the image too.
  The default `-m "not integration"` applies.
- The test stage copies `app/`, `tests/` and `scripts/` only. Tests marked `repo_layout` read
  repository infrastructure files (Dockerfile, `.dockerignore`, `.env.example`, compose files,
  `deploy/`, `frontend/tests/e2e-live/`). In the image these skip with the missing paths as the
  reason.
- Eval-harness tests also skip when their frozen manifest under the git-ignored `artifacts/`
  directory is absent.
- The expected result is exit code 0. To list every skip reason, add `-rs`.

## Unit suite on the host

```powershell
python -m pytest -q
python -m pytest -q -m repo_layout      # only the repository-layout checks
```

- In a repository checkout (a `.git` entry exists), every `repo_layout` test runs. If a file a
  test declares is missing, the test **fails** instead of skipping, so a broken layout is never
  hidden.
- Compose-based checks need the Docker Compose CLI on the host.

## Adding a repository-layout test

Mark the test with the paths it reads, relative to the repository root:

```python
@pytest.mark.repo_layout("compose.yaml", ".env.example")
def test_something_about_compose() -> None:
    ...
```

The hook in `tests/conftest.py` checks those paths before the test runs.

## Integration lanes

Integration tests need a real PostgreSQL with pgvector (and Redis for some lanes). Use a
throwaway database only. `tests/conftest.py` refuses production-looking URLs. The exact marker
combinations CI runs are in `.github/workflows/ci.yml`.
