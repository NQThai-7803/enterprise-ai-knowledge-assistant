param(
    [string]$ProjectName = "enterprise-ai-uat-v2",
    [string]$BackupRoot = ".backups/uat-corpus-v2"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "../..")).Path
$backupBase = Join-Path $projectRoot $BackupRoot
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$packageDir = Join-Path $backupBase $timestamp
New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

$dumpName = "uat_corpus_v2_postgres_$timestamp.dump"
$containerDump = "/tmp/$dumpName"
docker compose -p $ProjectName -f compose.yaml -f compose.uat-corpus-v2.yaml exec -T postgres `
    pg_dump -U app_user -d enterprise_ai -Fc --no-owner --no-privileges -f $containerDump
docker compose -p $ProjectName -f compose.yaml -f compose.uat-corpus-v2.yaml cp `
    "postgres:$containerDump" (Join-Path $packageDir $dumpName)
docker compose -p $ProjectName -f compose.yaml -f compose.uat-corpus-v2.yaml exec -T postgres `
    pg_restore --list $containerDump | Out-Null
docker compose -p $ProjectName -f compose.yaml -f compose.uat-corpus-v2.yaml exec -T postgres rm -f $containerDump

$uploadsName = "uat_corpus_v2_uploads_$timestamp.tgz"
$uploadsVolume = "${ProjectName}_uploads_data"
docker run --rm -v "${uploadsVolume}:/data:ro" -v "${packageDir}:/backup" `
    redis:7-alpine sh -c "cd /data && tar czf /backup/$uploadsName ."
docker run --rm -v "${packageDir}:/backup:ro" redis:7-alpine `
    sh -c "tar tzf /backup/$uploadsName >/dev/null"

$sourceArchive = Join-Path $packageDir "uat_corpus_v2_sources_$timestamp.zip"
$manifest = Get-Content -LiteralPath (Join-Path $projectRoot "uat/corpus-v2/manifest.json") -Raw | ConvertFrom-Json
$sourceFiles = @($manifest.documents | ForEach-Object { Join-Path $projectRoot $_.source })
Compress-Archive -LiteralPath $sourceFiles -DestinationPath $sourceArchive
Copy-Item -LiteralPath (Join-Path $projectRoot "uat/corpus-v2/manifest.json") -Destination $packageDir
Copy-Item -LiteralPath (Join-Path $projectRoot "uat/corpus-v2/README.md") -Destination $packageDir
Copy-Item -LiteralPath (Join-Path $projectRoot "artifacts/uat-corpus-v2/runtime-manifest.json") -Destination $packageDir
Copy-Item -LiteralPath (Join-Path $projectRoot "compose.yaml") -Destination $packageDir
Copy-Item -LiteralPath (Join-Path $projectRoot "compose.uat-corpus-v2.yaml") -Destination $packageDir
Copy-Item -LiteralPath (Join-Path $projectRoot "compose.uat-corpus-v2-restore-check.yaml") -Destination $packageDir
Copy-Item -LiteralPath (Join-Path $projectRoot "scripts/uat/smoke_corpus_v2.ps1") -Destination $packageDir

$restore = @"
# UAT Corpus v2 restore

Restore only into a new isolated Compose project and new volumes.

1. Start PostgreSQL for the target project and run migrations.
2. Copy the dump into PostgreSQL and run pg_restore with --no-owner --no-privileges.
3. Extract the uploads archive into the target project's new uploads volume.
4. Start the target with unique ports using compose.uat-corpus-v2-restore-check.yaml.
5. Verify migration head 20260822_0011, manifest hashes, document READY state,
   384-dimensional embeddings, accounts, visibility, and grants before use.
6. Run smoke_corpus_v2.ps1 against the restored API.
7. Supply UAT passwords separately; no secrets are stored in this package.
"@
Set-Content -LiteralPath (Join-Path $packageDir "RESTORE.md") -Value $restore -Encoding utf8

$checksums = Get-ChildItem -LiteralPath $packageDir -File | ForEach-Object {
    [ordered]@{file=$_.Name; sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$checksums | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $packageDir "SHA256SUMS.json") -Encoding utf8
Write-Output $packageDir

