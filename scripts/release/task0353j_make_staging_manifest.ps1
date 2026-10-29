param(
    [string]$Output = 'docs/release/TASK-035.3J-proposed-git-staging-manifest-20261014.json'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$priorPath = Join-Path $repo 'artifacts/task-035-3i-20261014-a6b8f7f7/source-manifest.json'
$prior = Get-Content -Raw -LiteralPath $priorPath | ConvertFrom-Json
$priorHashes = @{}
foreach ($entry in $prior.included) { $priorHashes[$entry.path] = $entry.sha256 }
foreach ($entry in $prior.included) {
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo $entry.path)).Hash.ToLowerInvariant()
    if ($actual -ne $entry.sha256) { throw "035.3I selected-source drift: $($entry.path)" }
}

function Choice([string]$p) {
    $result = [ordered]@{
        disposition = 'REVIEW_REQUIRED'; purpose = 'Existing project content needing provenance review'
        needed_to_build = $false; needed_to_test = $false; historical_reproducibility = $true
        sensitivity = 'POTENTIAL'; reason = 'No current build or test requirement established'
        approval = 'Engineering and publication owner'
    }
    if ($p -eq 'vite-monorepo') {
        $result.purpose = 'Nested repository Gitlink without parent .gitmodules/fetch URL'
        $result.reason = 'Fresh clone cannot populate the locally available commit from recorded parent metadata'
    } elseif ($p -match '^tore package\.json package-lock\.json$') {
        $result.purpose = 'Tracked frontend diff fragment, not a package manifest'
        $result.reason = 'No active build/CI reference; preserve provenance before disposition'
    } elseif ($p -match '^(files-for-chat/|frontend/files-for-chat/|frontend-stitch-reference/|frontend/\.agents/|frontend/skills-lock\.json$|enterprise_ai_md_updates_|Modelfile\.qwen2\.5-7b|README_UPDATE\.txt$)') {
        $result.purpose = 'Historical design/reference or legacy binary/model material'
        $result.reason = 'No active backend/frontend Docker or CI dependency found; historical/privacy role remains'
    } elseif ($p -match '^compose\.uat-corpus-v2|^scripts/uat/') {
        $result.purpose = 'Isolated UAT corpus operations/recovery configuration'
        $result.reason = 'Useful for historical reproduction but may carry private-runtime paths or operational controls'
        $result.approval = 'Engineering, operations and privacy owner'
    } elseif ($p -match '^uat/') {
        $result.disposition = 'KEEP_AS_PRIVATE_EVIDENCE'; $result.purpose = 'UAT corpus source/runtime metadata'
        $result.reason = 'Private corpus provenance, not ordinary Git source'; $result.sensitivity = 'PRIVATE'
        $result.approval = 'Data/privacy owner'
    } elseif ($p -match '^\.cache/') {
        $result.disposition = 'EXCLUDE_GENERATED_OUTPUT'; $result.purpose = 'Local generated model/tool cache'
        $result.historical_reproducibility = $false; $result.reason = 'Generated cache, not source'
        $result.sensitivity = 'POTENTIAL'; $result.approval = 'None for source exclusion; preserve original'
    } elseif ($p -match '^tmp_.*_trace\.py$') {
        $result.disposition = 'KEEP_AS_EXPERIMENTAL_EVIDENCE'; $result.purpose = 'Runtime retrieval diagnostic trace'
        $result.reason = 'One-off diagnostic, not build/test import; full-repo Ruff failures retained'
        $result.approval = 'Engineering and privacy owner before archive/publication'
    } elseif ($p -match '^tests/unit/test_task0353c2[ef]_eval_harness\.py$|^scripts/release/task0353c2[ef]_eval\.py$') {
        $result.disposition = 'KEEP_AS_EXPERIMENTAL_EVIDENCE'; $result.purpose = 'Independent semantic research harness'
        $result.reason = 'Historical research, not a maintained RC gate without owner promotion'
        $result.approval = 'Engineering/test owner'
    } elseif ($p -match '^app/') {
        $result.disposition = 'INCLUDE_IN_SOURCE_COMMIT'; $result.purpose = 'Backend application or migration source'
        $result.needed_to_build = $true; $result.needed_to_test = $true; $result.historical_reproducibility = $true
        $result.sensitivity = 'REVIEW_FOR_FIXTURES'; $result.reason = 'Backend Docker copies app tree; includes dirty H5.2 source'
        $result.approval = 'Engineering plus exact-diff privacy review'
    } elseif ($p -match '^frontend/src/.*(\.test\.|\.spec\.|/test/)') {
        $result.disposition = 'INCLUDE_IN_TEST_TOOLING_COMMIT'; $result.purpose = 'Frontend component or mocked-browser test'
        $result.needed_to_test = $true; $result.reason = 'Required to retain 035.3H correction regression evidence'
        $result.sensitivity = 'LOW_PENDING_REVIEW'; $result.approval = 'Frontend/test owner'
    } elseif ($p -match '^frontend/src/') {
        $result.disposition = 'INCLUDE_IN_SOURCE_COMMIT'; $result.purpose = 'Frontend application source'
        $result.needed_to_build = $true; $result.needed_to_test = $true
        $result.reason = 'Frontend Vite build input; includes corrected dialog'
        $result.sensitivity = 'LOW_PENDING_REVIEW'; $result.approval = 'Frontend owner and privacy review'
    } elseif ($p -match '^frontend/tests/|^tests/|^\.github/|^scripts/release/|^scripts/backup/') {
        $result.disposition = 'INCLUDE_IN_TEST_TOOLING_COMMIT'; $result.purpose = 'Application test, CI, release or backup tooling'
        $result.needed_to_test = $true; $result.reason = 'Maintains reproducible quality and release checks; includes red safety contracts'
        $result.sensitivity = 'REVIEW_FOR_FIXTURES'; $result.approval = 'Engineering/test/security owner'
    } elseif ($p -match '^frontend/(playwright(\.live)?\.config\.ts|vitest\.setup\.ts|eslint\.config\.js)$') {
        $result.disposition = 'INCLUDE_IN_TEST_TOOLING_COMMIT'; $result.purpose = 'Frontend quality/browser configuration'
        $result.needed_to_test = $true; $result.reason = 'Required for local/CI frontend checks'
        $result.sensitivity = 'LOW_PENDING_REVIEW'; $result.approval = 'Frontend/test owner'
    } elseif ($p -match '^frontend/(\.dockerignore|\.env\.example|Dockerfile|index\.html|package(-lock)?\.json|postcss\.config\.cjs|server\.mjs|tailwind\.config\.ts|tsconfig(\.node)?\.json|vite\.config\.ts)$|^deploy/|^(\.dockerignore|\.env\.example|\.env\.production\.example|\.gitignore|Dockerfile|alembic\.ini|pyproject\.toml|README\.md|compose\.yaml|compose\.prod\.yaml|compose\.uat\.yaml)$') {
        $result.disposition = 'INCLUDE_IN_SOURCE_COMMIT'; $result.purpose = 'Build, dependency, runtime template or deployment input'
        $result.needed_to_build = $true; $result.reason = 'Referenced by backend/frontend build or documented deployment path'
        $result.sensitivity = 'REVIEW_EXAMPLE_CONFIG'; $result.approval = 'Engineering/security owner'
    } elseif ($p -match '^docs/release/TASK-035\.3[IiJj]-|^docs/release/TASK-035\.3H-') {
        $result.disposition = 'INCLUDE_IN_RELEASE_DOCS_COMMIT'; $result.purpose = 'Recent reviewed checkpoint report'
        $result.reason = 'Links source/accessibility evidence without private document bytes'
        $result.sensitivity = 'REVIEW_REPORT'; $result.approval = 'Release and privacy owner'
    } elseif ($p -match '^docs/release/') {
        $result.purpose = 'Historical release or research report'
        $result.reason = 'May contain source excerpts, person names or runtime identifiers; individual privacy review needed'
        $result.approval = 'Release and privacy owner'
    } elseif ($p -match '^(PROJECT_STATUS\.md|TASKS\.md|CHANGELOG\.md)$|^docs/|^adr/|^templates/|^frontend/DESIGN\.md$|^[A-Z][A-Z_]+\.md$') {
        $result.disposition = 'INCLUDE_IN_RELEASE_DOCS_COMMIT'; $result.purpose = 'Project contract, status or documentation'
        $result.reason = 'Maintains source/evidence decision traceability'
        $result.sensitivity = 'REVIEW_REPORT'; $result.approval = 'Release and privacy owner'
    }
    return $result
}

