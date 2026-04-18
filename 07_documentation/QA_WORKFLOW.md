# OCR QA Workflow

This workflow is the gate between OCR and translation.

## Automated Screening

Run automated checks after each OCR batch:
- Flag pages where `raw_confidence_avg < 0.80`.
- Flag lines where `confidence < 0.50`.
- Flag suspicious tokens (repeated punctuation, long numeric noise, isolated single letters).

Severity bands:
- Red: `raw_confidence_avg < 0.75` or repeated anomalies
- Yellow: `0.75 <= raw_confidence_avg < 0.85`
- Green: `raw_confidence_avg >= 0.85` and no structural anomalies

## Manual Review

Minimum review set:
- 100 percent of Red pages
- At least 10 percent sample of Yellow pages

Manual checklist:
- Latin words are legible and not obviously garbled
- Line joins are corrected where OCR split words
- Chapter and section boundaries are preserved
- Body text has no unresolved critical tokens

## Translation Gate

Body text may proceed to translation only when:
- No unresolved Red pages remain in scope
- All reviewed pages have `qc_status` set
- Known OCR limitations are documented in `qc_notes`

## Output Artifacts

- `02_ocr_qc/ocr_confidence_report.json`
- `02_ocr_qc/qa_checklist.csv`
- `02_ocr_qc/problematic_pages/` (annotated references)
