# A/B spot-check — p0039

Sampled from 36 pooled segments across the judgment files.

Buckets:
- **5 high-swing segments** (largest |rubric swing|)
- **5 tied segments** (pooled v0 wins == v1 wins; seed=0)

For each pick, mark a verdict and add a one-line note. The judge's
decoded winner is shown for reference, not as a constraint.

---

## High-swing picks

### 1. `seg_p0039_body_l0019`

_v1 wins=0  v0 wins=3  ties=0  rubric swing(v1)=-8_

**Latin source:**

> ρωθεὶς καὶ τεθεὶς θάπτεται ἐκεῖ. Postremo in Britanniam

#### Pairing `run01`

- **v0:** [Greek: '...crucified and laid in the tomb, he is buried there.'] "Finally, having gone to Britain,
- **v1:** and laid out, he is buried there." Finally, having gone into Britain,
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=equal accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > B renders the Greek fragment explicitly with a bracketed translation, making clear what the citation says ('crucified and laid in the tomb'), whereas A omits 'crucified' and translates loosely. The Greek ρωθεὶς refers to crucifixion; B's accuracy is superior. Both are equally fluent and register-appropriate.

#### Pairing `run02`

- **v0:** crucified, and being laid down is buried there." Lastly, having set out for Britain,
- **v1:** ρωθεὶς καὶ τεθεὶς θάπτεται ἐκεῖ. "Finally, having gone to Britain,
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > B translates the Greek clause ('crucified, and being laid down is buried there') rather than leaving it untranslated, and renders the Latin transition naturally. A reproduces the Greek untranslated, which is a significant accuracy failure for an English translation.

#### Pairing `run03`

- **v0:** fied and laid out, he is buried there." "Finally, having set out for Britain,
- **v1:** ρωθεὶς καὶ τεθεὶς θάπτεται ἐκεῖ. "Finally, having travelled to Britain,
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > B completes the Greek clause ('shrouded and laid out, he is buried there') before rendering the Latin transition, giving a coherent full sentence. A leaves the Greek untranslated and begins mid-phrase. B's 'having set out for Britain' is also a more idiomatic rendering of the Latin motion implied by 'in Britanniam'.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 2. `seg_p0039_body_l0009`

_v1 wins=3  v0 wins=0  ties=0  rubric swing(v1)=+7_

**Latin source:**

> certe hujusmodi aliquo errore dictos Jacobi discipulos ad

#### Pairing `run01`

- **v0:** certainly, that the said disciples of James were, by some error of this kind,
- **v1:** certainly, that the said disciples of James were, through some such error,
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=equal proper_nouns=equal titles=equal register=v1
- **Reason:**

  > B's 'through some such error' is more natural modern prose than A's 'by some error of this kind,' which is slightly stilted. Both are accurate; the difference is purely stylistic fluency and register.

#### Pairing `run02`

- **v0:** certainly it is not unlike the truth that James's so-called disciples were, by some such error,
- **v1:** certainly it is not unlikely that, through some such error, James's said disciples
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=equal proper_nouns=equal titles=equal register=v1
- **Reason:**

  > B flows more naturally as a fragment opening, with 'through some such error' placed idiomatically mid-clause. A's 'not unlike the truth that' is slightly wordy and formal; B's 'not unlikely that' is tighter modern scholarly prose.

#### Pairing `run03`

- **v0:** certainly it is not far from the truth that by some such error the said disciples of James were
- **v1:** certainly it is not far from the truth that James's disciples, called such by some error of this kind,
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=v1 proper_nouns=equal titles=equal register=v1
- **Reason:**

  > A's 'the said disciples' is a legalistic archaism that misreads 'dictos' (= 'called such') as a backward reference. B renders 'dictos' correctly as 'called such' and places the participial phrase naturally, while A's word order is also more Latinate. Proper nouns and titles are not in play here.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 3. `seg_p0039_body_l0032`

_v1 wins=0  v0 wins=3  ties=0  rubric swing(v1)=-7_

**Latin source:**

> Christi;” ad extremum vero, cum “ verbo gratiæ multos

#### Pairing `run01`

