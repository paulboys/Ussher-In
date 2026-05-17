# Phase 2 diagnostic categories — Whitaker c1_ch1 baseline vs Parker Society

Baseline: `translation_prompts_whitaker.py` produced an aggregate
COMET-DA score of **0.7494** against the 1849 Parker Society reference
on c1_ch1 (15 alignment units × 3 runs = 45 records). The prompt is
highly deterministic (per-run means span only 0.002).

Divergences are **stylistic, not substantive**. The baseline is often
*arguably more faithful* to the Latin than Parker; Parker's choices
reflect mid-19th-century Victorian scholarly conventions that the
strict-modern v1-baseline rule set actively suppresses.

## Categories observed across the 5 lowest-scoring units

### C1 — Register tier: gold-standard archaisms suppressed by Rule 2

**Evidence — `ch1_u002` (0.5671), the worst unit:**

| | text |
|---|---|
| LAT | `In quo Controuerſia hæc omnis in ſuas particulares quæſtiones diſtribuitur.` |
| Parker | `WHEREIN THIS WHOLE CONTROVERSY IS DISTRIBUTED INTO ITS PARTICULAR QUESTIONS.` |
| Baseline | `In which this whole controversy is distributed into its particular questions.` |

Sole divergence: Parker `WHEREIN`, baseline `In which`. Hard Rule 2
forbids `wherein` and several other archaisms; the gold standard uses
some of them. The baseline correctly follows Rule 2, but Rule 2 is
miscalibrated against the gold standard register.

**Fix:** soften Rule 2 from "no archaisms" to "match the register of
the 1849 Parker Society translation; period constructions are
acceptable when they appear naturally in the gold standard." This
generalizes to Ussher (whose gold standard, when one exists, is the
register target — not strict modern English).

### C2 — Authorial voice: Latin plural `nos`/`-mus` → English "I"

**Evidence — `ch1_u012` (0.7269):**

| | text |
|---|---|
| LAT | `eam omnem in ſex quæſtiones hac ratione diſtribui poſſe iudicamus` |
| Parker | `I think it may be all divided into six questions, after the following manner` |
| Baseline | `we judge that the whole of it can be distributed in this way into six questions` |

Whitaker writes in first-person plural (`ponemus`, `iudicamus`,
`affirmamus`) — pluralis maiestatis. Parker treats this as
authorial-singular "I". Baseline preserves the plural literally.

**Fix:** new rule — single-author first-person plural (`-mus` verbs
without an explicit antecedent group) renders as English "I" / "my".
Likely generalizes to Ussher (also a single-author work).

### C3 — Rhetorical figures: litotes preserved verbatim

**Evidence — `ch1_u009` (0.6359):**

| | text |
|---|---|
| LAT | `Omnes enim Chriſto non obſcurum teſtimonium dicunt` |
| Parker | `All parts give plain testimony to Christ` |
| Baseline | `For all of them give no obscure testimony to Christ` |

Baseline preserves the Latin litotes (`non obſcurum` → `no obscure`);
Parker normalizes to the positive (`plain`). Both are correct;
Parker's reads more naturally in English.

**Fix:** optional rule — when a Latin litotes (`non` + negative
adjective) has a clean positive equivalent in English, prefer it.
Generalizes.

### C4 — Voice (active/passive)

**Evidence — same unit `ch1_u009`:**

| | text |
|---|---|
| LAT | `Scripturas autem & Papiſtæ celebrant` |
| Parker | `But the scriptures are praised by the papists` |
| Baseline | `The Papists too celebrate the Scriptures` |

Baseline preserves the Latin active (`celebrant` → `celebrate`); v1
lexicon Voice rule explicitly says "render Latin active verbs in
English active voice". Parker switches to passive (`are praised by`)
because the topic is the scriptures, not the papists.

**Fix:** loosen the Voice rule — prefer active when English idiom
naturally accepts it, allow passive when the discourse focus warrants.
Generalizes.

### C5 — Scripture citation style

**Evidence — `ch1_u003` (0.7506):**

| | text |
|---|---|
| LAT | `quæ apud Iohanem Euangeliſtam habentur, cap. 5. 39.` |
| Parker | `which are to be found in the fifth chapter of St John's Gospel at the thirty-ninth verse` |
| Baseline | `which are found in John the Evangelist, chapter 5, verse 39` |

Baseline uses numerals; Parker uses spelled-out ordinals and Victorian
phrasing (`fifth chapter`, `thirty-ninth verse`, `St John's Gospel`).

