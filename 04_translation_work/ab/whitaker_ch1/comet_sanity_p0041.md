# COMET sanity check on p0041

**Verdict:** PASS — COMET agrees with LLM judge directionally

- Model: `Unbabel/wmt22-cometkiwi-da`
- Mode: reference-free (CometKiwi)
- Runs aggregated: run01, run02, run03
- Segments scored: 78 / 81

## Aggregate COMET scores

| metric | v0 (baseline) | v1 (= v2 challenger) | delta (v1 − v0) |
|---|---:|---:|---:|
| mean | 0.5547 | 0.5173 | -0.0374 |
| median | 0.5441 | 0.4957 | — |
| segment wins | 47 | 29 | — |

## Per-run aggregates

| run | n_scored | v0_mean | v1_mean | mean_delta | v0_wins | v1_wins |
|---|---:|---:|---:|---:|---:|---:|
| run01 | 26 | 0.5536 | 0.5075 | -0.0461 | 16 | 9 |
| run02 | 26 | 0.5546 | 0.5100 | -0.0446 | 18 | 8 |
| run03 | 26 | 0.5559 | 0.5343 | -0.0216 | 13 | 12 |

## LLM judge verdict (from p0041_report.md)

- Overall: **FAIL** — v0 wins
- Wins (v0 / v1 / tie): 37 / 24 / 17
- v1 win-rate: 31% (gate was ≥55%)
- v1 lost rubrics: fluency, accuracy, register
- v1 won rubrics: format_compliance, source_preservation, titles

## Directional comparison

- LLM judge: **v0 wins**
- COMET: **v0_wins**
- Agreement: **YES**

## Interpretation guide

- **PASS** = COMET says v0 mean > v1 mean AND v0 segment-wins > v1 segment-wins. 
  This is the sanity floor: directionally agree with the LLM judge.
- Absolute COMET scores in 0.5–0.9 range are expected for modern WMT data; 
  16C scholastic Latin → Victorian English may produce lower absolute scores. 
  Don't compare to WMT benchmarks; only compare v0 vs v1 within this run.
- If COMET disagrees but v0 was an obvious win on fluency/register, the most 
  likely cause is domain mismatch (modern news training data). Investigate 
  per-segment deltas before discarding the hybrid plan.
