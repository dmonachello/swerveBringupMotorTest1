param(
    [string]$Python = "python",
    [switch]$InstallDeps,
    [switch]$StageGenerated
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

$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $repoRoot

Write-Info "== Regenerate Bridge CLI Parser =="
Write-Info "Repo: $repoRoot"

Ensure-Command $Python "ERROR: Python not found. Install Python 3.10+ and ensure it is on PATH, or pass -Python <path>."

if ($InstallDeps) {
    Write-Info "Installing Python dependencies..."
    & $Python .\install_windows.ps1
}

Write-Info "Generating grammar and constants..."
& $Python tools\can_nt\gen_bridge_cli_parser.py

Write-Info "Compiling Python sources..."
& $Python -m py_compile `
    tools\can_nt\bridge_cli_parser.py `
    tools\can_nt\bridge_cli_ast.py `
    tools\can_nt\bridge_cli_constants_gen.py `
    tools\can_nt\bridge_cli_grammar_gen.py `
    tools\can_nt\gen_bridge_cli_parser.py

if ($StageGenerated) {
    Write-Info "Staging generated outputs..."
    git add `
        tools\can_nt\bridge_cli_ebnf.txt `
        tools\can_nt\bridge_cli_grammar_meta.json `
        tools\can_nt\bridge_cli_grammar_gen.py `
        tools\can_nt\bridge_cli_constants_gen.py `
        tools\can_nt\gen_bridge_cli_parser.py
}

Write-Info "Done."
