# Demo stack helper (DEMO.md, "Chay tu ban clone moi"). Works on the repository this file is in:
#   deploy\demo\demo.ps1 init | build | up | seed | warmup | questions | status | down | reset
# Passwords: user environment variables EAKA_DEMO_{ADMIN,MANAGER,STAFF,OPS}_PASSWORD, created by
# `init` when missing and never printed. `down` keeps the <project>_* volumes.
# Optional: EAKA_DEMO_PROJECT (default eaka-demo), DEMO_BACKEND_IMAGE and DEMO_FRONTEND_IMAGE
# (default eaka-backend:demo-<commit> and eaka-frontend:demo-<commit>, made by `build`).
# Every action but init, build and questions refuses a .env without the line EAKA_PROFILE=demo.
param([ValidateSet('init', 'build', 'up', 'down', 'status', 'seed', 'warmup', 'questions', 'reset')]
    [string]$Action = 'status',
    [string]$Confirm)  # reset only: the text "reset demo" (otherwise it is asked for)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $Root
$Project = if ($env:EAKA_DEMO_PROJECT) { $env:EAKA_DEMO_PROJECT } else { 'eaka-demo' }
# The .env and the <project>_* volumes belong together: the .env of another stack (the dev one)
# would meet the demo database with the wrong password. `init` marks the demo's .env with this line.
$EnvFile = Join-Path $Root '.env'
$EnvMarker = 'EAKA_PROFILE=demo'
function Test-DemoEnv { (Test-Path $EnvFile) -and [bool](Select-String -Path $EnvFile -Pattern "^$EnvMarker\s*$" -Quiet) }
$NotDemoEnv = "$EnvFile is not the demo's .env (no $EnvMarker line): nothing done. Run the demo from its own clone, after deploy\demo\demo.ps1 init there (DEMO.md)."
if (($Action -notin 'init', 'build', 'questions') -and -not (Test-DemoEnv)) { throw $NotDemoEnv }
$commit = git -C $Root rev-parse --short HEAD
if (-not $env:DEMO_BACKEND_IMAGE) { $env:DEMO_BACKEND_IMAGE = "eaka-backend:demo-$commit" }
if (-not $env:DEMO_FRONTEND_IMAGE) { $env:DEMO_FRONTEND_IMAGE = "eaka-frontend:demo-$commit" }
$Url = 'http://127.0.0.1:18480'
$Roles = 'ADMIN', 'MANAGER', 'STAFF', 'OPS'
# Dev-set ids only (UAT Q001-Q100, RBAC dev); the text is read from the repository by id.
$DemoQuestions = 'Q016', 'Q043', 'Q084', 'RBD-01', 'RBD-13', 'RBD-07'
$SpareQuestions = 'Q027', 'Q061', 'RBD-02', 'RBD-09'
$WarmupQuestions = 'Q016', 'Q027', 'Q061'
# Windows PowerShell 5.1 turns docker's progress lines on stderr into errors under 'Stop'.
function Invoke-Docker { $ErrorActionPreference = 'Continue'; docker @args; if ($LASTEXITCODE) { throw "docker $($args[0]) failed" } }
$files = @('-p', $Project, '--profile', 'frontend', '-f', 'compose.yaml',
    '-f', 'compose.uat-corpus-v2.yaml', '-f', "$PSScriptRoot\compose.demo.yaml")

function Get-DemoPassword($Role) {
    $name = "EAKA_DEMO_${Role}_PASSWORD"
    $value = [Environment]::GetEnvironmentVariable($name, 'User')
    if ($value) { $value } else { [Environment]::GetEnvironmentVariable($name) }  # non-Windows: process
}

function Use-DemoPasswords {
    foreach ($role in $Roles) {
        $value = Get-DemoPassword $role
        if (-not $value) { throw "EAKA_DEMO_${role}_PASSWORD is not set: run deploy\demo\demo.ps1 init" }
        Set-Item "env:UAT_${role}_PASSWORD" $value
    }
    $env:DEMO_OPS_PASSWORD = $env:UAT_OPS_PASSWORD
}

