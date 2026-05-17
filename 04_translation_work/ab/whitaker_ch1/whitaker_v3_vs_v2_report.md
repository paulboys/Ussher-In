# whitaker_v3 vs v2 vs baseline — Phase 3 iter2 comparison

Three-way comparison at the alignment-unit level using `Unbabel/wmt22-comet-da`.

## Headline trajectory

| metric | baseline | v2 | v3 | v3 − v2 | v3 − baseline |
|---|---:|---:|---:|---:|---:|
| mean | 0.7494 | 0.7612 | **0.7557** | **-0.0055** | **+0.0063** |
| relative change | — | — | — | -0.72% | +0.85% |
| v3 unit-wins | — | — | — | 18/45 | 26/45 |
| v3 unit-losses | — | — | — | 24 | 18 |

**Verdict (vs v2):** v3 regresses against v2.
**Verdict (vs baseline):** v3 still improves on baseline.

## Per-run aggregates

| run | baseline | v2 | v3 | v3 − v2 | v3 − baseline |
|---|---:|---:|---:|---:|---:|
| run01 | 0.7492 | 0.7632 | 0.7449 | -0.0184 | -0.0044 |
| run02 | 0.7505 | 0.7607 | 0.7623 | +0.0016 | +0.0118 |
| run03 | 0.7484 | 0.7598 | 0.7600 | +0.0002 | +0.0116 |

## Per-unit (sorted: biggest v3-vs-v2 regressions first, biggest improvements last)

| unit_id | baseline | v2 | v3 | v3 − v2 | v3 − baseline |
|---|---:|---:|---:|---:|---:|
| ch1_u009 | 0.6359 | 0.7077 | 0.6767 | -0.0310 | +0.0408 |
| ch1_u012 | 0.7269 | 0.7151 | 0.6873 | -0.0278 | -0.0396 |
| ch1_u010 | 0.7357 | 0.7626 | 0.7383 | -0.0244 | +0.0026 |
| ch1_u013 | 0.7663 | 0.7611 | 0.7407 | -0.0204 | -0.0256 |
| ch1_u004 | 0.7526 | 0.7525 | 0.7399 | -0.0126 | -0.0128 |
| ch1_u014 | 0.7463 | 0.7530 | 0.7479 | -0.0051 | +0.0016 |
| ch1_u008 | 0.7926 | 0.8006 | 0.7966 | -0.0041 | +0.0040 |
| ch1_u015 | 0.7857 | 0.7995 | 0.7985 | -0.0010 | +0.0129 |
| ch1_u001 | 0.8827 | 0.9830 | 0.9830 | +0.0000 | +0.1003 |
| ch1_u007 | 0.7645 | 0.7396 | 0.7423 | +0.0028 | -0.0222 |
| ch1_u006 | 0.7734 | 0.7637 | 0.7689 | +0.0052 | -0.0045 |
| ch1_u003 | 0.7506 | 0.7612 | 0.7666 | +0.0054 | +0.0161 |
| ch1_u011 | 0.7663 | 0.7633 | 0.7689 | +0.0055 | +0.0026 |
| ch1_u005 | 0.7943 | 0.7904 | 0.8025 | +0.0121 | +0.0082 |
| ch1_u002 | 0.5671 | 0.5653 | 0.5779 | +0.0126 | +0.0108 |

## Interpretation guide

- **v3 − v2** is the immediate iteration's contribution.
- **v3 − baseline** is cumulative progress since the start of Phase 3.
- Aspirational target (per diagnostic_categories.md) was aggregate mean ≥ 0.78.
