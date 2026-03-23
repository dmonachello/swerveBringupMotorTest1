param(
    [string]$Python = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info($msg) {
    Write-Host $msg
}

function Ensure-Command($cmd, $hint) {
    $ok = $true
    try {
        & $cmd --version | Out-Null
    } catch {
        $ok = $false
    }
    if (-not $ok) {
        Write-Error $hint
        exit 2
    }
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Write-Info "== FRC Bringup Diagnostics Install (Windows) =="
Write-Info "Repo: $repoRoot"

Ensure-Command $Python "ERROR: Python not found. Install Python 3.10+ and ensure it is on PATH, or pass -Python <path>."

Write-Info "Checking pip..."
try {
    & $Python -m pip --version | Out-Null
} catch {
    Write-Error "ERROR: pip not available. Try: $Python -m ensurepip --upgrade"
    exit 2
}

Write-Info "Upgrading pip..."
& $Python -m pip install --upgrade pip

Write-Info "Installing Python dependencies..."
$deps = @(
    "python-can",
    "pyserial",
    "pyntcore",
    "pynetworktables",
    "reportlab"
)
& $Python -m pip install --upgrade @deps

Write-Info "Creating log folders..."
New-Item -ItemType Directory -Force -Path "tools\can_nt\logs" | Out-Null
New-Item -ItemType Directory -Force -Path "tools\can_nt\captures" | Out-Null

Write-Info ""
Write-Info "Done."
Write-Info "Next steps:"
Write-Info "  1) Topology editor: $Python tools\\can_topology\\can_top_editor.py"
Write-Info "  2) CAN listener:    $Python tools\\can_nt\\can_nt_bridge.py --rio <roborio-ip>"
Write-Info "  3) Deploy robot code via WPILib (GradleRIO)."
