# Chapter 2 model comparison — Fable 5 vs Opus 4.8 vs Baker (1930)

Two complete, independent sentence-level (cross-page) translations of
*Antiquitates* ch. 2 (pp. 46–68; 60 sentence units, 55 footnotes), scored
with reference-based COMET (`Unbabel/wmt22-comet-da`) against the identical
58 aligned references from H. Kendra Baker, *Glastonbury Traditions
concerning Joseph of Arimathea* (Covenant Publishing, 1930) — the only
published English rendering of any part of the *Antiquitates*.

Both systems used the identical prompt (v5 core + Antiquitates skin,
including the Vulgate-scripture rule and literalness policy derived from
the ch1 classicist review), identical segmentation, and identical Baker
references, so the comparison isolates the model.

## System scores

| | claude-fable-5 | claude-opus-4-8 |
|---|---|---|
| system COMET | **0.7578** | **0.7565** |
| median | 0.7732 | 0.7737 |
| stdev | 0.0739 | 0.0760 |
| min / max | 0.553 / 0.966 | 0.542 / 0.966 |

## Per-unit head-to-head (58 units)

| | count |
|---|---|
| Fable wins (Δ > 0.005) | 20 |
| Opus wins (Δ < −0.005) | 14 |
| ties (|Δ| ≤ 0.005) | 24 |
| mean Δ (Fable − Opus) | **+0.0013** |

**Verdict: a statistical tie.** The mean delta is two orders of magnitude
below the per-unit stdev; neither model is distinguishable from the other
on this benchmark. Both models also placed all 55 footnote carets inline
with exact Latin↔English parity and zero end-of-line dumps — the ch1-era
marker-placement pass was unnecessary for either.

## Reading the absolute number

0.756–0.758 measures *similarity to Baker*, not absolute quality. It is
depressed by legitimate divergence, not only by error:

- Baker, despite declaring his rendering "literal rather than free," often
  paraphrases, compresses, and uses archaic name forms ("Glaston",
  "Johns Tinmuth", "Glasconia") that the machine correctly modernizes.
- Baker translated the 1639 text; ours is the 1847 Elrington/Todd reissue
  (same text, occasional regularized spellings).
- The reference passed through 1930s typesetting and Google OCR; residual
  noise survives despite scrubbing.

The lowest-scoring units for BOTH systems are the same passages
(seg_p0060_s0001, p0050_s0006, p0049_s0001, p0062_s0001, p0058_s0002) —
i.e. where Baker diverges most from the Latin's surface, both models
diverge from Baker identically. That correlation is itself evidence the
floor is reference divergence rather than model failure.

## Unscored by design

- `seg_p0046_s0001` — the chapter argumentum; Baker replaced it with his
  book heading.
- `seg_p0050_s0007` — the leonine distich (*Anno trigeno primo…*); Baker
  omits the verse couplet. Our translation covers text his does not.

## Artifacts

- `baker_alignment.jsonl` — 58 aligned refs (6 hand-patched records carry
  `manual_fix` provenance notes)
- `baker_scores_fable-5.jsonl` / `baker_scores_opus-4-8.jsonl` — per-unit
- `baker_scores_*_summary.json` — the tables above
- MT sources: `03_segmented_text/part1/segments_sentences_xpage.jsonl`
  (fable-5) and `segments_sentences_xpage_opus48.jsonl` (opus-4-8)
