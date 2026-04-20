<#
.SYNOPSIS
    Run Kraken OCR on a PDF page range via WSL from Windows.

.DESCRIPTION
    Converts Windows paths to WSL-compatible /mnt/ paths, invokes the
    Kraken OCR pilot script inside WSL, and writes output to the project
    raw OCR output directory.

.PARAMETER PdfPath
    Relative or absolute path to the source PDF on Windows.

.PARAMETER Part
    Part label (part1 or part2).

.PARAMETER StartPage
    First page number to OCR.

.PARAMETER EndPage
    Last page number to OCR.

.PARAMETER OutputRoot
    Output root directory (default: 01_raw_ocr_output).

.PARAMETER KrakenModel
    Kraken model name or path (default: default).

.PARAMETER OcrEngine
    OCR engine to use: kraken or tesseract (default: kraken).

.EXAMPLE
    .\scripts\Invoke-KrakenOcr.ps1 -PdfPath "00_source_pdf\JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf" -Part part1 -StartPage 30 -EndPage 35
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$PdfPath,

    [Parameter(Mandatory = $true)]
    [ValidateSet("part1", "part2")]
    [string]$Part,

    [Parameter(Mandatory = $true)]
    [int]$StartPage,

    [Parameter(Mandatory = $true)]
    [int]$EndPage,

    [string]$OutputRoot = "01_raw_ocr_output",

    [string]$KrakenModel = "default",

    [ValidateSet("kraken", "tesseract")]
    [string]$OcrEngine = "kraken"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function ConvertTo-WslPath {
    param([string]$WindowsPath)
    $resolved = (Resolve-Path $WindowsPath -ErrorAction Stop).Path
    if ($resolved -match '^([A-Za-z]):\\(.*)$') {
        $drive = $Matches[1].ToLower()
        $rest = $Matches[2] -replace '\\', '/'
        return "/mnt/$drive/$rest"
    }
    throw "Cannot convert path to WSL format: $resolved"
}

# Resolve paths
$AbsPdf = if ([System.IO.Path]::IsPathRooted($PdfPath)) {
    $PdfPath
} else {
    Join-Path $ProjectRoot $PdfPath
}

$AbsOutput = if ([System.IO.Path]::IsPathRooted($OutputRoot)) {
    $OutputRoot
} else {
    Join-Path $ProjectRoot $OutputRoot
}

$WslPdf = ConvertTo-WslPath $AbsPdf
$WslOutput = ConvertTo-WslPath $AbsOutput
$WslProject = ConvertTo-WslPath $ProjectRoot

Write-Host "OCR Engine  : $OcrEngine" -ForegroundColor Cyan
Write-Host "PDF         : $WslPdf" -ForegroundColor Cyan
Write-Host "Pages       : $StartPage - $EndPage" -ForegroundColor Cyan
Write-Host "Output      : $WslOutput" -ForegroundColor Cyan

if ($OcrEngine -eq "kraken") {
    # Verify WSL is available
    $wslCheck = wsl --list --quiet 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "WSL is not available. Please install WSL2 and Ubuntu first. See 06_tools_config/wsl_kraken_setup.md"
    }

    $WslScript = "$WslProject/08_working_scratch/pipeline_scripts/kraken_ocr_runner.py"

    Write-Host "Running Kraken OCR via WSL..." -ForegroundColor Green
    wsl -- bash -c "source ~/kraken-env/bin/activate && python3 '$WslScript' --pdf '$WslPdf' --part '$Part' --start-page $StartPage --end-page $EndPage --output-root '$WslOutput' --model '$KrakenModel'"

    if ($LASTEXITCODE -ne 0) {
        throw "Kraken OCR failed with exit code $LASTEXITCODE"
    }
} else {
    # Tesseract fallback (runs natively on Windows)
    $PilotScript = Join-Path $ProjectRoot "08_working_scratch\pipeline_scripts\pilot_ocr.py"
    $PythonExe = "C:\Users\User\miniforge3\envs\ussher\python.exe"

    Write-Host "Running Tesseract OCR (fallback)..." -ForegroundColor Yellow
    & $PythonExe $PilotScript --pdf $AbsPdf --part $Part --start-page $StartPage --end-page $EndPage --output-root $AbsOutput --split-footnotes --normalize-ae

    if ($LASTEXITCODE -ne 0) {
        throw "Tesseract OCR failed with exit code $LASTEXITCODE"
    }
}

Write-Host "OCR complete. Output at: $AbsOutput\$Part" -ForegroundColor Green
