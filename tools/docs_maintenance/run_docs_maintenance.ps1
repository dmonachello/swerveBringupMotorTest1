$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..\..')
$reportsDir = Join-Path $scriptDir 'reports'
$timestamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$timestampedReport = Join-Path $reportsDir ("docs_health_" + $timestamp + ".json")
$latestReport = Join-Path $reportsDir 'latest.json'

New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null

Push-Location $repoRoot
try {
    python -m tools.docs_maintenance.main --repo-root . --pretty --write-artifacts --output $timestampedReport | Out-Null
    Copy-Item -LiteralPath $timestampedReport -Destination $latestReport -Force
    Write-Output ("Docs maintenance report written: " + $timestampedReport)
    Write-Output ("Latest report updated: " + $latestReport)
} finally {
    Pop-Location
}
