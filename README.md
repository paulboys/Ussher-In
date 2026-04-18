# Ussher In

Ussher In is a two-step workflow for producing a new translation of James Ussher's *Britannicarum Ecclesiarum Antiquitates*.

Step 1: OCR Latin text from source PDFs into structured, quality-controlled records.
Step 2: Translate structured Latin records into literal/academic English with machine-first plus human post-edit.

## Project Status

- Phase 0 started: project scaffolding and documentation baseline
- OCR engine baseline: Tesseract (Latin) first
- Scope for first pass: body text first, then footnotes and marginalia

## Quick Start

1. Place source PDFs in `00_source_pdf/`.
2. Follow setup instructions in `06_tools_config/tool_installation_guide.md`.
3. Review schema in `07_documentation/SCHEMA.md`.
4. Run pilot OCR using scripts in `08_working_scratch/pipeline_scripts/`.
5. Apply quality gates from `07_documentation/QA_WORKFLOW.md` before translation.

## Key Directories

- `00_source_pdf/`: canonical source inputs
- `01_raw_ocr_output/`: raw OCR by part and page
- `02_ocr_qc/`: confidence reports and QA artifacts
- `03_segmented_text/`: cleaned and segmented Latin records
- `04_translation_work/`: translation drafts and post-edit artifacts
- `05_final_output/`: release outputs
- `06_tools_config/`: environment and OCR tool configuration
- `07_documentation/`: process and standards docs
- `08_working_scratch/`: scripts, tests, and logs
