# A/B spot-check — p0041

Sampled from 27 pooled segments across the judgment files.

Buckets:
- **5 high-swing segments** (largest |rubric swing|)
- **5 tied segments** (pooled v0 wins == v1 wins; seed=0)

For each pick, mark a verdict and add a one-line note. The judge's
decoded winner is shown for reference, not as a constraint.

**Reviewer rule — embedded Greek (read before scoring):**

The candidates may use a three-slot format for embedded Greek:
the Greek is preserved verbatim, immediately followed by an English
rendering inside ⟦…⟧ brackets, optionally followed by Ussher's own
Latin paraphrase inside ⟪…⟫ brackets when one is present in the
source. Treat the brackets as scaffolding, not as prose.

Score with this in mind:

- Greek preserved verbatim is CORRECT (not a missing translation).
- ⟦English⟧ should faithfully render the Greek's meaning.
- ⟪Latin⟫ should reproduce Ussher's actual Latin paraphrase from
  the source — invented Latin is wrong.
- Signals that Ussher is paraphrasing the Greek (and so a ⟪Latin⟫
  slot should be present): quotation marks around or just after
  the Greek; a Latin clause that visibly echoes the Greek;
  connectives like *id est*, *hoc est*, *sive*, *inquit* near
  the Greek.
- A candidate that omits the brackets, uses wrong bracket
  characters (`[]`, `«»`, `<<>>`), or puts the slots in the wrong
  order is non-compliant on `format_compliance`.

Note: the LLM judge that produced the per-pairing winners shown
below was given this rule, but its application is imperfect.
Override the judge whenever your reading of the Latin source
disagrees.


---

## High-swing picks

### 1. `seg_p0041_body_l0012`

_v1 wins=3  v0 wins=0  ties=0  rubric swing(v1)=+15_

**Latin source:**

> quintum diem Martii, hujusmodi fit commemoratio: “ Οὗ-

#### Pairing `run01`

- **v0:** "This man
- **v1:** day of March, the following commemoration of Aristobulus is made: "Οὗ-
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=v1 source_preservation=v1 titles=equal register=v1 format_compliance=v1
- **Reason:**

  > B provides a meaningful translation fragment that follows the Latin source, naming Aristobulus and completing the date reference. A renders only 'This man', which is incomplete and loses the commemorative context. B is more accurate, fluent, and source-preserving despite both being truncated segments.

#### Pairing `run02`

- **v0:** "He
- **v1:** day of March, the following commemoration of Aristobulus is made: 'Οὗ-
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=v1 source_preservation=v1 titles=equal register=v1 format_compliance=v1
- **Reason:**

  > B renders the Latin fragment coherently—preserving the date, the commemorative formula, and the Greek opening—while A offers only the single word 'He', which misses virtually every element of the source. B wins on all applicable rubrics.

#### Pairing `run03`

- **v0:** "This man
- **v1:** teenth day of March the following commemoration is made: "Οὗ-
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=v1 source_preservation=v1 titles=equal register=v1 format_compliance=v1
- **Reason:**

  > B preserves the contextual framing ('the following commemoration is made') and the Greek incipit verbatim, faithfully rendering the Latin. A truncates to a bare fragment ('This man') that drops the introductory clause and misrepresents the source content.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 2. `seg_p0041_body_l0015`

_v1 wins=0  v0 wins=3  ties=0  rubric swing(v1)=-12_

**Latin source:**

> κουμένην διακονῶν αὐτῷ· ὑφ᾽ οὗ καὶ χειροτονεῖται ἐπίσκοπος

#### Pairing `run01`

- **v0:** world while ministering to him; by whom he is also ordained bishop
- **v1:** κουμένην διακονῶν αὐτῷ· ὑφ᾽ οὗ καὶ χειροτονεῖται ἐπίσκοπος
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=equal titles=equal register=v0 format_compliance=v0
- **Reason:**

  > A provides an actual English translation ('world while ministering to him; by whom he is also ordained bishop'), fulfilling the translation task. B merely reproduces the Greek source verbatim with no English rendering, which is a format_compliance failure and provides no translation value whatsoever.

