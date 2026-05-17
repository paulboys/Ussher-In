# whitaker_v2 vs baseline — Phase 3 A/B comparison

Both prompts scored at the **alignment-unit level** against the 1849 Parker Society reference using `Unbabel/wmt22-comet-da`.

## Headline result

| metric | baseline | v2 | delta |
|---|---:|---:|---:|
| mean | 0.7494 | 0.7612 | **+0.0119** |
| relative change | — | — | **+1.58%** |
| unit-wins for v2 | — | 26 | — |
| unit-wins for baseline | 17 | — | — |
| ties | — | — | 2 |

**Verdict:** v2 improves on baseline.

## Per-run aggregates

| run | baseline mean | v2 mean | delta |
|---|---:|---:|---:|
| whitaker_v2_run01 | 0.7492 | 0.7632 | +0.0140 |
| whitaker_v2_run02 | 0.7505 | 0.7607 | +0.0102 |
| whitaker_v2_run03 | 0.7484 | 0.7598 | +0.0113 |

## Per-unit deltas (sorted: biggest regressions first, biggest improvements last)

| unit_id | baseline mean | v2 mean | delta |
|---|---:|---:|---:|
| ch1_u007 | 0.7645 | 0.7396 | -0.0250 |
| ch1_u012 | 0.7269 | 0.7151 | -0.0117 |
| ch1_u006 | 0.7734 | 0.7637 | -0.0097 |
| ch1_u013 | 0.7663 | 0.7611 | -0.0052 |
| ch1_u005 | 0.7943 | 0.7904 | -0.0039 |
| ch1_u011 | 0.7663 | 0.7633 | -0.0029 |
| ch1_u002 | 0.5671 | 0.5653 | -0.0018 |
| ch1_u004 | 0.7526 | 0.7525 | -0.0001 |
| ch1_u014 | 0.7463 | 0.7530 | +0.0067 |
| ch1_u008 | 0.7926 | 0.8006 | +0.0081 |
| ch1_u003 | 0.7506 | 0.7612 | +0.0106 |
| ch1_u015 | 0.7857 | 0.7995 | +0.0138 |
| ch1_u010 | 0.7357 | 0.7626 | +0.0270 |
| ch1_u009 | 0.6359 | 0.7077 | +0.0718 |
| ch1_u001 | 0.8827 | 0.9830 | +0.1003 |

## Interpretation guide

- **Positive delta** = v2 closer to Parker Society than baseline on that unit.
- **Negative delta** = v2 farther from Parker Society than baseline (a regression).
- Aspirational target was aggregate mean ≥ 0.78 (per diagnostic_categories.md).
- If aggregate is positive but some units regressed, investigate the regressors 
  segment-by-segment and consider ablating the responsible rule.
