# A/B prompt test — p0041

**Verdict:** **FAIL**

Reasons:
- v1 win-rate 31% < 55% (gate 2).
- v1 won only 3 of 6 rubrics (need ≥5, gate 3).
- v1 lost on rubric(s): fluency, accuracy, register (gate 3).

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
- decoded: v0=37  v1=24  tie=17
- invalid: 0  errors: 3
- v1 win-rate: **31%**
- tie-rate: **22%**
- position bias |P(A) − 0.5|: **2%** (A picked 29, B picked 32)

## Judge — per rubric

| rubric | v0 | v1 | equal | invalid |
|---|---:|---:|---:|---:|
| accuracy ↓ | 36 | 17 | 25 | 0 |
| fluency ↓ | 47 | 15 | 16 | 0 |
| format_compliance ↑ | 8 | 22 | 48 | 0 |
| register ↓ | 38 | 13 | 27 | 0 |
| source_preservation ↑ | 6 | 20 | 52 | 0 |
| titles ↑ | 0 | 6 | 72 | 0 |

## Pre-registered thresholds

- gate 1: mechanical regressions = 0
- gate 2: v1 win-rate ≥ 55%, tie-rate < 30%
- gate 3: v1 wins ≥ 5/6 rubrics, no losses
- gate 4: |P(A) − 0.5| < 10%
- gate 5: invalid+error rate < 10%

