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
  "ocr_engine": "gemini",
  "ocr_model": "gemini-3.1-pro-preview",
  "ocr_lang": ["lat", "grc"],
  "ocr_timestamp": "2026-04-17T00:00:00Z",
  "raw_text": "...",
  "raw_confidence_avg": 0.0,
  "raw_confidence_min": 0.0,
  "page_summary": "short note about layout anomalies, if any",
  "lines": [
    {
      "alignment_index": 0,
      "region": "body",
      "line_index": 0,
      "line_id": "p0001_body_l0001",
      "text_raw_ocr": "Eccleſiarum",
      "normalized_form": "Ecclesiarum",
      "text_gold": "Ecclesiarum",
      "confidence": 0.91,
      "illegible": false,
      "marker_id": "",
      "marginalia_anchor_index": null
    }
  ],
  "qc_status": "pending",
  "qc_notes": ""
}
```

Supported `ocr_engine` values:
- `gemini` (primary; uses Gemini 3.1 Pro via the unified provider config)
- `tesseract` (legacy fallback during migration)
- `kraken` (legacy fallback; runs via WSL on Windows)

`ocr_model` records the exact model identifier (e.g. `gemini-3.1-pro-preview`,
`lat.traineddata`). For Gemini, configuration is sourced from
`06_tools_config/providers.json` plus `USSHERIN_PROVIDERS_*` env overrides.

### Per-line dual-text fields

Lines emitted by the Gemini path carry both raw and normalized text so
research consumers can audit OCR fidelity:

- `text_raw_ocr` — verbatim model output (preserves long-s, ligatures,
  polytonic Greek, historical numerals).
- `normalized_form` — post-normalization form used as the gold seed.
- `alignment_index` — original ordering in the model response.
- `region` — one of `header`, `body`, `footnote`, `marginalia`,
  `catchword` (marginalia and catchword are read by the Go verification
  layer; they fold into `body` during annotation seeding).
- `confidence` — model self-assessed accuracy in `[0.0, 1.0]`.
- `marginalia_anchor_index` — body line index a marginalia entry anchors
  to (`null` for non-marginalia lines).

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

## Translation Artifacts (Phase 5 output)

Machine drafts produced by `08_working_scratch/pipeline_scripts/translate_segments.py`
are written to `03_segmented_text/<part>/segments_with_translations.jsonl`
(one JSON object per line, keyed by `segment_id`). Each record uses the
Segment Record shape above with these conventions:

- `segment_id` — `seg_<line_id>` for body lines, `seg_<footnote_id>` for footnotes.
- `segment_type` — `body` or `footnote`.
- `latin_text` — `text_gold` from the Phase 3b annotation (falls back to `text_ocr_original`).
- Footnote records additionally carry `body_segment_id` and `marker_id` so the
  body→footnote anchor relationship survives outside the annotation file.
- `translation_history[]` entries include:
  - `version` (1, 2, ... append-only)
  - `stage` (`machine_draft`)
  - `timestamp` (UTC ISO-8601)
  - `english`, `notes`, `uncertain` (from the model)
  - `model` (e.g. `claude-opus-4-6`)
  - `lexicon_profile` (`auto` | `latin_only` | `latin_greek` | `minimal`)
  - `source_unit_id` (the `line_id` or `footnote_id` keyed in the prompt)
- Run logs are written to `03_segmented_text/<part>/.logs/translation_run_<timestamp>.json`.

Gating policy (enforced by the runner):
- Body lines: only `review_status == locked` are sent to translation.
- Footnotes: any footnote whose `body_line_id` references an included body
  line is sent regardless of footnote review_status.

## Traceability Rules

- Every segment must map to a single `page_id`.
- All edits must be appended in `translation_history`; do not overwrite prior entries.
- Corrections to OCR should preserve original text in `raw_text` and store corrected text in downstream files.
