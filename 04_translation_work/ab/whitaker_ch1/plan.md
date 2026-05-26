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
   `chapter2_alignment.jsonl` for `c1_ch2`. Confirmed boundaries:
   - Latin: `p0032_body_l0023` (`CAPVT SECVNDVM.`) through
     `p0035_body_l0022` (`confirmabo.`). ~88 body lines across
     3.5 pages (10 on p0032 + 33 on p0033 + 33 on p0034 + 22 on
     p0035). Note: `p0032_body_l0001`–`l0022` are the ch1 tail
     (questions 4/5/6 enumeration) and `p0035_body_l0023+`
     (`CAPVT TERTIVM.`) is ch3 — both excluded.
   - Parker: `p0043_body_l0006` (`CHAPTER II.`) through
     `p0046_body_l0006`. ~85 body lines (16 on p0043 + 28 on
     p0044 + 35 on p0045 + 6 on p0046).
   Run v4 on `c1_ch2` (3 runs), score against Parker. v4 passes
   the generalization gate iff its `c1_ch2` aggregate mean is
   within ~0.01 of its `c1_ch1` mean and no leakage pattern
   recurs. A stark drop would signal that v4's wins were
   ch1-specific.
4. Final shared-core prompt is locked only after the c1_ch2 check
   passes.

### Phase 5 — Ussher Validation (Britannicarum)

1. Build an Ussher-specific `TRANSLATOR_BRIEF` and Rule 2 register
   clause. **Done 2026-05-18** —
   `translation_prompts_ussher_v5.py` composes locked v4-Whitaker
   shared core (Rule 1 Greek+English-brackets / Latin-paraphrase
   collapse; Rules 5/6/7) with new Ussher corpus skin (Rule 2
   modern scholarly English with Latinate doctrinal vocabulary, no
   Parker anchor; Rule 3 patristic-historical citations, no
   polemical-noun lowercasing; Rule 4 `CAP. I.` style). The user
   directive of 2026-05-18 explicitly supersedes the old Ussher
   `translation_prompts_v4.py` Rule 1 (preserve Latin verbatim) —
   that rule is stale; v5 uses the Whitaker-learned rule.
2. Compose: locked shared core + Ussher corpus skin. **Done.** v5
   registered in `translate_segments.py` dispatch table.
3. Run on a chapter of Ussher Latin. **No human English translation
   exists** for this corpus (the planner's 2026-05-16 reference to
   "the one Ussher chapter for which an English translation exists"
   could not be confirmed in the repo). Per user direction
   2026-05-18: **scoring is author-fidelity LLM-judge only** (no
   COMET, no reference-anchored comparison).
4. The author-fidelity judge (`author_fidelity_judge.py`) extended
   2026-05-18 to support `--corpus ussher` (Ussher rubric prompt
   variant; no Parker reference; drops the `parker_divergence`
   field from output).
5. Output: `ussher_validation_report.md`. Inspect the worst-scoring
   units for systematic issues; iterate v5 corpus skin if a clear
   pattern emerges.
6. **Phase 5 outcome (complete 2026-05-18):** author-fidelity scores
   on Britannicarum p0036 confirmed v5 generalizes correctly.
   Prompt locked as production-ready for Britannicarum.

### Phase 6 — Annals Generalization Test **[COMPLETE 2026-05-25]**

Tests whether `ussher_v5_annals` (Annals corpus skin forked from v5)
transfers to Ussher's *Annales Veteris Testamenti* — a different
genre (biblical-chronological) with pervasive date annotations and
denser classical citation patterns than Britannicarum.

1. **OCR & annotation.** OCR'd 6 Latin pages (p0383–p0388, Vol I)
   and 5 English pages (p0695–p0699, 1658 Hamilton translation).
   Both manually reviewed and locked.
2. **Register modernization.** 1658 Restoration-era English
   register-normalized to Parker 1849 scholarly style via
   `modernize_to_parker_register.py` → sidecar
   `annals_english_parker_style.jsonl` (327 lines, 0 errors).
3. **Translation runs.** `ussher_v5_annals` run × 3 over p0383–p0388
   (289 segments/run). Prompt forked from v5: identical HARD_RULES,
   new TRANSLATOR_BRIEF for biblical-chronological genre.
4. **COMET scoring.** Chunked reference-based COMET-DA (34 chunks,
   8 reference lines/chunk) via `annals_chunked_comet_score.py`.
   Token-bridge alignment on run01.
5. **Author-fidelity judging.** `author_fidelity_judge.py` extended
   2026-05-25 to: (a) accept Annals COMET field names
   (`chunk_id`/`latin`/`machine`) alongside Whitaker format;
   (b) add `--resume` / `--no-resume` for quota-safe reruns.
