# Prompt Optimization Plan — Whitaker Chapter 1

**Date:** 2026-05-16
**Owner:** Paul Boys
**Starting prompt:** `08_working_scratch/pipeline_scripts/translation_prompts_whitaker.py`
(formerly planned as `translation_prompts_v4.py`; see §12 Revision Log)

---

## 1. Objective

Optimize the Latin-to-English translation prompt against the 1849 Parker
Society English translation (William Fitzgerald, tr.) of Whitaker's
*Disputatio de Sacra Scriptura*, with the explicit goal that the
resulting prompt transfer cleanly to Ussher's *Britannicarum
Ecclesiarum Antiquitates* — which has no comparable English reference.

Whitaker is the training environment; Ussher is the deployment target.

---

## 2. Strategic Frame

There are two ways to push A/B scores up against a gold standard:

| Track | Mechanism | Whitaker score | Cross-corpus transfer |
|---|---|---|---|
| **Memorization** | Few-shot exemplars from Fitzgerald | High | Poor — bakes in Whitaker voice/content |
| **Internalization** | Diagnose model failures, encode as rules | Moderate | Good — rules are corpus-general |

This plan follows the **internalization** track. Exemplars are permitted
*diagnostically* (to characterize a failure) but must not survive into
the deployed prompt without being ablated and proven redundant by
codified rules.

---

## 3. Prompt Architecture

The prompt is treated as two layers:

| Layer | Components | Optimized against | Deployed to Ussher |
|---|---|---|---|
| **Shared core** | `HARD_RULES`, `LEXICON_LATIN_HINTS`, `LEXICON_GREEK_HINTS`, `OUTPUT_CONTRACT`, `build_translation_prompt` | Whitaker | Unchanged |
| **Corpus skin** | `TRANSLATOR_BRIEF`, Rule 2 register clause | Whitaker | Replaced per author |

Discipline: every change accepted during this exercise must be tagged
*shared-core* or *corpus-skin*. Anything Whitaker-specific (Fitzgerald's
register, polemical-genre patterns) belongs to the skin.

---

## 4. Scope

| Item | Value |
|---|---|
| Source corpus | `08_working_scratch/phase3b/annotations/whitaker_latin/page_p0030.json`, `page_p0031.json` (section_id `c1_ch1`) |
| Reference corpus | 1849 Parker Society English, aligned region of `whitaker_english/` |
| Latin source edition | 1690 Latin edition |
| Reference edition | 1849 Parker Society (William Fitzgerald, tr.) |
| Baseline prompt | `translation_prompts_whitaker_v4.py` (locked 2026-05-17; see §12) |
| Out of scope | The ⟦⟧/⟪⟫ bracket apparatus from v3; permanent few-shot exemplars in the production prompt |

If statistical power is insufficient at 2 pages, scope extends to
Chapter 2 (`c1_ch2`, p0032–p0034).

---

## 5. Workflow

### Phase 0 — Setup (one-time)

**Phase 0.1 — Sentence alignment**

1. Sentence-align the Latin (p0030–p0031, section_id `c1_ch1`) to the
   Parker Society English (p0041–p0042, section_id `c1_ch1`). For 2
   pages × 2 pages, manual alignment is likely faster than tool setup;
   see Task 3 in tasklist.
2. Persist as `chapter1_alignment.jsonl`, one row per aligned unit:
   ```json
   {"unit_id": "ch1_s001",
    "latin_line_ids": ["p0030_body_l0004","p0030_body_l0005"],
    "english_line_ids": ["p0041_body_l0004","p0041_body_l0005","p0041_body_l0006"],
    "notes": ""}
   ```

**Phase 0.2 — Judging stack: hybrid COMET + LLM (user direction 2026-05-16)**

User raised a strong objection to LLM-as-judge as the primary gating
oracle: it is non-deterministic, opinionated in unauditable ways, and
expensive at scale. Replaced by a **hybrid stack**:

