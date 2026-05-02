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
      "seq": 1,
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
- `seq` — 1-based dense integer giving the **reading order within the
  region** (`header`, `body`, `footnotes`, `marginalia`, `catchwords`).
  This is the **ordering authority** for translation and rendering.
  `line_id` remains an immutable identifier and is not parsed for
  order. When a user drags a line in the annotation UI, `seq` is
  re-stamped to match the new array order; `line_id` is unchanged.
  Footnote `seq` follows the renumbering performed by
  `renumberFootnotes()` (anchor-sorted), so footnote `seq` and
  `marker_number` will typically be equal but are conceptually
  distinct (one is pipeline order, one is the printed numeral).

## Segment Record (Translation Unit)

```json
{
  "segment_id": "p0001_s0001",
  "page_id": "p0001",
  "segment_type": "body_text",
  "seq": 1,
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
- `seq` — 1-based dense integer carried through from the source line's
  `seq` (body) or footnote's `seq` (footnote). This is the ordering
  key consumed by `polish_translations.py` and `render_interlinear.py`.
  `segment_id` is identity only and is not parsed for order.
- `latin_text` — `text_gold` from the Phase 3b annotation (falls back to `text_ocr_original`).
  Body lines additionally have `^<marker_id>` caret sentinels spliced in
  at each marker's `char_offset` so the artifact is self-describing
  (e.g. `Hinc Arnobius^y “ Tam velociter…`). The caret character is
  reserved for this sentinel and never appears in source text.
- `markers` — body segments carry a list of structured marker
  cross-references (empty for footnote segments and for body lines
  without footnote anchors):
  ```json
  [
    {
      "marker_id": "y",
      "char_offset": 13,
      "footnote_segment_id": "seg_p0036_fn_001"
    }
  ]
  ```
- Footnote records additionally carry `body_segment_id` and `marker_id` so the
  body→footnote anchor relationship survives outside the annotation file.
- `translation_history[]` entries include:
  - `version` (1, 2, ... append-only)
  - `stage` (`machine_draft`)
  - `timestamp` (UTC ISO-8601)
  - `english`, `notes`, `uncertain` (from the model). For body
    segments, `english` mirrors the body line's `^<marker_id>` caret
    sentinels at the position that corresponds idiomatically to the
    same anchor in English word order, so both languages can be
    rendered with footnote superscripts at matching points. Footnote
    `english` values never contain caret sentinels.
  - `model` (e.g. `claude-opus-4-6`)
  - `lexicon_profile` (`auto` | `latin_only` | `latin_greek` | `minimal`)
  - `source_unit_id` (the `line_id` or `footnote_id` keyed in the prompt)
- Run logs are written to `03_segmented_text/<part>/.logs/translation_run_<timestamp>.json`.

Gating policy (enforced by the runner):
- Body lines: only `review_status == locked` are sent to translation.
- Footnotes: any footnote whose `body_line_id` references an included body
  line is sent regardless of footnote review_status.

## Polished Translations (Phase 5b output)

A second pass driven by `08_working_scratch/pipeline_scripts/polish_translations.py`
rewrites each page's literal `machine_draft` body lines as a single
flowing-prose narrative suited for reading. The polished output is
persisted as a per-page artifact at
`03_segmented_text/<part>/polished/<page_id>.json` with the following
shape:

```json
{
  "page_id": "p0036",
  "stage": "polished",
  "version": 1,
  "timestamp": "2026-05-01T16:00:00Z",
  "model": "claude-opus-4-6",
  "lexicon_profile": "auto",
  "source_versions": {
    "seg_p0036_body_l0001": 4,
    "seg_p0036_body_l0002": 4
  },
  "english": "Hence Arnobius^y declared that the gospel ran swiftly…",
  "warnings": []
}
```

Conventions:
- The polished pass is page-scoped: one artifact per `page_id`. Body
  lines and their footnote markers are joined into continuous prose;
  paragraph breaks reflect sense, not OCR line breaks.
- Footnote-anchor sentinels (`^X`) are preserved exactly once each at
  the idiomatic English position. The renderer turns these into
  footnote-linked superscripts in the same way as for `machine_draft`
  body lines.
- The polished pass does NOT overwrite `translation_history` on any
  segment; it is a separate, page-level artifact.
- Footnotes themselves are not polished; they remain at
  `machine_draft` and are rendered from the segment artifact.
- `source_versions` records which `translation_history.version` of
  each body segment was the input to this polish run, so a polished
  artifact can be invalidated when the underlying literal pass
  advances.
- `--force` re-runs increment `version` (1 → 2 → …); the artifact
  file is overwritten in place.
- Run logs are written to `03_segmented_text/<part>/.logs/polish_run_<timestamp>.json`.

The final renderer (`render_interlinear.py`) emits one combined file
per page in `05_final_output/<part>/p<NNNN>_interlinear.{md,html}`
with up to two sections: `## Interlinear` (paired Latin/literal
English lines plus the footnote block) and `## Reading` (the polished
prose, when the polished artifact is present). Footnote anchors in
both sections link to the same in-page footnote targets; only the
Latin line carries the `id="fnref-..."` backref attribute, so the
HTML stays valid (no duplicate ids).

## Traceability Rules

- Every segment must map to a single `page_id`.
- All edits must be appended in `translation_history`; do not overwrite prior entries.
- Corrections to OCR should preserve original text in `raw_text` and store corrected text in downstream files.