- **v0:** of Christ;" but in the end, when "he had enlightened many by the word of grace,
- **v1:** of Christ;" but at last, when "by the word of grace he had
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > A completes the clause ('he had enlightened many') where B truncates mid-phrase, leaving the sentence incomplete. A is also more fluent and natural as scholarly prose. Both are equal on proper nouns and titles since neither appear in this segment.

#### Pairing `run02`

- **v0:** of Christ;" but at last, when he "had enlightened many with the word of grace,
- **v1:** of Christ;" but at the last, when he had "enlightened many with the word of grace
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=equal proper_nouns=equal titles=equal register=v0
- **Reason:**

  > A's 'at last' is more natural modern prose than B's archaic 'at the last'. A's quotation marks correctly enclose the full verb phrase 'had enlightened many with the word of grace', whereas B misplaces the opening quote after 'had', breaking the cited passage boundary awkwardly.

#### Pairing `run03`

- **v0:** of Christ"; and at last, when "he had enlightened many with the word of grace
- **v1:** of Christ;" but at the last, when "he had enlightened many with the word of grace
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=equal proper_nouns=equal titles=equal register=v0
- **Reason:**

  > Both are accurate renderings. A's 'and at last' is more natural modern scholarly prose than B's 'but at the last,' where 'at the last' carries a faintly archaic cadence. The conjunction difference ('and' vs 'but') is negligible in context; fluency and register favour A.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 4. `seg_p0039_fn_002`

_v1 wins=3  v0 wins=0  ties=0  rubric swing(v1)=+6_

**Latin source:**

> Menolog. tom. 2. Antiqu. lect. Henr. Canisii. Antholog. Græc. edit. Rom. ann. 1598. pag. 406. et Menæis edit. Venet. ann. 1588.

#### Pairing `run01`

- **v0:** Menologium, vol. 2 of the Antiquae Lectiones of Henricus Canisius. Greek Anthology, Roman edition of the year 1598, p. 406. And in the Menaia, Venice edition of the year 1588.
- **v1:** Menologion, volume 2 of the Ancient Readings of Henricus Canisius. Greek Anthology, Rome edition of 1598, page 406; and the Menaia, Venice edition of 1588.
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=equal proper_nouns=equal titles=equal register=v1
- **Reason:**

  > B reads more naturally: 'Ancient Readings' over 'Antiquae Lectiones' reduces unnecessary Latinism, 'Rome edition' is crisper than 'Roman edition of the year', and the semicolon better joins the final citation. Both are accurate and handle proper nouns identically.

#### Pairing `run02`

- **v0:** Menologion, vol. 2 of the Antiquae Lectiones of Henricus Canisius; Greek Anthology, Rome edition of 1598, page 406; and Menaia, Venice edition of 1588.
- **v1:** Menology, volume 2 of Henricus Canisius's Antiquae Lectiones; Greek Anthology, Roman edition of 1598, page 406; and the Menaia, Venice edition of 1588.
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=equal proper_nouns=equal titles=equal register=v1
- **Reason:**

  > B reads more naturally with the possessive 'Canisius's' and the definite article before 'Menaia'; 'Roman edition' is marginally more idiomatic than 'Rome edition' for a scholarly publication descriptor. Both are accurate and handle titles and proper nouns equally.

#### Pairing `run03`

- **v0:** Menology, in volume 2 of the Antiquae Lectiones of Henricus Canisius. Greek Anthology, Roman edition of the year 1598, page 406; and in the Menaea, Venice edition of the year 1588.
- **v1:** Menology, volume 2 of the Antiquae Lectiones of Henricus Canisius. Greek Anthology, Roman edition of 1598, page 406. And in the Menaia, Venice edition of 1588.
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=equal proper_nouns=equal titles=equal register=v1
- **Reason:**

  > B reads more cleanly: 'of 1598' over 'of the year 1598' removes padding, and 'Menaia' is the standard modern scholarly spelling versus A's 'Menaea'. The period after '406' rather than a semicolon also better matches the bibliographic list structure.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 5. `seg_p0039_body_l0001`

_v1 wins=2  v0 wins=0  ties=0  rubric swing(v1)=+5_

**Latin source:**

> rum ibi subjicitur, de Jacobo legitur: “ Hic Hispaniæ, et

#### Pairing `run01`

