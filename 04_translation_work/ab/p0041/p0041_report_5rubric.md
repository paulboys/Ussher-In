# A/B prompt test — p0041

**Verdict:** **FAIL**

Reasons:
- v1 win-rate 29% < 55% (gate 2).
- v1 won only 1 of 5 rubrics (need ≥5, gate 3).
- v1 lost on rubric(s): fluency, accuracy, proper_nouns, register (gate 3).
- position bias |P(A) - 0.5| = 13% ≥ 10% (gate 4).

## Runs scored

| version | run_tag | segments | total findings |
|---|---|---:|---:|
| v0 | run01 | 27 | 5 |
| v0 | run02 | 27 | 5 |
| v0 | run03 | 27 | 5 |

## Mechanical (per-segment rate)

| rule | v0/seg | v1/seg | Δ (v1−v0) |
|---|---:|---:|---:|
| caret_in_english | 0.148 | 0.000 | -0.148 |
| empty_english | 0.037 | 0.000 | -0.037 |

Negative Δ means v1 has fewer of that finding (improvement). Positive Δ marked ⚠ is a regression and trips gate 1.

## Judge — pooled

- judgments total: **81**
- decoded: v0=45  v1=23  tie=10
- invalid: 0  errors: 3
- v1 win-rate: **29%**
- tie-rate: **13%**
- position bias |P(A) − 0.5|: **13%** (A picked 25, B picked 43)

## Judge — per rubric

| rubric | v0 | v1 | equal | invalid |
|---|---:|---:|---:|---:|
| accuracy ↓ | 28 | 15 | 35 | 0 |
| fluency ↓ | 42 | 14 | 22 | 0 |
| proper_nouns ↓ | 7 | 3 | 68 | 0 |
| register ↓ | 41 | 19 | 18 | 0 |
| titles ↑ | 1 | 8 | 69 | 0 |

## Pre-registered thresholds

- gate 1: mechanical regressions = 0
- gate 2: v1 win-rate ≥ 55%, tie-rate < 30%
- gate 3: v1 wins ≥ 5/5 rubrics, no losses
- gate 4: |P(A) − 0.5| < 10%
- gate 5: invalid+error rate < 10%

