$ErrorActionPreference = 'Stop'

$taskName = 'swerve3-docs-maintenance'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runnerPath = Join-Path $scriptDir 'run_docs_maintenance.ps1'
$runnerPath = (Resolve-Path $runnerPath).Path

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $runnerPath + '"')
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 9:00AM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description 'Run the swerve3 docs maintenance pipeline weekly.' -Force | Out-Null

Write-Output ("Scheduled task registered: " + $taskName)
Write-Output "Schedule: every Sunday at 9:00 AM local time"
