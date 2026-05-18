# whitaker_v4 ch2 — Phase 4 generalization check

v4 was tuned on ch1; this run scores it on ch2 (no prior versions on ch2 to pair against).

## Headline

| corpus | mean | n_units (×3 runs) |
|---|---:|---:|
| ch1 (v4, from prior report) | 0.7651 | 45 |
| **ch2 (v4, this report)**  | **0.7279** | 15 |
| delta (ch2 − ch1)         | -0.0372 | — |

**Generalization gate** (|ch2 − ch1| ≤ 0.01): FAIL (|delta| = 0.0372)

## Trajectory context (ch1 baselines, for reference only)

| version | ch1 mean |
|---|---:|
| baseline | 0.7494 |
| v2 | 0.7612 |
| v3 | 0.7557 |
| v4 | 0.7651 |

## Per-run aggregates (ch2)

| run | mean | n_units |
|---|---:|---:|
| run01 | 0.7254 | 5 |
| run02 | 0.7240 | 5 |
| run03 | 0.7342 | 5 |

## Per-unit (sorted worst-first)

| unit_id | mean | min | max | spread |
|---|---:|---:|---:|---:|
| ch2_u002 | 0.5553 | 0.5513 | 0.5573 | 0.0059 |
| ch2_u005 | 0.6456 | 0.6193 | 0.6623 | 0.0430 |
| ch2_u004 | 0.6611 | 0.6458 | 0.6690 | 0.0232 |
| ch2_u003 | 0.7940 | 0.7713 | 0.8065 | 0.0352 |
| ch2_u001 | 0.9833 | 0.9833 | 0.9833 | 0.0000 |

## Variance check (segment-boundary-leakage tell)

No units with spread ≥ 0.05. Stability looks ch1-like (v4 ch1 max spread was ~0.003).

## Interpretation

- v4 ch2 mean is 0.0372 below ch1 — outside the ±0.01 gate.
  Investigate worst-performing ch2 units for systematic register or content issues that
  ch1 didn't exhibit. The ch1 wins may have been corpus-specific.
