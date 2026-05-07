# A/B spot-check — p0041

Sampled from 27 pooled segments across the judgment files.

Buckets:
- **5 high-swing segments** (largest |rubric swing|)
- **3 tied segments** (pooled v0 wins == v1 wins; seed=0)

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

### 1. `seg_p0041_body_l0012`

_v1 wins=3  v0 wins=0  ties=0  rubric swing(v1)=+11_

**Latin source:**

> quintum diem Martii, hujusmodi fit commemoratio: “ Οὗ-

#### Pairing `run01`

- **v0:** "This man
- **v1:** day of March, the following commemoration of Aristobulus is made: "Οὗ-
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=v1 proper_nouns=v1 titles=equal register=v1
- **Reason:**

  > B preserves the liturgical calendar context ('day of March') and names the subject (Aristobulus), faithfully rendering the Latin's commemoratio structure before the Greek citation. A reduces to a bare fragment ('This man') that drops the calendar frame and the named subject, losing critical context from the segment.

#### Pairing `run02`

- **v0:** "He
- **v1:** day of March, the following commemoration of Aristobulus is made: 'Οὗ-
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=v1 proper_nouns=v1 titles=equal register=v1
- **Reason:**

  > Translation B preserves the Latin context ('day of March, the following commemoration of Aristobulus is made') and correctly carries the Greek incipit verbatim. Translation A renders only 'He', omitting almost all the Latin content and providing no meaningful rendition of the segment.

#### Pairing `run03`

- **v0:** "This man
- **v1:** teenth day of March the following commemoration is made: "Οὗ-
- **Judge winner:** `v1`  (swapped=False)
- **Rubric:** fluency=v1 accuracy=v1 proper_nouns=equal titles=equal register=v1
- **Reason:**

  > B preserves the structural context ('on the fifth day of March the following commemoration is made') that the Latin supplies, while A drops to a fragment with only 'This man,' losing the framing clause entirely. B's rendering is more accurate and coherent despite both being partial segments.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 2. `seg_p0041_body_l0013`

_v1 wins=0  v0 wins=3  ties=0  rubric swing(v1)=-9_

**Latin source:**

> τος ἦν εἷς τῶν ἑβδομήκοντα μαθητῶν, ἠκολούθησε δὲ τῷ ἁγίῳ

#### Pairing `run01`

- **v0:** was one of the seventy disciples, and he followed the holy
- **v1:** τος ἦν εἷς τῶν ἑβδομήκοντα μαθητῶν, ἠκολούθησε δὲ τῷ ἁγίῳ
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > The source segment is pure Greek with no Latin paraphrase present in this segment, so the domain rule requires an English rendering. B accurately translates the Greek fragment ('was one of the seventy disciples, and he followed the holy'). A merely reproduces the Greek verbatim, providing no English for the reader and constituting an accuracy failure under the stated rule.

#### Pairing `run02`

- **v0:** was one of the seventy disciples, and he followed the holy
- **v1:** τος ἦν εἷς τῶν ἑβδομήκοντα μαθητῶν, ἠκολούθησε δὲ τῷ ἁγίῳ
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > The source segment is pure Greek with no accompanying Latin paraphrase, so by the domain rule the Greek must be rendered into English. B does so correctly ('was one of the seventy disciples, and he followed the holy'), while A simply passes the Greek through verbatim—an accuracy and fluency failure here.

#### Pairing `run03`

- **v0:** was one of the seventy disciples, and he followed the holy
- **v1:** τος ἦν εἷς τῶν ἑβδομήκοντα μαθητῶν, ἠκολούθησε δὲ τῷ ἁγίῳ
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > The source segment is pure Greek with no Latin paraphrase present; under the domain rule, Greek standing alone must be rendered into English, making A's verbatim pass-through an accuracy failure. B supplies a competent, natural English rendering of the visible Greek content.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 3. `seg_p0041_body_l0015`

_v1 wins=0  v0 wins=3  ties=0  rubric swing(v1)=-9_

**Latin source:**

> κουμένην διακονῶν αὐτῷ· ὑφ᾽ οὗ καὶ χειροτονεῖται ἐπίσκοπος

#### Pairing `run01`

