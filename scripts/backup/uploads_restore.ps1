param(
    [Parameter(Mandatory = $true)]
    [string]$ArchivePath,
    [string]$TargetVolumeName = "enterprise-ai-knowledge-assistant-prod_uploads_restore_check",
    [switch]$AllowProductionOverwrite
)

$ErrorActionPreference = "Stop"

$resolvedArchive = Resolve-Path -LiteralPath $ArchivePath
if ($TargetVolumeName -eq "enterprise-ai-knowledge-assistant-prod_uploads_data" -and -not $AllowProductionOverwrite) {
    throw "Refusing to restore over production uploads volume without -AllowProductionOverwrite."
}

$fileName = Split-Path -Leaf $resolvedArchive
$archiveDir = Split-Path -Parent $resolvedArchive

docker volume create $TargetVolumeName | Out-Null
docker run --rm `
    -v "${TargetVolumeName}:/restore" `
    -v "${archiveDir}:/backup:ro" `
    redis:7-alpine sh -c "cd /restore && tar xzf /backup/$fileName"

Write-Output "Restored uploads archive into volume $TargetVolumeName."
