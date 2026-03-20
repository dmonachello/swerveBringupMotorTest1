param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

if ($Args.Count -ge 2 -and $Args[0] -ieq "journal" -and $Args[1] -ieq "note") {
    $text = ($Args[2..($Args.Count - 1)] -join " ").Trim()
    if (-not $text) {
        $text = Read-Host "Note text"
    }
    if (-not $text) {
        Write-Error "Note text is required."
        exit 2
    }
    python tools\add_journal_note.py --text $text
    exit $LASTEXITCODE
}

if ($Args.Count -ge 1 -and $Args[0] -ieq "tbd") {
    $text = ($Args[1..($Args.Count - 1)] -join " ").Trim()
    if (-not $text) {
        $text = Read-Host "TBD note text"
    }
    if (-not $text) {
        Write-Error "TBD note text is required."
        exit 2
    }
    python tools\add_tbd_note.py --text $text
    exit $LASTEXITCODE
}

Write-Host "Usage:"
Write-Host "  add journal note \"your text here\""
Write-Host "  add journal note"
Write-Host "  add tbd \"your text here\""
exit 2