- **v0:** world while ministering to him; by whom he is also ordained bishop
- **v1:** κουμένην διακονῶν αὐτῷ· ὑφ᾽ οὗ καὶ χειροτονεῖται ἐπίσκοπος
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > The Latin source is a Greek fragment with no surrounding Latin paraphrase in this segment, so the Greek should be rendered into English. A translates the Greek into natural scholarly English ('world while ministering to him; by whom he is also ordained bishop'). B merely reproduces the Greek untranslated, which is an accuracy failure given no Latin gloss is present.

#### Pairing `run02`

- **v0:** world while serving him; by whom he was also ordained bishop
- **v1:** κουμένην διακονῶν αὐτῷ· ὑφ᾽ οὗ καὶ χειροτονεῖται ἐπίσκοπος
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > The segment is entirely Greek with no Latin paraphrase present; per the domain rule the Greek should be rendered into English, making A correct and B an accuracy failure. B returns raw Greek as its 'translation,' which fails fluency and register entirely.

#### Pairing `run03`

- **v0:** world and ministering to him; by whom he was also ordained bishop
- **v1:** κουμένην διακονῶν αὐτῷ· ὑφ᾽ οὗ καὶ χειροτονεῖται ἐπίσκοπος
- **Judge winner:** `v0`  (swapped=False)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > The source segment is entirely Greek with no visible Latin paraphrase in this segment, so the domain rule requires rendering it into English. A provides a fluent, accurate English translation of the Greek fragment. B simply reproduces the Greek verbatim, yielding no English text at all and failing on fluency, accuracy, and register.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 4. `seg_p0041_body_l0016`

_v1 wins=0  v0 wins=3  ties=0  rubric swing(v1)=-9_

**Latin source:**

> εἰς τὴν τῶν Βρετανῶν χώραν, ἀγρίων ἀνδρῶν καὶ ὠμοτάτων·

#### Pairing `run01`

- **v0:** for the country of the Britons, men wild and most savage;
- **v1:** εἰς τὴν τῶν Βρετανῶν χώραν, ἀγρίων ἀνδρῶν καὶ ὠμοτάτων·
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=equal proper_nouns=v0 titles=equal register=equal
- **Reason:**

  > This segment is entirely Greek with no Latin present to serve as Ussher's own paraphrase, so leaving it untranslated (A) withholds substantive content from the English reader. B renders the passage into English and uses the Anglicized 'Britons' over the Greek form; its inverted word order ('men wild') is a minor stylistic weakness that does not outweigh the gain.

#### Pairing `run02`

- **v0:** for the country of the Britons, men savage and most cruel;
- **v1:** εἰς τὴν τῶν Βρετανῶν χώραν, ἀγρίων ἀνδρῶν καὶ ὠμοτάτων·
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=equal proper_nouns=v0 titles=equal register=v0
- **Reason:**

  > This segment is entirely Greek with no Latin present, so the 'leave Greek untranslated' rule applies only if a Latin paraphrase exists in an adjacent segment — which cannot be confirmed here (accuracy scored equal per the doubt rule). A produces no English at all; B delivers readable prose and correctly Anglicizes 'Britons,' though 'men savage and most cruel' carries mild archaic word order.

#### Pairing `run03`

- **v0:** for the country of the Britons, men savage and most cruel;
- **v1:** εἰς τὴν τῶν Βρετανῶν χώραν, ἀγρίων ἀνδρῶν καὶ ὠμοτάτων·
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=v0 titles=equal register=v0
- **Reason:**

  > The source segment is pure Greek with no Latin paraphrase present; the domain rule therefore requires an English rendering, not a verbatim pass-through. B correctly translates the Greek into English and uses the proper Anglicized form 'Britons.' A's untranslated Greek is an accuracy failure here, not an editorial virtue.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 5. `seg_p0041_body_l0023`

_v1 wins=0  v0 wins=3  ties=0  rubric swing(v1)=-9_

**Latin source:**

> copus ordinatus est in Britannorum regionem, ferorum

#### Pairing `run01`

- **v0:** bishop into the country of the Britons, of fierce
- **v1:** op he was ordained for the land of the Britons, of fierce
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > A renders 'episcopus' as 'op' (corrupted/truncated) and omits 'bishop', making it unintelligible. B correctly supplies 'bishop' and 'country' for 'regionem', yielding a coherent fragment. A's garbled opening is a clear accuracy and fluency failure.

#### Pairing `run02`

- **v0:** ordained bishop for the region of the Britons, of fierce
- **v1:** dained bishop into the region of the Britons, of fierce
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > Both are fragments, but B uses 'ordained' (complete) vs A's 'dained' (truncated, likely OCR artifact). B also uses 'for the region' which is slightly more idiomatic than 'into the region' for a bishop's jurisdiction, though the difference is minor.