**Fix:** lexicon hint or rule — Scripture references render with
spelled-out ordinals when the gold-standard register is Victorian
scholarly. Possibly Whitaker-specific (Ussher's references may differ).

### C6 — Polemical noun casing (Whitaker/Parker convention)

**Evidence — `ch1_u009` and `ch1_u010`:**

| LAT | Parker | Baseline |
|---|---|---|
| `Papiſtæ` | `papists` | `Papists` |
| `Scripturas` | `scriptures` | `Scriptures` |

Parker lowercases both "papists" and "scriptures" in running prose
(though it capitalizes "scripture" in some constructions). Baseline
capitalizes both.

**Fix:** corpus-skin lexicon hint specific to Whitaker/Parker. Does
not generalize to Ussher.

### C7 — Roman numerals in titles

**Evidence — `ch1_u001` (0.8827, highest scorer):**

| | text |
|---|---|
| LAT | `CAPVT PRIMVM.` |
| Parker | `CHAPTER I.` |
| Baseline | `CHAPTER ONE.` |

Trivial divergence. Baseline spells out cardinal; Parker uses Roman
numeral. Corpus-specific convention.

**Fix:** rule — render `CAPVT PRIMVM.` style titles as Roman numerals
(`CHAPTER I.`). Likely Whitaker-specific.

## Categorization for prompt architecture

| # | Category | Severity | Shared core or corpus skin? |
|---|---|---|---|
| C1 | Register tier | High (worst unit) | Shared core (register-by-reference principle) |
| C2 | Authorial "I" | High | Shared core (likely transfers to Ussher) |
| C3 | Litotes normalization | Medium | Shared core |
| C4 | Voice flexibility | Medium | Shared core (loosen v1 lexicon rule) |
| C5 | Scripture citation style | Medium | Mixed — principle is "match gold-standard reference style" (general); specifics are corpus |
| C6 | Polemical noun casing | Low–Medium | Corpus skin (Whitaker/Parker only) |
| C7 | Roman numerals in chapter titles | Low | Corpus skin |

## Proposed `whitaker_v2.py` deltas

1. **Rule 2 rewrite** (shared core register principle):
   "Match the register of the corpus's gold-standard reference. For
   Whitaker, that is the 1849 Parker Society translation, which uses
   formal Victorian scholarly English including period constructions
   (`wherein`, `whence`, `hath`, `whilst`) and Latinate vocabulary.
   Do not introduce archaisms gratuitously, but do not strip ones
   that appear naturally in the gold standard."

2. **New rule — authorial "I"** (shared core):
   "In single-author works, Latin first-person plural verbs and
   pronouns (`ponemus`, `iudicamus`, `nos`, `nobis`) referring to
   the author alone render as English first-person singular (`I`,
   `me`, `my`). Use plural only when the Latin clearly refers to a
   group including the author (e.g. `nos omnes`)."

3. **New rule — rhetorical figures** (shared core):
   "Where Latin uses litotes (`non` + negative adjective), prefer the
   English positive equivalent when it reads naturally (`non
   obscurum` → `plain`, not `no obscure`). Where Latin uses
   double-negation idiomatically, render the meaning, not the form."

4. **Lexicon hint adjustment — voice** (shared core, replaces v1's
   strict active-voice rule):
   "Render in the voice that English idiom and discourse focus
   warrant. Active is the default; passive is appropriate when the
   discourse topic is the patient rather than the agent, or when the
   gold standard uses passive."

5. **New rule — citations** (shared core principle):
   "Where the source uses abbreviated citation forms (`cap. 5. 39`,
   `lib. 2. cap. 40`), expand to the gold-standard reference style.
   For Whitaker / Parker Society, use spelled-out ordinals (`fifth
   chapter`, `thirty-ninth verse`)."

6. **Whitaker corpus-skin lexicon** (new section):
   - `papistae`, `pontifices`, `papisticus` → render lowercase (`papists`,
     `papist`) per Parker convention.
   - `Scripturas` in running prose → lowercase `scriptures` (Parker
     pattern); preserve capitalization where the source emphasizes
     (`SCRIPTURAS` in caps, or in a title).

7. **Whitaker corpus-skin rule — chapter titles**:
   `CAPVT PRIMVM.` → `CHAPTER I.`; `CAPVT SECVNDVM.` → `CHAPTER II.`;
   etc. Roman numerals with terminal period.

## Expected impact

Worst unit (C1, register) has a clean ~0.30 point gap that fixing the
single archaism issue would mostly close. Mid-range units have 2–3
overlapping issues; resolving even half should move the aggregate by
~0.03–0.05. Aspirational target for v2: aggregate mean **≥ 0.78**
(baseline 0.7494, +3.5%).
