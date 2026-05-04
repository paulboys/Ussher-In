# A/B prompt test — p0039

**Verdict:** **FAIL**

Reasons:
- v1 win-rate 45% < 55% (gate 2).
- v1 won only 3 of 5 rubrics (need ≥5, gate 3).
- v1 lost on rubric(s): accuracy, titles (gate 3).
- position bias |P(A) - 0.5| = 11% ≥ 10% (gate 4).

## Runs scored

| version | run_tag | segments | total findings |
|---|---|---:|---:|
| v0 | run01 | 36 | 3 |
| v0 | run02 | 36 | 3 |
| v0 | run03 | 36 | 3 |
| v1 | run01 | 36 | 3 |
| v1 | run02 | 36 | 3 |
| v1 | run03 | 36 | 3 |

## Mechanical (per-segment rate)

| rule | v0/seg | v1/seg | Δ (v1−v0) |
|---|---:|---:|---:|
| caret_in_english | 0.083 | 0.083 | +0.000 |

Negative Δ means v1 has fewer of that finding (improvement). Positive Δ marked ⚠ is a regression and trips gate 1.

## Judge — pooled

- judgments total: **108**
- decoded: v0=35  v1=48  tie=24
- invalid: 0  errors: 1
- v1 win-rate: **45%**
- tie-rate: **22%**
- position bias |P(A) − 0.5|: **11%** (A picked 32, B picked 51)

## Judge — per rubric

| rubric | v0 | v1 | equal | invalid |
|---|---:|---:|---:|---:|
| accuracy ↓ | 28 | 22 | 57 | 0 |
| fluency ↑ | 22 | 48 | 37 | 0 |
| proper_nouns ↑ | 3 | 7 | 97 | 0 |
| register ↑ | 26 | 44 | 37 | 0 |
| titles ↓ | 1 | 0 | 106 | 0 |

## Pre-registered thresholds

- gate 1: mechanical regressions = 0
- gate 2: v1 win-rate ≥ 55%, tie-rate < 30%
- gate 3: v1 wins ≥ 5/5 rubrics, no losses
- gate 4: |P(A) − 0.5| < 10%
- gate 5: invalid+error rate < 10%