- **v0:** ...is subjoined there, concerning James one reads: "He, to Spain and
- **v1:** things added there, we read concerning James: "He preached in Spain and
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=v1 accuracy=v1 proper_nouns=equal titles=equal register=v1
- **Reason:**

  > A renders 'legitur' naturally as 'we read' and supplies 'preached' to complete the fragmentary clause, yielding readable scholarly prose. B's 'is subjoined' is stiff and its 'one reads' plus dangling 'He, to Spain and' leaves the sentence syntactically broken and harder to follow.

#### Pairing `run02`

- **v0:** is added there, concerning James we read: "He preached in Spain and
- **v1:** of them is added there, concerning James we read: "He preached in Spain and
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=equal accuracy=v1 proper_nouns=equal titles=equal register=equal
- **Reason:**

  > The Latin fragment ends in '-rum ibi subjicitur', where '-rum' is the tail of a genitive plural (likely 'eorum'). A preserves 'of them', faithfully rendering that genitive; B silently drops it, producing a slightly less complete rendering of the source clause.

#### Pairing `run03`

- **v0:** is added there concerning these matters, of James one reads: "He preached to Spain and
- **v1:** is added there, the following is read concerning James: "He preached in Spain and
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=v1 accuracy=v0 proper_nouns=equal titles=equal register=v1
- **Reason:**

  > A reads more naturally ('the following is read concerning James') but drops 'de his rebus' / 'concerning these matters.' B preserves the referential phrase but uses awkward word order ('of James one reads'). Neither is clearly superior overall.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

## Tied picks

### 1. `seg_p0039_body_l0030`

_v1 wins=1  v0 wins=1  ties=0  rubric swing(v1)=+1_

**Latin source:**

> legimus, Petrum in Britannia “ longo tempore fuisse mo-

#### Pairing `run01`

- **v0:** we read that Peter in Britain "tarried for a long time,
- **v1:** read that Peter "stayed in Britain for a long time,
- **Judge winner:** `—`  (swapped=True)
- **Rubric:** fluency=— accuracy=— proper_nouns=— titles=— register=—
- **Judge error:** parse failed: Expecting ',' delimiter: line 10 column 108 (char 258)

#### Pairing `run02`

- **v0:** we read that Peter "remained for a long time in Britain,
- **v1:** we read that Peter "remained for a long time in Britain
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=equal accuracy=v0 proper_nouns=equal titles=equal register=equal
- **Reason:**

  > The Latin segment ends mid-phrase with 'mo-' (continuing a word, likely 'moratum'), indicating a dependent clause continues. B's trailing comma correctly signals syntactic continuation, whereas A's bare quote implies a complete thought. Both are otherwise identical.

#### Pairing `run03`

- **v0:** we read that Peter "tarried for a long time in Britain,
- **v1:** read that Peter "stayed in Britain for a long time,
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=v1 accuracy=equal proper_nouns=equal titles=equal register=v1
- **Reason:**

  > A uses 'stayed,' natural modern English, while B uses 'tarried,' an archaism penalized by the fluency and register rubrics. Both are accurate to the Latin 'fuisse mo[ratum]'. A's word order is also more natural for contemporary scholarly prose.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 2. `seg_p0039_body_l0024`

_v1 wins=1  v0 wins=1  ties=0  rubric swing(v1)=+0_

**Latin source:**

> et vigesimum in Perside martyrium subiisse legitur.

#### Pairing `run01`

- **v0:** he is read to have undergone martyrdom in Persia.
- **v1:** he is read to have suffered martyrdom in Persia.
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=v1 accuracy=equal proper_nouns=equal titles=equal register=v1
- **Reason:**

  > 'Suffered martyrdom' is the standard modern scholarly idiom; 'undergone martyrdom' is slightly awkward and less idiomatic in English. Both are accurate renderings of 'martyrium subiisse'. All other rubrics are equal.

#### Pairing `run02`

- **v0:** we read that he underwent martyrdom in Persia.
- **v1:** he is read to have undergone martyrdom in Persia.
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=equal proper_nouns=equal titles=equal register=v0
- **Reason:**

  > B renders the impersonal Latin passive 'legitur' as the natural scholarly idiom 'we read that,' avoiding A's awkward calque 'he is read to have undergone.' Both omit 'vigesimum' equally, so accuracy is a wash; the fluency and register edge goes clearly to B.