| Sub-phase | Tool | Purpose |
|---|---|---|
| Gating (pass/fail per A/B cycle) | COMET (`wmt22-comet-da`) with Parker Society reference | Deterministic, calibrated, locally hosted, principled MT metric |
| Reference-free score on Ussher | CometKiwi (`wmt22-cometkiwi-da`) | Use when no gold standard exists |
| Phase 2 diagnostics (rubric breakdown) | LLM-as-judge (`ab_judge.py`, refactored) | Categorized failure analysis to drive rule changes |

**Phase 0.2a — Calibrate COMET on existing p0041 data.** Before
committing to the hybrid stack, sanity-check that COMET's
directional verdict agrees with the existing LLM-judge verdict on the
p0041 v0-vs-v2 test (which the LLM judge ruled v0-wins). Domain
mismatch is the main risk: COMET was trained on modern WMT data
(news/Wikipedia), not 16th-century scholastic Latin → Victorian
scholarly English. If COMET agrees on direction, we have evidence
the mismatch isn't fatal.

**Phase 0.2b — Build `comet_score.py`.** Reusable module that loads
two segments JSONL artifacts plus optional alignment file, scores each
with COMET (reference) or CometKiwi (reference-free), aggregates, and
emits a report. Both modes share the same CLI shape as `ab_judge.py`.

**Phase 0.2c — Lighter LLM-judge refactor.** Reduced scope:
- Drop ⟦⟧/⟪⟫ bracket rubrics (already mandated by §10.4).
- Add corpus profile (`--corpus ussher|whitaker`) so the rubric prose
  references the right author and gold standard.
- Add `--reference <path>` so the LLM judge can also see the Parker
  Society aligned segment when running diagnostic passes.
- No reframing as the primary gating oracle — COMET handles that.

### Phase 1 — Baseline (`translation_prompts_whitaker.py`)

1. Run the baseline Whitaker prompt over `c1_ch1` pages with 3 runs
   (run01/run02/run03) for stability, mirroring the existing
   `p0041/v0/` layout.
2. Score against the aligned Parker Society sentences using the
   parameterized A/B judge in **reference mode** with the
   `whitaker` corpus profile (see Phase 0.5).
3. Output: `whitaker_baseline/runNN/segments_with_translations.jsonl`,
   judge `summary.json`, baseline `report.md`.

The baseline is named after the prompt, not "v4" — see Revision Log.

### Phase 2 — Diagnostic Analysis

For each aligned unit where v4 diverges from Fitzgerald, classify the
divergence:

- **Lexical sense** — wrong meaning of a polysemous word
- **Register tier** — too modern / too archaic / wrong vocabulary register
- **Construction** — lost subordination, wrong indirect-statement
  scaffolding, mishandled ablative absolute, etc.
- **Format** — Greek handling, citation form, title casing,
  footnote-marker leakage
- **Faithfulness** — content added / dropped / paraphrased away

Group divergences into rule-shaped categories. Each category becomes a
candidate rule change.

### Phase 3 — Iterative Refinement (v5, v6, …)

For each candidate change:

1. Draft the rule edit.
2. Tag it *shared-core* or *corpus-skin*.
3. A/B test the new version against the prior version (3 runs each).
4. Accept only if it passes the pre-registered gates (§7).
5. Log accepted changes in `diagnostic_categories.md` with the
   divergence example that motivated each.

Prefer rule **consolidation** over addition. v3's failure mode was rule
sprawl; we don't repeat it.

### Phase 4 — Ablation / Generalization Check

1. If any few-shot exemplars were used during Phase 3 diagnosis, remove
   them and re-run. Confirm the codified rules carry the gains.