function New-Secret([int]$Bytes) {
    $buffer = New-Object byte[] $Bytes
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
    ([BitConverter]::ToString($buffer) -replace '-', '').ToLower()
}

function Get-DevQuestion([string[]]$Ids) {
    $text = @{}
    $uat = [IO.File]::ReadAllText("$Root\eval-data\uat\questions.json", [Text.Encoding]::UTF8)
    foreach ($item in ($uat | ConvertFrom-Json).items) { $text[$item.id] = $item.question }
    foreach ($line in [IO.File]::ReadAllLines("$Root\tests\acceptance\rbac_dev_v1.yaml", [Text.Encoding]::UTF8)) {
        if ($line -match '\{id: (RBD-\d+),.*\bquestion: "([^"]*)"') { $text[$Matches[1]] = $Matches[2] }
    }
    foreach ($id in $Ids) {
        if (-not $text[$id]) { throw "no dev question $id" }
        [pscustomobject]@{ Id = $id; Question = $text[$id] }
    }
}

function Invoke-Api($Method, $Path, $Body, $Token) {
    $headers = @{}
    if ($Token) { $headers.Authorization = "Bearer $Token" }
    # Windows PowerShell 5.1 would not send a string body as UTF-8 by itself.
    # (Assigned directly: an `if` expression would unroll the byte[] into an object[].)
    $json = $null
    if ($Body) { $json = [Text.Encoding]::UTF8.GetBytes(($Body | ConvertTo-Json -Compress)) }
    Invoke-RestMethod -Method $Method -Uri "$Url$Path" -Headers $headers -Body $json `
        -ContentType 'application/json; charset=utf-8' -TimeoutSec 300
}

switch ($Action) {
    'init' {
        # .env from .env.example with random secrets and the demo's LLM settings; never overwritten.
        if (Test-Path $EnvFile) {
            if (-not (Test-DemoEnv)) { throw $NotDemoEnv }
            '.env exists: kept as it is'
        } else {
            $text = [IO.File]::ReadAllText((Join-Path $Root '.env.example'))
            $text = $text.Replace('replace-with-a-long-random-secret-key', (New-Secret 32))
            # POSTGRES_PASSWORD and the password inside DATABASE_URL
            $text = $text.Replace('change-me-for-local-development', (New-Secret 16))
            $settings = [ordered]@{
                LLM_ENABLED = 'true'; LLM_PROVIDER = 'ollama'
                LLM_OLLAMA_KEEP_ALIVE = '30m'  # the model stays loaded between demo questions
                LLM_MAX_OUTPUT_TOKENS = '512'
            }
            foreach ($key in $settings.Keys) {
                $line = "$key=$($settings[$key])"
                if ($text -match "(?m)^$key=") { $text = $text -replace "(?m)^$key=[^\r\n]*", $line }
                else { $text = $text.TrimEnd() + "`n$line`n" }
            }
            $text = $text.TrimEnd() + "`n# deploy\demo\demo.ps1 runs only on a .env with this line`n$EnvMarker`n"
            [IO.File]::WriteAllText($EnvFile, $text, (New-Object Text.UTF8Encoding $false))
            '.env written from .env.example (random SECRET_KEY and database password)'
        }
        foreach ($role in $Roles) {
            if (Get-DemoPassword $role) {
                "EAKA_DEMO_${role}_PASSWORD: already set, kept"
            } else {
                [Environment]::SetEnvironmentVariable("EAKA_DEMO_${role}_PASSWORD", "Demo$(New-Secret 12)!", 'User')
                "EAKA_DEMO_${role}_PASSWORD: created in the user environment (not printed)"
            }
        }
    }
    'build' {
        Invoke-Docker build --target runtime -t $env:DEMO_BACKEND_IMAGE .
        Invoke-Docker build -f deploy/frontend/Dockerfile --build-arg VITE_API_BASE_URL= -t $env:DEMO_FRONTEND_IMAGE .
    }
    'up' {
        foreach ($image in $env:DEMO_BACKEND_IMAGE, $env:DEMO_FRONTEND_IMAGE) {
            & { $ErrorActionPreference = 'Continue'; docker image inspect $image *> $null }
            if ($LASTEXITCODE) { throw "image $image is missing: run deploy\demo\demo.ps1 build" }
        }
        Use-DemoPasswords
        Invoke-Docker compose @files up -d --no-build
        $deadline = (Get-Date).AddMinutes(5)
        do {
            Start-Sleep -Seconds 3
            try { $ok = (Invoke-WebRequest "$Url/health/live" -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200 } catch { $ok = $false }
        } until ($ok -or (Get-Date) -gt $deadline)
        if (-not $ok) { throw "$Url/health/live is not answering" }
        "demo up: $Url (run deploy\demo\demo.ps1 warmup before presenting)"
    }
    'down' { Invoke-Docker compose @files down }   # no -v: the volumes stay
    'status' { Invoke-Docker compose @files ps }
    'seed' {
        Use-DemoPasswords
        Invoke-Docker run --rm --memory 512m --network "container:$Project-api-1" `
            -v "${Root}:/src:ro" -e UAT_ADMIN_PASSWORD -e UAT_MANAGER_PASSWORD -e DEMO_OPS_PASSWORD `
            --entrypoint python $env:DEMO_BACKEND_IMAGE /src/deploy/demo/seed_demo.py
    }
    'questions' {
        try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }
        Get-DevQuestion ($DemoQuestions + $SpareQuestions) | Format-Table -AutoSize -Wrap
    }
    'reset' {
        # Deletes the DATA volumes of the demo project (postgres, redis, uploads) and nothing
        # else, then up (which migrates), seed and warmup. The e5 model cache volume stays.
        if ($Confirm -ne 'reset demo') {
            $Confirm = Read-Host 'This deletes the demo data volumes. Type "reset demo" to go on'
        }
        if ($Confirm -ne 'reset demo') { throw 'not confirmed: nothing deleted' }
        Invoke-Docker compose @files down
        foreach ($volume in 'postgres_data', 'redis_data', 'uploads_data' | ForEach-Object { "${Project}_$_" }) {
            # (Labels as JSON: Windows PowerShell 5.1 drops the inner quotes of an {{index}} format.)
            $labels = & { $ErrorActionPreference = 'Continue'; docker volume inspect $volume --format '{{json .Labels}}' 2>$null }
            $owner = if ($LASTEXITCODE -eq 0 -and $labels) { ($labels | ConvertFrom-Json).'com.docker.compose.project' }
            if ($owner -eq $Project) { Invoke-Docker volume rm $volume } else { "skip $volume (not a volume of $Project)" }
        }
        & $PSCommandPath up
        & $PSCommandPath seed
        & $PSCommandPath warmup
    }
    'warmup' {
        # Loads the LLM and the embedding model, then times a few dev questions as staff;
        # the warmup chat sessions are deleted afterwards.
        Use-DemoPasswords
        $token = (Invoke-Api POST '/api/v1/auth/login' @{ email = 'staff.uat@example.test'; password = $env:UAT_STAFF_PASSWORD }).data.access_token
        foreach ($item in Get-DevQuestion $WarmupQuestions) {
            $session = (Invoke-Api POST '/api/v1/chat/sessions' @{ title = 'warmup' } $token).data.id
            $watch = [Diagnostics.Stopwatch]::StartNew()
            $answer = (Invoke-Api POST "/api/v1/chat/sessions/$session/messages" @{ content = $item.Question } $token).data
            $watch.Stop()
            '{0,-5} {1,6:N1} s  {2}  citations={3}' -f $item.Id, $watch.Elapsed.TotalSeconds, $answer.grounding_status, @($answer.assistant_message.citations).Count
            Invoke-Api DELETE "/api/v1/chat/sessions/$session" $null $token | Out-Null
        }
    }
}
