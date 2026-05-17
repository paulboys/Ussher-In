# whitaker_v4 vs v3 vs v2 vs baseline — Phase 3 iter3 comparison

Four-way comparison at the alignment-unit level using `Unbabel/wmt22-comet-da`.

## Headline trajectory

| metric | baseline | v2 | v3 | v4 | v4 − v3 | v4 − v2 | v4 − baseline |
|---|---:|---:|---:|---:|---:|---:|---:|
| mean | 0.7494 | 0.7612 | 0.7557 | **0.7651** | **+0.0094** | **+0.0039** | **+0.0157** |
| relative change | — | — | — | — | +1.24% | +0.51% | +2.10% |
| v4 unit-wins | — | — | — | — | 27/45 | 27/45 | 29/45 |
| v4 unit-losses | — | — | — | — | 12 | 15 | 16 |

**Verdict (vs v3):** v4 improves on v3.
**Verdict (vs v2):** v4 improves on v2.
**Verdict (vs baseline):** v4 improves on baseline.

## Per-run aggregates

| run | baseline | v2 | v3 | v4 | v4 − v3 | v4 − v2 | v4 − baseline |
|---|---:|---:|---:|---:|---:|---:|---:|
| run01 | 0.7492 | 0.7632 | 0.7449 | 0.7668 | +0.0220 | +0.0036 | +0.0176 |
| run02 | 0.7505 | 0.7607 | 0.7623 | 0.7643 | +0.0020 | +0.0036 | +0.0138 |
| run03 | 0.7484 | 0.7598 | 0.7600 | 0.7642 | +0.0042 | +0.0045 | +0.0158 |

## Per-unit (sorted: biggest v4-vs-v3 regressions first, biggest improvements last)

| unit_id | baseline | v2 | v3 | v4 | v4 − v3 | v4 − v2 | v4 − baseline |
|---|---:|---:|---:|---:|---:|---:|---:|
| ch1_u011 | 0.7663 | 0.7633 | 0.7689 | 0.7518 | -0.0170 | -0.0115 | -0.0144 |
| ch1_u007 | 0.7645 | 0.7396 | 0.7423 | 0.7420 | -0.0003 | +0.0024 | -0.0225 |
| ch1_u001 | 0.8827 | 0.9830 | 0.9830 | 0.9830 | +0.0000 | +0.0000 | +0.1003 |
| ch1_u002 | 0.5671 | 0.5653 | 0.5779 | 0.5779 | +0.0000 | +0.0126 | +0.0108 |
| ch1_u005 | 0.7943 | 0.7904 | 0.8025 | 0.8026 | +0.0002 | +0.0123 | +0.0083 |
| ch1_u015 | 0.7857 | 0.7995 | 0.7985 | 0.7988 | +0.0003 | -0.0007 | +0.0131 |
| ch1_u003 | 0.7506 | 0.7612 | 0.7666 | 0.7727 | +0.0061 | +0.0116 | +0.0222 |
| ch1_u008 | 0.7926 | 0.8006 | 0.7966 | 0.8047 | +0.0082 | +0.0041 | +0.0122 |
| ch1_u004 | 0.7526 | 0.7525 | 0.7399 | 0.7503 | +0.0105 | -0.0022 | -0.0023 |
| ch1_u014 | 0.7463 | 0.7530 | 0.7479 | 0.7678 | +0.0200 | +0.0149 | +0.0216 |
| ch1_u012 | 0.7269 | 0.7151 | 0.6873 | 0.7074 | +0.0201 | -0.0077 | -0.0195 |
| ch1_u010 | 0.7357 | 0.7626 | 0.7383 | 0.7588 | +0.0205 | -0.0038 | +0.0231 |
| ch1_u006 | 0.7734 | 0.7637 | 0.7689 | 0.7896 | +0.0206 | +0.0258 | +0.0161 |
| ch1_u013 | 0.7663 | 0.7611 | 0.7407 | 0.7645 | +0.0238 | +0.0034 | -0.0018 |
| ch1_u009 | 0.6359 | 0.7077 | 0.6767 | 0.7048 | +0.0281 | -0.0029 | +0.0689 |

## Interpretation guide

- **v4 − v3** is the primary test: does slimming Rule 2c restore the lost ground?
- **v4 − v2** checks whether v4 regains the v2 ceiling (v2 was the prior best).
- **v4 − baseline** is cumulative progress since the start of Phase 3.
- Watch unit-run01 for ch1_u009/u010/u012/u013 specifically — the v3 segment-
  boundary leakage diagnosis predicts those should normalize in v4.
- Aspirational target (per diagnostic_categories.md) was aggregate mean ≥ 0.78.
