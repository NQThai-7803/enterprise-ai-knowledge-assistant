param(
    [string]$BaseUrl = "http://127.0.0.1:18000",
    [string]$OutputPath = "artifacts/uat-corpus-v2/semantic-smoke.json"
)

$ErrorActionPreference = "Stop"
$passwords = @{
    "admin.uat@example.test" = if ($env:UAT_ADMIN_PASSWORD) { $env:UAT_ADMIN_PASSWORD } else { "LocalUatAdmin!2026" }
    "manager.uat@example.test" = if ($env:UAT_MANAGER_PASSWORD) { $env:UAT_MANAGER_PASSWORD } else { "LocalUatManager!2026" }
    "staff.uat@example.test" = if ($env:UAT_STAFF_PASSWORD) { $env:UAT_STAFF_PASSWORD } else { "LocalUatStaff!2026" }
}
$tokens = @{}
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "../..")).Path
$runtimeManifest = Get-Content -LiteralPath (Join-Path $projectRoot "artifacts/uat-corpus-v2/runtime-manifest.json") -Raw | ConvertFrom-Json
$knownDocumentIds = @($runtimeManifest.documents | ForEach-Object { [string]$_.id })

function Get-Token([string]$Email) {
    if ($tokens[$Email]) { return $tokens[$Email] }
    $body = @{email=$Email; password=$passwords[$Email]} | ConvertTo-Json
    $login = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/auth/login" -ContentType "application/json" -Body $body
    $tokens[$Email] = $login.data.access_token
    return $tokens[$Email]
}

function Ask([string]$Email, [string]$Title, [string]$Question) {
    $headers = @{Authorization="Bearer $(Get-Token $Email)"; Accept="application/json"}
    $session = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/chat/sessions" -Headers $headers `
        -ContentType "application/json" -Body (@{title=$Title} | ConvertTo-Json)
    $started = Get-Date
    $response = Invoke-RestMethod -Method Post `
        -Uri "$BaseUrl/api/v1/chat/sessions/$($session.data.id)/messages" -Headers $headers `
        -ContentType "application/json" -TimeoutSec 420 -Body (@{content=$Question} | ConvertTo-Json)
    return [ordered]@{
        email=$Email
        question=$Question
        grounding_status=$response.data.grounding_status
        answer=$response.data.assistant_message.content
        citations=@($response.data.assistant_message.citations)
        latency_ms=[int]((Get-Date)-$started).TotalMilliseconds
    }
}

function Check-DocumentDenied([string]$Email, [string]$DocumentId) {
    $headers = @{Authorization="Bearer $(Get-Token $Email)"; Accept="application/json"}
    $response = Invoke-WebRequest -Method Get -Uri "$BaseUrl/api/v1/documents/$DocumentId" `
        -Headers $headers -SkipHttpErrorCheck
    return [ordered]@{
        email=$Email
        question="Direct private-document access must be denied."
        grounding_status="ACCESS_DENIED"
        answer=""
        citations=@()
        latency_ms=0
        http_status=[int]$response.StatusCode
    }
}

$cases = @(
    @{id="organization"; email="staff.uat@example.test"; question="CEO Nova Digital là ai?"; expected="ANSWERED"; required=@("nguyễn anh khoa")},
    @{id="compensation"; email="staff.uat@example.test"; question="Tech Lead thì range lương bao nhiêu?"; expected="ANSWERED"; required=@("42", "70")},
    @{id="multi_document"; email="staff.uat@example.test"; question="Tôi on-call và phải xử lý incident vào Chủ nhật thì thời gian làm việc và tiền OT được xử lý thế nào?"; expected="ANSWERED"; required=@("on-call", "200")},
    @{id="unsupported"; email="staff.uat@example.test"; question="Nova Digital doanh thu năm 2025 là bao nhiêu?"; expected="NO_ANSWER"; required=@()},
    @{id="permission_granted"; email="manager.uat@example.test"; question="What approval must staff obtain before booking travel?"; expected="ANSWERED"; required=@("manager approval")},
    @{id="permission_isolated"; email="staff.uat@example.test"; question=""; expected="ACCESS_DENIED"; required=@()}
)
$results = @()
foreach ($case in $cases) {
    if ($case.expected -eq "ACCESS_DENIED") {
        $privateDocumentId = [string]($runtimeManifest.documents | Where-Object code -eq "UAT-GROUNDING-001").id
        $result = Check-DocumentDenied $case.email $privateDocumentId
    } else {
        $result = Ask $case.email "UAT v2 smoke $($case.id)" $case.question
    }
    $citationCount = @($result.citations).Count
    $normalizedAnswer = $result.answer.ToLowerInvariant()
    $materialAnswer = @($case.required | Where-Object { -not $normalizedAnswer.Contains($_) }).Count -eq 0
    $validCitationIds = @($result.citations | Where-Object { $knownDocumentIds -notcontains [string]$_.document_id }).Count -eq 0
    $passed = if ($case.expected -eq "ACCESS_DENIED") {
        $result.http_status -eq 404
    } else {
        $result.grounding_status -eq $case.expected -and `
            (($case.expected -eq "ANSWERED" -and $citationCount -gt 0) -or `
             ($case.expected -eq "NO_ANSWER" -and $citationCount -eq 0)) -and `
            $materialAnswer -and $validCitationIds
    }
    $result.id = $case.id
    $result.expected = $case.expected
    $result.material_answer = $materialAnswer
    $result.valid_citation_ids = $validCitationIds
    $result.passed = $passed
    $results += $result
    Write-Output "$($case.id): $($result.grounding_status) citations=$citationCount pass=$passed"
}
$payload = [ordered]@{
    generated_at=(Get-Date).ToString("o")
    model="qwen2.5:3b"
    passed=(@($results | Where-Object passed).Count)
    total=$results.Count
    cases=$results
}
$output = Join-Path $projectRoot $OutputPath
New-Item -ItemType Directory -Force -Path (Split-Path $output) | Out-Null
$payload | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $output -Encoding utf8
if ($payload.passed -ne $payload.total) { exit 1 }
Write-Output $output
