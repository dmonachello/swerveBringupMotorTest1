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
Push-Location $repoRoot
if ($Title) {
    python -m tools.md_to_docx.md_to_docx --input $inputPath --output $Output --title $Title
} else {
    python -m tools.md_to_docx.md_to_docx --input $inputPath --output $Output
}
Pop-Location
