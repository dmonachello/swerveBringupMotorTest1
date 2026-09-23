Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$DefaultRioHost = "172.22.11.2"
$VenvPythonRelativePath = ".venv\Scripts\python.exe"
$repoRoot = (Resolve-Path -Path (Join-Path $PSScriptRoot "..\..")).Path
$venvPython = Join-Path $repoRoot $VenvPythonRelativePath
$PythonExe = if ($env:CAN_NT_PYTHON) {
    $env:CAN_NT_PYTHON
} elseif (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    $venvPython
} else {
    "python"
}
$RioHost = if ($env:BRINGUP_RIO_HOST) { $env:BRINGUP_RIO_HOST } else { $DefaultRioHost }

Write-Host "Using Python: $PythonExe"
Push-Location $repoRoot
try {
    & $PythonExe -m tools.can_nt.can_nt_bridge --rio $RioHost @args
    $nativeExitCode = $LASTEXITCODE
    if ($nativeExitCode -ne 0) {
        exit $nativeExitCode
    }
} finally {
    Pop-Location
}
