# UAT Corpus v2

UAT Corpus v2 is the reproducible acceptance baseline that replaces the unrecoverable
September runtime. It contains nine permanent documents listed in `manifest.json`.
Temporary upload/delete/grant/revoke documents are deliberately excluded.

Start the isolated environment:

```powershell
docker compose -p enterprise-ai-uat-v2 -f compose.yaml -f compose.uat-corpus-v2.yaml up -d --build
```

Bootstrap the corpus through the normal upload API:

```powershell
./scripts/uat/bootstrap_corpus_v2.ps1
```

The bootstrap verifies source hashes, uploads only missing manifest documents, waits
for READY, creates required grants, and writes `artifacts/uat-corpus-v2/runtime-manifest.json`.
Passwords are read from environment variables and are never written to the manifest.

After validation, create the recovery package using
`./scripts/uat/backup_corpus_v2.ps1`. Restore into a new isolated project by starting
its PostgreSQL service, restoring the dump with `pg_restore --no-owner --no-privileges`,
and extracting the upload archive into that project's new uploads volume. Start the
restored API with `compose.uat-corpus-v2-restore-check.yaml`, using unique host ports.
Never restore over a populated runtime without explicit review.

Q018 remains an intentional authority conflict between ND-HR-002 and ND-HR-003.
Neither schedule is designated as superseding the other.