#### Pairing `run03`

- **v0:** ordained bishop for the region of the Britons, of fierce
- **v1:** op he was ordained for the region of the Britons, [a land] of fierce
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=v0 accuracy=v0 proper_nouns=equal titles=equal register=v0
- **Reason:**

  > A begins with a garbled fragment ('op he was ordained') that appears to be a OCR/truncation artifact, rendering it incoherent. B cleanly supplies 'ordained bishop' for 'episcopus ordinatus est' and reads as natural scholarly prose. A's mangled opening is a clear accuracy and fluency failure.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

## Tied picks

### 1. `seg_p0041_body_l0008`

_v1 wins=0  v0 wins=0  ties=0  rubric swing(v1)=+0_

**Latin source:**

> rone martyrio cursum consummavit.

#### Pairing `run01`

- **v0:** 
- **v1:** Nero he ended his course in martyrdom.
- **Judge winner:** `—`  (swapped=False)
- **Rubric:** fluency=— accuracy=— proper_nouns=— titles=— register=—
- **Judge error:** missing english on one side

#### Pairing `run02`

- **v0:** 
- **v1:** ro he completed his course in martyrdom.
- **Judge winner:** `—`  (swapped=False)
- **Rubric:** fluency=— accuracy=— proper_nouns=— titles=— register=—
- **Judge error:** missing english on one side

#### Pairing `run03`

- **v0:** 
- **v1:** ro he completed his course by martyrdom.
- **Judge winner:** `—`  (swapped=False)
- **Rubric:** fluency=— accuracy=— proper_nouns=— titles=— register=—
- **Judge error:** missing english on one side

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 2. `seg_p0041_fn_004`

_v1 wins=0  v0 wins=0  ties=0  rubric swing(v1)=+0_

**Latin source:**

> Rom. cap. 16. ver. 10.

#### Pairing `run01`

- **v0:** Romans, chapter 16, verse 10.
- **v1:** Romans, chapter 16, verse 10.
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both translations are identical renderings of a bare scriptural reference. There is no meaningful distinction to evaluate across any rubric.

#### Pairing `run02`

- **v0:** Romans, chapter 16, verse 10.
- **v1:** Romans, ch. 16, v. 10.
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both renderings are equally faithful and appropriate abbreviations of a bare scriptural citation. 'ch.' and 'v.' (A) vs. 'chapter' and 'verse' (B) are both standard scholarly conventions; neither is preferable on any rubric.

#### Pairing `run03`

- **v0:** Romans, chapter 16, verse 10.
- **v1:** Romans, chapter 16, verse 10.
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=equal accuracy=equal proper_nouns=equal titles=equal register=equal
- **Reason:**

  > Both translations are identical renderings of a simple biblical reference abbreviation. No meaningful distinction exists across any rubric.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---

### 3. `seg_p0041_fn_003`

_v1 wins=1  v0 wins=1  ties=0  rubric swing(v1)=+4_

**Latin source:**

> Πᾶσαν σχεδὸν τὴν γῆν διελθὼν, καὶ ἐπὶ πέντε καὶ τριάκοντα ὑπὲρ Χριστοῦ τῷ εὐαγγελίῳ διαθλεύσας ἐνιαυτοῖς. Niceph. hist. eccles. lib. 12. cap. 34. Vix triginta annorum spatio et Romanos, et Persas, et Parthos, et Medos, et Indos, et Scythas, et Sauromatas, et Sarracenos, et omne prorsus humanum genus sub jugum mitteret veritatis, &c. Chrysost. homil. 4. de laudib. Pauli. Clemens in epistola ad Corinthios pag. 8. de eodem: Κῆρυξ γενόμενος ἐν τῇ ἀνατολῇ καὶ ἐν τῇ δύσει, τὸ γενναῖον τῆς πίστεως αὑτοῦ κλέος ἔλαβεν δικαιοσύνην διδάξαι ὅλον τὸν κόσμον, καὶ ἐπὶ τὸ τέρμα τῆς δύσεως ἐλθὼν, καὶ μαρτυρήσας ἐπὶ τῶν ἡγουμένων, οὕτως ἀπηλλάγη τοῦ κόσμου. In oriente ac occidente verbi præco factus, illustrem fidei suæ fainam sortitus est, in justitia mundum universum instruens, et ad occidentis terminos veniens, et sub imperatoribus martyrium subiens, sic e mundo migravit.

