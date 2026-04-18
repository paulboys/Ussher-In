# Risk Register

## R1: Ligatures and historical glyphs

Risk: OCR confusion on glyphs and ligatures.
Mitigation: enable preprocessing fallback and target manual review on low-confidence lines.

## R2: Long s and typography variance

Risk: historical letterforms misread as modern characters.
Mitigation: apply pattern checks and conservative manual correction.

## R3: Layout complexity

Risk: footnotes/marginal notes interfere with body-text extraction.
Mitigation: first pass limits scope to body text and preserves placeholders for note linkage.

## R4: Translation drift from source syntax

Risk: machine output over-paraphrases.
Mitigation: literal/academic post-edit policy with glossary consistency checks.

## R5: Non-reproducible pipeline changes

Risk: scripts or settings change without trace.
Mitigation: keep config templates in `06_tools_config/` and append edit history in output metadata.
