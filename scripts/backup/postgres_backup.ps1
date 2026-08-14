param(
    [string]$ComposeFile = "compose.prod.yaml",
    [string]$EnvFile = "",
    [string]$ProjectName = "enterprise-ai-knowledge-assistant-prod",
    [string]$BackupDir = ".backups",
    [string]$DatabaseName = "enterprise_ai",
    [string]$DatabaseUser = "app_user",
    [int]$RetentionDays = 14
)

$ErrorActionPreference = "Stop"

function Get-ComposeArgs {
    $args = @("compose", "-p", $ProjectName)
    if ($EnvFile.Trim()) {
        $args += @("--env-file", $EnvFile)
    }
    $args += @("-f", $ComposeFile)
    return $args
}

$backupRoot = (Resolve-Path -LiteralPath (New-Item -ItemType Directory -Force -Path $BackupDir)).Path
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$fileName = "enterprise_ai_postgres_$timestamp.dump"
$hostPath = Join-Path $backupRoot $fileName
$containerPath = "/tmp/$fileName"
$composeArgs = Get-ComposeArgs

docker @composeArgs exec -T postgres pg_dump `
    -U $DatabaseUser -d $DatabaseName -Fc --no-owner --no-privileges -f $containerPath
docker @composeArgs cp "postgres:$containerPath" $hostPath
docker @composeArgs exec -T postgres pg_restore --list $containerPath | Out-Null
docker @composeArgs exec -T postgres rm -f $containerPath

Get-ChildItem -LiteralPath $backupRoot -Filter "enterprise_ai_postgres_*.dump" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$RetentionDays) } |
    Remove-Item -Force

Write-Output $hostPath