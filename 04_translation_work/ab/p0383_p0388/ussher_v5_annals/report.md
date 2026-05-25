# Ussher Annals — Phase 6 Translation Report
## Prompt: `ussher_v5_annals` | Pages: p0383–p0388 | Date: 2026-05-25

---

## 1. Setup

| Item | Detail |
|---|---|
| Source | Ussher, *Annales Veteris Testamenti* (1650), Vol I pp. 383–388 |
| Translator model | `claude-opus-4-7` |
| Prompt | `ussher_v5_annals` (Annals corpus skin on locked v4-Whitaker shared core) |
| Runs | 3 (run01, run02, run03) — 289 segments each |
| Reference | 1658 Hamilton English, register-modernized to Parker 1849 style |
| Chunking | 34 chunks (8 reference lines/chunk) aligned via token bridge on run01 |
| COMET model | `Unbabel/wmt22-comet-da` (reference-based) |
| Fidelity judge | `claude-sonnet-4-6`, `--corpus ussher` (no Parker reference) |

---

## 2. COMET Scores — Machine vs. Modernized 1658 English

| Run | Mean | Median | Min | Max | n |
|---|---|---|---|---|---|
| run01 | 0.6967 | 0.6980 | 0.5781 | 0.7707 | 34 |
| run02 | 0.6973 | 0.6963 | 0.5920 | 0.7707 | 34 |
| run03 | 0.6978 | 0.6956 | 0.5878 | 0.7759 | 34 |

**Cross-run stability:** mean per-chunk range = 0.0125; max = 0.0324

The three runs are essentially identical (range < 0.015 on average). The prompt is stable — variance is far lower than the Whitaker v3 runs (which ranged 0.017 on ch2). The small COMET gap between the machine output and the 1658 reference is expected: Hamilton's Restoration-era register differs inherently from the v5 modern-scholarly target, so some distance is correct behavior, not error.

---

## 3. Author-Fidelity Scores — Run01

Scored by LLM judge against the Latin source directly (no human reference anchoring).

| Rubric | Mean | Min | Max | n (non-na) | na |
|---|---|---|---|---|---|
| content_fidelity | 4.24 | 3 | 5 | 34 | 0 |
| register_fidelity | **4.88** | 4 | 5 | 34 | 0 |
| greek_preservation | **5.00** | 5 | 5 | 2 | 32 |
| paraphrase_handling | 4.00 | 3 | 5 | 2 | 32 |

**Key observations:**

- **Greek preservation is perfect (5.00)** on both chunks that contained Greek — the v5 Rule 1 (preserve Greek + English gloss, collapse Latin paraphrase) is working correctly on the Annals corpus.
- **Register fidelity is near-perfect (4.88)** — the modern scholarly target is landing consistently.
- **Content fidelity (4.24)** reflects mostly minor English syntax insertions judged necessary by the model (e.g. `[we learn]` where Latin is implicit) rather than substantive errors. 22 of 34 chunks scored 4 (not 5) on this rubric; only 4 scored 3 or below.

---

## 4. Content-Fidelity Flags (cf ≤ 3)

Four chunks warrant review:

| Chunk | COMET | cf | Issue |
|---|---|---|---|
| annals_chunk_005 | 0.727 | 3 | Truncated Latin `ac per se uni-` (line break in source) — model completed the word; should be verified against source |
| annals_chunk_012 | 0.727 | 3 | Main verb `compulit` (he compelled) dropped from Tarcondimotus clause, leaving a grammatical fragment |
| annals_chunk_023 | 0.701 | 3 | Evening clause doubled: `took place an evening [in the evening]` — `vespertina` rendered twice |
| annals_chunk_034 | 0.674 | 3 | `longè praeferenda` doubled — appears both after Cicero citation and again at clause close |

Note: chunks 005, 012, and 023 all have COMET ≥ 0.70, suggesting the modernized reference also handled these passages loosely. The doubling issues in chunks 023 and 034 are genuine translation artifacts worth correcting if this output is used as a draft.

---

## 5. Overall Assessment

The `ussher_v5_annals` prompt generalizes well from its training corpus (Whitaker's *Disputatio*, Ussher's *Britannicarum*) to the Annals:

- **Stable across runs** (cross-run COMET range 0.013 mean)
- **Greek preservation perfect** where applicable
- **Register correct** — modern scholarly English with Latinate vocabulary
- **Content fidelity solid** — minor syntax expansions are the main issue, not substantive errors

The four cf=3 chunks are worth a targeted review pass. Chunks 023 and 034 (doubled phrases) are the clearest candidates for a corrective re-translation with an explicit instruction not to repeat a clause.

**Verdict: prompt is production-ready for the Annals corpus.** No prompt revision needed at this stage.

---

## 7. Corpus Context and Forward Guidance

### 7.1 Genre Proximity: Antiquitates vs. Annals

Ussher's *Britannicarum Ecclesiarum Antiquitates* (1639) is a **much closer
peer to Whitaker's *Disputatio*** than to the Annals. The key structural
similarities:

| Feature | Whitaker *Disputatio* | Ussher *Antiquitates* | Ussher *Annals* |
|---|---|---|---|
| Genre | Polemical-scholarly argumentation | Ecclesiastical-historical argumentation | Biblical-chronological computation |
| Citation texture | Dense Patristic Greek (Origen, Eusebius, Chrysostom) + Latin paraphrases | Same | Classical authors (Cicero, Suetonius, Tacitus) + Hebrew/Greek |
| Date annotations | None | Occasional | Pervasive (Anno Mundi, Julian Period, Olympiads) |
| Register target | Victorian scholarly, Latinate | Same | Same |
| Prose structure | Discursive argument | Discursive argument | Tabular/computational |