#### Pairing `run01`

- **v0:** "Having gone through nearly the whole earth, and having contended in the gospel for Christ for thirty-five years." Nicephorus, Ecclesiastical History, book 12, chapter 34. "Within the space of scarcely thirty years he brought the Romans, the Persians, the Parthians, the Medes, the Indians, the Scythians, the Sauromatae, the Saracens, and absolutely the entire human race under the yoke of truth, etc." Chrysostom, Homily 4 on the Praises of Paul. Clement, in his Epistle to the Corinthians, page 8, concerning the same: "Having become a herald in the East and in the West, he received the noble renown of his faith, having taught righteousness to the whole world, and having come to the limit of the West, and having borne witness before the rulers, he thus departed from the world." "Having become a preacher of the word in the East and in the West, he obtained the illustrious fame of his faith, instructing the whole world in righteousness, and coming to the boundaries of the West, and undergoing martyrdom under the emperors, he thus departed from the world."
- **v1:** Πᾶσαν σχεδὸν τὴν γῆν διελθὼν, καὶ ἐπὶ πέντε καὶ τριάκοντα ὑπὲρ Χριστοῦ τῷ εὐαγγελίῳ διαθλεύσας ἐνιαυτοῖς. Nicephorus, "Ecclesiastical History," book 12, chapter 34. "In a span of barely thirty years he would bring under the yoke of truth the Romans, Persians, Parthians, Medes, Indians, Scythians, Sarmatians, Saracens, and indeed the whole human race, etc." Chrysostom, Homily 4, "On the Praises of Paul." Clement, in the Epistle to the Corinthians, page 8, on the same: Κῆρυξ γενόμενος ἐν τῇ ἀνατολῇ καὶ ἐν τῇ δύσει, τὸ γενναῖον τῆς πίστεως αὑτοῦ κλέος ἔλαβεν δικαιοσύνην διδάξαι ὅλον τὸν κόσμον, καὶ ἐπὶ τὸ τέρμα τῆς δύσεως ἐλθὼν, καὶ μαρτυρήσας ἐπὶ τῶν ἡγουμένων, οὕτως ἀπηλλάγη τοῦ κόσμου. "Having become a herald of the word in the East and the West, he obtained the illustrious fame of his faith, instructing the whole world in righteousness; and coming to the bounds of the West, and undergoing martyrdom under the rulers, thus he departed from the world."
- **Judge winner:** `tie`  (swapped=True)
- **Rubric:** fluency=v1 accuracy=v0 proper_nouns=v0 titles=v1 register=v1
- **Reason:**

  > A italicizes titles and reads more fluently, but incorrectly leaves the first Greek passage untranslated (it has no Latin paraphrase in this segment) and omits 'Sauromatae.' B translates the opening Greek correctly and preserves 'Sauromatae,' but double-translates the Clement Greek passage (rendering both Greek and Latin paraphrase) and is more stilted. Neither is clearly superior overall.

#### Pairing `run02`