#### Pairing `run02`

- **v0:** world while serving him; by whom he was also ordained bishop
- **v1:** κουμένην διακονῶν αὐτῷ· ὑφ᾽ οὗ καὶ χειροτονεῖται ἐπίσκοπος
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=equal titles=equal register=v0 format_compliance=v0
- **Reason:**

  > A provides a readable English rendering of the Greek fragment. B simply reproduces the Greek untranslated with no ⟦English⟧ slot, which is a format_compliance failure — Greek substantive content requires an English slot. A's 'world while serving him; by whom he was also ordained bishop' is fluent, accurate, and register-appropriate.

#### Pairing `run03`

- **v0:** world and ministering to him; by whom he was also ordained bishop
- **v1:** κουμένην διακονῶν αὐτῷ· ὑφ᾽ οὗ καὶ χειροτονεῖται ἐπίσκοπος
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=equal titles=equal register=v0 format_compliance=v0
- **Reason:**

  > A provides an actual English translation ('world and ministering to him; by whom he was also ordained bishop'), fulfilling the translation task. B reproduces only the Greek source text verbatim with no English rendering, failing fluency, accuracy, register, and format_compliance by omitting the required ⟦English⟧ slot after standalone Greek.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 3. `seg_p0041_body_l0019`

_v1 wins=0  v0 wins=3  ties=0  rubric swing(v1)=-12_

**Latin source:**

> ἐκκλησίας συστησάμενος, καὶ πρεσβυτέρους καὶ διακόνους ἐν

#### Pairing `run01`

- **v0:** having established churches, and appointed presbyters and deacons in them,
- **v1:** ἐκκλησίας συστησάμενος, καὶ πρεσβυτέρους καὶ διακόνους ἐν
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=equal titles=equal register=v0 format_compliance=v0
- **Reason:**

  > Translation A reproduces the Greek source verbatim without any English rendering, leaving the segment untranslated. Translation B provides a fluent, accurate English rendering of the Greek participial clause. On every applicable rubric B is superior; A fails format_compliance by omitting the required ⟦English⟧ slot after substantive Greek.

#### Pairing `run02`

- **v0:** having established churches and appointed presbyters and deacons in them,
- **v1:** ἐκκλησίας συστησάμενος, καὶ πρεσβυτέρους καὶ διακόνους ἐν
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=v0 titles=equal register=v0 format_compliance=equal
- **Reason:**

  > A provides no English rendering whatsoever — it merely reproduces the Greek source verbatim — so it fails every applicable rubric. B delivers clear, accurate prose that preserves the technical ecclesiastical terms 'presbyters' and 'deacons'. Both candidates fail format_compliance (A omits the ⟦English⟧ slot; B drops the Greek), so that rubric is scored equal.

#### Pairing `run03`

- **v0:** having established churches and appointed presbyters and deacons in them,
- **v1:** ἐκκλησίας συστησάμενος, καὶ πρεσβυτέρους καὶ διακόνους ἐν
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=equal titles=equal register=v0 format_compliance=v0
- **Reason:**

  > Translation A provides no English rendering whatsoever — it merely repeats the Greek verbatim, violating the requirement that an ⟦English⟧ slot follow standalone Greek and leaving fluency, accuracy, and register entirely unaddressed. Translation B supplies a clear, accurate, and scholarly English rendering of the Greek participial clause, making it the clear winner across all applicable rubrics.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 4. `seg_p0041_body_l0023`

_v1 wins=0  v0 wins=3  ties=0  rubric swing(v1)=-9_

**Latin source:**

> copus ordinatus est in Britannorum regionem, ferorum

#### Pairing `run01`

