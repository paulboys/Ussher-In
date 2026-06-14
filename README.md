<p align="center">
  <img src="Ussher_In_logo_v2.png" alt="Ussher In" width="300"/>
</p>

# Ussher In

**The first English translation of James Ussher's *Britannicarum Ecclesiarum Antiquitates* (1639), working from the 1847 Elrington / Todd Latin edition.**

Ussher's *Britannicarum Ecclesiarum Antiquitates* (1639) has never been translated into English in its entirety. One chapter—the second, on Glastonbury traditions—was translated by H. Kendra Baker, but the remaining sixteen chapters are accessible only in Latin.

This project works from the Latin text as reissued in volumes V–VI of *The Whole Works of the Most Rev. James Ussher, D.D.*, edited by Charles Richard Elrington and (after his death in 1850) James Henthorn Todd, published in Dublin by Hodges & Smith from 1847. The Elrington/Todd edition modernizes some of the 1639 orthography, regularizes references, and supplies an editorial apparatus, while preserving Ussher's text. References to "Ussher's 1639 corpus" elsewhere in this repository should be read as the 1639 work as transmitted by the 1847 Elrington/Todd reissue.

As a foundational history of the early British and Irish churches—their origins, monasticism, and ties to the wider Christian world—this work has remained out of reach for English readers. This project aims to change that.

## Background

This project was born from two historical questions I have been asking for years:
1.  How significant was James Ussher's influence on the Westminster Assembly, given the deep parallels between his earlier works and their famous Confession and Catechisms?
2.  How did St. Basil's monastic rule travel from 4th-century Cappadocia to the Celtic monasteries of Ireland and Scotland?

This second line of inquiry led to one, untranslated primary source: Ussher's *Antiquitates*. This work documents the history of the early insular church, its key figures like Columba, and its connections to the wider Christian world.

As a data scientist unable to read Latin, the only way to answer these questions was to build the tools to make the book accessible. This repository is the result—a data-driven attempt to produce the first English translation through a combination of vision-LLM OCR, paleography-aware prompting, and careful human review.

## How It Works

The pipeline has three linked stages:

1. **OCR** — Extract structured Latin (and polytonic Greek) text from the source PDFs using **Google Gemini 3.1 Pro** as the primary OCR engine, with paleography-aware prompts that preserve long-s, ligatures, and historical numerals. Each page is segmented into header, body, footnotes, marginalia, and catchword regions, then quality-checked. Tesseract and Kraken remain available as fallback engines during the migration.
2. **Reference English** — OCR and structure the existing English translation PDF/images into aligned English text where that witness is available. This serves as an initial gold-standard benchmark for evaluating machine translation from Latin to English.
3. **Translation** — Translate the structured Latin into modern academic-register English using **Claude Opus 4.8** (configured via the same provider layer as Gemini), followed by human post-editing. The translation prompt was developed and validated on a separate, scorable training corpus before deployment (see *Translation Methodology* below); output is scored with COMET and an author-fidelity LLM judge, and a post-hoc neuro-symbolic layer validates terminology consistency. The output remains bilingual Latin-English reading documents.

### Provider configuration

OCR and translation engines are selected via a unified provider config
(see [06_tools_config/providers.README.md](06_tools_config/providers.README.md)).
API keys may be supplied via `06_tools_config/providers.json` or environment
variables of the form `USSHERIN_PROVIDERS_<NAME>_API_KEY`.

### Verification (Go Claw)

A Go module under [08_working_scratch/phase3b/go-claw](08_working_scratch/phase3b/go-claw)
provides deterministic catchword + marginalia verification and a read-only
side-by-side review server (non-port-5000) that complements the Python
Flask annotation UI.

### Paleography-Aware Prompting

The source is the 1847 Elrington/Todd Latin reissue of Ussher's 1639 work, which retains many early-modern features: ligatures (æ/Æ, œ/Œ), polytonic Greek quotations, archaic numeral forms, and a dense scholarly apparatus of footnotes and marginalia. (Long-s is generally regularized in the 1847 setting, but appears in directly reproduced quotations and may surface in OCR of degraded scans.) Rather than relying on a stock OCR model and patching errors after the fact, this pipeline issues an explicit paleography-aware prompt to a vision-capable LLM (Gemini 3.1 Pro) that:

- preserves long-s, ligatures, and early-modern abbreviations verbatim,
- preserves polytonic Greek (breathings, accents, iota subscript),
- anchors marginalia to the body line they sit beside,
- emits a separate `catchword` region used by the Go verification layer, and
- suppresses watermarks, show-through, and stamps as non-text noise.

A small annotated gold set (Phase 3b, pages around p0030–p0060) is retained for regression checks and prompt evaluation rather than for model fine-tuning.

### Translation Methodology

Because no complete English gold standard exists for the *Antiquitates*, the translation prompt was developed on a **separate, scorable training corpus** and then transferred. William Whitaker's *Disputatio de Sacra Scriptura* (1690 Latin) was translated and scored against its published 1849 Parker Society English translation, iterating the prompt against COMET (reference-based) and an author-fidelity LLM judge that scores Greek preservation, paraphrase handling, and content/register fidelity directly against the Latin source. The resulting prompt is split into a locked **shared core** (translation rules, lexicon, output contract) and a swappable **corpus skin** (author brief, register clause); only the skin changes per author. The same core was generalization-tested on Ussher's *Annales Veteris Testamenti* and validated on the *Antiquitates* itself.

