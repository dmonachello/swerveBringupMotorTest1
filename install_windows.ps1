param(
    [string]$Python = "python",
    [string]$VenvPath = ".venv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Installer constants
$ExitFailure = 2
$MinimumPythonVersion = [Version]"3.10"
$RequirementsFileName = "requirements-windows.txt"
$VenvPythonRelativePath = "Scripts\python.exe"
$LogsRelativePath = "tools\can_nt\logs"
$CapturesRelativePath = "tools\can_nt\captures"
$PythonVersionCode = "import sys; print('.'.join(map(str, sys.version_info[:3])))"
$ImportCheckCode = "import can, serial, prompt_toolkit, reportlab, docx, tkinter; from tools.can_nt.cli_grammar_model import CliGrammarModel; from pathlib import Path; CliGrammarModel.from_ebnf(Path('tools/can_nt/bridge_cli_ebnf.txt'))"

function Write-Info {
    <#
    .SYNOPSIS
    Writes one installer status line.
    #>
    param([string]$Message)

    Write-Host $Message
}

function Invoke-NativeChecked {
    <#
    .SYNOPSIS
    Runs a native process and turns a nonzero exit into an installer failure.

    .DESCRIPTION
    Windows PowerShell 5.1 does not make native nonzero exits terminating
    errors. This boundary captures the exit code immediately and enforces it.
    #>
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$Operation
    )

    $output = & $FilePath @ArgumentList 2>&1
    $nativeExitCode = $LASTEXITCODE
    if ($nativeExitCode -ne 0) {
        $details = ($output | Out-String).Trim()
        if ($details) {
            throw "$Operation failed with exit code $nativeExitCode.`n$details"
        }
        throw "$Operation failed with exit code $nativeExitCode."
    }
    return $output
}

function Get-CheckedPythonVersion {
    <#
    .SYNOPSIS
    Reads and validates a Python interpreter version.

    .ERRORS
    Fails when the process cannot run, returns malformed output, or is older
    than the supported minimum.
    #>
    param(
        [string]$PythonExecutable,
        [string]$Description
    )

    $output = Invoke-NativeChecked `
        -FilePath $PythonExecutable `
        -ArgumentList @("-c", $PythonVersionCode) `
        -Operation "Checking $Description"
    $versionText = (($output | Select-Object -Last 1) -as [string]).Trim()
    $version = $null
    if (-not [Version]::TryParse($versionText, [ref]$version)) {
        throw "$Description returned an invalid version: $versionText"
    }
    if ($version -lt $MinimumPythonVersion) {
        throw "$Description is Python $version; Python $MinimumPythonVersion or newer is required."
    }
    return $version
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$requirementsPath = Join-Path $repoRoot $RequirementsFileName
$resolvedVenvPath = if ([IO.Path]::IsPathRooted($VenvPath)) {
    [IO.Path]::GetFullPath($VenvPath)
} else {
    [IO.Path]::GetFullPath((Join-Path $repoRoot $VenvPath))
}
$venvPython = Join-Path $resolvedVenvPath $VenvPythonRelativePath

try {
    Set-Location $repoRoot
    Write-Info "== FRC Bringup Diagnostics Install (Windows) =="
    Write-Info "Repo: $repoRoot"

    if (-not (Test-Path -LiteralPath $requirementsPath -PathType Leaf)) {
        throw "Dependency manifest not found: $requirementsPath"
    }

    $bootstrapVersion = Get-CheckedPythonVersion `
        -PythonExecutable $Python `
        -Description "bootstrap Python"
    Write-Info "Bootstrap Python: $bootstrapVersion ($Python)"

    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        if (Test-Path -LiteralPath $resolvedVenvPath) {
            throw "The virtual environment is incomplete: $resolvedVenvPath. Remove or rename it, then run the installer again."
        }
        Write-Info "Creating virtual environment: $resolvedVenvPath"
        Invoke-NativeChecked `
            -FilePath $Python `
            -ArgumentList @("-m", "venv", $resolvedVenvPath) `
            -Operation "Creating the virtual environment" | Out-Null
    } else {
        Write-Info "Reusing virtual environment: $resolvedVenvPath"
    }

    $venvVersion = Get-CheckedPythonVersion `
        -PythonExecutable $venvPython `
        -Description "virtual-environment Python"
    Write-Info "Runtime Python: $venvVersion ($venvPython)"

    Write-Info "Installing pinned dependencies..."
    Invoke-NativeChecked `
        -FilePath $venvPython `
        -ArgumentList @("-m", "pip", "install", "--disable-pip-version-check", "-r", $requirementsPath) `
        -Operation "Installing dependencies" | Out-Null

    Write-Info "Checking dependency consistency..."
    Invoke-NativeChecked `
        -FilePath $venvPython `
        -ArgumentList @("-m", "pip", "check", "--disable-pip-version-check") `
        -Operation "Checking installed dependencies" | Out-Null

    Write-Info "Checking required imports and the canonical EBNF..."
    Invoke-NativeChecked `
        -FilePath $venvPython `
        -ArgumentList @("-c", $ImportCheckCode) `
        -Operation "Verifying the installed tools" | Out-Null

    Write-Info "Creating log folders..."
    New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot $LogsRelativePath) | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot $CapturesRelativePath) | Out-Null

    Write-Info ""
    Write-Info "Done."
    Write-Info "Installed runtime: $venvPython"
    Write-Info "Next steps:"
    Write-Info "  Topology editor: & '$venvPython' -m tools.can_topology.can_top_editor"
    Write-Info "  CAN listener:    & '$venvPython' -m tools.can_nt.can_nt_bridge --rio 172.22.11.2"
    Write-Info "  Offline check:   & '$venvPython' -m tools.can_nt.can_nt_bridge --version"
    Write-Info "  Deploy robot code via WPILib (GradleRIO)."
} catch {
    Write-Error "Install failed: $($_.Exception.Message)"
    exit $ExitFailure
}
