# Schema Specification

This document defines the minimum structured records for OCR and translation.

## Page Record (OCR)

```json
{
  "project_id": "ussher_in",
  "source_pdf": "JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf",
  "part": "part1",
  "page_num": 1,
  "page_id": "p0001",
  "ocr_engine": "kraken",
  "ocr_model": "default",
  "ocr_lang": ["lat"],
  "ocr_timestamp": "2026-04-17T00:00:00Z",
  "raw_text": "...",
  "raw_confidence_avg": 0.0,
  "raw_confidence_min": 0.0,
  "lines": [
    {
      "line_id": "p0001_l0001",
      "text": "...",
      "confidence": 0.0
    }
  ],
  "qc_status": "pending",
  "qc_notes": ""
}
```

Supported `ocr_engine` values:
- `kraken` (primary, runs via WSL on Windows)
- `tesseract` (fallback)

The `ocr_model` field records which model was used (e.g. `default`, `lat.traineddata`).
```

## Segment Record (Translation Unit)

```json
{
  "segment_id": "p0001_s0001",
  "page_id": "p0001",
  "segment_type": "body_text",
  "latin_text": "...",
  "ocr_flags": [],
  "translation_history": [
    {
      "version": 1,
      "method": "machine",
      "engine": "deepl",
      "timestamp": "2026-04-17T00:00:00Z",
      "english_text": "...",
      "notes": "initial draft"
    }
  ],
  "final_english": "",
  "translation_status": "pending"
}
```

## Controlled Values

`qc_status` values:
- `pending`
- `pass_auto`
- `pass_manual`
- `fail_reocr`
- `blocked`

`segment_type` values for first pass:
- `body_text`
- `header`
- `chapter_title`

`translation_status` values:
- `pending`
- `machine_draft`
- `post_edit_in_progress`
- `finalized`

## Traceability Rules

- Every segment must map to a single `page_id`.
- All edits must be appended in `translation_history`; do not overwrite prior entries.
- Corrections to OCR should preserve original text in `raw_text` and store corrected text in downstream files.
