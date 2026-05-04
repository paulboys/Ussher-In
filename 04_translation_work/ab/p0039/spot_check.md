# A/B spot-check — p0039

Sampled from 36 pooled segments across the judgment files.

Buckets:
- **5 high-swing segments** (largest |rubric swing|)
- **5 tied segments** (pooled v0 wins == v1 wins; seed=0)

For each pick, mark a verdict and add a one-line note. The judge's
decoded winner is shown for reference, not as a constraint.

**Reviewer rule — embedded Greek (read before scoring):**

Ussher routinely quotes a Greek source and then paraphrases it into
Latin in the same or adjacent clause. When that pattern is present,
the *correct* editorial behavior is to **leave the Greek
untranslated** and render only the Latin into English — the Latin
paraphrase already serves as Ussher's gloss, and double-translating
produces redundant English.

Score with this rule in mind:

- Greek + adjacent Latin paraphrase → leaving the Greek verbatim is
  CORRECT. Do not mark a candidate down for omitting an English
  gloss of such Greek.
- Greek standing alone (no Latin paraphrase nearby; the Greek
  carries new substantive content) → it SHOULD be rendered into
  English (or English-glossed in brackets).
- Signals that Ussher is paraphrasing the Greek: quotation marks
  around or just after the Greek; a Latin clause that visibly
  echoes the Greek; connectives like *id est*, *hoc est*, *sive*,
  *inquit* near the Greek.

Note: the LLM judge that produced the per-pairing winners shown
below was given this rule, but its application is imperfect.
Override the judge whenever your reading of the Latin source
disagrees.


---

## High-swing picks

### 1. `seg_p0039_body_l0003`

_v1 wins=3  v0 wins=0  ties=0  rubric swing(v1)=+7_

**Latin source:**

> cæsus occubuit.” Addit Ordericus Vitalis Uticensis mo-

#### Pairing `run01`

- **v0:** having been struck, he fell." Orderic Vitalis, monk of Saint-Évroul (Uticensis), adds,
- **v1:** he was struck down and died.' Orderic Vitalis, the monk of Saint-Évroul, adds,
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=v1 proper_nouns=v1 titles=equal register=v1
- **Reason:**

  > B renders 'cæsus occubuit' more precisely as 'struck down and died' (occubuit denotes death, not mere falling), integrates 'Uticensis' cleanly without an awkward Latin parenthetical, and avoids A's archaic participial opening. No titles appear in either segment.

#### Pairing `run02`

- **v0:** Ordericus Vitalis, monk of Saint-Évroult, adds in
- **v1:** having been struck down, perished." Orderic Vitalis, the Saint-Évroul mo-
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=equal accuracy=v1 proper_nouns=v1 titles=equal register=equal
- **Reason:**

  > A silently drops the closing quoted clause 'cæsus occubuit' — a material accuracy failure. B renders it correctly and uses the standard Anglicized 'Orderic' over the Latin-form 'Ordericus'.

#### Pairing `run03`

