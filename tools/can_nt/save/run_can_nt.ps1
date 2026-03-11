$PythonExe = "C:\Users\dmona\AppData\Local\Programs\Python\Python312\python.exe"

$repoRoot = Resolve-Path -Path (Join-Path $PSScriptRoot "..\\..\\..")
Push-Location $repoRoot
& $PythonExe -m tools.can_nt.can_nt_bridge --rio 172.22.11.2
Pop-Location
