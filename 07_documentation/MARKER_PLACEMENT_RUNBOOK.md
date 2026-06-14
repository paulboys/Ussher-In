# Footnote Marker-Placement Runbook (per chapter)

This runbook is an **agentic procedure**, executed by Claude Code inside this
repo. It is *not* a script and makes **no API calls** — the agent reads the
Latin against the English and places each footnote superscript by judgment,
then verifies the result with deterministic checks. Run it **once per chapter,
after the sentence interlinear has been generated** (i.e. after
`translate_sentences.py --cross-page` + `place_markers.py` + `render_interlinear.py`).

## Why this step exists

`place_markers.py` inserts the `^x` footnote anchors into the English using an
LLM pass with an **end-of-line fallback**: when it cannot locate a marker's
anchor word, it appends the caret at the end of the sentence. Those appended
carets *look* placed but sit in the wrong spot, producing trailing **clusters**
like `…their arms?”^b^d^f^h`. This pass finds and fixes them. (The separate
cross-page footnote-desync bug — markers and definitions landing on different
pages — is already handled in `render_interlinear.group_by_page`; do not
re-solve it here.)

## Inputs / source of truth

- **Edit:** `03_segmented_text/<part>/segments_sentences_xpage.jsonl` — the
  sentence's English lives in the **last** `translation_history[].english`.
  Never edit the rendered `.md` (it is regenerated and will overwrite).
- **Render target:** `04_translation_work/ab/antiquitates_<ch>/sentence_interlinear_xpage/<part>/`

## Procedure

### 1. Detect dumped clusters (deterministic)

Scan the chapter's sentences for a trailing run of two-or-more adjacent carets.
This is the cluster signature:

```
regex on each latest english:  (?:\^[A-Za-z]{1,2}){2,}\s*$
```

Also eyeball for a **solitary** trailing caret after sentence-final punctuation
(`…sea.”^p`) — the same fallback can dump a single marker. List every affected
`segment_id` with its dumped marker letters.

### 2. Resolve each marker's anchor (judgment)

For each dumped marker `^x`, find the word it attaches to in the **Latin**
(`latin_text` carries the same `^x` carets) — the token immediately before the
caret. Then locate the corresponding position in the English. Anchor types, in
the order you'll usually meet them in Ussher:

- **Quotation / verse opening** (Latin caret sits at `“` or the first word of a
  quoted scripture/poem): place the English caret at the **opening of the same
  quotation** (after the first word or two of the English quote). Most common case.
- **Proper name / author** (`Origenes`, `Martialis`, `Gregorius`, `Hieronymus`):
  place **immediately after the English form of the name** (Origen, Martial,
  Gregory of Nyssa, Jerome). Maintain a running name-equivalence list per
  chapter; it speeds later chapters and aids consistency.
- **Common word** (`viri`, `idem`, `sub`, `sunt`): place after the English word
  that renders it (men, the same author, under, words).

Placement rules:
- Keep markers in **reading order** within the sentence (e.g. `^t` before `^u`).
  If the translation reordered a name to the front, place the marker at the
  *in-order* occurrence, not the fronted one.
- When a word repeats (e.g. two "under"s), choose a **unique** surrounding
  substring as the anchor so the edit targets the right occurrence.
- Match the printed book's superscript position as closely as the English allows.

### 3. Apply the edit (mechanical, with assertions)

For each affected sentence:
1. Strip the trailing cluster: `re.sub(r'(?:\^[A-Za-z]{1,2})+\s*$', '', english)`.
2. Insert each `^x` after its chosen unique anchor substring. **Assert the
   anchor occurs exactly once** before inserting.
3. **Assert the marker set is unchanged** (same letters before/after — you are
   relocating, never adding or dropping) and **no cluster remains**.
4. Append a **new** `translation_history` entry, do not mutate the old one:
   `{"stage": "marker_placement_handfix", "model": "(hand)", "timestamp": <utc>,
   "english": <fixed>, "version": <prev+1>}`. This preserves provenance.

Write the JSONL back with `ensure_ascii=False` (the text is full of `“ ” ’ æ`
and Greek — never let it escape to `\uXXXX`).

### 4. Re-render

```
python render_interlinear.py --part <part> --format markdown \
  --segments-name segments_sentences_xpage.jsonl \
  --polished-subdir polished_sentences_xpage \
  --out-dir 04_translation_work/ab/antiquitates_<ch>/sentence_interlinear_xpage
```

### 5. Verify (deterministic gate — must pass before commit)

For every rendered page in the chapter:
- **Zero clusters:** no EN line ends with `</sup><sup>…</sup>` adjacency.
- **Zero orphans, both directions:** the set of `<sup>` marker letters in the
  Interlinear body == the set of `^letter` definitions in the Footnotes section.
- **Spot-check** a few placements (a name, a quotation opening, a repeated-word
  case) land at the intended English word.
- **File encoding** is clean UTF-8 (no `U+FFFD`).

If any check fails, return to step 2 for the offending sentence.

## Handoff to the classicist

Markers placed inside quoted **verse/scripture** (Martial, Psalms, Jerome) are
the judgment-heavy cases. Flag those segment_ids in the chapter's
`translation_log.md` so the reviewer can confirm the superscript sits where the
1847 print places it.

## Worked precedent

Chapter 1 (`antiquitates_ch1`, part1): 23 markers across 8 sentences
(`seg_p0032_s0003`, `p0033_s0002`, `p0035_s0004`, `p0036_s0004`, `p0040_s0001`,
`p0040_s0002`, `p0043_s0009`, `p0044_s0001`) relocated from end-clusters to their
anchors; verified zero clusters / zero orphans on all 14 pages. Use it as the
reference example when running a new chapter.