$tracked = @(git -C $repo ls-files)
if ($LASTEXITCODE -ne 0) { throw 'git ls-files failed' }
$untracked = @(git -C $repo ls-files --others --exclude-standard)
if ($LASTEXITCODE -ne 0) { throw 'git untracked listing failed' }
$modified = @(git -C $repo -c core.safecrlf=false diff --name-only)
if ($LASTEXITCODE -ne 0) { throw 'git modified listing failed' }
$trackedSet = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
$modifiedSet = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach ($p in $tracked) { [void]$trackedSet.Add($p.Replace('\','/')) }
foreach ($p in $modified) { [void]$modifiedSet.Add($p.Replace('\','/')) }
$items = [Collections.Generic.List[object]]::new()
foreach ($raw in @(($tracked + $untracked) | Where-Object { $_.Replace('\','/') -ne $Output } | Sort-Object -Unique)) {
    $p = $raw.Replace('\','/')
    $c = Choice $p
    $state = if ($p -eq 'vite-monorepo') { 'TRACKED_GITLINK' } elseif ($trackedSet.Contains($p)) { if ($modifiedSet.Contains($p)) { 'MODIFIED_TRACKED' } else { 'TRACKED_UNMODIFIED' } } else { 'UNTRACKED' }
    $sha = $null
    if ($p -eq 'vite-monorepo') {
        $sha = 'gitlink:3becadbd1d46a68a61a173731a3c7b946fec024f'
    } else {
        $full = Join-Path $repo $p
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "Selected path missing: $p" }
        $sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $full).Hash.ToLowerInvariant()
    }
    $items.Add([ordered]@{
        path=$p; git_state=$state; proposed_disposition=$c.disposition
        sha256_or_gitlink=$sha; in_0353i_source_snapshot=$priorHashes.ContainsKey($p)
        purpose=$c.purpose; needed_to_build=$c.needed_to_build; needed_to_test=$c.needed_to_test
        historical_reproducibility=$c.historical_reproducibility; sensitivity=$c.sensitivity
        reason=$c.reason; required_approval=$c.approval
    })
}

$evidencePaths = @(
    'artifacts/uat-corpus-v2/h5-2-broad-v2-final-20261013.json',
    'artifacts/uat-corpus-v2/h5-2-qualification-20261013.md',
    'artifacts/task-035-3a-20261013/candidate-source.tar',
    'artifacts/task-035-3b-20261013/permission-safety.json',
    'artifacts/task-035-3i-20261014-a6b8f7f7/reviewed-source.tar',
    '.backups/uat-corpus-v2/20260930-010258/SHA256SUMS.json'
)
$evidence = [Collections.Generic.List[object]]::new()
foreach ($p in $evidencePaths) {
    $full = Join-Path $repo $p
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "Protected evidence missing: $p" }
    $evidence.Add([ordered]@{path=$p; proposed_disposition='KEEP_AS_PRIVATE_EVIDENCE'; sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $full).Hash.ToLowerInvariant(); required_approval='Release/data/privacy owner for access-controlled storage'})
}
$manifest = [ordered]@{
    checkpoint='TASK-035.3J'; generated_utc=[DateTime]::UtcNow.ToString('o')
    git_head=(git -C $repo rev-parse HEAD); branch=(git -C $repo branch --show-current)
    purpose='Proposed per-path Git source/test/docs staging categories; no git add executed'
    source_snapshot_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo 'artifacts/task-035-3i-20261014-a6b8f7f7/reviewed-source.tar')).Hash.ToLowerInvariant()
    git_visible_path_count=$items.Count; git_visible_paths=@($items)
    representative_ignored_private_evidence=@($evidence)
    ignored_path_rules=@(
        [ordered]@{prefix='.env and .env.* except reviewed examples'; disposition='KEEP_AS_PRIVATE_EVIDENCE'},
        [ordered]@{prefix='artifacts/, .backups/, data/, uat/ private material'; disposition='KEEP_AS_PRIVATE_EVIDENCE'},
        [ordered]@{prefix='.venv/, caches, frontend/node_modules/, frontend/dist/, coverage and test-results'; disposition='EXCLUDE_GENERATED_OUTPUT'}
    )
    self_path=$Output; self_hash='NOT_RECORDED_SELF_REFERENTIAL'; self_disposition='INCLUDE_IN_RELEASE_DOCS_COMMIT_AFTER_REVIEW'
    no_git_index_write=$true
}
$outPath = Join-Path $repo $Output
if (Test-Path -LiteralPath $outPath) {
    $previous = Get-Content -Raw -LiteralPath $outPath | ConvertFrom-Json
    if ($previous.checkpoint -ne 'TASK-035.3J' -or $previous.self_path -ne $Output) {
        throw "Refusing to overwrite unrelated manifest: $Output"
    }
}
$json = ($manifest | ConvertTo-Json -Depth 10) + "`n"
[IO.File]::WriteAllText($outPath, $json, [Text.UTF8Encoding]::new($false))
if (-not (Test-Path -LiteralPath $outPath -PathType Leaf)) { throw 'Manifest write failed' }
Write-Output "manifest=$outPath"
Write-Output "git_visible_paths=$($items.Count) protected_evidence=$($evidence.Count)"
Write-Output "sha256=$((Get-FileHash -Algorithm SHA256 -LiteralPath $outPath).Hash.ToLowerInvariant())"
