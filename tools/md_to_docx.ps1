param(
    [Parameter(Mandatory = $true)]
    [string]$Input,
    [string]$Output,
    [string]$Title
)

$inputPath = Resolve-Path -Path $Input

if (-not $Output) {
    $outDir = Split-Path -Path $inputPath -Parent
    $base = [System.IO.Path]::GetFileNameWithoutExtension($inputPath)
    $Output = Join-Path $outDir ($base + ".docx")
}

python tools\\md_to_docx.py --input $inputPath --output $Output $(if ($Title) { \"--title `\"$Title`\"\" })
