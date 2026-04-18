param(
    [string]$TaskName = "UssherIn Agent Loop",
    [int]$IntervalMinutes = 60
)

$ErrorActionPreference = "Stop"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    throw "Run this script as Administrator to register a scheduled task."
}

$workspace = Split-Path -Parent $PSScriptRoot
$runBat = Join-Path $workspace "scripts\run_agent_loop.bat"
if (-not (Test-Path $runBat)) {
    throw "Missing script: $runBat"
}

$action = New-ScheduledTaskAction -Execute $runBat -WorkingDirectory $workspace
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
$trigger.RepetitionInterval = "PT$($IntervalMinutes)M"
$trigger.RepetitionDuration = "P1D"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host "Task registered: $TaskName"
Write-Host "Action: $runBat"
Write-Host "Repeat interval: $IntervalMinutes minute(s)"
