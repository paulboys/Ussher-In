# run_ab_v0_v2_p0041_midnight_est.ps1
# -----------------------------------
# Schedules and runs the full v0-vs-v2 A/B comparison for page p0041.
#
# Behavior:
#   0. Wait until the next 00:00:00 in America/New_York.
#   1. Run translator jobs for v0 and v2 (run01..run03), skipping existing artifacts.
#   2. Run judge pairings (v0/runNN vs v2/runNN), skipping existing outputs.
#   3. Build aggregated report.
#   4. Build spot-check file.

$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\User\Documents\UssherIn'

# ---------------------------------------------------------------------------
# 0. Wait until the next midnight in Eastern time
# ---------------------------------------------------------------------------
#$etTz = [System.TimeZoneInfo]::FindSystemTimeZoneById('Eastern Standard Time')
#$localTz = [System.TimeZoneInfo]::Local
#$nowLocal = Get-Date
#$nowEt = [System.TimeZoneInfo]::ConvertTime($nowLocal, $localTz, $etTz)
#$targetEt = $nowEt.Date.AddDays(1)
#$targetLocal = [System.TimeZoneInfo]::ConvertTime($targetEt, $etTz, $localTz)
#$waitSecs = [int][Math]::Ceiling(($targetLocal - (Get-Date)).TotalSeconds)
#
#if ($waitSecs -gt 0) {
#    Write-Host "[wait] sleeping $waitSecs sec until ET midnight ($targetEt ET / $targetLocal local)"
#    Start-Sleep -Seconds $waitSecs
#}
#Write-Host "[wake] starting at $(Get-Date -Format HH:mm:ss)"

# (Skipped — quota already reset)

# ---------------------------------------------------------------------------
# 1. Translator runs (skip if artifact already on disk)
# ---------------------------------------------------------------------------
foreach ($v in 'v0','v2') {
    foreach ($r in 'run01','run02','run03') {
        $artifact = "04_translation_work/ab/p0041/$v/$r/segments_with_translations.jsonl"
        if (Test-Path $artifact) {
            Write-Host "[trans $v/$r] already present, skipping"
            continue
        }

        Write-Host "[trans $v/$r] starting at $(Get-Date -Format HH:mm:ss)"
        python 08_working_scratch/pipeline_scripts/translate_segments.py `
            --part part1 --start-page 41 --end-page 41 `
            --prompt-version $v --run-tag $r --model claude-opus-4-7
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[trans $v/$r] FAILED exit=$LASTEXITCODE -- aborting" -ForegroundColor Red
            exit $LASTEXITCODE
        }
        Write-Host "[trans $v/$r] done at $(Get-Date -Format HH:mm:ss)"
    }
}

# ---------------------------------------------------------------------------
# 2. Judge pairings (v0/runNN vs v2/runNN)
# ---------------------------------------------------------------------------
foreach ($pair in 'run01','run02','run03') {
    $outFile = "04_translation_work/ab/p0041/judgments/$pair.jsonl"
    if (Test-Path $outFile) {
        Write-Host "[judge $pair] $outFile already exists, skipping"
        continue
    }

    Write-Host "[judge $pair] starting at $(Get-Date -Format HH:mm:ss)"
    python 08_working_scratch/phase3b/scripts/ab_judge.py `
        04_translation_work/ab/p0041/v0/$pair/segments_with_translations.jsonl `
        04_translation_work/ab/p0041/v2/$pair/segments_with_translations.jsonl `
        --output  04_translation_work/ab/p0041/judgments/$pair.jsonl `
        --summary 04_translation_work/ab/p0041/judgments/${pair}_summary.json `
        --judge-model claude-sonnet-4-6 --seed 0
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[judge $pair] FAILED exit=$LASTEXITCODE -- aborting" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "[judge $pair] done at $(Get-Date -Format HH:mm:ss)"
}

# ---------------------------------------------------------------------------
# 3. Aggregator
# ---------------------------------------------------------------------------
Write-Host "[report] starting at $(Get-Date -Format HH:mm:ss)"
python 08_working_scratch/phase3b/scripts/ab_report.py 04_translation_work/ab/p0041 --page p0041
if ($LASTEXITCODE -ne 0) {
    Write-Host "[report] FAILED" -ForegroundColor Red
    exit $LASTEXITCODE
}

# ---------------------------------------------------------------------------
# 4. Spot-check picker
# ---------------------------------------------------------------------------
Write-Host "[spot]   starting at $(Get-Date -Format HH:mm:ss)"
python 08_working_scratch/phase3b/scripts/ab_spot_check.py 04_translation_work/ab/p0041 --page p0041 --seed 0
if ($LASTEXITCODE -ne 0) {
    Write-Host "[spot] FAILED" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "[done]   finished at $(Get-Date -Format HH:mm:ss)"
