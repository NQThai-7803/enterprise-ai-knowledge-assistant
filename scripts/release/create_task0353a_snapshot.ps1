param(
    [string]$SnapshotName = 'task-035-3a-20261013'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$artifactRoot = Join-Path $repoRoot (Join-Path 'artifacts' $SnapshotName)
$stageRoot = Join-Path $artifactRoot 'candidate-source'
$archivePath = Join-Path $artifactRoot 'candidate-source.tar'
$manifestPath = Join-Path $artifactRoot 'source-manifest.json'

if ((Test-Path -LiteralPath $archivePath) -or (Test-Path -LiteralPath $manifestPath)) {
    throw "Completed candidate artifact target already exists: $artifactRoot"
}
if ((Test-Path -LiteralPath $artifactRoot) -and -not (Test-Path -LiteralPath $stageRoot)) {
    throw "Unexpected candidate artifact target exists: $artifactRoot"
}

$paths = [System.Collections.Generic.List[string]]::new()
$rootFiles = @(
    '.dockerignore', 'Dockerfile', 'alembic.ini', 'pyproject.toml', 'README.md',
    'compose.yaml', 'compose.prod.yaml', 'compose.uat-corpus-v2.yaml',
    '.github/workflows/ci.yml', '.github/scripts/security_scan.py',
    'scripts/release/Dockerfile.task0353a',
    'scripts/release/create_task0353a_snapshot.ps1'
)
foreach ($relative in $rootFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $relative))) {
        throw "Required snapshot input is missing: $relative"
    }
    $paths.Add($relative)
}

foreach ($tree in @('app', 'tests')) {
    $treePath = Join-Path $repoRoot $tree
    $sourceFiles = Get-ChildItem -LiteralPath $treePath -Recurse -File |
        Where-Object { $_.Extension -in @('.py', '.mako', '.json') }
    foreach ($file in $sourceFiles) {
        $relative = $file.FullName.Substring($repoRoot.Length + 1).Replace('\', '/')
        $paths.Add($relative)
    }
}

$uniquePaths = @($paths | Sort-Object -Unique)
foreach ($relative in $uniquePaths) {
    $source = Join-Path $repoRoot $relative
    $item = Get-Item -LiteralPath $source
    # OneDrive placeholder files carry ReparsePoint without being filesystem
    # links. Reject actual links, but allow checksum-verified local placeholders.
    if ($item.LinkType -or $item.Target) {
        throw "Refusing linked snapshot input: $relative"
    }
}

New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null
$records = [System.Collections.Generic.List[object]]::new()
foreach ($relative in $uniquePaths) {
    $source = Join-Path $repoRoot $relative
    $target = Join-Path $stageRoot $relative
    $parent = Split-Path -Parent $target
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()
    if ($relative -eq 'scripts/release/create_task0353a_snapshot.ps1') {
        # This provenance script may have been corrected after a failed,
        # incomplete first pass. It is not a protected source or prior archive.
        Copy-Item -LiteralPath $source -Destination $target -Force
    } elseif (-not (Test-Path -LiteralPath $target)) {
        Copy-Item -LiteralPath $source -Destination $target
    }
    $targetHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
    if ($sourceHash -ne $targetHash) {
        throw "Snapshot copy hash mismatch: $relative"
    }
    $records.Add([ordered]@{
        path = $relative.Replace('\', '/')
        bytes = (Get-Item -LiteralPath $target).Length
        sha256 = $targetHash
    })
}

$freeze = @(docker exec enterprise-ai-uat-v2-api-1 python -m pip freeze)
if ($LASTEXITCODE -ne 0 -or $freeze.Count -ne 92 -or
    @($freeze | Where-Object { $_ -notmatch '^[A-Za-z0-9_.-]+==[^\s]+$' }).Count -ne 0) {
    throw 'Accepted API package inventory is unavailable or unexpected; no lock written.'
}
$lockPath = Join-Path $stageRoot 'requirements.lock'
$lockText = (($freeze | Sort-Object) -join "`n") + "`n"
[IO.File]::WriteAllText($lockPath, $lockText, [Text.UTF8Encoding]::new($false))
$records.Add([ordered]@{
    path = 'requirements.lock'
    bytes = (Get-Item -LiteralPath $lockPath).Length
    sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $lockPath).Hash.ToLowerInvariant()
})

$manifest = [ordered]@{
    checkpoint = 'TASK-035.3A'
    scope = 'local isolated source and exact accepted-API package versions; not off-host DR'
    accepted_api_image = 'sha256:1f057785bd8cacb68aa8573e3aa12e29a23c37692e0ad045997770d4adf2648e'
    python = '3.12.15'
    included_count = $records.Count
    included = @($records)
    excluded = @(
        '.env and .env.* credential files',
        '.git, .venv, caches, __pycache__, .pyc and generated coverage/build outputs',
        'artifacts, .backups, data/uploads, data/models and private corpus PDFs',
        'uat/corpus-v2 runtime/source manifest and recovered document metadata',
        'temporary diagnostic scripts and recovery-specific Compose overrides',
        'frontend, unrelated experimental worktrees and external models'
    )
}
$manifestJson = $manifest | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText($manifestPath, $manifestJson + "`n", [Text.UTF8Encoding]::new($false))

& tar -cf $archivePath -C $stageRoot .
if ($LASTEXITCODE -ne 0) {
    throw 'Candidate source archive creation failed.'
}
Write-Output "snapshot=$stageRoot"
Write-Output "included_files=$($records.Count)"
Write-Output "archive_sha256=$((Get-FileHash -Algorithm SHA256 -LiteralPath $archivePath).Hash.ToLowerInvariant())"
Write-Output "manifest_sha256=$((Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant())"
Write-Output "lock_sha256=$((Get-FileHash -Algorithm SHA256 -LiteralPath $lockPath).Hash.ToLowerInvariant())"
