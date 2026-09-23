param(
    [string]$Python = "python",
    [switch]$InstallDeps,
    [switch]$StageGenerated
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$VenvPythonRelativePath = ".venv\Scripts\python.exe"
$InstallerRelativePath = "install_windows.ps1"
$GeneratedPaths = @(
    "tools\can_nt\bridge_cli_ebnf.txt",
    "tools\can_nt\bridge_cli_grammar_meta.json",
    "tools\can_nt\bridge_cli_grammar_gen.py",
    "tools\can_nt\bridge_cli_constants_gen.py",
    "tools\can_nt\gen_bridge_cli_parser.py"
)
$CompilePaths = @(
    "tools\can_nt\bridge_cli_parser.py",
    "tools\can_nt\bridge_cli_ast.py",
    "tools\can_nt\bridge_cli_constants_gen.py",
    "tools\can_nt\bridge_cli_grammar_gen.py",
    "tools\can_nt\gen_bridge_cli_parser.py"
)

function Invoke-NativeChecked {
    <#
    .SYNOPSIS
    Runs a native process and fails when it returns a nonzero exit code.
    #>
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$Operation
    )

    & $FilePath @ArgumentList
    $nativeExitCode = $LASTEXITCODE
    if ($nativeExitCode -ne 0) {
        throw "$Operation failed with exit code $nativeExitCode."
    }
}

$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$venvPython = Join-Path $repoRoot $VenvPythonRelativePath
$installerPath = Join-Path $repoRoot $InstallerRelativePath
Set-Location $repoRoot

Write-Host "== Regenerate Bridge CLI Parser =="
Write-Host "Repo: $repoRoot"

if ($InstallDeps) {
    Write-Host "Installing Python dependencies..."
    Invoke-NativeChecked `
        -FilePath "powershell.exe" `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", $installerPath,
            "-Python", $Python
        ) `
        -Operation "Installing dependencies"
    $selectedPython = $venvPython
} elseif ($env:CAN_NT_PYTHON) {
    $selectedPython = $env:CAN_NT_PYTHON
} elseif (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    $selectedPython = $venvPython
} else {
    $selectedPython = $Python
}

Write-Host "Using Python: $selectedPython"
Invoke-NativeChecked `
    -FilePath $selectedPython `
    -ArgumentList @("--version") `
    -Operation "Checking Python"

Write-Host "Generating grammar and constants..."
Invoke-NativeChecked `
    -FilePath $selectedPython `
    -ArgumentList @("tools\can_nt\gen_bridge_cli_parser.py") `
    -Operation "Generating the CLI parser artifacts"

Write-Host "Compiling Python sources..."
Invoke-NativeChecked `
    -FilePath $selectedPython `
    -ArgumentList (@("-m", "py_compile") + $CompilePaths) `
    -Operation "Compiling generated Python sources"

if ($StageGenerated) {
    Write-Host "Staging generated outputs..."
    Invoke-NativeChecked `
        -FilePath "git" `
        -ArgumentList (@("add") + $GeneratedPaths) `
        -Operation "Staging generated outputs"
}

Write-Host "Done."