- **v0:** "Having traversed nearly the whole earth, and having contended for Christ in the gospel for thirty-five years." Nicephorus, Ecclesiastical History, book 12, chapter 34. "In scarcely thirty years' span he brought under the yoke of truth the Romans, the Persians, the Parthians, the Medes, the Indians, the Scythians, the Sauromatae, the Saracens, and absolutely the whole human race, etc." Chrysostom, Homily 4 in Praise of Paul. Clement, in his Epistle to the Corinthians, page 8, says of the same man: "Having become a herald in the East and in the West, he obtained the noble renown of his faith, teaching righteousness to the whole world; and having come to the limit of the West, and having borne witness before the rulers, he thus departed from the world." "Made a herald of the word in the East and the West, he won an illustrious reputation for his faith, instructing the whole world in righteousness, and coming to the bounds of the West, and undergoing martyrdom under the emperors, thus he departed from the world."
- **v1:** Πᾶσαν σχεδὸν τὴν γῆν διελθὼν, καὶ ἐπὶ πέντε καὶ τριάκοντα ὑπὲρ Χριστοῦ τῷ εὐαγγελίῳ διαθλεύσας ἐνιαυτοῖς. Nicephorus, Ecclesiastical History, book 12, ch. 34. Within scarcely thirty years' span he would bring under the yoke of truth both the Romans, and the Persians, and the Parthians, and the Medes, and the Indians, and the Scythians, and the Sauromatae, and the Saracens, and altogether the whole human race, etc. Chrysostom, "Homily 4 on the Praises of Paul." Clement, in his epistle to the Corinthians, p. 8, on the same: Κῆρυξ γενόμενος ἐν τῇ ἀνατολῇ καὶ ἐν τῇ δύσει, τὸ γενναῖον τῆς πίστεως αὑτοῦ κλέος ἔλαβεν δικαιοσύνην διδάξαι ὅλον τὸν κόσμον, καὶ ἐπὶ τὸ τέρμα τῆς δύσεως ἐλθὼν, καὶ μαρτυρήσας ἐπὶ τῶν ἡγουμένων, οὕτως ἀπηλλάγη τοῦ κόσμου. Having become a herald in the East and in the West, he obtained illustrious renown for his faith, instructing the whole world in righteousness, and, coming to the western limits and undergoing martyrdom under the rulers, he thus departed from the world.
- **Judge winner:** `v0`  (swapped=True)
- **Rubric:** fluency=equal accuracy=v0 proper_nouns=equal titles=v1 register=v0
- **Reason:**

  > B correctly renders the standalone Nicephorus Greek (which has no Latin paraphrase and therefore must be translated), where A leaves it untranslated — a clear accuracy failure. B also produces cleaner register in the Chrysostom passage, avoiding A's awkward 'both...and...and...' enumeration across eight items. A earns the titles point by quoting the Chrysostom homily title rather than leaving it b

#### Pairing `run03`

- **v0:** "Having traversed nearly the whole earth, and having contended in the gospel for Christ for thirty-five years." Nicephorus, Ecclesiastical History, book 12, chapter 34. "In scarcely the space of thirty years he subjected to the yoke of truth Romans and Persians and Parthians and Medes and Indians and Scythians and Sauromatae and Saracens, and indeed the whole human race, etc." Chrysostom, Homily 4 In Praise of Paul. Clement, in the Epistle to the Corinthians, page 8, of the same: "Becoming a herald in the East and in the West, he obtained the noble renown of his faith, teaching righteousness to the whole world, and having come to the bounds of the West and borne witness before the rulers, thus he departed from the world." "Made a preacher of the word in the East and the West, he obtained the illustrious fame of his faith, instructing the whole world in righteousness, and coming to the bounds of the West and undergoing martyrdom under the emperors, thus he passed from the world."
- **v1:** Having traversed nearly the whole earth, and having contended for Christ through the gospel for five and thirty years. Nicephorus, Ecclesiastical History, book 12, chapter 34. Within scarcely thirty years' span he would bring under the yoke of truth the Romans, the Persians, the Parthians, the Medes, the Indians, the Scythians, the Sarmatians, the Saracens, and the entire human race outright, etc. Chrysostom, homily 4, "On the Praises of Paul." Clement, in the epistle to the Corinthians, page 8, on the same: Κῆρυξ γενόμενος ἐν τῇ ἀνατολῇ καὶ ἐν τῇ δύσει, τὸ γενναῖον τῆς πίστεως αὑτοῦ κλέος ἔλαβεν δικαιοσύνην διδάξαι ὅλον τὸν κόσμον, καὶ ἐπὶ τὸ τέρμα τῆς δύσεως ἐλθὼν, καὶ μαρτυρήσας ἐπὶ τῶν ἡγουμένων, οὕτως ἀπηλλάγη τοῦ κόσμου. Becoming the herald of the word in the East and in the West, he obtained illustrious fame for his faith, instructing the whole world in righteousness, and coming to the limits of the West, and undergoing martyrdom under the emperors, he thus departed from the world.
- **Judge winner:** `v1`  (swapped=True)
- **Rubric:** fluency=v1 accuracy=v1 proper_nouns=v1 titles=equal register=v1
- **Reason:**

  > A correctly leaves the Clement Greek untranslated (Latin paraphrase follows) and renders only the Latin into English once. B double-translates by providing an English gloss of the Greek then separately rendering the Latin paraphrase, producing redundant text. B also uses 'Sauromatae' (Latinism) where A has 'Sarmatians', and its quoted-speech formatting fragments the prose register.

**Reviewer verdict:**  [ ] v0 better   [ ] v1 better   [ ] tie   [ ] both bad

**Reviewer notes:**

> 

---
