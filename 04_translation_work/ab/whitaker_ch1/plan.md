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
| Baseline prompt | `translation_prompts_whitaker.py` |
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

**Phase 0.2 — Parameterize the A/B judge**

Existing `ab_judge.py` is Ussher-hardcoded and v3-bracket-aware in its
rubrics. The bracket framework is being dropped from the whole system
(see §10.4), so the refactor covers both profiles:

- Introduce a `CorpusProfile` abstraction holding `JUDGE_SYSTEM` and
  rubric definitions.
- Define two profiles:
  - `ussher` — Ussher framing, Greek+(optional preserved Latin) pattern
    expected, no ⟦⟧/⟪⟫ scoring.
  - `whitaker` — Whitaker framing, Greek+English-in-square-brackets
    pattern expected, no ⟦⟧/⟪⟫ scoring.
  Format_compliance is repurposed to score the corpus-appropriate
  Greek handling pattern in plain prose (no exotic Unicode brackets).
- Add `--corpus {ussher,whitaker}` CLI flag.
- Add `--reference <path>` CLI flag accepting the
  `chapter1_alignment.jsonl` produced in Phase 0.1. When provided, the
  judge prompt includes the aligned Parker Society English as a
  register/accuracy reference. When omitted, behaviour is the existing
  Latin-as-source-only mode.
- Update tests in `08_working_scratch/tests/test_ab_judge.py`.

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
3. Final shared-core prompt is locked.

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
