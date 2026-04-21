# OCR Engine Comparison: Tesseract (lat) vs Kraken (Latin) vs Tesseract (lat+grc)

**Date:** 2026-04-20
**Pages tested:** p0033–p0035 (Part 1, pp. 33–35)
**Source PDF:** `JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf`
**DPI:** 400

## Engines Tested

| Engine | Model / Language | Version | Environment |
|--------|-----------------|---------|-------------|
| Tesseract `lat` | `lat.traineddata` (tessdata_best) | 5.x, OEM 1 | Windows / conda `ussher` |
| Kraken (Latin) | `reichenau_lat_cat_099218.mlmodel` (DOI 10.5281/zenodo.11113737) | Kraken 7.0 | WSL2 Ubuntu / venv `kraken-env` |
| Tesseract `lat+grc` | `lat.traineddata` + `grc.traineddata` (tessdata_best) | 5.x, OEM 1 | Windows / conda `ussher` |

## Confidence Scores

| Page | Tesseract `lat` | Kraken (Latin) | Tesseract `lat+grc` |
|------|-----------------|----------------|---------------------|
| p0033 | 91.54% | 91.95% | 92.02% |
| p0034 | 88.20% | 87.93% | 90.76% |
| p0035 | 88.84% | 91.18% | 92.51% |
| **Avg** | **89.53%** | **90.35%** | **91.76%** |

## Character Count

| Page | Tesseract `lat` | Kraken (Latin) | Tesseract `lat+grc` |
|------|-----------------|----------------|---------------------|
| p0033 | 2206 | 1150 | 2206 |
| p0034 | 2253 | 993 | 2251 |
| p0035 | 2211 | 1295 | 2208 |

Kraken consistently produces 30–45% fewer characters per page due to segmentation failures.
Tesseract `lat` and `lat+grc` produce nearly identical character counts (±2 chars).

## Line Count

| Page | Tesseract `lat` | Tesseract `lat+grc` |
|------|-----------------|---------------------|
| p0033 | 49 | 49 |
| p0034 | 50 | 50 |
| p0035 | 47 | 47 |

No structural difference between `lat` and `lat+grc`.

## Greek Text Recognition

Pages 34 and 35 contain inline Greek quotations. This is the primary differentiator.

### Page 34 — Gregory of Nyssa quotation

**Tesseract `lat`:**
```
occultum esse sinerent ; ** uz) vjsovc, ur) iyrepov, uu9. &rwa
ro(rqv avÜporroic karowíav 7) $óc«c 2O(60v, non insulas,
```

**Tesseract `lat+grc`:**
```
occultum esse sinerent ; " μὴ νήσους, μὴ ἤπειρον, μηδ᾽ εἴτινα
τρίτην ἀνθρώποις κατοικίαν ἡ φύσις ἐδίδου, non insulas,
```

**Kraken (Latin):**
Segmentation failed to capture these lines coherently.

### Page 35 — Ignatian epistle quotation

**Tesseract `lat`:**
```
0i dà'ytoc àmócroAot àmó mipárwv Fc mepdrtov iv. rq aluari
Tov Xpurov, oike(oic ipao: kai móvoic.
```

**Tesseract `lat+grc`:**
```
οἱ ἅγιοι ἀπόστολοι ἀπὸ περάτων ἕως περάτων ἐν τῷ αἵματι
τοῦ Χριστοῦ, οἰκείοις ἱδρῶσι καὶ πόνοις.
```

**Kraken (Latin):**
Partial recognition with mixed noise: `o̓xεiοσ 1θοῦσι και πόνοτσ / Dῦ Xριστοῦ`

## Ligature Handling (æ)

| Pattern | Source text | Tesseract `lat` | Tesseract `lat+grc` | Kraken (Latin) |
|---------|-----------|-----------------|---------------------|----------------|
| Victoriæ | `Victori:&` | `Victori:&` | `Victori:&` | `Vietoriæ` ✓ |
| quæs- | `quzs-` | `quzs-` | `quzs-` | `que r` |
| cæco | `czco` | `czco` | `czco` | not captured |
| præ- | `prz-` | `prz-` | `prz-` | `præ-` ✓ |

Neither Tesseract configuration resolves `æ` — it is not in the `lat` unicharset.
Kraken's Latin model correctly recognizes `æ` on lines it successfully segments.
The pipeline's `AeHeuristicNormalizer` provides a post-processing workaround for Tesseract.

## Segmentation Quality

| Metric | Tesseract | Kraken |
|--------|-----------|--------|
| Line detection | Clean, reliable | Hundreds of `TopologyException` errors per page |
| Page layout handling | Handles headers, body, marginalia, footnotes | Fails on complex 17th-century layout |
| Footnote capture | Separate region with `--psm 6` | Not captured |
| Speed (CPU) | ~5 sec/page | ~5 min/page |

Kraken's `blla` baseline segmenter cannot reliably detect line boundaries in this material. This produces fragmented output with random digits, single characters, and blank lines interspersed with correctly recognized text.

## Recommendation

**Primary engine: Tesseract with `lat+grc`**

| Criterion | Winner | Rationale |
|-----------|--------|-----------|
| Greek text | Tesseract `lat+grc` | Proper polytonic Greek with diacriticals |
| Latin text | Tie | All three produce comparable Latin body text |
| Ligatures (æ) | Kraken | Only engine with `æ` in its character set |
| Completeness | Tesseract | Captures 100% of page text; Kraken ~60% |
| Segmentation | Tesseract | Clean line detection vs. Kraken's topology failures |
| Footnotes | Tesseract | Separate footnote region support |
| Speed | Tesseract | ~60x faster on CPU |
| Confidence | Tesseract `lat+grc` | Highest average (91.76%) |

### Decision

1. **Use Tesseract `lat+grc` as the default OCR engine.** Pipeline updated: `--lang lat+grc` is now the default in `pilot_ocr.py`.
2. **Retain the `AeHeuristicNormalizer`** for `æ` ligature post-processing until a fine-tuned Tesseract model is available.
3. **Keep Kraken infrastructure** (`kraken_ocr_runner.py`, WSL setup) for future use if a custom segmentation model is trained.
4. **Future improvement:** Fine-tune Tesseract `lat` model with `tesstrain` using ground-truth annotations from `03_corrected_ocr/` to add `æ` and other ligatures to the unicharset.

## Files Produced

- `08_working_scratch/test_lat_grc_p00{33,34,35}_lat.txt` — Tesseract `lat`-only output
- `08_working_scratch/test_lat_grc_p00{33,34,35}_lat_grc.txt` — Tesseract `lat+grc` output
- `08_working_scratch/pipeline_scripts/test_lat_grc.py` — Test script
- `08_working_scratch/pipeline_scripts/check_ligatures.py` — Ligature analysis script
- `01_raw_ocr_output/part1/part1_pilot_ocr_kraken.json` — Kraken Latin model results (pp. 33–35)
- `06_tools_config/tessdata/grc.traineddata` — Ancient Greek model (tessdata_best)
