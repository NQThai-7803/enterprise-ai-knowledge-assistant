param(
    [string]$PackageDir = ".backups/uat-corpus-v2/20260930-010258"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "../..")).Path
$target = (Resolve-Path -LiteralPath (Join-Path $projectRoot $PackageDir)).Path

$copies = @(
    @{source="uat/corpus-v2/manifest.json"; target="manifest.json"},
    @{source="uat/corpus-v2/README.md"; target="README.md"},
    @{source="compose.uat-corpus-v2-restore-check.yaml"; target="compose.uat-corpus-v2-restore-check.yaml"},
    @{source="scripts/uat/smoke_corpus_v2.ps1"; target="smoke_corpus_v2.ps1"},
    @{source="artifacts/uat-corpus-v2/restore-check-structural-validation.json"; target="restore-check-structural-validation.json"},
    @{source="artifacts/uat-corpus-v2/restore-check-semantic-smoke.json"; target="restore-check-semantic-smoke.json"}
)
foreach ($copy in $copies) {
    Copy-Item -LiteralPath (Join-Path $projectRoot $copy.source) `
        -Destination (Join-Path $target $copy.target) -Force
}

$restore = @"
# UAT Corpus v2 restore

Restore only into a new isolated Compose project and new volumes.

1. Start PostgreSQL for the target project on unused host ports.
2. Copy the dump into PostgreSQL and run pg_restore with --no-owner --no-privileges.
3. Extract the uploads archive into the target project's new uploads volume.
4. Start API/worker/Redis with compose.uat-corpus-v2-restore-check.yaml.
5. Verify migration 20260822_0011, 3 UAT users, 9 READY documents, 143 chunks,
   384-dimensional embeddings, source/upload hashes, ownership, visibility, and grants.
6. Run smoke_corpus_v2.ps1 against the restored API and require 6/6 PASS.
7. Supply UAT passwords separately; this package contains no secrets.
"@
Set-Content -LiteralPath (Join-Path $target "RESTORE.md") -Value $restore -Encoding utf8

$checksumPath = Join-Path $target "SHA256SUMS.json"
$checksums = Get-ChildItem -LiteralPath $target -File |
    Where-Object Name -ne "SHA256SUMS.json" |
    ForEach-Object {
        [ordered]@{
            file=$_.Name
            sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
$checksums | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $checksumPath -Encoding utf8

foreach ($checksum in (Get-Content -LiteralPath $checksumPath -Raw | ConvertFrom-Json)) {
    $actual = (Get-FileHash -LiteralPath (Join-Path $target $checksum.file) -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $checksum.sha256) { throw "Package checksum mismatch: $($checksum.file)" }
}
Write-Output $target
