# whitaker_v4 ch2 — Phase 4 generalization check

v4 was tuned on ch1; this run scores it on ch2 (no prior versions on ch2 to pair against).

## Headline

| corpus | mean | n_units (×3 runs) |
|---|---:|---:|
| ch1 (v4, from prior report) | 0.7651 | 45 |
| **ch2 (v4, this report)**  | **0.7074** | 99 |
| delta (ch2 − ch1)         | -0.0577 | — |

**Generalization gate** (|ch2 − ch1| ≤ 0.01): FAIL (|delta| = 0.0577)

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
| run01 | 0.7110 | 33 |
| run02 | 0.7030 | 33 |
| run03 | 0.7083 | 33 |

## Per-unit (sorted worst-first)

| unit_id | mean | min | max | spread |
|---|---:|---:|---:|---:|
| ch2_u033 | 0.4704 | 0.4637 | 0.4786 | 0.0149 |
| ch2_u002 | 0.5553 | 0.5513 | 0.5573 | 0.0059 |
| ch2_u008 | 0.5885 | 0.5824 | 0.5919 | 0.0095 |
| ch2_u005 | 0.6072 | 0.5971 | 0.6262 | 0.0290 |
| ch2_u030 | 0.6317 | 0.6257 | 0.6435 | 0.0178 |
| ch2_u010 | 0.6321 | 0.6002 | 0.6537 | **0.0534** |
| ch2_u023 | 0.6455 | 0.6361 | 0.6575 | 0.0213 |
| ch2_u009 | 0.6541 | 0.6514 | 0.6576 | 0.0062 |
| ch2_u011 | 0.6626 | 0.6338 | 0.6819 | 0.0481 |
| ch2_u004 | 0.6634 | 0.6466 | 0.6943 | 0.0478 |
| ch2_u017 | 0.6773 | 0.6691 | 0.6817 | 0.0126 |
| ch2_u015 | 0.6888 | 0.6494 | 0.7148 | **0.0654** |
| ch2_u013 | 0.6892 | 0.6787 | 0.6993 | 0.0206 |
| ch2_u006 | 0.7028 | 0.6815 | 0.7156 | 0.0341 |
| ch2_u012 | 0.7054 | 0.7005 | 0.7135 | 0.0130 |
| ch2_u028 | 0.7082 | 0.7018 | 0.7129 | 0.0111 |
| ch2_u026 | 0.7197 | 0.6824 | 0.7398 | **0.0574** |
| ch2_u016 | 0.7201 | 0.7020 | 0.7332 | 0.0312 |
| ch2_u032 | 0.7264 | 0.7151 | 0.7406 | 0.0254 |
| ch2_u014 | 0.7295 | 0.7233 | 0.7347 | 0.0114 |
| ch2_u019 | 0.7320 | 0.7255 | 0.7434 | 0.0178 |
| ch2_u027 | 0.7330 | 0.7295 | 0.7397 | 0.0102 |
| ch2_u021 | 0.7404 | 0.7329 | 0.7555 | 0.0225 |
| ch2_u025 | 0.7581 | 0.7450 | 0.7809 | 0.0359 |
| ch2_u020 | 0.7660 | 0.7596 | 0.7786 | 0.0190 |
| ch2_u007 | 0.7698 | 0.7566 | 0.7829 | 0.0263 |
| ch2_u031 | 0.7735 | 0.7603 | 0.7856 | 0.0253 |
| ch2_u022 | 0.7755 | 0.7659 | 0.7896 | 0.0237 |
| ch2_u024 | 0.7770 | 0.7681 | 0.7848 | 0.0167 |
| ch2_u018 | 0.7806 | 0.7757 | 0.7848 | 0.0091 |
| ch2_u003 | 0.7838 | 0.7711 | 0.7921 | 0.0211 |
| ch2_u029 | 0.7941 | 0.7843 | 0.8026 | 0.0184 |
| ch2_u001 | 0.9833 | 0.9833 | 0.9833 | 0.0000 |

## Variance check (segment-boundary-leakage tell)

Units with intra-run spread ≥ 0.05 (potential boundary leakage): 3
- `ch2_u010`: spread 0.0534  (min 0.6002, max 0.6537)
- `ch2_u015`: spread 0.0654  (min 0.6494, max 0.7148)
- `ch2_u026`: spread 0.0574  (min 0.6824, max 0.7398)

Inspect these unit translations across runs to confirm — v3's tell was
identical-unit translations starting with a fragment of the previous unit's text.

## Interpretation

- v4 ch2 mean is 0.0577 below ch1 — outside the ±0.01 gate.
  Investigate worst-performing ch2 units for systematic register or content issues that
  ch1 didn't exhibit. The ch1 wins may have been corpus-specific.
