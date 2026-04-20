# Phase 3b Implementation (Layout + Fine-Tuning)

This document implements Phase 3b for the remaining OCR issues.

Active scope:
- AE/ae fidelity
- Footnote marker detection and body-to-footnote linking

Resolved and out of active scope:
- Open-C numerals

## Directory layout

- `08_working_scratch/phase3b/annotations/`
- `08_working_scratch/phase3b/manifests/`
- `08_working_scratch/phase3b/ground_truth/`
- `08_working_scratch/phase3b/eval/`
- `08_working_scratch/phase3b/scripts/`

## Implementation sequence

1. Build the gold set page list in `manifests/gold_set_manifest.csv`.
2. Seed annotation files from raw OCR with `scripts/seed_annotations_from_raw_ocr.py`.
3. Annotate lines and marker links using `annotations/page_XXXX.json`.
4. Run manifest build checks using `scripts/build_manifest.py`.
5. Export line-level ground truth files to `ground_truth/`.
6. Run evaluation and record metrics in `eval/`.

## User-Friendly Daily Loop

1. Run OCR for selected pages (Kraken via WSL by default, Tesseract as fallback).
2. Seed annotation JSON from OCR text.
3. Open PDF + raw text + page JSON side-by-side.
4. Correct `text_gold` only where OCR is wrong.
5. Lock corrected lines.
6. Rebuild manifest.
7. Export locked lines to training files.

## Promotion gate (must all pass)

- AE/ae target CER improves by at least 25 percent vs baseline.
- Footnote marker-link accuracy is at least 95 percent.
- Non-target baseline CER regression is no more than 2 percent.

## Commands

### Run OCR (Kraken via WSL — recommended)

```powershell
.\scripts\Invoke-KrakenOcr.ps1 -PdfPath "00_source_pdf\JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf" -Part part1 -StartPage 30 -EndPage 35
```

### Run OCR (Tesseract fallback)

```powershell
.\scripts\Invoke-KrakenOcr.ps1 -PdfPath "00_source_pdf\JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf" -Part part1 -StartPage 30 -EndPage 35 -OcrEngine tesseract
```

### Compare engines on the same pages

```powershell
& "C:\Users\User\miniforge3\envs\ussher\python.exe" "C:\Users\User\Documents\UssherIn\08_working_scratch\pipeline_scripts\compare_ocr_engines.py" --kraken-json 01_raw_ocr_output/part1/part1_pilot_ocr_kraken.json --tesseract-json 01_raw_ocr_output/part1/part1_pilot_ocr.json
```

### Initialize annotation skeletons for a page range

```powershell
& "C:\Users\User\miniforge3\envs\ussher\python.exe" "C:\Users\User\Documents\UssherIn\08_working_scratch\phase3b\scripts\init_gold_annotations.py" --part part1 --source-pdf "C:\Users\User\Documents\UssherIn\00_source_pdf\JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf" --start-page 30 --end-page 35
```

### Seed annotation JSON directly from raw OCR output (recommended)

```powershell
& "C:\Users\User\miniforge3\envs\ussher\python.exe" "C:\Users\User\Documents\UssherIn\08_working_scratch\phase3b\scripts\seed_annotations_from_raw_ocr.py" --part part1 --source-pdf "C:\Users\User\Documents\UssherIn\00_source_pdf\JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf" --start-page 30 --end-page 35 --force
```

### Build/update manifest from annotation JSON files

```powershell
& "C:\Users\User\miniforge3\envs\ussher\python.exe" "C:\Users\User\Documents\UssherIn\08_working_scratch\phase3b\scripts\build_manifest.py"
```

### Export locked annotations into line-level ground-truth files

```powershell
& "C:\Users\User\miniforge3\envs\ussher\python.exe" "C:\Users\User\Documents\UssherIn\08_working_scratch\phase3b\scripts\export_tesseract_ground_truth.py"
```

Optional mode: include non-locked pages but export only line-level entries marked `review_status=locked`:

```powershell
& "C:\Users\User\miniforge3\envs\ussher\python.exe" "C:\Users\User\Documents\UssherIn\08_working_scratch\phase3b\scripts\export_tesseract_ground_truth.py" --include-line-level-locked
```

### Rollback to Tesseract

To revert OCR to Tesseract, pass `--ocr-engine tesseract` to the wrapper or pilot script.
All annotation and export infrastructure remains engine-neutral.
