<p align="center">
  <img src="Ussher_In_logo_v2.png" alt="Ussher In" width="300"/>
</p>

# Ussher In

**The first English translation of James Ussher's *Britannicarum Ecclesiarum Antiquitates* (1639).**

Ussher's *Britannicarum Ecclesiarum Antiquitates* (1639) has never been translated into English in its entirety. One chapter—the second, on Glastonbury traditions—was translated by H. Kendra Baker, but the remaining sixteen chapters remain accessible only in Latin. 

As a foundational history of the early British and Irish churches—their origins, monasticism, and ties to the wider Christian world—this has left the full body of Ussher's scholarship out of reach for English readers. This project aims to change that.

## Background

This project was born from two historical questions I have been asking for years:
1.  How significant was James Ussher's influence on the Westminster Assembly, given the deep parallels between his earlier works and their famous Confession and Catechisms?
2.  How did St. Basil's monastic rule travel from 4th-century Cappadocia to the Celtic monasteries of Ireland and Scotland?

This second line of inquiry led to one, untranslated primary source: Ussher's *Antiquitates*. This work documents the history of the early insular church, its key figures like Columba, and its connections to the wider Christian world.

As a data scientist unable to read Latin, the only way to answer these questions was to build the tools to make the book accessible. This repository is the result—a data-driven attempt to produce the first English translation through a combination of OCR, machine learning, and careful human review.

## How It Works

The pipeline has three linked stages:

1. **OCR** — Extract structured Latin text from photocopied book PDFs using a fine-tuned OCR model designed for this source material. The goal is a stable model that does not need continuous manual updating. Each page is segmented into body, footnotes, and marginalia, then quality-checked.
2. **Reference English** — OCR and structure the existing English translation PDF/images into aligned English text where that witness is available. This serves as an initial gold-standard benchmark for evaluating machine translation from Latin to English.
3. **Translation** — Translate the structured Latin into literal, academic-register English using machine translation with human post-editing. Where aligned English reference text exists, machine output can be scored with BLEU, COMET, or similar metrics, and those aligned pairs may later inform model training or selection. The output remains bilingual Latin-English reading documents.

### Fine-Tuning for Historical Print

The source material is a 19th-century edition with ligatures (æ/Æ), footnote markers, and archaic numeral forms that stock OCR models misread. Rather than patching errors with regex, the project builds a carefully annotated gold set (15–25 representative pages) using a custom annotation pipeline with seeding, review, and ground-truth export scripts. This training data is used to fine-tune an OCR model so the pipeline remains accurate without constant reconfiguration.

## Project Status

| Phase | Status |
|---|---|
| Project scaffold & docs | ✅ Complete |
| Environment setup & pilot OCR (pages 30–35) | ✅ Complete |
| OCR model fine-tuning workflow | ✅ Built, validation in progress |
| Annotation pipeline for fine-tuning | ✅ Built, annotation in progress |
| English reference benchmark set | ⬜ Pending ingestion/OCR/alignment |
| LSTM fine-tuning | ⬜ Pending gold-set completion |
| Full OCR run (~800 pages) | ⬜ Pending |
| Translation | ⬜ Pending |

## Quick Start

1. Place source PDFs in `00_source_pdf/`.
2. Follow setup instructions in `06_tools_config/tool_installation_guide.md`.
3. Review the schema in `07_documentation/SCHEMA.md`.
4. Run pilot OCR using scripts in `08_working_scratch/pipeline_scripts/`.
5. Apply quality gates from `07_documentation/QA_WORKFLOW.md` before translation.

## Repository Structure

| Directory | Contents |
|---|---|
| `00_source_pdf/` | Canonical source PDFs (git-ignored) |
| `01_raw_ocr_output/` | Raw OCR output by part and page |
| `02_ocr_qc/` | Confidence reports and QA artifacts |
| `03_segmented_text/` | Cleaned and segmented Latin records |
| `04_translation_work/` | Translation drafts and post-edit work |
| `05_final_output/` | Release-ready bilingual documents |
| `06_tools_config/` | Environment, Tesseract config, and tessdata |
| `07_documentation/` | Process docs, schema, execution plan |
| `08_working_scratch/` | Pipeline scripts, annotation tooling, fine-tuning workspace |

## Collaboration

This project is intended to be collaborative. Anyone interested in contributing—whether with Latin, historical context, or technical expertise—is welcome. Please open an issue on GitHub or reach out to paul.d.boys@gmail.com.

## License

See [LICENSE](LICENSE).