2. Audit every rule added during Phase 3 for Whitaker- or
   Fitzgerald-specificity. Anything genre-bound (theological-polemic
   patterns, Fitzgerald's specific lexical choices) gets demoted to
   corpus-skin or removed.
3. **Cross-chapter generalization (added 2026-05-17).** Build
   `chapter2_alignment.jsonl` for `c1_ch2` (Latin p0032–p0034 →
   Parker p0044–p0047; chapter title `CAPVT SECVNDVM`). Run v4
   on `c1_ch2` (3 runs), score against Parker. v4 passes the
   generalization gate iff its `c1_ch2` aggregate mean is within
   ~0.01 of its `c1_ch1` mean and no leakage pattern recurs. A
   stark drop would signal that v4's wins were ch1-specific.
4. Final shared-core prompt is locked only after the c1_ch2 check
   passes.

### Phase 5 — Ussher Validation

1. Build an Ussher-specific `TRANSLATOR_BRIEF` and Rule 2 register
   clause.
2. Compose: locked shared core + Ussher corpus skin.
3. Run on the one Ussher chapter for which an English translation
   exists (acknowledged dubious quality — used as a *sanity floor*,
   not a gold standard).
4. Output: `ussher_validation_report.md`. Investigate, don't
   auto-reject, points where the model disagrees with that translation.

---

## 6. Artifacts

```
04_translation_work/ab/whitaker_ch1/
├── plan.md                              (this document)
├── chapter1_alignment.jsonl             (Phase 0 output)
├── diagnostic_categories.md             (running log; Phase 2–3)
├── v4/
│   ├── run01/segments_with_translations.jsonl
│   ├── run02/segments_with_translations.jsonl
│   └── run03/segments_with_translations.jsonl
├── v4_baseline_report.md
├── v5/  v6/  …                          (subsequent iterations)
├── vN_vs_vM_report.md                   (per iteration)
└── ussher_validation_report.md          (Phase 5)
```

---

## 7. Pre-registered Acceptance Gates

Borrowed from the existing A/B framework (`p0041_report.md`). A
candidate version `v(N+1)` replaces `vN` only if **all** gates pass:

| Gate | Threshold |
|---|---|
| 1. Mechanical regressions | = 0 (no rule-detector finding increases per segment) |
| 2. Win-rate | ≥ 55%, tie-rate < 30% |
| 3. Rubric coverage | wins ≥ 5/6 rubrics, no losses |
| 4. Position bias | \|P(A) − 0.5\| < 10% |
| 5. Invalid + error rate | < 10% |

---

## 8. Success Criteria

- v(final) beats v4 on **accuracy and fluency** rubrics (the rubrics v3
  lost; see `p0041_report.md`).
- No regression on format_compliance or source_preservation.
- Shared core is verifiably free of Whitaker- or Fitzgerald-specific
  content (Phase 4 audit signed off).
- Ussher validation: prompt produces output the reviewer judges
  qualitatively better than v4-on-Ussher baseline.

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Fitzgerald's idiosyncrasies get encoded as general rules | Phase 4 ablation + per-rule shared-core/corpus-skin tagging |
| 2-page sample too small for statistical power | Extend scope to Chapter 2 if A/B gates oscillate |
| Sentence alignment is noisy | Manual review of `chapter1_alignment.jsonl` before any A/B run |
| Rule sprawl (v3 failure mode) | Prefer consolidation over addition; periodic rule audit |
| Judge reference-mode unsupported | See §10.1 |

---

## 10. Open Questions

**10.1** ~~Does the existing A/B judge accept a sentence-aligned
external reference?~~ **RESOLVED:** No. Existing judge is pairwise
model-vs-model only, hardcoded for Ussher, and assumes v3's ⟦⟧/⟪⟫
bracket framework in its rubrics. Resolution: parameterize the judge
in Phase 0.2 (corpus profile + reference-mode flag).

**10.2** Minimum segment count for meaningful gate evaluation on this
corpus. p0041 had 27 segments and produced 81 judgments (3 runs × 27).
c1_ch1 may have fewer segments after sentence-grouping; if so,
Chapter 2 inclusion is automatic.

**10.3** ~~Whether to keep v4's relaxed Rule 2~~ **RESOLVED:** v4 is
archived. Baseline is `translation_prompts_whitaker.py`, which uses
strict Rule 2 ("no archaisms"). This will likely produce a register
mismatch with Fitzgerald's 1849 register (which uses "hath"); the
mismatch is expected to surface in Phase 2 diagnostics as a
register-tier divergence category, motivating a register refinement
in Phase 3.

**10.4** ~~Whether to retain the v3 ⟦⟧/⟪⟫ bracket framework anywhere
in the system?~~ **RESOLVED:** No. User-directed (2026-05-16): the
mathematical-bracket convention is dropped from both the Whitaker and
Ussher prompts and from the judge. Reasons: (a) v3 failed its A/B test
on accuracy/fluency/register; (b) the bracket characters complicate
the downstream searchable database. Ordinary ASCII `[ ]` for
editorial English glosses remains allowed where natural. The judge's
`format_compliance` rubric is repurposed (see Phase 0.2) and no
longer scores ⟦⟧/⟪⟫ usage.

---

## 11. Out of Scope (Explicitly Deferred)

- Translating the full Whitaker volume (only Chapter 1 is in scope
  here; full-volume work is downstream of this exercise).
- Ussher production translation (only sanity validation in Phase 5).
- Multi-author prompt with author-detection logic (corpus skin is
  human-selected, not auto-detected).
- The v3 ⟦⟧/⟪⟫ mathematical-bracket framework — abandoned permanently
  (see §10.4), not just deferred. Square brackets `[ ]` for editorial
  English glosses remain allowed.

## 12. Revision Log

- **2026-05-17 (Phase 3 closed; v4 locked as working baseline).**
  COMET-DA trajectory on `c1_ch1`: baseline 0.7494 → v2 0.7612 →
  v3 0.7557 (regressed) → v4 **0.7651** (+2.10% over baseline,
  +0.51% over the prior best v2). v3's regression was diagnosed
  as Rule 2c bloat (~65-line Latinate-vocabulary lecture)
  consuming attention budget and causing segment-boundary leakage
  on `u009/u010/u012/u013` run01. v4 slimmed 2c to ~16 lines;
  leakage disappeared, run-to-run variance collapsed (v4 range
  0.003 vs v3 range 0.017). One unit regressed on v4 vs v3 (`u011`,
  -0.017) — flagged for inspection if a v5 iteration is needed.
  v4 is now the working baseline for §4 and Phase 4 generalization.
  Two leftover items below baseline-or-noise after v4: `u002`
  (0.578, persistent register cap) and `u007` (0.742, lexical
  drift); both stable across v3→v4.
- **2026-05-16 (initial)** — plan drafted around `translation_prompts_v4.py`.
- **2026-05-16 (Phase-0 prerequisite findings)**:
  - Discovered `translation_prompts_whitaker.py` already exists with a
    Whitaker-correct Rule 1 (Greek+English-brackets, no Latin-paraphrase
    assumption). v4's Rule 1 was inherited from the Ussher pattern and
    is wrong for Whitaker. Decision: archive v4, use
    `translation_prompts_whitaker.py` as the baseline. v4's
    Latin-preservation insight is preserved for the Ussher exercise.
  - Discovered `ab_judge.py` is Ussher-hardcoded and assumes the v3
    ⟦⟧/⟪⟫ bracket framework. Decision: parameterize into corpus
    profiles, add reference-mode flag (Phase 0.2 added).
  - User direction: drop ⟦⟧/⟪⟫ from the system entirely (both prompts
    and the judge). Reason: v3 failed its A/B test, and the exotic
    brackets complicate the downstream searchable database. Captured
    in §10.4.
  - During Phase 0.1 alignment drafting, observed at Latin
    `p0030_body_l0007` that Whitaker does sometimes follow Greek
    with a Latin paraphrase (`Ἐρευνᾶτε τὰς γραφὰς, Scrutamini
    Scripturas`), contradicting the original `translation_prompts_
    whitaker.py` docstring claim that the pattern doesn't occur. Parker
    Society's handling: Greek preserved + single English rendering of
    the meaning (in caps in print), Latin paraphrase elided. User
    directed (2026-05-16) that this rule be introduced into Rule 1
    proactively rather than discovered empirically in Phase 2. Done:
    `translation_prompts_whitaker.py` Rule 1 now explicitly tells the
    model to COLLAPSE Whitaker's Latin paraphrase into the English-in-
    brackets slot, with positive and negative examples.
  - Whether the same collapse-Latin behaviour generalizes to Ussher is
    deferred to Phase 5 (Ussher validation). For Ussher, v4 currently
    hypothesises preserve-Latin-verbatim; the searchable-database
    requirement may push Ussher toward Whitaker-style collapse too,
    but that decision is empirical.
