# Neuro-Symbolic Translation Plan

**Date:** 2026-05-17
**Project:** Ussher translation pipeline
**Status:** Proposed architecture
**Scope:** Latin/Greek-to-English translation support for Ussher, Whitaker,
near-peer early modern theological corpora, and patristic source material.

---

## 1. Purpose

This document formalizes a neuro-symbolic architecture for the translation
project. The goal is to combine deterministic scholarly controls with neural
translation, retrieval, and evaluation.

The system should not treat an LLM as a standalone translator. Instead, each
translation should be produced from a structured evidence packet:

```text
source segment
+ symbolic features
+ near-peer translation parallels
+ lexicon and morphology hints
+ accepted rules learned from prompt optimization
+ citation and patristic context
+ neural retrieval results
=> constrained LLM translation
=> symbolic and neural validation
=> auditable translation artifact
```

The intended result is a translation workflow that can explain why a rendering
was chosen, which evidence supported it, which rules governed it, and which
validation checks it passed or failed.

---

## 2. Design Principles

1. **Symbolic evidence constrains neural generation.** The symbolic layer
   identifies what must be preserved, normalized, collapsed, flagged, or
   checked before the LLM translates.

2. **Neural systems propose, retrieve, and reason.** Embeddings, rerankers,
   and LLMs are used for semantic retrieval, candidate generation, diagnostic
   analysis, and ambiguous judgment.

3. **Prompt text is not the source of truth.** Learned translation rules
   should live in a versioned rule registry and be compiled into prompts.
   Prompt constants may be experimental artifacts, but accepted rules should
   be represented outside any single prompt file.

4. **Whitaker is the supervised laboratory; Ussher is the deployment target.**
   Whitaker's *Disputatio* can be scored against the Parker Society English
   translation. Ussher usually lacks a gold reference, so Whitaker should be
   used to calibrate rules and validation methods before deployment.

5. **Near-peer parallels are evidence, not imitation targets.** Ussher's
   *Annals*, Whitaker, and patristic translations should inform choices
   without forcing the model to memorize or overfit a single translator's
   English style.

6. **Every accepted change must survive ablation.** Additions to rules,
   retrieval, lexicon hints, or prompt structure should be tested against
   simpler baselines to confirm they add value.

---

## 3. Core Objects

### 3.1 Translation Segment

The segment is the central unit of work. A segment may correspond to a line,
sentence, footnote, marginal note, or manually grouped translation unit.

Suggested JSONL shape:

```json
{
  "segment_id": "ussher_p0041_s003",
  "page_id": "p0041",
  "section_id": "c1_ch1",
  "source_latin": "",
  "source_greek": "",
  "source_text": "",
  "segment_type": "body",
  "symbolic_features": {},
  "retrieval_evidence": [],
  "translation_candidates": [],
  "selected_translation": "",
  "validation": {},
  "notes": []
}
```

### 3.2 Parallel Pair

Near-peer aligned pairs form the project's translation memory and retrieval
corpus.

Suggested JSONL shape:

```json
{
  "pair_id": "whitaker_c1_s017",
  "source_work": "Whitaker Disputatio",
  "source_author": "William Whitaker",
  "translator": "Parker Society",
  "reference_date": 1849,
  "latin": "",
  "greek": "",
  "english": "",
  "metadata": {
    "genre": "theological polemic",
    "confidence": "gold",
    "alignment_method": "manual"
  }
}
```

### 3.3 Symbolic Feature Bundle

Symbolic features are deterministic or semi-deterministic observations attached
to a segment before neural generation.

Example:

```json
{
  "has_greek": true,
  "greek_spans": [],
  "latin_paraphrase_after_greek": null,
  "detected_authors": [],
  "detected_titles": [],
  "detected_scripture_refs": [],
  "footnote_markers": [],
  "lexicon_matches": [],
  "rules_triggered": []
}
```

### 3.4 Rule Registry Entry

Rules learned from prompt optimization should be represented as structured,
versioned records.

Suggested shape:

```json
{
  "rule_id": "R-GREEK-001",
  "name": "Preserve Greek With English Bracket",
  "scope": "shared-core",
  "status": "accepted",
  "trigger": "segment.has_greek == true",
  "instruction": "Preserve Greek verbatim and add concise English in square brackets.",
  "source": "whitaker_ch1_ab",
  "accepted_by": "ablation",
  "notes": []
}
```

