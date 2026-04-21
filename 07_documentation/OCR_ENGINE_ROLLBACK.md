# OCR Engine Rollback Procedure

If Kraken produces inferior results or WSL becomes unavailable, switch back
to Tesseract with no code changes beyond a flag.

## Quick rollback

### Via PowerShell wrapper

```powershell
.\scripts\Invoke-KrakenOcr.ps1 -OcrEngine tesseract -PdfPath ... -Part part1 -StartPage 30 -EndPage 35
```

### Via Python pilot script

```powershell
python 08_working_scratch/pipeline_scripts/pilot_ocr.py --ocr-engine tesseract
```

## What changes

- Raw OCR output files are written to the same directory structure.
- The `ocr_engine` field in the output JSON changes from `"kraken"` to `"tesseract"`.
- Annotation seeding and ground-truth export scripts are engine-neutral and require no changes.

## What does NOT change

- Annotation JSON schema (body/footnote/header regions, line records)
- QA workflow thresholds (may need recalibration; see `QA_WORKFLOW.md`)
- Phase 3b ground-truth export pipeline

## When to rollback

- WSL environment is broken or unavailable on the machine
- Kraken confidence scores are consistently below Tesseract on pilot pages
- Kraken segmentation misses footnote boundaries that Tesseract handles

## Verification after rollback

1. Re-run pilot OCR on pages 30–35 with `--ocr-engine tesseract`.
2. Run the comparison script to confirm Tesseract output matches prior baseline.
3. Spot-check 2–3 annotation pages seeded from the new Tesseract output.
