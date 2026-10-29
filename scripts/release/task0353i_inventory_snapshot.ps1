param(
    [string]$SnapshotName = ('task-035-3i-20261014-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$out = Join-Path $repo (Join-Path 'artifacts' $SnapshotName)
if (Test-Path -LiteralPath $out) { throw "Snapshot target already exists: $out" }
$stage = Join-Path $out 'reviewed-source'
$extract = Join-Path $out 'verification-extract'
$archive = Join-Path $out 'reviewed-source.tar'
$manifestPath = Join-Path $out 'source-manifest.json'
$inventoryPath = Join-Path $out 'working-tree-inventory.json'

function Rel([string]$path) { return $path.Replace('\', '/') }
function Hash([string]$path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() }
function Classify([string]$path) {
    if ($path -match '^(\.cache/|tmp_).*') { return 'DIAGNOSTIC_SCRATCH' }
    if ($path -match '^uat/') { return 'SENSITIVE_POTENTIAL' }
    if ($path -match '^docs/release/') { return 'HISTORICAL_RELEASE_EVIDENCE' }
    if ($path -match '^app/') { return 'PRODUCTION_BACKEND_SOURCE' }
    if ($path -match '^frontend/src/.*\.(test|spec)\.') { return 'PRODUCTION_TEST' }
    if ($path -match '^frontend/src/|^frontend/server\.mjs$') { return 'PRODUCTION_FRONTEND_SOURCE' }
    if ($path -match '^frontend/tests/|^tests/acceptance/|^tests/integration/') { return 'RELEASE_QUALIFICATION_TEST' }
    if ($path -match '^tests/unit/test_task0353c2[ef]_eval_harness\.py$|^scripts/release/task0353c2[ef]_eval\.py$') { return 'EXPERIMENTAL_RESEARCH_HARNESS' }
    if ($path -match '^tests/') { return 'PRODUCTION_TEST' }
    if ($path -match '^scripts/uat/|^compose\.uat-corpus-v2') { return 'HISTORICAL_RELEASE_EVIDENCE' }
    if ($path -match '^scripts/release/') { return 'RELEASE_QUALIFICATION_TEST' }
    if ($path -match '^(PROJECT_|TASKS\.md$|CHANGELOG\.md$|docs/|adr/|README\.md$|RELEASE_CHECKLIST\.md$)') { return 'AUTHORITATIVE_PROJECT_DOCUMENTATION' }
    if ($path -match '(^|/)(\.env|.*\.pem$|.*\.key$|.*\.dump$|.*\.pdf$|.*\.zip$)') { return 'SENSITIVE_POTENTIAL' }
    if ($path -match '^(frontend/|deploy/|\.github/|templates/|scripts/)') { return 'RELEASE_BUILD_INPUT' }
    return 'REVIEW_REQUIRED'
}
function Include([string]$path) {
    if ($path -match '^(app/.*\.(py|mako|json)|tests/.*\.(py|json|txt|md)|\.github/.*\.(py|yml|yaml)|deploy/.*|templates/.*)$') { return $true }
    if ($path -match '^frontend/src/.*\.(ts|tsx|css|svg)$|^frontend/tests/.*\.(ts|tsx|mjs)$') { return $true }
    if ($path -match '^frontend/(\.dockerignore|\.env\.example|Dockerfile|DESIGN\.md|eslint\.config\.js|index\.html|package\.json|package-lock\.json|playwright(\.live)?\.config\.ts|postcss\.config\.cjs|server\.mjs|tailwind\.config\.ts|tsconfig(\.node)?\.json|vite\.config\.ts|vitest\.setup\.ts)$') { return $true }
    if ($path -match '^scripts/release/.*\.(py|ps1|yaml)$|^scripts/release/Dockerfile\.task0353a$') { return $true }
    if ($path -in @('.dockerignore','.env.example','.env.production.example','.gitignore','Dockerfile','alembic.ini','pyproject.toml','README.md','compose.yaml','compose.prod.yaml','compose.uat.yaml')) { return $true }
    return $false
}

$tracked = @(git -C $repo ls-files | ForEach-Object { Rel $_ })
if ($LASTEXITCODE -ne 0) { throw 'git ls-files failed' }
$untracked = @(git -C $repo ls-files --others --exclude-standard | ForEach-Object { Rel $_ })
if ($LASTEXITCODE -ne 0) { throw 'git untracked inventory failed' }
$modified = @(git -C $repo diff --name-only | ForEach-Object { Rel $_ })
if ($LASTEXITCODE -ne 0) { throw 'git modified inventory failed' }
$trackedSet = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
$modifiedSet = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach ($p in $tracked) { [void]$trackedSet.Add($p) }
foreach ($p in $modified) { [void]$modifiedSet.Add($p) }
$all = @(($tracked + $untracked) | Sort-Object -Unique)
$inventory = [Collections.Generic.List[object]]::new()
$included = [Collections.Generic.List[object]]::new()
$excluded = [Collections.Generic.List[object]]::new()
New-Item -ItemType Directory -Path $stage -Force | Out-Null
foreach ($p in $all) {
    $src = Join-Path $repo $p
    if ($p -eq 'vite-monorepo') {
        $inventory.Add([ordered]@{path=$p; bytes=$null; sha256=$null; git='TRACKED_GITLINK'; classification='REVIEW_REQUIRED'; source_snapshot=$false; gitlink_commit='3becadbd1d46a68a61a173731a3c7b946fec024f'})
        $excluded.Add([ordered]@{path=$p; classification='REVIEW_REQUIRED_GITLINK'})
        continue
    }
    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { throw "Listed file missing: $p" }
    $item = Get-Item -LiteralPath $src
    if ($item.LinkType -or $item.Target) { throw "Linked file requires review: $p" }
    $sha = Hash $src
    $class = Classify $p
    $isTracked = $trackedSet.Contains($p)
    $take = Include $p
    if ($p -match '^tests/unit/test_task0353c2[ef]_eval_harness\.py$|^scripts/release/task0353c2[ef]_eval\.py$') { $take = $false }
    $record = [ordered]@{path=$p; bytes=$item.Length; sha256=$sha; git=$(if($isTracked){if($modifiedSet.Contains($p)){'MODIFIED_TRACKED'}else{'TRACKED'}}else{'UNTRACKED'}); classification=$class; source_snapshot=$take}
    $inventory.Add($record)
    if ($take) {
        $dst = Join-Path $stage $p
        New-Item -ItemType Directory -Path (Split-Path -Parent $dst) -Force | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst
        if ((Hash $dst) -ne $sha) { throw "Copy mismatch: $p" }
        $included.Add([ordered]@{path=$p; bytes=$item.Length; sha256=$sha})
    } else {
        $excluded.Add([ordered]@{path=$p; classification=$class})
    }
}

$manifest = [ordered]@{
    checkpoint='TASK-035.3I'; created_utc=[DateTime]::UtcNow.ToString('o')
    git_head=(git -C $repo rev-parse HEAD); branch=(git -C $repo branch --show-current)
    scope='Reviewed local source copy, not a qualified RC or off-host backup'
    included_count=$included.Count; included=@($included)
    excluded_from_source=@($excluded)
    blanket_exclusions=@('.git; .env and .env.* except examples; artifacts; .backups; uat; data; Docker volumes; model weights; node_modules; .venv; caches; generated dist; database dumps; private uploaded documents')
}
$utf8 = [Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText($inventoryPath, (($inventory | ConvertTo-Json -Depth 5) + "`n"), $utf8)
[IO.File]::WriteAllText($manifestPath, (($manifest | ConvertTo-Json -Depth 8) + "`n"), $utf8)
& tar -cf $archive -C $stage .
if ($LASTEXITCODE -ne 0) { throw 'tar creation failed' }
New-Item -ItemType Directory -Path $extract -Force | Out-Null
& tar -xf $archive -C $extract
if ($LASTEXITCODE -ne 0) { throw 'tar extraction failed' }
$verified = 0
foreach ($entry in $included) {
    $path = Join-Path $extract $entry.path
    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Hash $path) -ne $entry.sha256) { throw "Extraction mismatch: $($entry.path)" }
    $verified++
}
$actualCount = @(Get-ChildItem -LiteralPath $extract -Recurse -File).Count
if ($actualCount -ne $included.Count) { throw "Extracted count mismatch: $actualCount versus $($included.Count)" }
Write-Output "snapshot=$out"
Write-Output "tracked=$($tracked.Count) untracked=$($untracked.Count) included=$($included.Count) excluded=$($excluded.Count) extracted_verified=$verified"
Write-Output "archive_sha256=$(Hash $archive)"
Write-Output "manifest_sha256=$(Hash $manifestPath)"
Write-Output "inventory_sha256=$(Hash $inventoryPath)"