- **v0:** having been struck down, he met his death." Ordericus Vitalis, monk of Saint-Évroul (Uticensis), adds,
- **v1:** he was struck down and perished." Orderic Vitalis, the monk of Saint-Évroult (Uticensis),
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=v1 titles=equal register=equal
- **Reason:**

  > B uses the standard modern spelling 'Orderic Vitalis' (vs A's 'Ordericus'), which is the preferred Anglicized form for this historian. Both are accurate and fluent renderings of the fragment; the proper noun difference is the sole meaningful distinction.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 2. `seg_p0039_body_l0016`

_v1 wins=0  v0 wins=3  ties=0  rubric swing(v1)=-7_

**Latin source:**

> In quibus ad Maii diem decimum de Simone ita scriptum

#### Pairing `run01`

- **v0:** In which, on the tenth day of May, we read written concerning Simon
- **v1:** In which (menologies), on the tenth day of May, concerning Simon, written thus
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=equal proper_nouns=equal titles=equal register=v0
- **Reason:**

  > B reads as natural scholarly prose by supplying a finite verb ('we read written') that flows smoothly, whereas A's parenthetical gloss '(menologies)' is an editorial addition not in the Latin. Both are accurate, but B's register is cleaner modern English without the awkward interpolation.

#### Pairing `run02`

- **v0:** In them, on the tenth day of May, we read the following written about Simon:
- **v1:** In which, under the tenth day of May, concerning Simon we read it written thus:
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=equal proper_nouns=equal titles=equal register=v0
- **Reason:**

  > B reads more naturally as modern scholarly prose: 'In them, on the tenth day of May' flows better than 'In which, under the tenth day of May', and 'we read the following written about' is cleaner than 'we read it written thus'. Both are accurate; B simply has better register and fluency.

#### Pairing `run03`

- **v0:** In which, under the tenth day of May concerning Simon, we read it thus written:
- **v1:** In which, at the tenth day of May, concerning Simon we read it written
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > B renders 'ad Maii diem decimum' more naturally as 'under the tenth day of May' (calendar-entry idiom) and captures 'ita' with 'thus', which A omits. B's colon after 'written' correctly signals the quotation that follows. A's 'we read it written' is slightly awkward and loses 'ita'.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 3. `seg_p0039_body_l0028`

_v1 wins=3  v0 wins=0  ties=0  rubric swing(v1)=+7_

**Latin source:**

> in occidente,” retulit alicubi Eusebius Pamphili; siqui-

#### Pairing `run01`

- **v0:** in the west," Eusebius of Pamphilus reported somewhere; if indeed
- **v1:** in the West,' Eusebius Pamphili reports somewhere; if
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=v1 accuracy=equal proper_nouns=v1 titles=equal register=v1
- **Reason:**

  > A uses 'Eusebius Pamphili' (standard scholarly form) over B's awkward 'Eusebius of Pamphilus' (Pamphilus is a person, not a place, making 'of' misleading). A's present tense 'reports' is more natural for citing ancient authors; B's 'reported' and 'if indeed' add unnecessary weight to a fragment.

#### Pairing `run02`

- **v0:** in the West"—if indeed
- **v1:** in the West," Eusebius Pamphili reported somewhere; if in-
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=v1 accuracy=v1 proper_nouns=equal titles=equal register=v1
- **Reason:**

  > A preserves the full clause including 'Eusebius Pamphili reported somewhere,' which is present in the Latin ('retulit alicubi Eusebius Pamphili'). B drops this attribution entirely, a clear accuracy failure. Both handle the fragment equally on other rubrics.

#### Pairing `run03`

- **v0:** in the west," Eusebius Pamphili reported somewhere — if
- **v1:** in the West," Eusebius Pamphili reported somewhere — if
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=v1
- **Reason:**

  > The only difference is capitalization of 'West' vs 'west'. In scholarly prose referring to a named geopolitical region ('the West' as a recognized historical zone), capitalization is conventional and preferred. A's 'West' is the stronger register choice.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 4. `seg_p0039_body_l0008`

_v1 wins=1  v0 wins=2  ties=0  rubric swing(v1)=-6_

**Latin source:**

> Hibernis exaratum repererit, aliis conjiciendum relinquo :

#### Pairing `run01`

- **v0:** may have found it written 'Hibernis' instead of 'Hiberis,' I leave for others to conjecture:
- **v1:** may have found 'Hibernis' (the Irish) written for 'Hiberis,' I leave for others to conjecture:
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=equal accuracy=v1 proper_nouns=equal titles=equal register=equal
- **Reason:**

  > B adds the parenthetical gloss '(the Irish)' which correctly identifies what 'Hibernis' means in context, making the crux of the textual issue clear to the reader. A leaves the substitution opaque. Both are otherwise equally fluent and register-appropriate.

#### Pairing `run02`

- **v0:** 'Hibernis' written instead of 'Hiberis' I leave for others to conjecture:
- **v1:** found "Hibernians" written, I leave for others to conjecture:
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=v0 titles=equal register=v0
- **Reason:**

  > A correctly identifies the textual-critical crux: Ussher is noting that a source reads 'Hibernis' where 'Hiberis' (Iberians) might be expected, and preserves both Latin forms for scholarly scrutiny. B translates 'Hibernis' as 'Hibernians', collapsing the very distinction Ussher is flagging and materially distorting the passage's meaning.

#### Pairing `run03`

- **v0:** may have found it written "Hibernis," I leave to others to conjecture:
- **v1:** found "Hibernians" written instead, I leave for others to conjecture;
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > A preserves 'Hibernis' as a quoted Latin form (correct, since the point is about a word found in the text), whereas B renders it as 'Hibernians,' converting a textual crux into a proper noun and obscuring the philological issue. A's phrasing is also more natural scholarly English.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 5. `seg_p0039_body_l0004`

_v1 wins=3  v0 wins=0  ties=0  rubric swing(v1)=+5_

**Latin source:**

> nachus, libro secundo ecclesiasticæ historiæ, septem

#### Pairing `run01`

- **v0:** in the second book of his Ecclesiastical History, that seven
- **v1:** in the second book of his "Ecclesiastical History," that seven
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=v1 register=equal
- **Reason:**

  > The two renderings are otherwise identical; A marks 'Ecclesiastical History' in quotation marks, satisfying the rubric that book titles be italicized or quoted rather than left bare in running text. B leaves the title unformatted, which the rubric penalizes.

#### Pairing `run02`

- **v0:** the second book of his Ecclesiastical History that seven
- **v1:** nk, in the second book of his Ecclesiastical History, adds that seven
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=v1 accuracy=v1 proper_nouns=equal titles=equal register=v1
- **Reason:**

  > Both are fragments, but A includes 'adds that' which preserves the governing verb's sense (the author is making an assertion), while B's 'that' hangs without a verb, leaving the syntax incomplete. A reads more naturally as a clause continuation.

#### Pairing `run03`

- **v0:** in the second book of his Ecclesiastical History, that seven
- **v1:** adds, in book two of his "Ecclesiastical History," that seven
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=v1 register=equal
- **Reason:**

  > Both renderings are fluent and accurate for this fragment. A italicizes/quotes 'Ecclesiastical History' per the titles rubric, which B leaves bare in running text. That single distinction tips the decision to A.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

## Tied picks

### 1. `seg_p0039_body_l0020`

_v1 wins=1  v0 wins=1  ties=0  rubric swing(v1)=-2_

**Latin source:**

> profectus, cum multos evangelii verbo illustrasset, ab in-

#### Pairing `run01`

- **v0:** when he had enlightened many by the word of the gospel, by the un-
- **v1:** after he had enlightened many with the word of the gospel, by un-
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=v1 accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both fragments are accurate renderings of an incomplete sentence. A's 'after he had' is slightly more natural modern prose than B's 'when he had'; B's added 'the' before 'un-' is trivially different. A edges ahead on fluency.

#### Pairing `run02`

- **v0:** when he had enlightened many with the word of the gospel, by the
- **v1:** after he had enlightened many by the word of the gospel, by un-
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > Both are truncated mid-sentence, but B's 'when he had enlightened' is more natural modern English than A's 'after he had enlightened', and B preserves the article before 'word' ('with the word') where A drops it ('by the word'). B's rendering is slightly more fluent and complete.

#### Pairing `run03`

- **v0:** when he had enlightened many with the word of the gospel, by un-
- **v1:** when he had enlightened many with the word of the gospel, by un-
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both translations are identical, rendering the same partial sentence fragment. No differentiating features can be assessed.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 2. `seg_p0039_body_l0018`

_v1 wins=1  v0 wins=1  ties=0  rubric swing(v1)=+0_

**Latin source:**

> τῷ λόγῳ τοῦ εὐαγγελίου φωτίσας, ὑπὸ τῶν ἀπίστων σταυ-

#### Pairing `run01`

- **v0:** [Greek citation continues: '...having illumined many by the word of the gospel, by the unbelievers having been']
- **v1:** τῷ λόγῳ τοῦ εὐαγγελίου φωτίσας, ὑπὸ τῶν ἀπίστων σταυ-
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=v1 accuracy=v1 proper_nouns=equal titles=equal register=v1
- **Reason:**

  > The segment is a truncated Greek citation with no Latin in this segment; passing the Greek through verbatim (A) is the correct editorial choice per the domain rule. B's English gloss uses inverted, archaic word order ('by the unbelievers having been') and introduces editorial brackets not present in the source.

#### Pairing `run02`

- **v0:** by the word of the gospel, by the unbelievers he was
- **v1:** τῷ λόγῳ τοῦ εὐαγγελίου φωτίσας, ὑπὸ τῶν ἀπίστων σταυ-
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > The source segment is pure Greek with no Latin paraphrase present, so per the domain rule the Greek should be rendered into English rather than passed through verbatim. B correctly translates the fragment; A merely echoes the untranslated Greek, providing no scholarly English rendering.

#### Pairing `run03`

- **v0:** having enlightened with the word of the gospel, by the unbelievers cruci-
- **v1:** τῷ λόγῳ τοῦ εὐαγγελίου φωτίσας, ὑπὸ τῶν ἀπίστων σταυ-
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > The Latin source is a mid-sentence Greek fragment with no accompanying Latin paraphrase in this segment. A correctly passes the Greek through untranslated (appropriate given the domain rule when the segment is Greek-only with unclear paraphrase context). B renders the Greek into English, which is also acceptable. Neither is penalizable; all rubrics are equal.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 3. `seg_p0039_body_l0013`

_v1 wins=1  v0 wins=1  ties=0  rubric swing(v1)=+1_

**Latin source:**

> author est Nicephorus^q Callisti. Eundem “ in Britannia

#### Pairing `run01`

- **v0:** is asserted by Nicephorus^q Callistus. That the same man "in Britain
- **v1:** Nicephorus^q Callistus is the authority. The same man (Simon), 'in Britain
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=v1 proper_nouns=equal titles=equal register=v1
- **Reason:**

  > B restructures the sentence more naturally ('is the authority' vs. passive 'is asserted by') and helpfully supplies the referent '(Simon)' in brackets. A's 'is asserted by' is slightly awkward and passive where B's construction reads more cleanly as modern scholarly prose.

#### Pairing `run02`

- **v0:** is attested by Nicephorus^q Callistus. That the same man "in Britain
- **v1:** is reported by Nicephorus^q Callistus. That the same [apostle] "in Britain
- **Judge winner:** `tie`  (swapped=False)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > The two versions differ only in 'attested' vs 'reported' (both reasonable for 'auctor est') and the editorial gloss '[apostle]' in B. Neither gloss nor word choice is materially wrong; the Latin is too brief to favour one decisively.

#### Pairing `run03`

- **v0:** is attested by Nicephorus^q Callistus. That the same man was "in Britain
- **v1:** is reported by Nicephorus^q Callistus. That the same man "in Britain
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=equal
- **Reason:**

  > A renders 'author est' more precisely as 'is attested by' (capturing the evidentiary sense) and preserves the full clause 'That the same man was in Britain', whereas B drops 'was', leaving the subordinate clause incomplete and syntactically awkward.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 4. `seg_p0039_fn_003`

_v1 wins=1  v0 wins=1  ties=0  rubric swing(v1)=-1_

**Latin source:**

> Metaphrast. commentar. de Petro et Paulo, ad diem 29. Junii, de quo vid. Baron. annal. tom. 1. an. 61. sec. 4.

#### Pairing `run01`

- **v0:** Metaphrastes, Commentary on Peter and Paul, on the 29th day of June; on which see Baronius, Annals, vol. 1, year 61, section 4.
- **v1:** Metaphrastes, "Commentary on Peter and Paul," on the 29th day of June, concerning which see Baronius, "Annals," vol. 1, year 61, section 4.
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=v1 register=equal
- **Reason:**

  > Both render the bibliographic reference accurately and fluently. A edges ahead on the titles rubric by consistently quoting treatise titles ('Commentary on Peter and Paul', 'Annals'), while B leaves them bare in running text, contrary to the instruction to italicize or quote titles.

#### Pairing `run02`

- **v0:** Metaphrastes, Commentary on Peter and Paul, on the 29th of June; on which see Baronius, Annals, vol. 1, year 61, section 4.
- **v1:** Metaphrastes, commentary on Peter and Paul, for the 29th of June; on which see Baronius, Annals, volume 1, year 61, section 4.
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both renderings are accurate and fluent bibliographic citations with no meaningful differences in accuracy, register, or proper nouns. The only variation is 'for the 29th' (A) vs 'on the 29th' (B) and 'volume' vs 'vol.' — minor stylistic choices that do not favour either candidate.

#### Pairing `run03`

- **v0:** Metaphrastes, Commentary on Peter and Paul, on the 29th day of June; concerning which see Baronius, Annals, volume 1, year 61, section 4.
- **v1:** Metaphrastes, "Commentary on Peter and Paul," at the day of June 29; on which see Baronius, "Annals," volume 1, year 61, section 4.
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=equal proper_nouns=equal titles=equal register=v0
- **Reason:**

  > Both italicize/quote titles equally, but B renders 'on the 29th day of June' more naturally than A's 'at the day of June 29', and 'concerning which' vs 'on which' is a minor wash. B's unquoted italicized titles are the modern scholarly standard; A's quotation marks are acceptable but slightly informal.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 5. `seg_p0039_fn_001`

_v1 wins=1  v0 wins=1  ties=0  rubric swing(v1)=-1_

**Latin source:**

> Niceph. hist. ecclesiast. lib. 2. cap. 40.

#### Pairing `run01`

- **v0:** Nicephorus, Ecclesiastical History, book 2, chapter 40.
- **v1:** Nicephorus, "Ecclesiastical History," book 2, chapter 40.
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=v1 register=equal
- **Reason:**

  > Both are accurate bibliographic citations, but A italicizes (or quotes) the title 'Ecclesiastical History' per standard scholarly citation practice, while B leaves it bare. The titles rubric therefore favors A, giving it the overall edge.

#### Pairing `run02`

- **v0:** Nicephorus, Ecclesiastical History, book 2, chapter 40.
- **v1:** Nicephorus, Ecclesiastical History, book 2, chapter 40.
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both translations are identical, rendering the bibliographic citation in the same standard modern scholarly form with italicized title and Anglicized proper noun.

#### Pairing `run03`

- **v0:** Nicephorus, Ecclesiastical History, book 2, chapter 40.
- **v1:** Nicephorus, "Ecclesiastical History," book 2, chapter 40.
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=v0 register=v0
- **Reason:**

  > Both are accurate and fluent for a bare citation. B uses italics for the title (standard scholarly practice for book-length works), while A wraps it in quotation marks, which is less conventional for a treatise title in modern academic prose.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---
