param(
    [string]$BaseBranch = "dev",
    [string]$DefaultBranch = "main",
    [switch]$SkipClaude,
    [int]$MaxFixAttempts = 1
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

New-Item -ItemType Directory -Path ".agent" -Force | Out-Null

function Require-Command([string]$name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $name"
    }
}

Require-Command "git"
Require-Command "gh"
if (-not $SkipClaude) {
    Require-Command "claude"
}

$currentBranch = (git branch --show-current).Trim()
if ($currentBranch -eq $DefaultBranch) {
    throw "Refusing to run automation from '$DefaultBranch'. Switch to '$BaseBranch'."
}

if ($currentBranch -ne $BaseBranch) {
    git checkout $BaseBranch | Out-Null
}

git pull --ff-only origin $BaseBranch | Out-Null

# Find latest failed CI run on base branch
$runJsonRaw = gh run list --branch $BaseBranch --status failure --limit 1 --json databaseId,displayTitle,createdAt,workflowName
if (-not $runJsonRaw) {
    Write-Host "No failed runs found for branch '$BaseBranch'."
    exit 0
}
$runList = $runJsonRaw | ConvertFrom-Json
if (-not $runList -or $runList.Count -eq 0) {
    Write-Host "No failed runs found for branch '$BaseBranch'."
    exit 0
}
$run = $runList[0]
$runId = [string]$run.databaseId

$sessionDir = Join-Path ".agent" ("run_" + $runId)
New-Item -ItemType Directory -Path $sessionDir -Force | Out-Null
$failedLog = Join-Path $sessionDir "failed.log"
$summary = Join-Path $sessionDir "fix_summary.md"

# Pull failed logs as agent input
gh run view $runId --log-failed | Out-File -FilePath $failedLog -Encoding utf8

if (-not (Test-Path $failedLog)) {
    throw "Failed to fetch run logs for run id $runId"
}

$agentBranch = "agent/fix-run-$runId"

for ($attempt = 1; $attempt -le $MaxFixAttempts; $attempt++) {
    if (-not $SkipClaude) {
        $prompt = @"
Read .agent/run_$runId/failed.log and fix only deterministic code issues that caused CI failure.
Constraints:
- Do not modify infrastructure outside this repo.
- Do not change branch protection or workflow check names.
- Do not commit directly to main.
- Keep changes minimal and focused on failing checks.
After edits, summarize what changed in .agent/run_$runId/fix_summary.md
"@
        claude -p $prompt --dangerously-skip-permissions | Out-File -FilePath (Join-Path $sessionDir "claude_output.txt") -Encoding utf8
    }

    & "C:/Users/User/miniforge3/python.exe" -m pytest 08_working_scratch/tests -q
    & "C:/Users/User/miniforge3/python.exe" -m mypy 08_working_scratch/pipeline_scripts 08_working_scratch/phase3b/scripts --ignore-missing-imports

    if ($LASTEXITCODE -eq 0) {
        break
    }

    if ($attempt -eq $MaxFixAttempts) {
        throw "Local checks still failing after $MaxFixAttempts attempt(s)."
    }
}

$changes = git status --porcelain
if (-not $changes) {
    Write-Host "No code changes produced; exiting."
    exit 0
}

# PR-only policy: always publish on dedicated agent branch, never direct to main/dev
if ((git branch --list $agentBranch) -eq $null -or (git branch --list $agentBranch).Length -eq 0) {
    git checkout -b $agentBranch | Out-Null
} else {
    git checkout $agentBranch | Out-Null
}

git add -A
git commit -m "Agent remediation for CI run $runId"
git push -u origin $agentBranch

$prTitle = "Agent remediation: CI run $runId"
$prBody = @"
Automated remediation from failed CI run: $runId

Source workflow: $($run.workflowName)
Created at: $($run.createdAt)

See:
- .agent/run_$runId/failed.log
- .agent/run_$runId/fix_summary.md
"@

# Create PR only if one does not already exist for this branch
$existingPr = gh pr list --head $agentBranch --state open --json number
if (($existingPr | ConvertFrom-Json).Count -eq 0) {
    gh pr create --base $BaseBranch --head $agentBranch --title $prTitle --body $prBody | Out-Null
}

Write-Host "Agent loop completed for run id $runId"
