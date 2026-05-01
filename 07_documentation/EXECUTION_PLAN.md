# Execution Plan

## Phase 0 (Now)

- Create project scaffold
- Define schema and QA gate
- Prepare OCR scripts and tool config templates

## Phase 1 (Pilot OCR)

- Run pilot OCR on 10 to 20 body-text pages from each part
- Measure confidence and tune preprocessing thresholds
- Confirm go/no-go criteria for full OCR run

## Phase 2 (Full OCR Body Text)

- Process all body pages for Part 1 and Part 2
- Save raw outputs and confidence metrics
- Run automated screening and manual QA

## Phase 3 (Segmentation)

- Convert cleaned OCR into translation units
- Preserve source page mapping and identifiers

## Phase 4 (English Reference Benchmark Set)

- OCR and structure the existing English translation PDF/images into aligned English records
- Build an initial Latin-English benchmark set where the English witness exists
- Use this benchmark set to score machine translation output with BLEU, COMET, and related metrics
- Preserve page and segment alignment so benchmark pairs can be reused for later model training or selection

## Phase 5 (Translation)

- Generate machine drafts via the Claude Code CLI adapter
  (`08_working_scratch/pipeline_scripts/translate_segments.py`,
  `translation_adapters.py`, `translation_prompts.py`).
- Prompts include era-specific lexicon hints: 17th-century Latin
  (Forcellini + Du Cange, with Lewis & Short fallback) and Patristic
  Greek (Lampe, with Sophocles + LSJ fallback). The Greek block is
  emitted automatically when Greek script is present in a batch
  (`auto` profile) or forced via `--lexicon-profile latin_greek`.
- Body lines and linked footnotes are translated together in one
  whole-page request; outputs are persisted as append-only
  `translation_history` entries under
  `03_segmented_text/<part>/segments_with_translations.jsonl`.
- Score machine drafts against the English benchmark set where aligned reference text exists
- Human post-edit to literal/academic register
- Track provenance in translation history

## Phase 6 (Deliverables)

- Produce bilingual reading files as primary output
- Store structured assets for reproducibility

## Expansion Phase

- Add footnotes and marginalia using same QA and translation standards