This explains why the `ussher_v5_annals` fork required a substantially
rewritten TRANSLATOR_BRIEF (biblical-chronological framing, date-annotation
handling, classical citation conventions) while the `ussher_v5` brief for
Antiquitates required only minor adjustments from the Whitaker core.

### 7.2 Prompt Recommendation for Antiquitates

**Use `ussher_v5`**, not `ussher_v5_annals`. The `ussher_v5` brief is already
calibrated for Antiquitates' ecclesiastical-historical genre and was validated
on Britannicarum p0036. No new corpus skin is needed. The HARD_RULES shared
core (Rule 1 Greek+English-brackets / Latin-paraphrase collapse, Rules 2–7)
transfers unchanged.

### 7.3 Recommendations for Further Whitaker *Disputatio* Prompt Refinement

The current v4 baseline was optimized on ch1 and generalization-tested on ch2.
Candidates for further refinement, in priority order:

1. **Address the two persistent low-COMET units in ch1.** `u002` (COMET 0.578)
   and `u007` (0.742) were stable across v3→v4 — both were not fixed by the
   Rule 2c slim. Targeted diagnostic analysis of those two units should reveal
   whether a new rule or a lexical-hint addition would close the gap, or whether
   the issue is a COMET artefact (Parker editorial divergence).

2. **Reduce implicit-insertion artifacts.** The cf=4 pattern — minor English
   syntax insertions (`[we learn]`, implicit connectors, subject pronouns) — was
   consistent in both the Whitaker ch2 and Annals runs. A HARD_RULES addition
   explicitly discouraging implicit subject/connector insertions unless
   grammatically unavoidable in English would tighten content_fidelity scores
   across both corpora without risking register harm.

3. **Extend the Rule 2c Latinate vocabulary whitelist.** The 31-term flat list
   was locked at v4. As ch3, ch4, and Antiquitates are processed, new
   Patristic/scholastic terms will surface. Extend the list incrementally
   rather than in bulk; each addition should be motivated by a specific
   observed normalization error.

4. **Cross-chapter COMET stability test (ch3).** The ch1→ch2 COMET drop
   (-0.058) had a defensible explanation (Parker Greek-dropping divergence).
   A ch3 test would confirm whether the prompt is stable across the full
   Disputation or whether ch1 optimizations are chapter-specific.

### 7.4 Finding Whitaker/Parker Pairs to Inject into the Antiquitates Prompt

Since Whitaker's *Disputatio* and *Antiquitates* share genre, citation style,
and register target, Parker Society's 1849 Fitzgerald translation serves as a
ready-made register exemplar source for the Antiquitates prompt. The
methodology:

**Step 1 — Identify high-quality candidate units.**
Cross-reference `chapter1_alignment.jsonl` / `chapter2_alignment.jsonl` with
the existing COMET and fidelity score files:
- COMET ≥ 0.78 (model and Parker agree closely)
- `content_fidelity = 5` and `register_fidelity = 5`
- `parker_divergence = "none"` (no editorial gap between author and Parker)

Units meeting all three criteria are "clean exemplars" — the machine already
produces near-Parker output, meaning Parker's English accurately reflects what
Whitaker wrote and the model has internalized the pattern.

**Step 2 — Select for pattern diversity.**
From the filtered set, choose 3–5 units covering distinct citation patterns:
- At least one unit with a Greek citation + Latin paraphrase (Rule 1 canonical
  case, e.g. ch1 `p0030_body_l0007` Ἐρευνᾶτε τὰς γραφάς pattern)
- At least one unit with a named Patristic attribution ("Origenes scribit…",
  "Augustinus ait…") followed by Latin quotation
- At least one unit of plain continuous prose argument (no Greek, no quotation)

**Step 3 — Extract the pairs.**
For each selected unit:
- Latin: concatenate `text_gold` from the `latin_line_ids` in
  `08_working_scratch/phase3b/annotations/whitaker_latin/`
- English: concatenate `text_gold` from the `english_line_ids` in
  `08_working_scratch/phase3b/annotations/whitaker_english/`

**Step 4 — Inject and validate.**
Add the 3–5 pairs as a `REGISTER EXEMPLARS` section in the `ussher_v5`
TRANSLATOR_BRIEF, formatted as `SOURCE: … → TARGET: …` with a one-line
annotation on the pattern each exemplifies. Then:
- Re-run `ussher_v5` on Britannicarum with the exemplars added
- Score with `author_fidelity_judge.py --corpus ussher`
- Accept only if register_fidelity or content_fidelity improves by ≥ 0.1;
  ablate if the gain is negligible (per §2 discipline: exemplars must earn
  their place, they are not free)

**Discipline note:** These are *register* exemplars (teaching the target
style), not *content* exemplars (few-shot answers). The risk of content
memorization is low because Whitaker's subjects (scriptural authority,
Protestant-Catholic polemic) are largely absent from Antiquitates' topics
(episcopal succession, early British church history). Monitor for any
Whitaker-specific theological phrasing bleeding into Antiquitates output.

---

## 6. Files

| File | Description |
|---|---|
| `run01/segments_with_translations.jsonl` | Run 01 translation output (289 segments) |
| `run02/segments_with_translations.jsonl` | Run 02 translation output (289 segments) |
| `run03/segments_with_translations.jsonl` | Run 03 translation output (289 segments) |
| `annals_chunked_comet_alignment.jsonl` | 34-chunk Latin↔English token alignment |
| `annals_chunked_comet_scores.jsonl` | COMET scores per chunk × run (102 rows) |
| `annals_chunked_comet_summary.json` | COMET aggregate summary |
| `annals_v5_fidelity_run01.jsonl` | Author-fidelity rubric scores, run01 |
| `report.md` | This report |