Rule status values:

```text
proposed
experimental
accepted
rejected
ablation-needed
corpus-skin-only
```

Rule scope values:

```text
shared-core
ussher-skin
whitaker-skin
patristic-skin
diagnostic-only
```

---

## 4. Symbolic Feature Layer

The symbolic feature layer should run before translation. Its job is to turn
the raw source segment into structured constraints and signals.

### 4.1 Initial Feature Extractors

Implement deterministic extractors for:

| Feature | Purpose |
|---|---|
| Greek span detection | Preserve Greek and trigger bracket-gloss rules |
| Latin/Greek adjacency | Detect possible Latin paraphrase of Greek |
| Footnote-marker sentinels | Prevent caret/superscript leakage into English |
| Named entities | Normalize authors, places, councils, and adversaries |
| Patristic author names | Support citation-aware retrieval |
| Book and treatise titles | Preserve title structure and capitalization |
| Scripture references | Support biblical quotation handling |
| Quotation markers | Distinguish quoted source from authorial prose |
| Date expressions | Preserve chronology and avoid paraphrase loss |
| Ecclesiastical terms | Stabilize technical vocabulary |
| Known formulae | Detect recurring scholastic or patristic phrases |

### 4.2 Lexicon and Morphology Matching

The lexicon layer should provide controlled hints, not forced translations.

Candidate sources:

```text
Lewis and Short
Whitaker's Words
Logeion
Perseus/Morpheus
custom ecclesiastical lexicon
project-specific preferred renderings
Greek lexica for embedded Greek
```

Suggested lexicon match shape:

```json
{
  "token": "ratio",
  "lemma": "ratio",
  "language": "latin",
  "candidate_senses": ["reason", "account", "method", "argument"],
  "project_preferences": ["argument", "account"],
  "confidence": "medium",
  "warning": "Avoid defaulting to modern philosophical 'rationality' unless context requires it."
}
```

### 4.3 Rule Triggering

Feature extractors should trigger rule IDs from the rule registry. The
translation prompt should receive concise, concrete rule instructions rather
than the whole registry.

Example trigger bundle:

```json
{
  "rules_triggered": [
    "R-GREEK-001",
    "R-FOOTNOTE-001",
    "R-TITLE-002"
  ]
}
```

---

## 5. Near-Peer Parallel Corpus

The near-peer corpus supplies symbolic examples and neural retrieval material.

### 5.1 Priority Sources

| Priority | Source | Use |
|---|---|---|
| 1 | Ussher's *Annals* | Best near-peer for Ussherian prose and known English renderings |
| 2 | Whitaker's *Disputatio* | Supervised training environment with Parker Society English |
| 3 | Eusebius, Augustine, Jerome, Basil, and other patristic selections | Citation and quotation parallels |
| 4 | Vulgate, Greek NT, LXX, conciliar formulae | Biblical and ecclesiastical phrase handling |
| 5 | Existing project translations and reviewed outputs | Local style and rule consistency |

### 5.2 Alignment Requirements

Each aligned pair should include:

```text
source work
source author
source language(s)
English reference
translator or edition
date
genre
alignment confidence
line/page references
notes on omissions, paraphrases, or rearrangements
```

### 5.3 Use Policy

Near-peer parallels may be used for:

```text
retrieval evidence
lexical disambiguation
citation recognition
register diagnostics
rule discovery
validation examples
```

Near-peer parallels should not be used as permanent few-shot examples unless
they survive ablation and are proven not to overfit a specific translator or
corpus.

---

## 6. Neural Retrieval Layer

The retrieval layer should use embeddings and reranking to find relevant
evidence before translation.

### 6.1 Retrieval Views

Embed and retrieve across multiple views:

```text
raw Latin
lemmatized Latin
Greek spans
Latin plus Greek
named entities only
citation phrases
symbolic feature signature
English reference text
```

### 6.2 Retrieval Output

For each segment, retrieve:

```text
top lexical parallels
top semantic parallels
top citation or patristic parallels
top Greek/Latin phrase parallels
top project-local reviewed examples
```

### 6.3 Reranking

Rerank retrieved examples using a combination of symbolic and neural signals:

```text
same author
same genre
same patristic source
same biblical source
same lemma pattern
same named entity
same Greek phrase
high semantic similarity
high alignment confidence
```

The final evidence packet should include only a compact set of high-value
parallels.

---

## 7. Evidence Packet Compiler

Before translation, compile an evidence packet that gives the LLM the minimum
necessary context and constraints.

Suggested packet sections:

```text
SOURCE
SYMBOLIC FINDINGS
RULES TRIGGERED
NEAR-PEER PARALLELS
LEXICON AND MORPHOLOGY
TRANSLATION CONSTRAINTS
OUTPUT CONTRACT
```

Example:

```text
SOURCE:
<segment text>

SYMBOLIC FINDINGS:
- Greek span followed by possible Latin paraphrase.
- Detected scripture quotation.

RULES TRIGGERED:
- R-GREEK-001: preserve Greek verbatim and add an English bracket gloss.
- R-WHITAKER-002: collapse Whitaker's Latin paraphrase into the bracket gloss.

NEAR-PEER PARALLELS:
1. Whitaker/Parker: Greek phrase -> "Search the scriptures."
2. Vulgate: Scrutamini Scripturas -> "Search the scriptures."

LEXICON AND MORPHOLOGY:
- scriptura: scripture, writings; here scriptural canon.

TRANSLATION CONSTRAINTS:
- Preserve Greek verbatim.
- Add concise English bracket gloss.
- Do not separately translate the Latin paraphrase.
```

---

## 8. Neural Generation

The LLM should translate from the evidence packet, not from the raw source
alone.

### 8.1 Candidate Generation

Generate multiple candidates under controlled profiles:

| Candidate | Profile |
|---|---|
| A | Strict literal |
| B | Source-preserving scholarly English |
| C | Corpus-skin register target |
| D | High fluency with strict symbolic constraints |

The profiles should be compiled from the rule registry and corpus skin, not
hand-edited ad hoc.

### 8.2 Selection

Candidate selection should combine:

```text
symbolic validation
reference-based metric where available
reference-free metric where no gold standard exists
LLM diagnostic judgment
human review
```

Symbolic hard-rule failures should have veto power.

---

## 9. Validation Layer

Validation should run after candidate generation and before a translation is
accepted.

### 9.1 Symbolic Validators

Initial validators:

| Validator | Failure caught |
|---|---|
| Greek preserved | Greek span dropped or normalized away |
| Bracket gloss present | Greek preserved without English explanation |
| Latin paraphrase policy | Wrong collapse/preserve behavior by corpus |
| Footnote marker leakage | Caret/superscript sentinels copied into English |
| Named entity normalization | Known author/place rendered inconsistently |
| Title preservation | Treatise title dissolved into prose |
| Citation preservation | Biblical or patristic reference dropped |
| Output schema | Invalid JSON or missing fields |
| Forbidden bracket convention | Disallowed exotic bracket apparatus reintroduced |

### 9.2 Neural Validators

Use neural validation where it is appropriate:

| Tool | Use |
|---|---|
| COMET | Whitaker scoring against Parker Society reference |
| CometKiwi | Ussher reference-free quality estimate |
| Embedding similarity | Detect large semantic drift |
| LLM diagnostic judge | Categorized failure analysis, not sole gate |

### 9.3 Validation Report

Each segment should produce a validation report:

```json
{
  "segment_id": "ussher_p0041_s003",
  "candidate_id": "C",
  "symbolic": {
    "passed": true,
    "failures": []
  },
  "neural": {
    "comet": null,
    "cometkiwi": 0.0,
    "embedding_similarity": 0.0
  },
  "diagnostics": [],
  "decision": "accepted"
}
```

---

## 10. Prompt Compiler

The prompt compiler should replace direct hand-editing of large prompt
constants wherever possible.

### 10.1 Inputs

```text
translator brief
accepted shared-core rules
corpus-skin rules
lexicon profile
evidence packet
output contract
candidate-generation profile
```

### 10.2 Outputs

```text
compiled prompt text
prompt metadata
rule IDs included
corpus skin version
lexicon profile version
evidence packet hash
```

### 10.3 Benefits

The compiler should:

```text
prevent accidental prompt drift
make A/B experiments reproducible
separate shared-core rules from corpus-specific skin
support rule ablation
preserve traceability from prompt text back to accepted rules
```

