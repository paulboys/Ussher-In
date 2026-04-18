# Annotation Guideline (Phase 3b)

Purpose:
- Standardize line-level ground truth for OCR evaluation and fine-tuning.

Scope:
- Include headers, body lines, footnote lines, and body-to-footnote markers.
- Exclude translation decisions and Open-C numeral normalization.

## 5-Minute Workflow (Recommended)

1. Seed annotation files from raw OCR text.
2. Open one seeded `page_pXXXX.json` alongside the source PDF and raw text output.
3. Edit only what is wrong in `text_gold` fields.
4. Mark corrected lines as `review_status: "locked"`.
5. When the page is sufficiently reviewed, set `meta.review_status: "locked"`.
6. Run manifest update and export commands.

## Seed Command (Raw OCR -> Annotation JSON)

```powershell
& "C:\Users\User\miniforge3\envs\ussher\python.exe" "C:\Users\User\Documents\UssherIn\08_working_scratch\phase3b\scripts\seed_annotations_from_raw_ocr.py" --part part1 --source-pdf "C:\Users\User\Documents\UssherIn\00_source_pdf\JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf" --start-page 30 --end-page 35 --force
```

Use `--force` only when you intentionally want to replace existing annotation JSON.

## Unit of annotation

- Primary unit is line.
- Region values:
- `header`
- `body`
- `footnote`

## Transcription policy

- Use diplomatic transcription.
- Preserve printed capitalization and punctuation.
- Preserve historical spelling except obvious OCR noise in source extraction aids.
- Encode ligature intent as `AE/ae` in gold text.

## AE/ae policy

- If printed glyph is ligature, record as `AE/ae`.
- If uncertain between `e` and `ae`, set `uncertain_ae=true` and record rationale.

## Marker-link policy

- Capture body marker as printed.
- Capture corresponding note marker as printed.
- Record explicit link `marker_id -> footnote_id`.
- If uncertain, set `marker_uncertain=true` and note alternatives.

## Required fields per line

- `page_id`
- `region`
- `line_id`
- `text_gold`
- `contains_ae_target`
- `contains_marker`
- `marker_id`
- `marker_link_target`
- `uncertain_ae`
- `marker_uncertain`
- `reviewer`
- `review_status`
- `notes`

### Minimal fields you usually edit

- `text_gold` (fix OCR errors)
- `contains_ae_target` (true if line contains AE/ae target)
- `contains_marker` (true if line includes note marker)
- `marker_id` / `marker_link_target` (when markers can be linked)
- `review_status` (`draft` -> `reviewed` -> `locked`)

Allowed review status values:
- `draft`
- `reviewed`
- `locked`

## Review protocol

- First pass by annotator.
- Second pass on at least 20 percent random sample plus all uncertain lines.
- Track disagreements in `08_working_scratch/phase3b/manifests/review_disagreements.md`.

## Practical Example (One Line)

Before:

```json
{
	"line_id": "p0034_body_l0036",
	"text_gold": "indulget, id est, sua pracepta Christus. Quse licet ab",
	"contains_ae_target": false,
	"review_status": "draft"
}
```

After:

```json
{
	"line_id": "p0034_body_l0036",
	"text_gold": "indulget, id est, sua praecepta Christus. Quae licet ab",
	"contains_ae_target": true,
	"review_status": "locked",
	"notes": "Corrected ae ligatures against PDF"
}
```
