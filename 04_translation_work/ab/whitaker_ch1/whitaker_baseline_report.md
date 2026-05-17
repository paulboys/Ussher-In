# Whitaker baseline — Phase 1 scoring report (unit-level)

Score: `translation_prompts_whitaker.py` over c1_ch1 (p0030–p0031) scored at the **alignment-unit level** against the 1849 Parker Society English reference using [`Unbabel/wmt22-comet-da`](https://huggingface.co/Unbabel/wmt22-comet-da).

Per-segment scoring was abandoned: a single Latin body-line fragment compared against its multi-line aligned reference scored systematically low because most of the reference was unaccounted for in the candidate. Unit-level scoring concatenates per-line candidates back into the sentence they belong to (per `chapter1_alignment.jsonl`) before scoring.

- Alignment file: `04_translation_work\ab\whitaker_ch1\chapter1_alignment.jsonl`
- Runs scored: whitaker_baseline_run01, whitaker_baseline_run02, whitaker_baseline_run03
- Reference part: `whitaker_english`

## Aggregate (all runs)

| metric | value |
|---|---:|
| (run × unit) records scored | 45 |
| records skipped (no reference) | 0 |
| records skipped (empty english) | 0 |
| mean | **0.7494** |
| median | 0.7629 |
| stdev | 0.0699 |
| min | 0.5671 |
| max | 0.8827 |

## Per-run aggregates

| run | n | mean | median | min | max |
|---|---:|---:|---:|---:|---:|
| whitaker_baseline_run01 | 15 | 0.7492 | 0.7527 | 0.5671 | 0.8827 |
| whitaker_baseline_run02 | 15 | 0.7505 | 0.7658 | 0.5671 | 0.8827 |
| whitaker_baseline_run03 | 15 | 0.7484 | 0.7643 | 0.5671 | 0.8827 |

## Run-to-run stability

Top-5 units with highest cross-run standard deviation — where the prompt is least deterministic:

| unit_id | mean score | stdev across runs |
|---|---:|---:|
| ch1_u007 | 0.7645 | 0.0172 |
| ch1_u009 | 0.6359 | 0.0088 |
| ch1_u010 | 0.7357 | 0.0083 |
| ch1_u012 | 0.7269 | 0.0073 |
| ch1_u006 | 0.7734 | 0.0070 |

## Lowest-scoring units (Phase 2 diagnostic starters)

These are where the baseline diverges most from Parker Society. 
Read the actual English vs reference in `whitaker_baseline_unit_scores.jsonl` 
and classify by divergence category.

| unit_id | mean score | stdev | run01 | run02 | run03 |
|---|---:|---:|---:|---:|---:|
| ch1_u002 | 0.5671 | 0.0000 | 0.5671 | 0.5671 | 0.5671 |
| ch1_u009 | 0.6359 | 0.0088 | 0.6460 | 0.6305 | 0.6313 |
| ch1_u012 | 0.7269 | 0.0073 | 0.7261 | 0.7345 | 0.7200 |
| ch1_u010 | 0.7357 | 0.0083 | 0.7311 | 0.7453 | 0.7307 |
| ch1_u014 | 0.7463 | 0.0040 | 0.7503 | 0.7462 | 0.7423 |

## Highest-scoring units (where the baseline already matches Parker Society)

| unit_id | mean score | stdev |
|---|---:|---:|
| ch1_u001 | 0.8827 | 0.0000 |
| ch1_u005 | 0.7943 | 0.0063 |
| ch1_u008 | 0.7926 | 0.0037 |
| ch1_u015 | 0.7857 | 0.0047 |
| ch1_u006 | 0.7734 | 0.0070 |

## Interpretation guide

- COMET-DA scores are in 0–1; for modern WMT translations, 
  typical good scores land 0.75–0.90. 16C scholastic Latin → Victorian 
  English is well out of distribution; absolute scores will be lower. 
  **Only compare against other runs of this corpus, not against WMT benchmarks.**
- The baseline mean is the number `v_next` needs to beat.
- Low cross-run stdev = prompt is producing consistent output across runs. 
  High stdev = same prompt yields meaningfully different translations.
