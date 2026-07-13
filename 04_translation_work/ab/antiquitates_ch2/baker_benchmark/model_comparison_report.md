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

## Alignment methodology

Baker's 1930 prose and our sentence-level Latin segmentation share no
common unit — one Ussher sentence can span several short Baker sentences,
or vice versa — so `baker_align.py` builds the correspondence in four
deterministic steps, then a final human-patching pass.

1. **Reconstruct continuous Baker text from the scans.** The 44
   HathiTrust page scans came through as noisy Google OCR text layers.
   Each page is cleaned before concatenation: strip the trailing page
   number and the footnote block at the page bottom (detected by a
   "single-letter marker + citation" line regex), drop OCR noise lines,
   and re-join words split by end-of-line hyphenation (`be-\nlievers` →
   `believers`). The 44 cleaned pages are concatenated into one
   continuous string.

2. **Split Baker into sentences — quote-aware.** A plain split on
   `.!?` badly under-segments Baker, who (like Ussher) is
   quotation-dense: a sentence ending inside a closing quote
   (`…Glaston."`) needs to break there too, or it fuses with the next
   sentence. The splitter breaks on terminal punctuation whether or not
   it is wrapped in a closing quote, and skips a small abbreviation list
   (`St.`, `cap.`, `Lib.`, `Cantab.`, …) so those periods don't trigger
   false breaks. This mattered in practice — without the quote-aware
   rule, whole passages merged into mega-sentences and the alignment
   around the opening pages was visibly wrong on inspection.

3. **Score every candidate (machine-unit, Baker-span) pairing.** For
   each of the 60 machine units and each contiguous span of up to 24
   Baker sentences, compute content-word Jaccard similarity (lowercased
   words ≥3 letters, common stopwords removed) multiplied by a
   length-balance factor (`min(len)/max(len)` of the two word-sets) so a
   long span can't win purely by containing more vocabulary — it must
   also be roughly proportionate in size.

4. **Monotonic dynamic programming picks the alignment.** A DP table
   where `score[i][j]` is the best cumulative similarity using the
   first *i* machine units and first *j* Baker sentences; at each step a
   unit either skips (small penalty, −0.05, for units with no real
   Baker counterpart) or consumes a span `[j, k)` scored as above.
   Monotonicity — unit order and Baker-sentence order both strictly
   increase — enforces that an earlier unit can't be matched to later
   Baker text than a later unit, which is the correct constraint since
   both texts follow the same narrative order. Backtracking recovers,
   for every unit, its matched Baker span.

5. **Human patching of the DP's failure modes.** The automatic pass
   aligned 58/60 units correctly; the remaining cases needed a person:
   - Two units have **no Baker counterpart at all** (the chapter
     argumentum and the leonine-verse couplet — see "Unscored by
     design" below). The DP correctly left these unaligned; these were
     confirmed as non-failures and excluded from scoring.
   - A **footnote citation leaked into a reference span** where a
     footnote sat mid-page rather than at the page bottom, past the
     page-cleaner's detection. Found by grepping aligned refs for
     footnote-citation patterns and manually scrubbed.
   - A **charter-formula passage** ("In witness whereof, &c. At
     Westminster…") split across DP boundaries that didn't match how
     the English units broke it up; re-cut by hand across three
     adjacent short units.

   Every hand-patch is recorded with a `manual_fix` provenance note
   directly in `baker_alignment.jsonl` rather than silently folded in.

Steps 1–4 are fully deterministic and reusable: the same
`baker_alignment.jsonl` scored both Fable and Opus without re-running any
of this — `baker_score.py --mt-segments` simply swaps in a different
system's English against the identical aligned references.

## Artifacts

- `baker_alignment.jsonl` — 58 aligned refs (6 hand-patched records carry
  `manual_fix` provenance notes)
- `baker_scores_fable-5.jsonl` / `baker_scores_opus-4-8.jsonl` — per-unit
- `baker_scores_*_summary.json` — the tables above
- MT sources: `03_segmented_text/part1/segments_sentences_xpage.jsonl`
  (fable-5) and `segments_sentences_xpage_opus48.jsonl` (opus-4-8)