- **v0:** bishop into the country of the Britons, of fierce
- **v1:** op he was ordained for the land of the Britons, of fierce
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=equal titles=equal register=v0 format_compliance=equal
- **Reason:**

  > A begins with 'op' — a clear OCR/truncation artifact missing the 'bish' prefix — making it incomplete and inaccurate. B correctly renders 'episcopus ordinatus est' as 'bishop...was ordained' and reads as coherent scholarly English. All other rubrics are essentially equal given the fragment's brevity.

#### Pairing `run02`

- **v0:** ordained bishop for the region of the Britons, of fierce
- **v1:** dained bishop into the region of the Britons, of fierce
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=equal titles=equal register=v0 format_compliance=equal
- **Reason:**

  > B uses 'for the region' (Latin 'in' with accusative of destination can idiomatically render as 'for'), which is more natural English for describing episcopal appointment. A's 'into' is slightly awkward for a jurisdictional appointment. Both are fragments; no Greek, titles, or source terms present.

#### Pairing `run03`

- **v0:** ordained bishop for the region of the Britons, of fierce
- **v1:** op he was ordained for the region of the Britons, [a land] of fierce
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=equal titles=equal register=v0 format_compliance=equal
- **Reason:**

  > A contains a garbled fragment ('op he was ordained') that makes it incoherent and inaccurate. B renders the Latin cleanly as 'ordained bishop for the region of the Britons, of fierce,' which is fluid and accurate despite both being partial segments. A's interpolated '[a land]' is a minor addition not in the source.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 5. `seg_p0041_body_l0013`

_v1 wins=0  v0 wins=2  ties=0  rubric swing(v1)=-7_

**Latin source:**

> τος ἦν εἷς τῶν ἑβδομήκοντα μαθητῶν, ἠκολούθησε δὲ τῷ ἁγίῳ

#### Pairing `run01`

- **v0:** was one of the seventy disciples, and he followed the holy
- **v1:** τος ἦν εἷς τῶν ἑβδομήκοντα μαθητῶν, ἠκολούθησε δὲ τῷ ἁγίῳ
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=equal source_preservation=v1 titles=equal register=v0 format_compliance=v1
- **Reason:**

  > A preserves the Greek verbatim per format rules; B renders it into English prose, which is more fluent and readable but omits the source Greek entirely. A wins format_compliance and source_preservation; B wins fluency and register. With no Latin paraphrase present and titles not applicable, rubrics split evenly 2-2 with 2 equal, yielding a tie.

#### Pairing `run02`

- **v0:** was one of the seventy disciples, and he followed the holy
- **v1:** τος ἦν εἷς τῶν ἑβδομήκοντα μαθητῶν, ἠκολούθησε δὲ τῷ ἁγίῳ
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=equal source_preservation=equal titles=equal register=v0 format_compliance=v0
- **Reason:**

  > A reproduces raw Greek with no English rendering, leaving the segment untranslated and unreadable as English prose. B provides a fluent, accurate English rendering of the Greek fragment. Since Greek appears as substantive content, B's English translation is format-compliant while A's bare Greek is not.

#### Pairing `run03`

- **v0:** was one of the seventy disciples, and he followed the holy
- **v1:** τος ἦν εἷς τῶν ἑβδομήκοντα μαθητῶν, ἠκολούθησε δὲ τῷ ἁγίῳ
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=equal titles=equal register=v0 format_compliance=v0
- **Reason:**

  > A reproduces the Greek verbatim without an ⟦English⟧ slot, leaving the fragment untranslated and non-compliant with the three-slot format. B provides a fluent, accurate English rendering of the Greek clause. Titles and source_preservation are not applicable to this segment.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

## Tied picks

### 1. `seg_p0041_body_l0010`

_v1 wins=1  v0 wins=1  ties=0  rubric swing(v1)=-3_

**Latin source:**

> meminit, Britannorum episcopum a Paulo ordinatum, in

#### Pairing `run01`

