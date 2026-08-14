param(
    [string]$BackupDir = ".backups",
    [string]$VolumeName = "enterprise-ai-knowledge-assistant-prod_uploads_data",
    [int]$RetentionDays = 14
)

$ErrorActionPreference = "Stop"

$backupRoot = Resolve-Path -LiteralPath (New-Item -ItemType Directory -Force -Path $BackupDir)
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$fileName = "enterprise_ai_uploads_$timestamp.tgz"
$hostPath = Join-Path $backupRoot $fileName

docker run --rm `
    -v "${VolumeName}:/data:ro" `
    -v "${backupRoot}:/backup" `
    redis:7-alpine sh -c "cd /data && tar czf /backup/$fileName ."
docker run --rm `
    -v "${backupRoot}:/backup:ro" `
    redis:7-alpine sh -c "tar tzf /backup/$fileName >/dev/null"

Get-ChildItem -LiteralPath $backupRoot -Filter "enterprise_ai_uploads_*.tgz" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$RetentionDays) } |
    Remove-Item -Force

Write-Output $hostPath
