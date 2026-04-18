<p align="center">
  <img src="Ussher_In_logo.png" alt="Ussher In" width="300"/>
</p>

# Ussher In

**The first English translation of James Ussher's *Britannicarum Ecclesiarum Antiquitates* (1639).**

Ussher's *Antiquitates* is a foundational history of the early British and Irish churches — their origins, their monasticism, their ties to the wider Christian world — written entirely in Latin. Despite its importance to church history, it has never been translated into English. This project aims to change that.

## Background

My interest in Ussher began with his *Irish Articles* and *Body of Divinity*. Reading them, I was struck by how closely they anticipate the Westminster Confession and Larger Catechism — in structure, language, and theological instinct. His treatment of God's nature and the Lord's Prayer in particular left me wondering just how deep his influence on the Westminster Assembly really was.

Separately, I had been tracing the transmission of St Basil's monastic rule from fourth-century Cappadocia to the Celtic monasteries of Ireland and Scotland — how a tradition born in what is now Turkey reached Iona. That trail leads, almost inevitably, to Ussher. His *Antiquitates* is precisely where he documented that history: Columba, the early insular churches, and their connections to the broader Christian world.

Then I discovered no English translation exists.

I cannot read Latin. But I am a data scientist with some spare time and enough stubbornness to try. *Ussher In* is the result: OCR of the 19th-century Elrington & Todd edition, machine-assisted Latin-to-English translation, and careful human review. A nights-and-weekends project, driven entirely by wanting to read this book.

## How It Works

The pipeline has two stages:

1. **OCR** — Extract structured Latin text from photocopied book PDFs using Tesseract with LSTM fine-tuning for historical print. Each page is segmented into body, footnotes, and marginalia, then quality-checked.
2. **Translation** — Translate the structured Latin into literal, academic-register English using machine translation with human post-editing. The output is bilingual Latin–English reading documents.

### Fine-Tuning for Historical Print

The source material is a 19th-century edition with ligatures (æ/Æ), footnote markers, and archaic numeral forms that stock OCR models misread. Rather than patching errors with regex, the project fine-tunes a custom Tesseract LSTM model using a small, carefully annotated gold set (15–25 representative pages). An annotation pipeline with seeding, review, and ground-truth export scripts supports building that training data.

## Project Status

| Phase | Status |
|---|---|
| Project scaffold & docs | ✅ Complete |
| Environment setup & pilot OCR (pages 30–35) | ✅ Complete |
| Annotation pipeline for fine-tuning | ✅ Built, annotation in progress |
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

## License

See [LICENSE](LICENSE).
