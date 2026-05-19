$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\User\miniforge3\envs\ussher\python.exe"
$ClaudeBin = "C:\Users\User\.local\bin"
$RunDir = Join-Path $RepoRoot "04_translation_work\ab\p0032_p0035\whitaker_v4\whitaker_v4_ch2_run03"
$SchedulerLogDir = Join-Path $RunDir ".scheduler"

New-Item -ItemType Directory -Force -Path $SchedulerLogDir | Out-Null

$Stamp = Get-Date -Format "yyyyMMddTHHmmss"
$StdoutPath = Join-Path $SchedulerLogDir "run03_$Stamp.stdout.log"
$StderrPath = Join-Path $SchedulerLogDir "run03_$Stamp.stderr.log"
$SummaryPath = Join-Path $SchedulerLogDir "run03_$Stamp.summary.json"

$env:PATH = "$ClaudeBin;C:\Users\User\miniforge3\envs\ussher;C:\Users\User\miniforge3\envs\ussher\Scripts;$env:PATH"

$Args = @(
    "08_working_scratch\pipeline_scripts\translate_segments.py",
    "--part", "whitaker_latin",
    "--start-page", "32",
    "--end-page", "35",
    "--prompt-version", "whitaker_v4",
    "--run-tag", "whitaker_v4_ch2_run03"
)

Set-Location $RepoRoot

$StartedAt = Get-Date -Format "o"
$ExitCode = $null
$ErrorText = $null

try {
    $Process = Start-Process `
        -FilePath $Python `
        -ArgumentList $Args `
        -WorkingDirectory $RepoRoot `
        -RedirectStandardOutput $StdoutPath `
        -RedirectStandardError $StderrPath `
        -NoNewWindow `
        -Wait `
        -PassThru

    $ExitCode = $Process.ExitCode
} catch {
    $ExitCode = 1
    $ErrorText = $_.Exception.Message
    $ErrorText | Set-Content -Path $StderrPath -Encoding UTF8
}

$FinishedAt = Get-Date -Format "o"

[ordered]@{
    started_at = $StartedAt
    finished_at = $FinishedAt
    exit_code = $ExitCode
    repo_root = $RepoRoot
    python = $Python
    command = "$Python $($Args -join ' ')"
    stdout = $StdoutPath
    stderr = $StderrPath
    error = $ErrorText
} | ConvertTo-Json -Depth 3 | Set-Content -Path $SummaryPath -Encoding UTF8

exit $ExitCode
