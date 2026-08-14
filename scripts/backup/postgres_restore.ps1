param(
    [Parameter(Mandatory = $true)]
    [string]$DumpPath,
    [string]$ComposeFile = "compose.prod.yaml",
    [string]$EnvFile = "",
    [string]$ProjectName = "enterprise-ai-knowledge-assistant-prod",
    [string]$TargetDatabase = "enterprise_ai_restore_check",
    [string]$DatabaseUser = "app_user",
    [switch]$AllowProductionOverwrite
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

$resolvedDump = (Resolve-Path -LiteralPath $DumpPath).Path
if ($TargetDatabase -eq "enterprise_ai" -and -not $AllowProductionOverwrite) {
    throw "Refusing to restore over enterprise_ai without -AllowProductionOverwrite."
}

$fileName = Split-Path -Leaf $resolvedDump
$containerPath = "/tmp/$fileName"
$composeArgs = Get-ComposeArgs

docker @composeArgs cp $resolvedDump "postgres:$containerPath"
docker @composeArgs exec -T postgres sh -c `
    "createdb -U '$DatabaseUser' '$TargetDatabase' 2>/dev/null || true"
docker @composeArgs exec -T postgres pg_restore `
    -U $DatabaseUser -d $TargetDatabase --clean --if-exists --no-owner --no-privileges $containerPath
docker @composeArgs exec -T postgres rm -f $containerPath

Write-Output "Restored PostgreSQL backup into $TargetDatabase."