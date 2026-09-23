param(
    [Parameter(Mandatory = $true)]
    [Alias("Input")]
    [string]$InputFile,
    [string]$Output,
    [string]$Title
)

$InputFile = $InputFile.Trim()
if ([string]::IsNullOrWhiteSpace($InputFile)) {
    throw "Input path is required. Example: -InputFile TESTING.md"
}

$inputPath = Resolve-Path -Path $InputFile

if (-not $Output) {
    $outDir = Split-Path -Path $inputPath -Parent
    $base = [System.IO.Path]::GetFileNameWithoutExtension($inputPath)
    $Output = Join-Path $outDir ($base + ".docx")
}

$repoRoot = Resolve-Path -Path (Join-Path $PSScriptRoot "..\\..")
$venvPython = Join-Path $repoRoot ".venv\\Scripts\\python.exe"
$pythonExe = if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    $venvPython
} else {
    "python"
}
Push-Location $repoRoot
try {
    if ($Title) {
        & $pythonExe -m tools.md_to_docx.md_to_docx --input $inputPath --output $Output --title $Title
    } else {
        & $pythonExe -m tools.md_to_docx.md_to_docx --input $inputPath --output $Output
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Markdown conversion failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