- **v0:** I find in the Menaia of the Greeks to have been ordained bishop of the Britons by Paul:
- **v1:** makes mention — ordained as bishop of the Britons by Paul, I find
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v1 source_preservation=equal titles=equal register=equal format_compliance=equal
- **Reason:**

  > B flows more naturally as a unit, but A stays closer to the actual Latin in the segment: it does not import 'Menaia of the Greeks,' which belongs to surrounding context outside this fragment. The fluency gain in B is offset by the accuracy loss; four rubrics are inapplicable, leaving one mark each way.

#### Pairing `run02`

- **v0:** I find in the Greek Menaea to have been ordained bishop of the Britons by Paul:
- **v1:** ordained bishop of the Britons by Paul, I find in
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=v0 titles=equal register=v0 format_compliance=equal
- **Reason:**

  > B forms a coherent infinitive clause ('I find in the Greek Menaea to have been ordained…') that integrates naturally with the dangling 'in' at the segment end, and it preserves the technical term 'Menaea.' A opens with a dangling passive participle and omits the source reference, leaving the clause structurally incomplete and less faithful to the implied referent of 'in.'

#### Pairing `run03`

- **v0:** I find in the Greek Menaia to have been ordained bishop of the Britons by Paul:
- **v1:** I find — ordained bishop of the Britons by Paul — in
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=equal accuracy=v1 source_preservation=equal titles=equal register=equal format_compliance=equal
- **Reason:**

  > The Latin segment ends with 'in' and contains no mention of 'Greek Menaia'; B introduces that phrase as if it were present in this fragment, which is an accuracy failure for the segment as given. A stays closer to the Latin without adding content absent from the supplied text.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 2. `seg_p0041_body_l0009`

_v1 wins=1  v0 wins=1  ties=0  rubric swing(v1)=-1_

**Latin source:**

> Aristobulum quoque cujus ipse in epistola ad Romanos^f

#### Pairing `run01`

- **v0:** Aristobulus also, whom he himself mentions in the Epistle to the Romans^f,
- **v1:** Aristobulus too — of whom he himself in the Epistle to the Romans^f
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=equal titles=equal register=v0 format_compliance=equal
- **Reason:**

  > B is a complete sentence fragment that reads naturally as modern scholarly prose; A's em-dash construction leaves the clause suspended without a verb, making it harder to parse. B supplies the implied verb 'mentions' that the Latin truncation requires, while A's dash defers resolution awkwardly.

#### Pairing `run02`

- **v0:** Aristobulus too, whom he himself mentions in the Epistle to the Romans,^f
- **v1:** Aristobulus also, whom he himself mentions in the epistle to the Romans^f,
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal source_preservation=equal titles=equal register=equal format_compliance=equal
- **Reason:**

  > Both translations are nearly identical in meaning and quality. The only differences are 'also' vs 'too' (stylistic equals) and footnote marker placement (A places ^f after 'Romans', B places it after the comma). Neither difference creates a clear advantage on any rubric.

#### Pairing `run03`

- **v0:** Aristobulus too, of whom he himself makes mention in the Epistle to the Romans^f,
- **v1:** Aristobulus too, whom he himself mentions in the epistle to the Romans^f,
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=v1 accuracy=equal source_preservation=equal titles=equal register=v1 format_compliance=equal
- **Reason:**

  > A's 'whom he himself mentions' is more natural modern scholarly English than B's 'of whom he himself makes mention,' which uses the wordy periphrastic 'makes mention' and feels slightly archaic. Both are accurate; no Greek, titles, or source-preservation issues arise.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 3. `seg_p0041_body_l0008`

_v1 wins=0  v0 wins=0  ties=0  rubric swing(v1)=+0_

**Latin source:**

> rone martyrio cursum consummavit.

#### Pairing `run01`

- **v0:** 
- **v1:** Nero he ended his course in martyrdom.
- **Judge winner:** `—`  (swapped=False)
- **Rubric:** fluency=— accuracy=— source_preservation=— titles=— register=— format_compliance=—
- **Judge error:** missing english on one side

#### Pairing `run02`