6. **Report.** `04_translation_work/ab/p0383_p0388/ussher_v5_annals/
   report.md`.

**Phase 6 outcome:** PASS. See §12 revision log entry 2026-05-25.

### Phase 7 — Antiquitates Deployment and Cross-Corpus Exemplar Injection

*Added 2026-05-25 following Phase 6 genre-proximity analysis.*

**7.1 Prompt for Antiquitates**

Use `ussher_v5` unchanged. *Antiquitates* is genre-adjacent to Whitaker's
*Disputatio* (polemical-scholarly argumentation, Patristic Greek citations,
discursive prose), not to the Annals (biblical-chronological computation).
The `ussher_v5` TRANSLATOR_BRIEF is already calibrated for ecclesiastical-
historical Latin; no new corpus skin is needed. The `ussher_v5_annals` fork
was necessary precisely because the Annals is a different genre — that
reasoning does not apply here.

**7.2 Further Whitaker Refinement (pre-Antiquitates)**

Before injecting exemplars into the Antiquitates prompt, address the two
priority refinement candidates in the Whitaker baseline:

1. ~~Diagnose persistent low-COMET units `u002` (0.578) and `u007` (0.742)
   from ch1.~~ **RESOLVED 2026-05-25 — both are COMET/alignment artefacts,
   no prompt fix warranted.**
   - **u002 (chapter subtitle):** v4 output is word-for-word identical to
     Parker; the only difference is casing (Parker prints the subtitle in
     ALL CAPS, v4 produced normal sentence case). The 0.578 score reflects
     COMET case-sensitivity plus short-segment deflation on a ~10-word
     heading. Translation is perfect; normal-case output is arguably more
     correct than mimicking print-only all-caps.
   - **u007:** Two non-error factors. (a) **Alignment boundary mismatch** —
     the Latin unit begins mid-sentence at `industriamque acuit`, so v4
     correctly renders "and sharpens their industry," but Parker's
     translator split the sentence elsewhere and that clause sits in the
     neighboring English unit; the extra clause vs the Parker reference
     depresses COMET. (b) **Parker paraphrase** — Parker adds "their
     meaning" (not in the Latin) and renders `diligentissime` as "with
     anxious toil"; v4 is more literal. By the author-fidelity criterion,
     v4 is preferable; COMET penalizes it precisely for not copying
     Parker's editorial flourishes.
   - **No edit to `translation_prompts_whitaker_v4.py`.** Optional cosmetic
     cleanup: re-cut `chapter1_alignment.jsonl` so the "sharpens their
     industry" clause sits in the same unit on both sides — raises u007's
     COMET without touching the prompt. Cosmetic only; deferred.

2. **Implicit-insertion pattern — do NOT add a rule now (contingency only).**
   The cf=4 pattern (`[we learn]`, subject-pronoun expansions, enclitic
   connector translations) appears in both Whitaker ch2 and Annals, but it
   is **not currently worth a HARD_RULES addition**:
   - cf=4 is a good score, not a failure; the judge described the insertions
     as "judged necessary," and many genuinely are — Latin is pro-drop, uses
     enclitic `-que`, and omits the copula, so English often *requires* the
     supplied words. A blanket rule risks trading a cosmetic cf ding for real
     fluency/grammaticality damage. The model already brackets the truly
     editorial insertions (`[we learn]`), which is the correct signal.
   - A "discourage X unless grammatically unavoidable" rule is a *judgment*
     instruction (high attention cost, inconsistently applied), unlike cheap
     mechanical rules ("preserve Greek verbatim"). v3's regression is direct
     evidence that marginal rules degrade *unrelated* behaviors via attention
     budget (segment-boundary leakage on u009/u010/u012/u013). §2 discipline:
     prefer consolidation over addition.
   - **Trigger to revisit:** only if a future chapter shows content_fidelity
     drop below ~4.0, or the insertions shift from cosmetic to genuine
     omission/distortion. Until then, accept cf=4 — chasing cf=4→5 is chasing
     the metric, not the translation (cf. the u002/u007 diagnosis, §7.2 item 1).
   - **If ever pursued:** consolidate one bracketing clause into an existing
     rule (Rule 5 subject-continuity or the content-fidelity language), not a
     new standalone rule, and gate it through the §7.3 ablation test.

**7.3 Cross-Corpus Exemplar Injection**

Whitaker/Parker pairs are high-quality register exemplars for Antiquitates
because both works share genre and target register. Methodology:

1. **Identify candidates** from `chapter1_alignment.jsonl` /
   `chapter2_alignment.jsonl`. **Filter revised 2026-05-25 to
   fidelity-first:** `content_fidelity = 5 AND register_fidelity = 5`,
   selecting for pattern diversity. The original `COMET ≥ 0.78` gate was
   **dropped** — it yielded only 1 candidate (ch2_u001) and excluded the
   best Greek-preservation units *by design*: every unit where v4
   correctly preserved Greek that Parker dropped has `div=major` and low
   COMET (e.g. ch2_u004/u008/u015 at COMET 0.59–0.69 but `gp=5 ph=5`).
   The high-COMET gate therefore filtered out exactly the behavior the
   exemplars are meant to teach. Author-fidelity scores (cf/rf) measure
   "clean exemplar" directly and better. (ch1 has COMET but no fidelity
   scores, so selection drew from ch2, which has full dual scoring.)

2. **Selected 3 units** (2026-05-25), maximally diverse, all `cf=5 rf=5`:
   - **ch2_u006** — Greek + author's Latin paraphrase collapsed into the
     bracket, inside a named Patristic citation (Eusebius, bk 7 ch 30).
     Covers Rule 1 canonical case + citation form. `gp=5 ph=5`.
   - **ch2_u017** — bare Greek + bracketed English gloss with **no** Latin
     paraphrase in the source (the contrast case; gloss still supplied).
     `gp=5`.
   - **ch2_u029** — plain scholarly prose with crisp antithesis ("They
     affirm it; we deny it"); register/voice anchor, no Greek.

3. **Extracted pairs**: Latin from `annotations/whitaker_latin/`, English
   from the v4 machine output (author-fidelity-validated `cf=5 rf=5`,
   de-hyphenated and trimmed to self-contained sentences).

4. **Injected** as a `REGISTER_EXEMPLARS` section (not in the BRIEF but as
   its own section after HARD_RULES) in a **forked prompt**
   `translation_prompts_ussher_v5_exemplars.py` (registered as
   `ussher_v5_exemplars`). Forked rather than edited in place so plain
   `ussher_v5` remains the untouched control for the ablation test. The
   fork shares HARD_RULES and TRANSLATOR_BRIEF with v5 by identity; the
   only delta is the ~2 kB exemplar block.

5. **Validate** (ablation): run both `ussher_v5` (control) and
   `ussher_v5_exemplars` (treatment) on Britannicarum **p0036** (9 Greek
   lines, fully locked — the Phase 5 page, so Greek exemplars are actually
   exercised), score both with `author_fidelity_judge.py --corpus ussher`.
   **Accept the exemplars only if register_fidelity or content_fidelity
   improves ≥ 0.1; otherwise delete the fork and keep plain ussher_v5.**

**Result (2026-05-26): REJECTED — fork ablated.** Both runs scored all 32
shared units. Group means (judge `claude-sonnet-4-6`, `--corpus ussher`):

| Rubric | control (v5_base) | treatment (v5_ex) | delta |
|---|---|---|---|
| content_fidelity | 4.281 | 4.156 | **−0.125** |
| register_fidelity | 4.812 | 4.781 | **−0.031** |

Neither rubric cleared the +0.10 gate; **both went negative.** Per-unit
data showed churn rather than systematic gain — a few units improved
(l0008 cf +2, l0017/l0024 cf +1) but units already strong in the control
were disrupted (l0009 cf 5→3, l0034 cf 4→2 / rf 5→3, l0007 cf/rf −1 each).
This reproduces the **v3 attention-budget regression**: the ~2 kB
`REGISTER_EXEMPLARS` block displaced attention from the passage under
translation, degrading exactly the units the shared core already handled
well. Conclusion: cross-corpus register exemplars do **not** earn their
place for this prompt. The fork
(`translation_prompts_ussher_v5_exemplars.py`) and its `translate_segments`
dispatch entry were deleted; plain `ussher_v5` remains the production
prompt. Ablation harness retained at
`08_working_scratch/pipeline_scripts/ablation_verdict.py`; the
`segments_to_fidelity_input.py` bridge (general, reusable) is kept.

**Implication for §7.4 (Antiquitates exemplars):** the §7.4 plan to inject
Whitaker/Parker pairs into the Antiquitates prompt is now **discouraged** —
this ablation is the direct test of that hypothesis on a genre-adjacent
page and it failed. Pursue register tuning through the BRIEF/HARD_RULES
(consolidation, not addition) rather than appended exemplar blocks.

**Discipline:** These are register exemplars (target style), not content
exemplars (few-shot answers). Monitor that Whitaker's polemical-theological
phrasing does not bleed into Antiquitates output.

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

**Moved into scope (Phase 7, 2026-05-25):**
- Cross-corpus exemplar injection: using Whitaker/Parker aligned pairs
  as register exemplars in the `ussher_v5` Antiquitates prompt. Previously
  deferred as "permanent few-shot exemplars" — now scoped as a gated
  Phase 7 experiment with explicit ablation test before acceptance.

## 12. Revision Log

- **2026-05-25 (ch1 u002/u007 diagnostic closed).** The two persistent
  low-COMET units flagged 2026-05-17 are confirmed COMET/alignment
  artefacts, not prompt failures. u002 is a word-for-word-correct chapter
  subtitle deflated by all-caps-vs-normal-case + short-segment behavior;
  u007 is depressed by an alignment boundary mismatch (Latin unit cut
  mid-sentence) plus Parker's stylistic paraphrasing that author-fidelity
  scoring does not want v4 to imitate. No edit to
  `translation_prompts_whitaker_v4.py`. See §7.2 item 1 for detail.

- **2026-05-25 (Phase 6 complete — Annals generalization test).**
  `ussher_v5_annals` evaluated on *Annales Veteris Testamenti* p0383–p0388
  (6 Latin pages, 3 runs, 34 COMET chunks) against the 1658 Hamilton
  English register-normalized to Parker 1849 style.
  - **COMET (machine vs modernized 1658 English):** run01 0.6967,
    run02 0.6973, run03 0.6978. Cross-run range mean 0.013 — highly
    stable (lower variance than any Whitaker run).
  - **Author-fidelity (run01, 34 chunks):** content_fidelity 4.24/5,
    register_fidelity 4.88/5, greek_preservation 5.00/5 (n=2; 32 n/a —
    few Greek citations in these pages), paraphrase_handling 4.00/5 (n=2).
  - **Flags:** 4 chunks scored cf=3 (two doubled-phrase artifacts in
    chunks 023/034; one dropped verb in chunk 012; one line-break
    completion in chunk 005). None are systemic prompt failures.
  - **Decision:** PASS. No prompt revision needed. `ussher_v5_annals`
    is production-ready for the Annals corpus. The COMET gap vs the
    1658 reference is expected — Hamilton's Restoration register
    inherently differs from the v5 modern-scholarly target.
  - Artifacts: `04_translation_work/ab/p0383_p0388/ussher_v5_annals/`
    (run01–03 JSONL, alignment, COMET scores/summary, fidelity scores,
    `report.md`).
  - Infrastructure additions: `annals_chunked_comet_score.py`
    (chunked reference-COMET with token-bridge alignment);
    `author_fidelity_judge.py` updated with `--resume`/`--no-resume`
    and dual-format field normalization.

- **2026-05-18 (Phase 4 complete; v4 locked; moving to Phase 5).**
  v4 evaluated on c1_ch2 (33 alignment units × 3 runs) with dual scoring:
  - **COMET vs Parker (1849):** ch2 mean = 0.7074 vs ch1 mean = 0.7651
    (-0.058). Phase 4's COMET-only gate (±0.01) FAILS.
  - **LLM-judge author-fidelity (Sonnet 4.6, run01, 33 units):**
    content_fidelity 4.48/5, register_fidelity 4.85/5, greek_preservation
    5.00/5 (when applicable, n=10), paraphrase_handling 4.86/5 (when
    applicable, n=7).
  - **Cross-tab finding:** 8 of 33 units flagged "major" Parker
    divergence (Parker dropped Greek script in patristic citations that
    Whitaker wrote; v4 correctly preserved). Those 8 units have mean
    COMET 0.6343 but PERFECT greek_preservation = 5.00. Excluding them,
    the remaining 25 units mean COMET = 0.7252, ~0.025 below ch1.
  - **Decision (user direction 2026-05-18):** accept the COMET drop as
    a measurement artifact of the Parker-anchored metric; v4 remains
    the locked working baseline. The user's stated criterion is
    AUTHOR-fidelity (follow Whitaker, not Parker's editorial choices).
    By that criterion v4 generalizes correctly to ch2.
  - **Phase 4 outcome:** PASS on author-fidelity criterion. The
    COMET-only gate is retired in favor of dual scoring (COMET for
    deterministic context + LLM-judge for author-fidelity verdict).
  - Artifacts: `whitaker_v4_ch2_unit_scores.jsonl`,
    `whitaker_v4_ch2_fidelity_run01.jsonl`,
    `whitaker_v4_ch2_combined_report.md`,
    `author_fidelity_judge.py` (08_working_scratch/pipeline_scripts).
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
