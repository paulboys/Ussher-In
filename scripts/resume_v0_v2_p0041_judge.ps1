# resume_v0_v2_p0041_judge.ps1
# ----------------------------
# Finishes the v0-vs-v2 A/B judge pipeline on p0041 under the new
# 6-rubric design. The first judge pass (run01) was completed under
# the new rubric; this script picks up at run02 and run03, then
# rebuilds the aggregator and spot-check.
#
# Idempotent: each judge step skips if its output JSONL already
# exists, so re-running after a partial completion is safe.
#
# Quota: judge calls go through claude-sonnet-4-6 via the Claude
# Code CLI. The CLI exits 3 (JudgeQuotaError) on quota refusal;
# the script aborts in that case so you do not waste the rest of
# the runs trying to call a refused endpoint. Re-run after the
# quota window resets.
#
# Output (under 04_translation_work/ab/p0041/):
#   judgments/run02.jsonl + run02_summary.json
#   judgments/run03.jsonl + run03_summary.json
#   summary.json
#   p0041_report.md
#   spot_check.md

$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\User\Documents\UssherIn'

# ---------------------------------------------------------------------------
# 1. Judge pairings (v0/runNN vs v2/runNN), skip if already on disk
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
# 2. Aggregator
# ---------------------------------------------------------------------------
Write-Host "[report] starting at $(Get-Date -Format HH:mm:ss)"
python 08_working_scratch/phase3b/scripts/ab_report.py 04_translation_work/ab/p0041 --page p0041
if ($LASTEXITCODE -ne 0) { Write-Host "[report] FAILED" -ForegroundColor Red; exit $LASTEXITCODE }

# ---------------------------------------------------------------------------
# 3. Spot-check picker
# ---------------------------------------------------------------------------
Write-Host "[spot]   starting at $(Get-Date -Format HH:mm:ss)"
python 08_working_scratch/phase3b/scripts/ab_spot_check.py 04_translation_work/ab/p0041 --page p0041 --seed 0
if ($LASTEXITCODE -ne 0) { Write-Host "[spot] FAILED" -ForegroundColor Red; exit $LASTEXITCODE }

Write-Host "[done]   finished at $(Get-Date -Format HH:mm:ss)"
