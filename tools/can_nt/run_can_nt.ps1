$PythonExe = if ($env:CAN_NT_PYTHON) { $env:CAN_NT_PYTHON } else { "python" }
$RioHost = if ($env:BRINGUP_RIO_HOST) { $env:BRINGUP_RIO_HOST } else { "172.22.11.2" }

$repoRoot = Resolve-Path -Path (Join-Path $PSScriptRoot "..\\..")
Push-Location $repoRoot
& $PythonExe -m tools.can_nt.can_nt_bridge --rio $RioHost
Pop-Location