- **v0:** 
- **v1:** ro he completed his course in martyrdom.
- **Judge winner:** `—`  (swapped=False)
- **Rubric:** fluency=— accuracy=— source_preservation=— titles=— register=— format_compliance=—
- **Judge error:** missing english on one side

#### Pairing `run03`

- **v0:** 
- **v1:** ro he completed his course by martyrdom.
- **Judge winner:** `—`  (swapped=False)
- **Rubric:** fluency=— accuracy=— source_preservation=— titles=— register=— format_compliance=—
- **Judge error:** missing english on one side

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 4. `seg_p0041_fn_004`

_v1 wins=0  v0 wins=0  ties=0  rubric swing(v1)=+0_

**Latin source:**

> Rom. cap. 16. ver. 10.

#### Pairing `run01`

- **v0:** Romans, chapter 16, verse 10.
- **v1:** Romans, chapter 16, verse 10.
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal source_preservation=equal titles=equal register=equal format_compliance=equal
- **Reason:**

  > Both translations are identical, rendering the bare scriptural citation in standard modern form. No rubric differentiates them.

#### Pairing `run02`

- **v0:** Romans, chapter 16, verse 10.
- **v1:** Romans, ch. 16, v. 10.
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal source_preservation=equal titles=equal register=equal format_compliance=equal
- **Reason:**

  > Both render a bare scripture reference correctly. A uses standard abbreviatory style ('ch.', 'v.'); B spells out 'chapter' and 'verse'. Neither is superior: abbreviated style is equally conventional in scholarly apparatus. All other rubrics are not meaningfully applicable to this minimal segment.

#### Pairing `run03`

- **v0:** Romans, chapter 16, verse 10.
- **v1:** Romans, chapter 16, verse 10.
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal source_preservation=equal titles=equal register=equal format_compliance=equal
- **Reason:**

  > Both translations are identical, rendering the bare scriptural reference in standard modern scholarly form. No differentiating features exist across any rubric.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 5. `seg_p0041_body_l0020`

_v1 wins=1  v0 wins=1  ties=0  rubric swing(v1)=+3_

**Latin source:**

> αὐτῇ καταστήσας, ἐτελειώθη. E septuaginta discipulis erat

#### Pairing `run01`

- **v0:** he was perfected (i.e., died)." Of the seventy disciples
- **v1:** αὐτῇ καταστήσας, ἐτελειώθη. He was one of the seventy disciples,
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=v1 source_preservation=v1 titles=equal register=equal format_compliance=v1
- **Reason:**

  > B preserves the Greek verbatim and renders the Latin clause as a complete sentence ('He was one of the seventy disciples'), while A silently translates away the Greek without preservation and reduces the Latin to a dangling prepositional fragment ('Of the seventy disciples'). B's missing ⟦⟧ slot is a lesser defect than A's total loss of the source Greek.

#### Pairing `run02`

- **v0:** he was perfected." He was one of the seventy disciples,
- **v1:** αὐτῇ καταστήσας, ἐτελειώθη. Of the seventy disciples this man was
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=v1 titles=equal register=v0 format_compliance=v1
- **Reason:**

  > A provides a complete rendering of both the Greek and Latin portions, reads as natural prose, and conveys the full meaning to the reader. B preserves the Greek verbatim (better for source_preservation and format_compliance) but leaves it entirely untranslated, and its inverted Latin word order ('Of the seventy disciples this man was') is mildly archaic.

#### Pairing `run03`

- **v0:** he was perfected [in martyrdom]." Of the seventy disciples this man was
- **v1:** αὐτῇ καταστήσας, ἐτελειώθη. Of the seventy disciples this man was
- **Judge winner:** `tie`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 source_preservation=v1 titles=equal register=equal format_compliance=v1
- **Reason:**

  > A provides readable English for the Greek and translates it accurately, but silently drops the Greek source entirely — the primary format violation. B preserves the Greek verbatim (better for source_preservation and format_compliance) but supplies no ⟦English⟧ slot, leaving the Greek unrendered. The failures cancel: rubrics split 2-2-2.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---