#### Pairing `run03`

- **v0:** he is reported to have undergone martyrdom in Persia.
- **v1:** he is reported to have undergone martyrdom in Persia.
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both translations are identical word-for-word, rendering the Latin faithfully and naturally. No distinction can be drawn on any rubric.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 3. `seg_p0039_body_l0023`

_v1 wins=0  v0 wins=0  ties=0  rubric swing(v1)=+0_

**Latin source:**

> atque Adonis martyrologiis, ad Octobris diem octavum

#### Pairing `run01`

- **v0:** and Ado, on the twenty-eighth day of October
- **v1:** and Ado, on the twenty-eighth day of October
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both translations are identical in wording and quality. Neither can be distinguished on any rubric.

#### Pairing `run02`

- **v0:** and Ado, on the twenty-eighth day of October
- **v1:** and Ado, on the twenty-eighth day of October
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both translations are identical in wording and rendering. No basis for distinguishing them on any rubric.

#### Pairing `run03`

- **v0:** and Ado, on the twenty-eighth day of October
- **v1:** and Ado, on the twenty-eighth day of October
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both translations are identical, so no distinction can be drawn on any rubric.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 4. `seg_p0039_body_l0008`

_v1 wins=1  v0 wins=1  ties=0  rubric swing(v1)=+0_

**Latin source:**

> Hibernis exaratum repererit, aliis conjiciendum relinquo :

#### Pairing `run01`

- **v0:** may have found it written 'Hibernis' instead of 'Hiberis,' I leave for others to conjecture:
- **v1:** 'Hibernis' (Irish) written in place of 'Hiberis' (Iberians), I leave for others to conjecture:
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > A preserves the implicit conditional clause ('may have found it written') that mirrors the Latin's conjunctive mood, giving a fuller and more accurate rendering. B's parenthetical glosses (Irish/Iberians) add interpretive content absent from the Latin and disrupt the scholarly register with an editorial intrusion.

#### Pairing `run02`

- **v0:** 'Hibernis' written instead of 'Hiberis' I leave for others to conjecture:
- **v1:** found it written 'Hibernis' instead of 'Hiberis,' I leave for others to conjecture:
- **Judge winner:** `tie`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v1 proper_nouns=equal titles=equal register=equal
- **Reason:**

  > A reads more fluently as a standalone clause but omits 'repererit' (found). B preserves the participial structure and is more accurate to the Latin, though slightly less elegant. Neither is clearly superior overall.

#### Pairing `run03`

- **v0:** may have found it written "Hibernis," I leave to others to conjecture:
- **v1:** 'Hibernis' (the Irish) written in place of 'Hiberis' (the Iberians), I leave for others to conjecture:
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=v1 proper_nouns=equal titles=equal register=v1
- **Reason:**

  > B explicitly glosses both 'Hibernis' (Irish) and 'Hiberis' (Iberians), making the textual confusion intelligible to the reader — the crux of the passage. A leaves the reader to guess the significance. B is also slightly more fluent as a complete clause.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 5. `seg_p0039_fn_001`

_v1 wins=0  v0 wins=0  ties=0  rubric swing(v1)=+0_

**Latin source:**

> Niceph. hist. ecclesiast. lib. 2. cap. 40.

#### Pairing `run01`

- **v0:** Nicephorus, Ecclesiastical History, book 2, chapter 40.
- **v1:** Nicephorus, Ecclesiastical History, book 2, chapter 40.
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both translations are identical, rendering the abbreviated citation in full standard scholarly form with no differences in any rubric.

#### Pairing `run02`

- **v0:** Nicephorus, Ecclesiastical History, book 2, chapter 40.
- **v1:** Nicephorus, Ecclesiastical History, book 2, chapter 40.
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both translations are identical, rendering the abbreviated citation in the same fully expanded form with consistent proper noun and title treatment.

#### Pairing `run03`

- **v0:** Nicephorus, Ecclesiastical History, book 2, chapter 40.
- **v1:** Nicephorus, Ecclesiastical History, book 2, chapter 40.
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both translations are identical, rendering the abbreviated citation in the same expanded form with consistent treatment of the proper noun and title.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---