---

## 11. A/B and Ablation Framework

Every new symbolic or neural component should be tested by comparison with a
simpler baseline.

### 11.1 Ablation Matrix

Recommended comparisons:

| Run | Components |
|---|---|
| Baseline | Current prompt only |
| Lexicon | Baseline plus lexicon hints |
| Rules | Baseline plus compiled symbolic rules |
| Retrieval | Baseline plus neural retrieval |
| Rules + retrieval | Baseline plus rules and retrieval |
| Full packet | Rules, retrieval, lexicon, validators, and candidate selection |

### 11.2 Acceptance Gates

A change is accepted only if it improves quality without increasing hard-rule
violations.

Suggested gates:

| Gate | Threshold |
|---|---|
| Symbolic hard-rule regressions | 0 new regressions |
| Whitaker COMET | Directionally improved or statistically tied with fewer rule failures |
| Ussher CometKiwi | Directionally improved on validation set |
| LLM diagnostic judge | Fewer accuracy, register, or faithfulness failures |
| Human review | No evidence of Fitzgerald or Whitaker overfitting |
| Ablation | Component adds value beyond simpler baseline |

---

## 12. Human Review Interface

The reviewer should see more than a final translation.

For each segment, the interface should display:

```text
source segment
selected translation
alternate candidates
rules triggered
retrieved parallels
lexicon choices
symbolic validation warnings
neural scores
reason for selected candidate
human override notes
```

This makes the pipeline a scholarly translation workstation rather than a
black-box generation system.

---

## 13. Implementation Phases

### Phase 1: Schema and Data Groundwork

Deliverables:

```text
translation_segment.schema.json
parallel_pair.schema.json
symbolic_feature_bundle.schema.json
rule_registry.schema.json
validation_report.schema.json
```

Tasks:

1. Define the JSONL schema for translation segments.
2. Define the JSONL schema for near-peer parallel pairs.
3. Define the rule registry format.
4. Convert existing Whitaker Chapter 1 alignment into the parallel-pair format.
5. Identify Ussher's *Annals* material suitable for alignment.

### Phase 2: Symbolic Baseline

Deliverables:

```text
extract_symbolic_features.py
rule_registry.json
symbolic_feature reports
unit tests for extractors
```

Tasks:

1. Implement Greek span detection.
2. Implement footnote-marker detection.
3. Implement title and citation pattern detection.
4. Implement named-entity extraction for common authors and places.
5. Implement lexicon match scaffolding.
6. Implement rule triggering from symbolic features.

### Phase 3: Near-Peer Corpus and Retrieval

Deliverables:

```text
parallel_corpus.jsonl
build_retrieval_index.py
retrieve_evidence.py
retrieval evaluation report
```

Tasks:

1. Build the initial parallel corpus from Whitaker and reviewed local outputs.
2. Add Ussher *Annals* pairs where available.
3. Add selected patristic and biblical pairs.
4. Generate embeddings for multiple retrieval views.
5. Implement symbolic-neural reranking.
6. Evaluate retrieval quality on known Whitaker alignments.

### Phase 4: Evidence Packet and Prompt Compiler

Deliverables:

```text
compile_evidence_packet.py
compile_translation_prompt.py
compiled prompt metadata
prompt reproducibility tests
```

Tasks:

1. Define compact evidence-packet format.
2. Compile accepted rules into prompt text.
3. Add corpus-skin selection.
4. Add lexicon profile selection.
5. Record prompt metadata and evidence hashes.
6. Write tests that prevent accidental prompt drift in locked experiments.

### Phase 5: Candidate Generation and Validation

Deliverables:

```text
generate_candidates.py
validate_translation_candidate.py
candidate_selection_report.json
```

Tasks:

1. Generate multiple candidates per segment.
2. Run symbolic validators on each candidate.
3. Run COMET for Whitaker where references exist.
4. Run CometKiwi for Ussher where no reference exists.
5. Add LLM diagnostic judge as a secondary analysis tool.
6. Select candidates using hard-rule veto plus score aggregation.

### Phase 6: A/B Optimization Loop

Deliverables:

```text
ablation_matrix reports
accepted_rules changelog
diagnostic_categories.md
```

Tasks:

1. Run ablations for each new symbolic or neural component.
2. Accept only changes that pass pre-registered gates.
3. Record every accepted rule with motivating examples.
4. Demote corpus-specific rules to corpus skin.
5. Reject changes that improve Whitaker by memorizing Fitzgerald.

### Phase 7: Ussher Deployment

Deliverables:

```text
ussher_corpus_skin.json
ussher_validation_report.md
reviewer-facing evidence packets
production translation artifacts
```

Tasks:

1. Compile locked shared core plus Ussher corpus skin.
2. Run on Ussher validation material.
3. Review disagreements with any available English reference as diagnostic,
   not automatic failure.
4. Produce translation artifacts with evidence and validation trails.
5. Feed reviewer overrides back into the rule and retrieval systems.

---

## 14. Proposed Artifact Layout

```text
04_translation_work/
├── neuro_symbolic/
│   ├── rule_registry.json
│   ├── schemas/
│   │   ├── translation_segment.schema.json
│   │   ├── parallel_pair.schema.json
│   │   ├── symbolic_feature_bundle.schema.json
│   │   └── validation_report.schema.json
│   ├── parallel_corpus/
│   │   ├── whitaker.jsonl
│   │   ├── ussher_annals.jsonl
│   │   ├── patristic.jsonl
│   │   └── biblical.jsonl
│   ├── retrieval/
│   │   ├── indexes/
│   │   └── retrieval_reports/
│   ├── evidence_packets/
│   ├── validation_reports/
│   └── ablations/
```

Suggested script locations:

```text
08_working_scratch/pipeline_scripts/
├── extract_symbolic_features.py
├── compile_evidence_packet.py
├── compile_translation_prompt.py
├── build_retrieval_index.py
├── retrieve_evidence.py
├── generate_candidates.py
└── validate_translation_candidate.py
```

---

## 15. Open Questions

1. Which edition and translation of Ussher's *Annals* should be treated as
   the highest-confidence near-peer source?

2. Which patristic corpora should be included first, and which translations
   are acceptable as references?

3. Should Greek handling rules be shared-core by default, or corpus-skin until
   validated separately on Ussher?

4. Which embedding model should be used for Latin and mixed Latin/Greek
   retrieval?

5. Should COMET be accepted as a primary gate after calibration on Whitaker, or
   kept as an advisory score?

6. What is the minimum segment count for each A/B or ablation run?

7. Should reviewer corrections become training examples, rule proposals, or
   both?

---

## 16. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Overfitting to Parker Society English | Require ablation and shared-core/corpus-skin review |
| Retrieval noise pollutes prompts | Rerank and cap evidence packet size |
| Rule sprawl | Prefer consolidation and maintain rule status lifecycle |
| Prompt drift breaks experiments | Compile prompts from versioned rules and metadata |
| Lexicon hints overconstrain translation | Mark lexicon matches as hints with confidence |
| Neural judge instability | Use LLM judging only for diagnostics, not sole gating |
| Ussher lacks gold reference | Validate symbolic compliance, use CometKiwi, and require human review |
| Patristic references are misidentified | Attach confidence and require citation-aware review |

---

## 17. Immediate Next Steps

1. Create the rule registry schema and seed it with accepted rules currently
   embedded in `translation_prompts_whitaker.py`.

2. Create a `parallel_pair` schema and convert the Whitaker Chapter 1 alignment
   into that format.

3. Implement a minimal symbolic feature extractor for Greek spans, footnote
   markers, titles, named entities, and rule triggers.

4. Build the first evidence-packet compiler without embeddings. Validate that
   symbolic packets alone improve prompt auditability.

5. Add retrieval only after the symbolic packet format is stable.

6. Run the first ablation:

```text
current Whitaker prompt
vs.
current Whitaker prompt + symbolic evidence packet
```

7. Use the result to decide whether the next investment should be retrieval,
   lexicon enrichment, or prompt compilation.

---

## 18. Summary

The symbolic side should answer:

```text
What do we know?
What rules apply?
What parallels exist?
What must not be violated?
```

The neural side should answer:

```text
Given that evidence, what is the best English rendering?
```

That division is the core of the proposed neuro-symbolic structure. It allows
the project to benefit from LLM fluency and semantic retrieval while retaining
scholarly control, reproducibility, and auditability.