Two reliability layers run after generation, in code rather than in the prompt:

- a **completeness safety net** that detects any source line the model omitted and re-translates just that span; and
- a **neuro-symbolic validation layer**, built lightest-first: a controlled glossary/termbase flags terminology drift and banned renderings against the Latin source (Phase A, implemented), with a translation memory and structured-artifact validators (citations, proper names, language switches) planned. The model performs the creative translation; the deterministic layer validates consistency and surfaces editor flags rather than making silent edits.

### Interlinear Rendering & Footnote Anchoring

The translated output is rendered as bilingual review documents — a paired
Latin/English **interlinear**, a flowing-prose **reading** view, and a linked
**footnotes** section — by `render_interlinear.py`. Two features keep the dense
scholarly apparatus faithful across page breaks:

- **Cross-page sentence grouping.** A sentence whose Latin runs across a page
  break is translated whole on its home page; the renderer attaches each
  footnote to the page where its anchoring line is actually rendered, so a
  marker and its definition never drift onto different pages.
- **Per-chapter marker-placement pass.** Footnote superscripts (`^a`, `^b`, …)
  are anchored inline in both the Latin and the English. Where the automated
  placement falls back (dumping a marker at a sentence's end), an **agentic
  pass run inside Claude Code** relocates each marker to the English word
  matching its Latin anchor — quotation openings, proper names, or the rendered
  word — then verifies the page deterministically (zero dangling clusters, exact
  marker↔definition parity). The procedure is documented as a repeatable
  per-chapter runbook in
  [07_documentation/MARKER_PLACEMENT_RUNBOOK.md](07_documentation/MARKER_PLACEMENT_RUNBOOK.md).

## Project Status

| Phase | Status |
|---|---|
| Project scaffold & docs | ✅ Complete |
| Pilot OCR validation (pages 30–35) | ✅ Complete |
| Provider config + Gemini OCR adapter | ✅ Complete |
| Phase 3b annotation UI + gold set | ✅ Complete (ongoing review) |
| Go Claw verification module (catchword + marginalia + side-by-side server) | ✅ Complete |
| Paleography prompt evaluation against gold set | ✅ Complete |
| English reference benchmark ingestion/alignment | 🟡 In progress |
| Full OCR run (~1200 pages) via Gemini | 🟡 In progress |
| Translation prompt development & validation (Whitaker corpus, COMET + author-fidelity) | ✅ Complete |
| Cross-corpus generalization test (Ussher *Annals*) | ✅ Complete |
| Translation prompt validated for *Antiquitates* (p0036) | ✅ Complete |
| Completeness safety net (detect-and-rerun) | ✅ Complete |
| Neuro-symbolic validation — Phase A (controlled glossary) | ✅ Complete |
| Neuro-symbolic validation — Phase B (translation memory) & C (artifact validators) | ⬜ Planned |
| Chapter 1 translation (pp. 32–45, Claude Opus 4.8) | ✅ Draft complete; under review |
| Interlinear rendering: cross-page sentences + footnote marker anchoring (Chapter 1) | ✅ Complete |
| Full translation (remaining chapters) + post-editing | ⬜ Pending |

## Quick Start

1. Place source PDFs in `00_source_pdf/`.
2. Follow setup instructions in `06_tools_config/tool_installation_guide.md`.
3. Copy `06_tools_config/providers.example.json` to `providers.json` and set the Gemini API key, or export `USSHERIN_PROVIDERS_GEMINI_API_KEY`.
4. Review the schema in `07_documentation/SCHEMA.md`.
5. Run pilot OCR using scripts in `08_working_scratch/pipeline_scripts/` (default engine: Gemini 3.1 Pro).
6. Apply quality gates from `07_documentation/QA_WORKFLOW.md` and run the Go Claw verifier (`08_working_scratch/phase3b/go-claw`) before translation.

## Repository Structure

| Directory | Contents |
|---|---|
| `00_source_pdf/` | Canonical source PDFs (git-ignored) |
| `01_raw_ocr_output/` | Raw OCR output by part and page |
| `02_ocr_qc/` | Confidence reports and QA artifacts |
| `03_segmented_text/` | Cleaned and segmented Latin records |
| `04_translation_work/` | Translation drafts and post-edit work |
| `05_final_output/` | Release-ready bilingual documents |
| `06_tools_config/` | Provider configuration, environment setup, legacy Tesseract/Kraken assets |
| `07_documentation/` | Process docs, schema, execution plan |
| `08_working_scratch/` | Pipeline scripts, annotation tooling, Go Claw verification module |

## Collaboration

Contributions are welcome—whether with Latin, historical context, or technical expertise. Please open an issue on GitHub or reach out to paul.d.boys@gmail.com.

## License

Released under the MIT License — see [LICENSE](LICENSE).
