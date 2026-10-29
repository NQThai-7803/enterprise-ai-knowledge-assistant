param(
    [string]$BaseUrl = "http://127.0.0.1:18000",
    [string]$ManifestPath = "uat/corpus-v2/manifest.json",
    [int]$ReadyTimeoutSeconds = 1800
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "../..")).Path
$manifestFile = (Resolve-Path -LiteralPath (Join-Path $projectRoot $ManifestPath)).Path
$manifest = Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
$adminPassword = if ($env:UAT_ADMIN_PASSWORD) { $env:UAT_ADMIN_PASSWORD } else { "LocalUatAdmin!2026" }
$managerPassword = if ($env:UAT_MANAGER_PASSWORD) { $env:UAT_MANAGER_PASSWORD } else { "LocalUatManager!2026" }

function Get-Token([string]$Email, [string]$Password) {
    $response = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/auth/login" `
        -ContentType "application/json" -Body (@{email=$Email; password=$Password} | ConvertTo-Json)
    return $response.data
}

function Get-AuthHeaders([string]$Token) {
    return @{Authorization = "Bearer $Token"; Accept = "application/json"}
}

$admin = Get-Token "admin.uat@example.test" $adminPassword
$manager = Get-Token "manager.uat@example.test" $managerPassword
$headers = Get-AuthHeaders $admin.access_token
$existing = (Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/v1/documents?page_size=100" -Headers $headers).data
$runtimeDocuments = @()

foreach ($document in $manifest.documents) {
    $source = (Resolve-Path -LiteralPath (Join-Path $projectRoot $document.source)).Path
    $actualHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $document.sha256) {
        throw "Source hash mismatch for $($document.code): expected $($document.sha256), got $actualHash"
    }

    $runtime = $existing | Where-Object { $_.document_code -eq $document.code } | Select-Object -First 1
    if (-not $runtime) {
        $rawUpload = & curl.exe -sS --fail-with-body -X POST `
            -H "Authorization: Bearer $($admin.access_token)" `
            -H "Accept: application/json" `
            -F "file=@$source;type=application/pdf" `
            -F "title=$($document.title)" `
            -F "access_scope=$($document.visibility)" `
            -F "document_code=$($document.code)" `
            -F "document_version=$($manifest.corpus_version)" `
            -F "description=UAT Corpus v2: $($document.category)" `
            "$BaseUrl/api/v1/documents/upload"
        if ($LASTEXITCODE -ne 0) { throw "Upload failed for $($document.code): $rawUpload" }
        $uploaded = $rawUpload | ConvertFrom-Json
        $runtime = $uploaded.data
    }

    $deadline = (Get-Date).AddSeconds($ReadyTimeoutSeconds)
    do {
        $status = (Invoke-RestMethod -Method Get `
            -Uri "$BaseUrl/api/v1/documents/$($runtime.id)/status" -Headers $headers).data
        if ($status.status -eq "FAILED") {
            throw "Ingestion failed for $($document.code): $($status.error_message)"
        }
        if ($status.status -ne "READY") { Start-Sleep -Seconds 3 }
    } while ($status.status -ne "READY" -and (Get-Date) -lt $deadline)
    if ($status.status -ne "READY") { throw "READY timeout for $($document.code)" }

    foreach ($grant in $document.required_grants) {
        $userId = if ($grant.user -eq "manager.uat@example.test") { $manager.user.id } else { throw "Unknown grant user $($grant.user)" }
        $permissions = (Invoke-RestMethod -Method Get `
            -Uri "$BaseUrl/api/v1/documents/$($runtime.id)/permissions" -Headers $headers).data
        if (-not ($permissions | Where-Object { $_.user_id -eq $userId })) {
            Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/documents/$($runtime.id)/permissions" `
                -Headers $headers -ContentType "application/json" `
                -Body (@{user_id=$userId; permission=$grant.permission} | ConvertTo-Json) | Out-Null
        }
    }

    $runtimeDocuments += [ordered]@{
        code = $document.code
        id = $runtime.id
        title = $document.title
        sha256 = $actualHash
        status = $status.status
        visibility = $document.visibility
        owner = $document.owner
        required_grants = $document.required_grants
    }
    Write-Output "$($document.code): READY ($($runtime.id))"
}

$artifactDir = Join-Path $projectRoot "artifacts/uat-corpus-v2"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
$runtimeManifest = [ordered]@{
    corpus_version = $manifest.corpus_version
    generated_at = (Get-Date).ToString("o")
    api_url = $BaseUrl
    documents = $runtimeDocuments
}
$runtimePath = Join-Path $artifactDir "runtime-manifest.json"
$runtimeManifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $runtimePath -Encoding utf8
Write-Output $runtimePath

