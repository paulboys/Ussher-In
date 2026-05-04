# run_ab_v0_v2_p0039.ps1
# ----------------------
# Single async job for the v0-vs-v2 A/B comparison on p0039.
#
# Sleeps until the Claude Code quota resets, then runs the full pipeline
# end-to-end:
#   1. 6 translator runs (3x v0, 3x v2) with claude-opus-4-7
#      NOTE: v0 runs are reused from disk if already present.
#   2. 3 judge pairings (v0/runNN vs v2/runNN) with claude-sonnet-4-6
#   3. Aggregator (PASS/FAIL/INSUFFICIENT verdict)
#   4. Spot-check picker (5 high-swing + 5 tied segments)
#
# Each step short-circuits on $LASTEXITCODE != 0. Judge step also halts
# the foreach loop on quota refusals (ab_judge.py exits 3 via JudgeQuotaError).
#
# Output:
#   04_translation_work/ab/p0039/v2/run0{1,2,3}/segments_with_translations.jsonl
#   04_translation_work/ab/p0039/judgments/run0{1,2,3}.jsonl + _summary.json
#   04_translation_work/ab/p0039/summary.json
#   04_translation_work/ab/p0039/p0039_report.md
#   04_translation_work/ab/p0039/spot_check.md

$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\User\Documents\UssherIn'

# ---------------------------------------------------------------------------
# 0. Wait until 19:00:30 local time (quota resets at 19:00 America/New_York)
# ---------------------------------------------------------------------------
$resetTarget = Get-Date -Hour 19 -Minute 0 -Second 30 -Millisecond 0
$now = Get-Date
if ($now -lt $resetTarget) {
    $waitSecs = [int]($resetTarget - $now).TotalSeconds
    Write-Host "[wait] sleeping $waitSecs sec until quota reset at $resetTarget"
    Start-Sleep -Seconds $waitSecs
}
Write-Host "[wake] starting at $(Get-Date -Format HH:mm:ss)"

# ---------------------------------------------------------------------------
# 1. Translator runs (skip if artifact already on disk)
# ---------------------------------------------------------------------------
foreach ($v in 'v0','v2') {
    foreach ($r in 'run01','run02','run03') {
        $artifact = "04_translation_work/ab/p0039/$v/$r/segments_with_translations.jsonl"
        if (Test-Path $artifact) {
            Write-Host "[trans $v/$r] already present, skipping"
            continue
        }
        Write-Host "[trans $v/$r] starting at $(Get-Date -Format HH:mm:ss)"
        python 08_working_scratch/pipeline_scripts/translate_segments.py `
            --part part1 --start-page 39 --end-page 39 `
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
    $outFile = "04_translation_work/ab/p0039/judgments/$pair.jsonl"
    if (Test-Path $outFile) {
        Write-Host "[judge $pair] $outFile already exists, skipping"
        continue
    }
    Write-Host "[judge $pair] starting at $(Get-Date -Format HH:mm:ss)"
    python 08_working_scratch/phase3b/scripts/ab_judge.py `
        04_translation_work/ab/p0039/v0/$pair/segments_with_translations.jsonl `
        04_translation_work/ab/p0039/v2/$pair/segments_with_translations.jsonl `
        --output  04_translation_work/ab/p0039/judgments/$pair.jsonl `
        --summary 04_translation_work/ab/p0039/judgments/${pair}_summary.json `
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
python 08_working_scratch/phase3b/scripts/ab_report.py 04_translation_work/ab/p0039 --page p0039
if ($LASTEXITCODE -ne 0) { Write-Host "[report] FAILED" -ForegroundColor Red; exit $LASTEXITCODE }

# ---------------------------------------------------------------------------
# 4. Spot-check picker
# ---------------------------------------------------------------------------
Write-Host "[spot]   starting at $(Get-Date -Format HH:mm:ss)"
python 08_working_scratch/phase3b/scripts/ab_spot_check.py 04_translation_work/ab/p0039 --page p0039 --seed 0
if ($LASTEXITCODE -ne 0) { Write-Host "[spot] FAILED" -ForegroundColor Red; exit $LASTEXITCODE }

Write-Host "[done]   finished at $(Get-Date -Format HH:mm:ss)"
