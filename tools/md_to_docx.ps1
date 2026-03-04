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

if ($Title) {
    python tools\md_to_docx.py --input $inputPath --output $Output --title $Title
} else {
    python tools\md_to_docx.py --input $inputPath --output $Output
}
