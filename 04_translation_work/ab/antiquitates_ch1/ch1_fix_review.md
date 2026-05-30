# Fix Review — Chapter 1 (ussher_v5)

Source: `08_working_scratch\phase3b\ch1_fidelity_fixes.jsonl`  
Units with proposed corrections: **127**  
Of which **126** are real changes; **1** marked NO CHANGE (fixer disagreed with the judge — the prior English is being kept).

### Distribution by judge content-fidelity score

| cf | n |
|---:|---:|
| 1 | 10 |
| 2 | 42 |
| 3 | 74 |
| 4 | 1 |

### How to review

Walk top-to-bottom. cf=1 (catastrophic) comes first. For each block:

- Compare **Prior English** with **Proposed English** against the judge's diagnosis.
- Check the box next to your decision. If you choose **edit**, write your edited version on the line below the decision.
- A separate `apply_fixes.py` pass (to be built) will read this file and apply your decisions back into `segments_with_translations.jsonl`.

---


## cf = 1 — catastrophic

### `seg_p0033_body_l0025` &nbsp;·&nbsp; page p0033
**Scores:** cf=1 · rf=1 · gp=na · ph=na

**Judge:** Candidate is a bare em-dash offering no translation of the Latin fragment 'multitudines,' so content fidelity is completely absent and register cannot be assessed.

**Latin source:**
```
multitudines;
```

**Prior English:**
```
—
```

**Proposed English:** _(model: claude-opus-4-7)_
```
multitudes;
```

**Fixer:** Replaced the bare em-dash with a direct English rendering of the Latin fragment 'multitudines'.

**Decision:** [x] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0009` &nbsp;·&nbsp; page p0036
**Scores:** cf=1 · rf=4 · gp=na · ph=na

**Judge:** 'cladem illam maximam' (that greatest disaster/calamity) is wholly omitted, and 'Lioness' has no basis in the Latin fragment; only 'treacherous' (dolosam) is correctly rendered.

**Latin source:**
```
ille appellat dolosam, cladem illam maximam) adversus
```

**Prior English:**
```
calls a treacherous Lioness) against
```

**Proposed English:** _(model: claude-opus-4-7)_
```
he calls treacherous — that greatest disaster) against
```

**Fixer:** Restored the omitted 'cladem illam maximam' as 'that greatest disaster' and removed the unsupported 'Lioness'; 'dolosam' agrees with the feminine 'cladem' (disaster), so it modifies the disaster, not a lioness.

**Decision:** [x] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0019` &nbsp;·&nbsp; page p0036
**Scores:** cf=1 · rf=1 · gp=5 · ph=na

**Judge:** Greek is preserved verbatim; however, the candidate provides no English translation whatsoever—it is a bare repetition of the Greek source fragment, so content_fidelity and register_fidelity both score 1.

**Latin source:**
```
ἀνθρώποις τοὺς εὐαγγελικοὺς προσενηνόχασι νόμους· καὶ οὐ
```

**Prior English:**
```
ἀνθρώποις τοὺς εὐαγγελικοὺς προσενηνόχασι νόμους· καὶ οὐ
```

**Proposed English:** _(model: claude-opus-4-7)_
```
ἀνθρώποις τοὺς εὐαγγελικοὺς προσενηνόχασι νόμους· καὶ οὐ [have brought the evangelical laws to men; and not]
```

**Fixer:** Added the required English bracket gloss after the preserved Greek, per Rule 1.

**Decision:** [ ] accept   [ ] reject (keep prior)   [x] edit (write below)
ἀνθρώποις τοὺς εὐαγγελικοὺς προσενηνόχασι νόμους· καὶ οὐ [they have brought the evangelical precepts to men; and not]
---

### `seg_p0036_body_l0026` &nbsp;·&nbsp; page p0036
**Scores:** cf=1 · rf=3 · gp=na · ph=na

**Judge:** 'torque' (twisted metal neck-ornament/collar) is rendered as 'leather-worker' — a fundamental lexical error; 'legem' (law) is softened to 'teaching'; and a finite verb is introduced with no Latin basis; register is otherwise acceptable modern scholarly prose.

**Latin source:**
```
torque ille noster, cunctis nationibus legem evangelicam
```

**Prior English:**
```
leather-worker of ours, brought the evangelical teaching to all nations.
```

**Proposed English:** _(model: claude-opus-4-7)_
```
that torque of ours, the evangelical law to all nations
```

**Fixer:** Corrected 'leather-worker' to 'torque' (the neck-ornament sense of 'torque'), restored 'legem' as 'law' rather than 'teaching', and removed the unwarranted finite verb since the Latin fragment has none.

**Decision:** [ ] accept   [x] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0010` &nbsp;·&nbsp; page p0038
**Scores:** cf=1 · rf=4 · gp=na · ph=na

**Judge:** The Latin specifies ordination at Rome ('apud Romam ordinantur') before sending to preach, but the translation omits the Roman ordination entirely, reducing two distinct clauses to one; register is appropriate scholarly English.

**Latin source:**
```
apud Romam ordinantur, et ad prædicandum Dei verbum
```

**Prior English:**
```
and were sent to preach the word of God
```

**Proposed English:** _(model: claude-opus-4-7)_
```
are ordained at Rome, and sent to preach the word of God
```

**Fixer:** Restored the omitted 'apud Romam ordinantur' clause as 'are ordained at Rome' to capture both distinct actions the Latin specifies.

**Decision:** [ ] accept   [ ] reject (keep prior)   [x] edit (write below)
They are ordained at Rome, and for preaching the word of God
---

### `seg_p0039_body_l0023` &nbsp;·&nbsp; page p0039
**Scores:** cf=1 · rf=4 · gp=na · ph=na

**Judge:** Two compounding errors: 'martyrologiis' (martyrologies) is silently dropped, and 'octavum' (eighth) is rendered as 'twenty-eighth'—a factual mistranslation that changes the calendrical reference.

**Latin source:**
```
atque Adonis martyrologiis, ad Octobris diem octavum
```

**Prior English:**
```
and Ado, on the twenty-eighth day of October
```

**Proposed English:** _(model: claude-opus-4-7)_
```
and in the martyrologies of Ado, on the eighth day of October
```

**Fixer:** Restored the dropped 'martyrologiis' and corrected 'octavum' from 'twenty-eighth' to 'eighth'.

**Decision:** [x] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0041_body_l0012` &nbsp;·&nbsp; page p0041
**Scores:** cf=1 · rf=4 · gp=5 · ph=na

**Judge:** "quintum diem" (fifth day) is rendered as "fifteenth day" — a clear mistranslation; the bracketed "[This—" has no visible counterpart in the Latin source; Greek "Οὗ-" is preserved verbatim.

**Latin source:**
```
quintum diem Martii, hujusmodi fit commemoratio: “ Οὗ-
```

**Prior English:**
```
fifteenth day of March, a commemoration of this kind is made: "Οὗ- [This—
```

**Proposed English:** _(model: claude-opus-4-7)_
```
on thefifth day of March, a commemoration of this kind is made: "Οὗ-
```

**Fixer:** Corrected 'fifteenth' to 'fifth' (quintum) and removed the spurious bracketed gloss '[This—', since the truncated Greek 'Οὗ-' is a mid-word fragment with no translatable content.

**Decision:** [ ] accept   [ ] reject (keep prior)   [x] edit (write below)
on the fifth day of March, a commemoration of this kind is made: "Οὗ-
---

### `seg_p0044_fn_003` &nbsp;·&nbsp; page p0044
**Scores:** cf=1 · rf=3 · gp=1 · ph=na

**Judge:** The candidate renders only the citation header, omitting the entire Martial verse, the prose sentence on Trajan/Nerva, and the Greek quotation from Aelian (Ἐπεὶ δὲ τῷ Θεῷ…), so content_fidelity and greek_preservation both fail; the single translated line is register-appropriate but too brief to assess fully.

**Latin source:**
```
Martial. lib. 11. epigram. 4.

Et qui purpureis jam tertia nomina fastis,
Iane, refers Nervæ.

Trajanus vero post adoptionem, Nerva etiam dictus est: ut apud Ælianum, in
Tacticorum proœmio ad Hadrian. Imp. Ἐπεὶ δὲ τῷ Θεῷ πατρί σου Νέρουᾳ
συμβαλὼν, &c.
```

**Prior English:**
```
Martial, book 11, epigram 4.
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Martial, book 11, epigram 4.

And you, Janus, who now bring back for the third time the name of Nerva in the purple fasti.

But Trajan too, after his adoption, was called Nerva: as in Aelian, in the preface to the "Tactics" addressed to the Emperor Hadrian, Ἐπεὶ δὲ τῷ Θεῷ πατρί σου Νέρουᾳ συμβαλὼν, &c. [Since, having conferred with your divine father Nerva, etc.].
```

**Fixer:** Added the missing Martial verse, the prose sentence on Trajan/Nerva, and the Greek citation from Aelian with an English bracket gloss per Rule 1.

**Decision:** [ ] accept   [ ] reject (keep prior)   [x] edit (write below)
Martial, Book XI, Epigram 4:

"And you, Janus, who now record Nerva's name for the third time in the imperial fasti."

But Trajan also, after his adoption, was called Nerva, as appears in Aelian's Tactics, in the preface addressed to the Emperor Hadrian:

Ἐπεὶ δὲ τῷ Θεῷ πατρί σου Νέρουᾳ συμβαλὼν, etc.

("Since, having had dealings with your divine father Nerva, ...")
---

### `seg_p0045_body_l0005` &nbsp;·&nbsp; page p0045
**Scores:** cf=1 · rf=3 · gp=na · ph=na

**Judge:** The main verb 'Rexerat' (he had ruled/reigned) is entirely dropped, leaving only the relative clause; 'hallowed' for 'sacer' carries KJV resonance rather than neutral scholarly register.

**Latin source:**
```
Rexerat, asserto qui sacer orbe fuit :
```

**Prior English:**
```
he who was hallowed when the world was set free,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
he had reigned, who was consecrated when the world was set free,
```

**Fixer:** Restored the dropped main verb 'Rexerat' ('he had reigned') and replaced KJV-toned 'hallowed' with the neutral scholarly 'consecrated' for 'sacer'.

**Decision:** [ ] accept   [x] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0045_body_l0010` &nbsp;·&nbsp; page p0045
**Scores:** cf=1 · rf=4 · gp=na · ph=na

**Judge:** The translation adds 'and Claudia' which is absent from the Latin source ('Pudens et Linus' only); register is appropriate scholarly English.

**Latin source:**
```
est epistola, in qua Timotheum salutant Pudens et Linus
```

**Prior English:**
```
in which Pudens and Linus and Claudia greet Timothy
```

**Proposed English:** _(model: claude-opus-4-7)_
```
in which Pudens and Linus greet Timothy
```

**Fixer:** Removed 'and Claudia' which is not present in the Latin source ('Pudens et Linus' only).

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---


## cf = 2 — moderate

### `seg_p0032_body_l0016` &nbsp;·&nbsp; page p0032
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** No Greek present. 'barbarous' and 'round about' are not in the Latin fragment ('omnesque' = 'and all'); these additions materially expand Ussher's text. Register is appropriately scholarly throughout.

**Latin source:**
```
“et Scoticæ gentes omnesque usque ad oceanum per
```

**Prior English:**
```
“and the Scottish peoples, and all the barbarous nations round about, as far as the ocean,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
and the Scottish peoples, and all as far as the ocean,
```

**Fixer:** Removed unsupported 'barbarous' and 'round about'; 'omnesque' is simply 'and all', so the addition was unwarranted expansion of Ussher's text.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0032_body_l0017` &nbsp;·&nbsp; page p0032
**Scores:** cf=2 · rf=5 · gp=na · ph=na

**Judge:** The fragment 'circuitum barbaræ nationes' (the surrounding barbarian nations) is entirely absent from the translation, which renders only the verb and its objects; register is modern scholarly and appropriate.

**Latin source:**
```
circuitum barbaræ nationes Moysen prophetasque cogno-
```

**Prior English:**
```
had come to know Moses and the prophets.”
```

**Proposed English:** _(model: claude-opus-4-7)_
```
the surrounding barbarian nations had come to know Moses and the prophets.”
```

**Fixer:** Added the missing subject 'circuitum barbaræ nationes' as 'the surrounding barbarian nations' so the clause has its full content per Rule 2.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0034_body_l0010` &nbsp;·&nbsp; page p0034
**Scores:** cf=2 · rf=5 · gp=5 · ph=na

**Judge:** Greek preserved verbatim with accurate bracketed gloss; however 'non insulas' is entirely omitted from the translation, dropping Ussher's contrasting qualification ('not islands') that is integral to the sentence's meaning.

**Latin source:**
```
τρίτην ἀνθρώποις κατοικίαν ἡ φύσις ἐδίδου, non insulas,
```

**Prior English:**
```
τρίτην ἀνθρώποις κατοικίαν ἡ φύσις ἐδίδου [third dwelling-place that nature granted to men]
```

**Proposed English:** _(model: claude-opus-4-7)_
```
τρίτην ἀνθρώποις κατοικίαν ἡ φύσις ἐδίδου [third dwelling-place that nature granted to men], not islands,
```

**Fixer:** Appended the omitted Latin qualification 'non insulas' as 'not islands,' preserving Ussher's contrasting clause integral to the sentence's meaning.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0034_body_l0026` &nbsp;·&nbsp; page p0034
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The key ablative 'secessu' (withdrawal/retreat) is wholly absent from the translation, and 'merely temporal' is added with no basis in the Latin fragment; 'de firma-' supports only 'firmament,' not a qualified epithet.

**Latin source:**
```
secessu soli visibili non proximæ verus ille non de ﬁrma-
```

**Prior English:**
```
not near to the visible sun—that true Sun, not from the merely temporal firmament
```

**Proposed English:** _(model: claude-opus-4-7)_
```
by a withdrawal not near to the visible sun—that true Sun, not from the firma-
```

**Fixer:** Restored 'secessu' as 'by a withdrawal' and removed the unsupported 'merely temporal' epithet, leaving the truncated 'firma-' fragment as in the Latin.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0034_body_l0027` &nbsp;·&nbsp; page p0034
**Scores:** cf=2 · rf=3 · gp=na · ph=na

**Judge:** 'temporali' (temporal) is dropped entirely from the translation, and 'citadel' is added with no Latin warrant — 'summa cœlorum' means 'summit/heights of the heavens'; 'citadel' inflates the register toward the dramatic rather than the scholarly.

**Latin source:**
```
mento solum^q temporali, sed de summa etiam cœlorum
```

**Prior English:**
```
alone^q, but also from the highest citadel of the heavens
```

**Proposed English:** _(model: claude-opus-4-7)_
```
temporal alone^q, but also from the highest heavens
```

**Fixer:** Restored the dropped 'temporali' ('temporal') and replaced 'citadel of the heavens' with the plainer 'highest heavens' to match the scholarly register.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0034_body_l0031` &nbsp;·&nbsp; page p0034
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** 'religio' (the subject) is entirely absent from the translation, and the verb 'gabatur' is unrendered; 'comminata' is rendered as 'death being threatened' (supplying 'morte' not present in the fragment) rather than modifying 'religio'; register is appropriately scholarly.

**Latin source:**
```
gabatur religio comminata, senatu nolente, a principe^r
```

**Prior English:**
```
death being threatened—the senate being unwilling—by the prince^r
```

**Proposed English:** _(model: claude-opus-4-7)_
```
religion was being threatened with prohibition, the senate being unwilling, by the prince^r
```

**Fixer:** Restored the missing subject 'religio' and rendered the verb 'gabatur' (passive imperfect, likely from 'abrogabatur' — the religion was being abrogated/prohibited) with 'comminata' modifying it, instead of inventing 'death'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0034_body_l0032` &nbsp;·&nbsp; page p0034
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** 'morte' (death/by death) is entirely dropped; 'ejusdem' (of the same) is expanded to 'that same faith' with 'faith' having no Latin warrant; register is otherwise appropriate for a scholarly fragment.

**Latin source:**
```
morte delatoribus^s militum ejusdem) radios suos primum
```

**Prior English:**
```
against the informers of the soldiers of that same faith)^s—his rays, first,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
by death of the informers of those same soldiers)^s—his rays, first,
```

**Fixer:** Restored dropped 'morte' as 'by death' and corrected 'ejusdem' to modify 'soldiers' ('those same soldiers') rather than inventing 'faith'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0027` &nbsp;·&nbsp; page p0035
**Scores:** cf=2 · rf=3 · gp=na · ph=na

**Judge:** 'listarum scilicet' (roughly 'of these, namely') is entirely unrendered, and 'their words' is inserted without warrant from this fragment; 'unto' is a KJV archaism the rubric disallows, though it may reflect the embedded scriptural quotation.

**Latin source:**
```
listarum scilicet et apostolorum, et in fines orbis terræ
```

**Prior English:**
```
and the apostles' — "and their words unto the ends of the world."
```

**Proposed English:** _(model: claude-opus-4-7)_
```
of the evangelists, namely, and of the apostles, and into the ends of the earth
```

**Fixer:** Rendered the unrendered 'listarum scilicet' (taking 'listarum' as the truncated genitive of 'evangelistarum'), removed the unwarranted 'their words' insertion, and replaced KJV 'unto' with plain 'into'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0033` &nbsp;·&nbsp; page p0035
**Scores:** cf=2 · rf=4 · gp=5 · ph=na

**Judge:** Greek is preserved verbatim with accents; no visible Latin paraphrase in source so paraphrase_handling is na; 'its worship' badly misrenders 'ejus expers relinqueretur' (verbal passive subjunctive and expers='deprived of' are lost entirely); register is appropriately scholarly though '[which were founded]' has a subject-verb agreement error.

**Latin source:**
```
ejus expers relinqueretur." Μία^x ἡ ἐκκλησία, ἣν ἱδρύσαντο
```

**Prior English:**
```
its worship.^x" Μία ἡ ἐκκλησία, ἣν ἱδρύσαντο [There is one Church, which were founded]
```

**Proposed English:** _(model: claude-opus-4-7)_
```
would be left deprived of it." Μία ἡ ἐκκλησία, ἣν ἱδρύσαντο [There is one Church, which they founded]
```

**Fixer:** Rendered 'ejus expers relinqueretur' as 'would be left deprived of it' (passive subjunctive + expers) and fixed the bracket gloss to 'which they founded' for subject-verb agreement.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0002` &nbsp;·&nbsp; page p0036
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** 'in sola Judæa' (in Judea alone) is silently dropped—a key limiting phrase—and 'God' is supplied from context but absent from this clause; register is appropriately scholarly but the content loss is substantial.

**Latin source:**
```
cum per tot millia annorum in sola Judæa notus fuerit
```

**Prior English:**
```
although through so many thousands of years God was known
```

**Proposed English:** _(model: claude-opus-4-7)_
```
although through so many thousands of years he was known in Judea alone
```

**Fixer:** Restored the dropped limiting phrase 'in sola Judæa' as 'in Judea alone' and replaced the context-supplied 'God' with 'he' to match the Latin's third-person singular subject without overspecifying.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0003` &nbsp;·&nbsp; page p0036
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The candidate translates 'Deus' as 'in Judaea alone' — a serious content failure introducing an absent phrase and dropping 'God' as the subject — though the rest of the fragment ('now within a few years…hidden neither from the Indians') is accurately rendered.

**Latin source:**
```
Deus, nunc intra paucos annos, nec ipsos Iɴᴅᴏs lateat a
```

**Prior English:**
```
in Judaea alone, now within a few years he lies hidden neither from the Indians on
```

**Proposed English:** _(model: claude-opus-4-7)_
```
God, now within a few years, lies hidden not even from the Indians themselves on
```

**Fixer:** Replaced the spurious 'in Judaea alone' with the actual subject 'God' (Deus) and rendered 'nec ipsos Indos' as 'not even from the Indians themselves' to capture the emphatic 'ipsos'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0008` &nbsp;·&nbsp; page p0036
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** 'Leænam' (the Lioness) is dropped entirely from the candidate, and 'that very great disaster' inserts 'very great' with no Latin warrant in the fragment; register is otherwise appropriately scholarly.

**Latin source:**
```
a Romanis, (post acceptam a Boadicia regina, quam Leænam
```

**Prior English:**
```
waged by the Romans (after suffering that very great disaster at the hands of Queen Boadicea, whom he
```

**Proposed English:** _(model: claude-opus-4-7)_
```
by the Romans (after suffering that disaster at the hands of Queen Boadicea, whom he called the Lioness
```

**Fixer:** Restored the dropped 'Leænam' as 'the Lioness' and removed the unwarranted 'very great' intensifier flagged by the judge.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0013` &nbsp;·&nbsp; page p0036
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The ablative absolute (cæsis Britannorum octoginta millibus) is correctly rendered, but veritatis suæ ('of his truth') is dropped entirely and 'Christ, he indicates,' is inserted without basis in the provided Latin fragment, constituting a significant omission and addition.

**Latin source:**
```
est, cæsis Britannorum octoginta millibus) veritatis suæ
```

**Prior English:**
```
with eighty thousand of the Britons slain) — Christ, he indicates,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
with eighty thousand of the Britons slain) of his truth
```

**Fixer:** Restored the dropped genitive 'veritatis suæ' as 'of his truth' and removed the unsupported insertion 'Christ, he indicates,' which had no basis in the Latin fragment.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0031` &nbsp;·&nbsp; page p0036
**Scores:** cf=2 · rf=3 · gp=na · ph=na

**Judge:** 'induxerunt' means 'led into/brought to' (a belief), not 'persuaded to accept teachings' — the object of crucifixi (of the crucified one) is dropped entirely, a significant content omission; register is acceptable but imprecise.

**Latin source:**
```
hominum genus, nationesque omnes induxerunt crucifixi
```

**Prior English:**
```
race of men and all nations — they persuaded to accept the teachings
```

**Proposed English:** _(model: claude-opus-4-7)_
```
they led the race of men and all nations to the faith of the crucified one
```

**Fixer:** Restored the dropped object 'crucifixi' (of the crucified one) and rendered 'induxerunt' as 'led to' rather than 'persuaded to accept teachings'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0037_body_l0008` &nbsp;·&nbsp; page p0037
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** 'Circumfertur nomine' ('is circulated/known under the name') is dropped and 'That [James preached]' inserts content entirely absent from the source; 'Saragossa' is an acceptable vernacular rendering of Caesaraugusta.

**Latin source:**
```
Cæsaraugustani episcopi circumfertur nomine. Britannis,
```

**Prior English:**
```
bishop of Saragossa. That [James preached] to the Britons,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
is circulated under the name of the bishop of Saragossa. To the Britons,
```

**Fixer:** Restored the dropped 'circumfertur nomine' ('is circulated under the name of') and removed the inserted '[James preached]' content that was absent from the source.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0037_body_l0009` &nbsp;·&nbsp; page p0037
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The translation inserts 'affirms; that he preached to the Irish' which has no basis in the Latin fragment ('larvam induit, Hibernis Vin-'); 'dons the mask' renders 'larvam induit' acceptably; register is appropriate scholarly English.

**Latin source:**
```
ille qui Flavii Lucii Dextri larvam induit, Hibernis Vin-
```

**Prior English:**
```
the man who dons the mask of Flavius Lucius Dexter affirms; that he preached to the Irish, Vin-
```

**Proposed English:** _(model: claude-opus-4-7)_
```
the man who dons the mask of Flavius Lucius Dexter, to the Irish Vin-
```

**Fixer:** Removed the unsupported insertion 'affirms; that he preached'; the Latin fragment ends after 'larvam induit' with the dative 'Hibernis' and the truncated 'Vin-', so I render it as a trailing fragment rather than inventing a verb.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0037_body_l0017` &nbsp;·&nbsp; page p0037
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** 'oratore' (envoy/ambassador) and 'productus' (brought forward/presented) are both dropped; 'writes' is added with no Latin warrant; 'Apostolis diversa' is expanded to 'the apostles were going to' — three content departures in a very short fragment.

**Latin source:**
```
tellani regis oratore, productus) ita: “Apostolis diversa
```

**Prior English:**
```
tilian king) writes thus: "As the apostles were going to the various
```

**Proposed English:** _(model: claude-opus-4-7)_
```
tilian king, brought forward as spokesman) thus: "To the apostles, various
```

**Fixer:** Restored 'oratore' (as spokesman) and 'productus' (brought forward), dropped the unwarranted 'writes', and rendered 'Apostolis diversa' literally as a dative + adjective fragment without expansion.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0037_body_l0018` &nbsp;·&nbsp; page p0037
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** 'cosmi climata adeuntibus' means 'for those approaching the regions of the world/cosmos' (a participial clause), but the translation adds 'driven to the shores' which invents content not in the Latin; 'nutu Dei' is correctly rendered 'by God's will'.

**Latin source:**
```
cosmi climata adeuntibus, nutu Dei Jacobus Hiberniæ
```

**Prior English:**
```
regions of the world, by God's will James, driven to the shores
```

**Proposed English:** _(model: claude-opus-4-7)_
```
regions of the world, by God's will James
```

**Fixer:** Removed the invented phrase 'driven to the shores'; the Latin participial clause 'cosmi climata adeuntibus' means only 'approaching the regions of the world', with no shoreward motion in the source.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0004` &nbsp;·&nbsp; page p0038
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The Latin is an ablative absolute ('duobus remanentibus') meaning 'two having remained'; the translation renders the noun clause correctly but appends 'went with' which has no source and misrepresents the fragment as a main clause.

**Latin source:**
```
duobus in Galæcia prædicandi causa remanentibus, cum
```

**Prior English:**
```
two remained in Galicia for the sake of preaching, went with
```

**Proposed English:** _(model: claude-opus-4-7)_
```
two remained in Galicia for the sake of preaching, while
```

**Fixer:** Replaced spurious 'went with' with 'while' to render the ablative absolute as a subordinate clause, leaving the 'cum' to introduce the following main clause without inventing content.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0016` &nbsp;·&nbsp; page p0038
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** 'we read' is added without Latin basis; 'Baronius' from footnote ^m is imported as main-clause subject; 'once published under the name of' substantially expands the bare genitive 'Hieronymi'; register is appropriate scholarly English.

**Latin source:**
```
Et ita sane in martyrologio Romano (quod Hieronymi^m
```

**Prior English:**
```
And so indeed we read in the Roman martyrology (which Baronius^m confirms was once published under the name of Jerome,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
And so indeed in the Roman martyrology (which^m of Jerome,
```

**Fixer:** Removed the unfounded 'we read' addition, dropped the imported 'Baronius' from footnote ^m, and rendered the bare genitive 'Hieronymi' simply as 'of Jerome' without expansion.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0017` &nbsp;·&nbsp; page p0038
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** Translation omits 'nomine olim editum' (formerly published under the name) and 'supposita' (spurious/supposititious), while adding 'the epistle' and 'Jerome' not present in this fragment; register of what is rendered ('epistle') is appropriately scholarly.

**Latin source:**
```
nomine olim editum, supposita^n quoque ejusdem ad Chro-
```

**Prior English:**
```
the epistle^n of the same Jerome to Chro-
```

**Proposed English:** _(model: claude-opus-4-7)_
```
formerly published under the name^n, with the spurious letter of the same to Chro-
```

**Fixer:** Restored 'nomine olim editum' (formerly published under the name) and 'supposita' (spurious), and removed the unsupported additions 'epistle' and 'Jerome' not present in this fragment.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0021` &nbsp;·&nbsp; page p0038
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The translation renders 'et ad prædicandum verbum Dei in His-' adequately but omits 'copos ordinatos' (ordained bishops), a substantive clause present in the Latin fragment; register is appropriate modern scholarly English.

**Latin source:**
```
copos ordinatos, et ad prædicandum verbum Dei in His-
```

**Prior English:**
```
and were sent to preach the word of God into the Spanish
```

**Proposed English:** _(model: claude-opus-4-7)_
```
ordained bishops, and were sent to preach the word of God into the Spanish
```

**Fixer:** Added the omitted 'copos ordinatos' as 'ordained bishops' at the start to restore the missing substantive clause.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0028` &nbsp;·&nbsp; page p0038
**Scores:** cf=2 · rf=5 · gp=na · ph=na

**Judge:** Two unsupported additions: 'son of' interprets the genitive patronymic rather than rendering it, and 'bishop' is wholly absent from the Latin — Menevensis is a locative adjective with no episcopal title; register is otherwise appropriate scholarly English.

**Latin source:**
```
scribendum curavit Ricemarchus Sulgeni Menevensis
```

**Prior English:**
```
Ricemarchus, son of Sulgenus bishop of Menevia, had transcribed,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Ricemarchus of Sulgenus of Menevia had taken care to write,
```

**Fixer:** Removed unsupported 'son of' and 'bishop'; rendered the genitive and locative adjective plainly and restored 'curavit scribendum' as 'had taken care to write'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0029` &nbsp;·&nbsp; page p0038
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** 'episcopi filius' (son of a bishop) is entirely dropped from the translation, a significant content omission; the addition of 'catalogue' is a reasonable inferential gloss but cannot compensate; register is otherwise appropriate scholarly English.

**Latin source:**
```
episcopi filius, ne nominantur quidem. In apostolorum
```

**Prior English:**
```
they are not even named. In the catalogue of the apostles,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
a bishop's son, are not even named. In the catalogue of the apostles,
```

**Fixer:** Restored the dropped phrase 'episcopi filius' as 'a bishop's son' to repair the content omission flagged by the judge.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0039_body_l0006` &nbsp;·&nbsp; page p0039
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The Latin fragment 'primum fidem et religionem' means 'first the faith and religion' (accusative objects), not 'first preached the faith and religion'; 'preached' is an addition not in this clause, shifting the syntax and inserting an unwarranted verb.

**Latin source:**
```
a rege Galliciæ susceptos, primum fidem et religionem
```

**Prior English:**
```
having been received by the king of Galicia, first preached the faith and religion
```

**Proposed English:** _(model: claude-opus-4-7)_
```
having been received by the king of Galicia, first the faith and religion
```

**Fixer:** Removed the unwarranted verb 'preached'; the Latin clause has only accusative objects ('fidem et religionem') without a finite verb here.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0039_body_l0019` &nbsp;·&nbsp; page p0039
**Scores:** cf=2 · rf=4 · gp=5 · ph=na

**Judge:** Greek preserved verbatim; content_fidelity penalised because the bracketed rendering adds 'enlightened many by the word of the gospel' and 'by the unbelievers'—content absent from the visible source fragment 'Postremo in Britanniam'; register is appropriate scholarly English throughout.

**Latin source:**
```
ρωθεὶς καὶ τεθεὶς θάπτεται ἐκεῖ. Postremo in Britanniam
```

**Prior English:**
```
ρωθεὶς καὶ τεθεὶς θάπτεται ἐκεῖ. [Afterward, having come to Britain and having enlightened many by the word of the gospel, he was crucified by the unbelievers, laid out, and buried there.]
```

**Proposed English:** _(model: claude-opus-4-7)_
```
ρωθεὶς καὶ τεθεὶς θάπτεται ἐκεῖ [having been crucified and laid out, he is buried there]. Finally into Britain
```

**Fixer:** Trimmed the bracketed gloss to render only the visible Greek fragment (removing the invented 'enlightened many by the word of the gospel' and 'by the unbelievers'), and supplied a translation for the previously untranslated Latin tail 'Postremo in Britanniam'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0040_body_l0023` &nbsp;·&nbsp; page p0040
**Scores:** cf=2 · rf=5 · gp=na · ph=na

**Judge:** 'nantius' (likely a participial fragment, e.g. part of 'pronuntians'/'enuntians') is silently dropped, while 'writes' is added with no Latin warrant; register is appropriate modern scholarly English.

**Latin source:**
```
nantius Fortunatus^a :
```

**Prior English:**
```
Fortunatus^a writes:
```

**Proposed English:** _(model: claude-opus-4-7)_
```
...Fortunatus^a,
```

**Fixer:** The Latin fragment 'nantius Fortunatus' is the tail of a name/participle split across lines (likely 'Venantius Fortunatus' or a participle ending in '-nantius'); since only the suffix and the proper name are present here, render just the name with the footnote sentinel and a trailing comma, dropping the unwarranted invented verb 'writes'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0040_body_l0027` &nbsp;·&nbsp; page p0040
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The translation invents 'indicates that Paul preached the gospel' — the Latin fragment only says 'concerning the birthday of the apostles, Paul [preached] to the Spanish and Britons'; 'Hispanis et Britannis' (dative) is dropped and an unattested predicate is added.

**Latin source:**
```
de natali apostolorum, Paulum Hispanis et Britannis
```

**Prior English:**
```
on the birthday of the apostles, indicates that Paul preached the gospel
```

**Proposed English:** _(model: claude-opus-4-7)_
```
on the birthday of the apostles, Paul to the Spaniards and Britons
```

**Fixer:** Removed the invented predicate 'indicates that Paul preached the gospel' and restored the dropped dative 'Hispanis et Britannis' as 'to the Spaniards and Britons', keeping the fragment's literal content.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0040_body_l0028` &nbsp;·&nbsp; page p0040
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The core verb phrase 'evangelium prædicasse significat' (signifies that [he] preached the gospel) is entirely absent from the translation, while 'to the Spaniards and the Britons' appears with no basis in this Latin fragment; only 'quod tamen ex aliorum^b' is reasonably rendered.

**Latin source:**
```
evangelium prædicasse significat: quod tamen ex aliorum^b
```

**Prior English:**
```
to the Spaniards and the Britons—which, however, on the testimony of others^b
```

**Proposed English:** _(model: claude-opus-4-7)_
```
signifies that he preached the gospel: which, however, on the testimony of others^b
```

**Fixer:** Restored the missing core verb phrase 'evangelium prædicasse significat' as 'signifies that he preached the gospel' and removed the unsupported 'to the Spaniards and the Britons' which had no basis in this Latin fragment.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0041_body_l0003` &nbsp;·&nbsp; page p0041
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The Latin says Pentecost [attests] that he went from Spain 'into the farthest parts' of the earth, but the translation inverts the direction ('ran from Spain') and introduces 'suggests' for an implied verb of testimony, significantly shifting the referential content.

**Latin source:**
```
Pentecoste, ab Hispaniis “ in ultimas partes” terræ eum
```

**Prior English:**
```
Pentecost suggests that he ran from Spain "into the farthest parts" of the earth.
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Pentecost [attests] that he went from Spain "into the farthest parts" of the earth.
```

**Fixer:** Reversed the inverted direction ("ran from Spain" → "went from Spain ... into the farthest parts") and replaced the unwarranted "suggests" with a bracketed [attests] reflecting the elided verb of testimony.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0041_body_l0010` &nbsp;·&nbsp; page p0041
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** 'meminit' (3rd-person singular: 'he mentions/records') is mistranslated as 1st-person 'I find,' shifting both person and verb sense; word order and other elements are otherwise acceptable and register is broadly scholarly.

**Latin source:**
```
meminit, Britannorum episcopum a Paulo ordinatum, in
```

**Prior English:**
```
as ordained bishop of the Britons by Paul, I find in
```

**Proposed English:** _(model: claude-opus-4-7)_
```
he mentions a bishop of the Britons ordained by Paul, in
```

**Fixer:** Corrected 'meminit' from 1st-person 'I find' to 3rd-person 'he mentions' to match the Latin verb's person and sense.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0041_body_l0020` &nbsp;·&nbsp; page p0041
**Scores:** cf=2 · rf=3 · gp=5 · ph=na

**Judge:** Greek preserved verbatim; however the Latin clause 'E septuaginta discipulis erat' is entirely dropped, and the bracketed gloss '[it, he was perfected]' is a garbled partial rendering rather than a proper translation of the Greek, lowering content fidelity significantly.

**Latin source:**
```
αὐτῇ καταστήσας, ἐτελειώθη. E septuaginta discipulis erat
```

**Prior English:**
```
αὐτῇ καταστήσας, ἐτελειώθη. [it, he was perfected.]
```

**Proposed English:** _(model: claude-opus-4-7)_
```
αὐτῇ καταστήσας, ἐτελειώθη [having appointed (a bishop) over it, he was perfected (i.e. martyred)]. He was of the seventy disciples
```

**Fixer:** Replaced the garbled bracket gloss with a proper English rendering of the Greek and restored the dropped Latin clause 'E septuaginta discipulis erat'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0042_body_l0034` &nbsp;·&nbsp; page p0042
**Scores:** cf=2 · rf=5 · gp=na · ph=na

**Judge:** The candidate inserts 'Pseudo-Clement intimates that' — an agent and reporting verb absent from the visible Latin fragment — while otherwise correctly rendering 'Linum, primum Ecclesiæ Romanæ episcopum a Paulo or[dinatum]'; register is appropriately scholarly throughout.

**Latin source:**
```
Linum, primum Ecclesiæ Romanæ episcopum a Paulo or-
```

**Prior English:**
```
Pseudo-Clement intimates that Linus, the first bishop of the Roman Church, ordained by Paul,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Linus, the first bishop of the Roman Church, ordained by Paul,
```

**Fixer:** Removed the inserted 'Pseudo-Clement intimates that' clause, which has no basis in the Latin fragment.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0042_body_l0035` &nbsp;·&nbsp; page p0042
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** Translation drops the attributing source ('Pseudo-Clemens suggests') and the verb 'innuit', rendering only the bare propositional content while omitting Ussher's scholarly hedging via citation.

**Latin source:**
```
dinatum, Claudiæ filium fuisse innuit Pseudo-Clemens^h.
```

**Prior English:**
```
was the son of Claudia.^h
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Pseudo-Clement suggests that [he] was the son of Claudia.^h
```

**Fixer:** Restored the attributing source 'Pseudo-Clement' and the hedging verb 'innuit' ('suggests') that the prior rendering had dropped.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0043_body_l0006` &nbsp;·&nbsp; page p0043
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** 'Romanam' (Roman) is rendered 'Italian,' a clear content substitution; 'is hers' is added with no Latin warrant; and the translation appears truncated, dropping the infinitive clause that completes the sense.

**Latin source:**
```
Quale decus formæ? Romanam credere matres
```

**Prior English:**
```
What grace of form is hers! The Italian mothers
```

**Proposed English:** _(model: claude-opus-4-7)_
```
What grace of form! The mothers would believe him Roman
```

**Fixer:** Restored 'Romanam' as 'Roman' (not 'Italian'), removed the unwarranted 'is hers,' and added the dropped infinitive clause ('credere' + 'Romanam') so the sense completes.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0043_body_l0007` &nbsp;·&nbsp; page p0043
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The Latin names 'Italides' (Italian women) and 'Atthides' (Attic women) are replaced by 'Roman' and 'women of Attica'; 'Italides' specifically means Italian, not Roman, shifting the referent, and the elliptical structure ('esse suam') is rendered with a supplanted 'believe' not present in this fragment.

**Latin source:**
```
Italides possunt, Atthides esse suam.
```

**Prior English:**
```
could believe her Roman, and the women of Attica that she is their own.
```

**Proposed English:** _(model: claude-opus-4-7)_
```
the Italian women could think her their own, and the Attic women theirs.
```

**Fixer:** Restored 'Italides' as 'Italian women' (not 'Roman') and made the elliptical 'esse suam' parallel for both groups without supplying 'believe'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0043_body_l0031` &nbsp;·&nbsp; page p0043
**Scores:** cf=2 · rf=5 · gp=na · ph=na

**Judge:** 'diæ illius priscæ' ('of that ancient goddess/divine one') is entirely dropped; the translation renders only 'Vestalis utique illius nominatissimæ,' omitting a full adjectival-genitive phrase Ussher wrote; register is correctly modern scholarly.

**Latin source:**
```
diæ illius priscæ, Vestalis utique illius nominatissimæ,
```

**Prior English:**
```
—that most celebrated Vestal Virgin, of course—
```

**Proposed English:** _(model: claude-opus-4-7)_
```
—of that ancient goddess, that most celebrated Vestal of course—
```

**Fixer:** Restored the dropped 'diæ illius priscæ' as 'of that ancient goddess', the adjectival-genitive phrase the judge identified as omitted.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0010` &nbsp;·&nbsp; page p0044
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The translation renders 'primam Scotici' as 'the first syllable of the name Scoti-' but the Latin fragment ends mid-phrase (likely 'primam Scotici nominis syllabam' or similar), so the expansion adds interpretive content not present in the supplied source fragment; 'veteres illos' is adequately rendered.

**Latin source:**
```
Apollinarem Sidonium ac veteres illos, primam Scotici
```

**Prior English:**
```
Apollinaris Sidonius, and those ancient writers, the first syllable of the name 'Scoti-'
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Apollinaris Sidonius, and those ancient writers, the first of the Scottish
```

**Fixer:** Removed the interpretive expansion 'syllable of the name Scoti-' since the Latin fragment ends mid-phrase at 'primam Scotici'; rendered literally without supplying content not in the source.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0011` &nbsp;·&nbsp; page p0044
**Scores:** cf=2 · rf=5 · gp=na · ph=na

**Judge:** No Greek present; register is appropriately scholarly; but 'nominis syllabam' (the syllable of the name) is silently dropped, leaving only the predicate 'semper productam legi' rendered, a meaningful content omission even in a fragmentary clause.

**Latin source:**
```
nominis syllabam semper productam legi; et in antiquis
```

**Prior English:**
```
is always read as long; and that in ancient
```

**Proposed English:** _(model: claude-opus-4-7)_
```
the syllable of the name is always read as long; and that in ancient
```

**Fixer:** Restored the dropped subject 'nominis syllabam' (the syllable of the name) so the clause's content is no longer truncated.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0016` &nbsp;·&nbsp; page p0044
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** The figura etymologica 'insaniret insaniam' (the core expression of madness) is entirely absent from the translation, and 'in Britain' is added without basis in the given Latin fragment; register is otherwise appropriate modern scholarly English.

**Latin source:**
```
insaniret insaniam, ut Claudiæ temporibus Angliam quæ-
```

**Prior English:**
```
so as to look for England in Britain in the times of Claudia:
```

**Proposed English:** _(model: claude-opus-4-7)_
```
would rave with such madness as to look for England in the times of Claudia—
```

**Fixer:** Rendered the figura etymologica 'insaniret insaniam' as 'rave with such madness' and removed the unsupported 'in Britain' addition.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0025` &nbsp;·&nbsp; page p0044
**Scores:** cf=2 · rf=4 · gp=na · ph=na

**Judge:** 'aliqua' means 'certain things/some matters' but the translation inserts 'poems composed,' an interpretive addition absent from the Latin fragment; register is appropriately scholarly otherwise.

**Latin source:**
```
occurrrunt aliqua sub^q tertio vel Nervæ vel Trajani consu-
```

**Prior English:**
```
there occur certain poems composed under^q the third consulship of either Nerva or Trajan,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
there occur some matters under^q the third consulship of either Nerva or Trajan,
```

**Fixer:** Removed the interpretive insertion 'poems composed' and rendered 'aliqua' literally as 'some matters' per the judge's content-fidelity flag.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0027` &nbsp;·&nbsp; page p0044
**Scores:** cf=2 · rf=5 · gp=na · ph=na

**Judge:** 'fuisse composita' (to have been composed) is dropped entirely from the first clause, and 'the poet met his' is added with no basis in the Latin fragment, where only 'mortem' (death) appears without an explicit subject or verb.

**Latin source:**
```
tempore fuisse composita. Et licet sub Trajano mortem
```

**Prior English:**
```
time. And although the poet met his death under Trajan,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
to have been composed at that time. And although he met his death under Trajan,
```

**Fixer:** Restored the dropped 'fuisse composita' as 'to have been composed' and removed the unwarranted added subject 'the poet,' leaving the implicit subject from prior context.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---


## cf = 3 — minor

### `seg_p0032_body_l0005` &nbsp;·&nbsp; page p0032
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The fragment is a mid-sentence carry-over ('tish isles' truncating 'British isles') that omits the main verb phrase 'evangelium primi prædicasse dicuntur' (are said to have first preached the gospel); register is appropriately scholarly.

**Latin source:**
```
tannicis insulis evangelium primi prædicasse dicuntur : Jacobo Zebedæi,
```

**Prior English:**
```
tish isles: James the son of Zebedee,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
tish isles: James the son of Zebedee are said to have first preached the gospel,
```

**Fixer:** Added the omitted main verb phrase 'are said to have first preached the gospel' to restore the content the judge flagged as missing.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0032_body_l0009` &nbsp;·&nbsp; page p0032
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The fragment renders the core nominal phrase accurately but adds 'our' (not in source) and drops the verb 'præcesserunt' (preceded/came before), losing the predicate entirely; register is appropriate scholarly English.

**Latin source:**
```
Christi adventum præcesserunt, Britannos et Hibernos
```

**Prior English:**
```
advent of Christ, that our Britons and Irish
```

**Proposed English:** _(model: claude-opus-4-7)_
```
preceded the advent of Christ, the Britons and Irish
```

**Fixer:** Restored the dropped verb 'præcesserunt' as 'preceded' and removed the unsourced 'our'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0033_body_l0012` &nbsp;·&nbsp; page p0033
**Scores:** cf=3 · rf=3 · gp=na · ph=na

**Judge:** 'manum genus' rendered as 'man race' (awkward; 'humanum genus'/'mankind' expected), 'obligabatur adstrictum' adequately as 'held fast in bondage' though slightly redundant, 'nec enumerans' correctly literal; register acceptable but 'man race' is unidiomatic.

**Latin source:**
```
manum genus obligabatur adstrictum; nec enumerans
```

**Prior English:**
```
man race was held fast in bondage; nor enumerating
```

**Proposed English:** _(model: claude-opus-4-7)_
```
mankind was held fast in bondage; nor enumerating
```

**Fixer:** Corrected 'man race' to 'mankind' (the standard rendering of 'humanum genus'), keeping the rest of the prior English intact.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0033_body_l0013` &nbsp;·&nbsp; page p0033
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'My' is added to patriæ (no possessive pronoun in the Latin) and 'exceeding' is inserted without warrant, shifting the neutral pene numero Egyptiaca ('almost Egyptian in number') into a claim of surpassing rather than near-equality; both are interpretive expansions absent from the source.

**Latin source:**
```
patriæ portenta ipsa diabolica, pene numero Egyptiaca
```

**Prior English:**
```
the very diabolical prodigies of my homeland, almost exceeding in number those of Egypt,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
the very diabolical prodigies of the homeland, almost Egyptian in number,
```

**Fixer:** Removed unwarranted 'my' (no possessive in Latin) and replaced 'exceeding in number those of Egypt' with the neutral 'almost Egyptian in number' to match pene numero Egyptiaca.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0033_body_l0015` &nbsp;·&nbsp; page p0033
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** Translation is incomplete — 'torvis' (fierce/grim looks) is cut off mid-phrase, leaving the ablative of manner unresolved; 'solito more' rendered as 'in their customary fashion' adds 'their' with no Latin warrant, but register is appropriately scholarly.

**Latin source:**
```
intra vel extra deserta mœnia, solito more rigentia torvis
```

**Prior English:**
```
within or outside the deserted walls, rigid in their customary fashion, with grim
```

**Proposed English:** _(model: claude-opus-4-7)_
```
within or outside the deserted walls, in customary fashion bristling with grim looks
```

**Fixer:** Completed the cut-off 'torvis' by rendering 'rigentia torvis' as 'bristling with grim looks' and removed the unwarranted 'their' from 'solito more'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0033_body_l0024` &nbsp;·&nbsp; page p0033
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** No Greek present. 'Multitudes of' is added for 'tantarum gentium' (which is simply 'of so many nations'), and 'oceani' as a genitive loses its syntactic relationship via the em-dash; register is otherwise appropriate modern scholarly English.

**Latin source:**
```
oceani tam innumerabiles populi, et tantarum gentium
```

**Prior English:**
```
ocean — so countless peoples, and the multitudes of so many nations,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
of the ocean, so countless peoples, and of so many nations,
```

**Fixer:** Restored 'oceani' as a genitive ('of the ocean') and removed the added 'multitudes of' so 'tantarum gentium' renders simply as 'of so many nations'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0034_body_l0002` &nbsp;·&nbsp; page p0034
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** Translation adds 'placed' (not in source) and renders only a sentence fragment ending abruptly; 'darkness and the shadow of death' is accurate but the interpolated verb and truncated clause reduce content fidelity.

**Latin source:**
```
ratum.” Indeque iis qui in tenebris et umbra mortis erant
```

**Prior English:**
```
known.” And hence to those who were placed in darkness and the shadow of death,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
established." And hence to those who were in darkness and the shadow of death,
```

**Fixer:** Removed interpolated 'placed' (not in source) so 'erant' renders as plain 'were'; also corrected the closing word of the prior quotation from 'known' to 'established' to better match 'ratum'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0034_fn_006` &nbsp;·&nbsp; page p0034
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** 'al. Sol.' is exactly rendered as 'another reading: Sol' but the translation appends '[Sun]'—an English gloss for the Latin word Sol—which is not present in Ussher's text; minor addition, core meaning intact.

**Latin source:**
```
al. Sol.
```

**Prior English:**
```
another reading: “Sol” [Sun].
```

**Proposed English:** _(model: claude-opus-4-7)_
```
another reading: "Sol."
```

**Fixer:** Removed the unwarranted English gloss '[Sun]' since Ussher's text contains only the Latin variant reading 'Sol' with no translation provided.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0034_body_l0008` &nbsp;·&nbsp; page p0034
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** No Greek present. Register is appropriately scholarly throughout. Content loses a point because 'to remain hidden from' is an interpretive expansion absent from the Latin fragment (nullum locum cœlesti doctrinæ supplies no verb implying concealment); the core sense is preserved but the addition is unwarranted.

**Latin source:**
```
prædicarunt ubique, ita ut nullum locum cœlesti doctrinæ
```

**Prior English:**
```
and preached everywhere, so that they allowed no place to remain hidden from the heavenly doctrine;
```

**Proposed English:** _(model: claude-opus-4-7)_
```
and preached everywhere, so that they left no place untouched by the heavenly doctrine;
```

**Fixer:** Replaced the interpretive 'allowed no place to remain hidden from' with 'left no place untouched by', which conveys the elliptical Latin sense without inserting a verb of concealment.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0034_body_l0009` &nbsp;·&nbsp; page p0034
**Scores:** cf=3 · rf=4 · gp=5 · ph=5

**Judge:** Greek preserved verbatim with accents; bracketed English gloss renders the paraphrase meaning correctly; content_fidelity docked because the Latin preamble 'occultum esse sinerent' is dropped entirely from the candidate; register is appropriately scholarly.

**Latin source:**
```
occultum esse sinerent; “μὴ νήσους, μὴ ἤπειρον, μηδ' εἴτινα
```

**Prior English:**
```
μὴ νήσους, μὴ ἤπειρον, μηδ' εἴτινα [neither islands, nor mainland, nor any]
```

**Proposed English:** _(model: claude-opus-4-7)_
```
would allow to remain hidden; μὴ νήσους, μὴ ἤπειρον, μηδ' εἴτινα [neither islands, nor mainland, nor any]
```

**Fixer:** Added the dropped Latin preamble 'occultum esse sinerent' as 'would allow to remain hidden' before the preserved Greek with its bracketed gloss.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0034_body_l0013` &nbsp;·&nbsp; page p0034
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'God had formerly foretold' adds theological elaboration absent from the terse Latin ('senex loquitur. Atque ita completum est quod per Esaiam'); 'says' drops 'senex loquitur' (the old man speaks) context, though register is appropriately scholarly.

**Latin source:**
```
senus loquitur. Atque ita completum est quod per Esaiam
```

**Prior English:**
```
says. And so was fulfilled what God had formerly foretold through Isaiah:
```

**Proposed English:** _(model: claude-opus-4-7)_
```
the old man says. And so was fulfilled what was foretold through Isaiah:
```

**Fixer:** Restored 'the old man says' for 'senex loquitur' and removed the added 'God had formerly' elaboration not present in the Latin.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0034_body_l0029` &nbsp;·&nbsp; page p0034
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'coruscum' (gleaming/shining) rendered adequately but 'summo' (highest/greatest) is translated as 'last period' — a significant semantic shift that loses Ussher's superlative sense; register is appropriately scholarly.

**Latin source:**
```
dum sui coruscum ostendens tempore, ut scimus, summo
```

**Prior English:**
```
gleam of himself—at the time, as we know, in the last period
```

**Proposed English:** _(model: claude-opus-4-7)_
```
gleam of himself—at the time, as we know, of greatest moment
```

**Fixer:** Replaced 'last period' with 'of greatest moment' to capture the superlative force of 'summo' rather than a temporal-final sense.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0002` &nbsp;·&nbsp; page p0035
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The fragment is rendered accurately but ends mid-sentence with a dangling 'they', suggesting an incomplete segment; 'less so' is a reasonable rendering of 'minus' and register is appropriately scholarly.

**Latin source:**
```
et alios minus, usque ad persecutionem Diocletiani per-
```

**Prior English:**
```
and among others less so, until the persecution of Diocletian they
```

**Proposed English:** _(model: claude-opus-4-7)_
```
and others less so, up to the persecution of Diocletian
```

**Fixer:** Removed the dangling 'they' (a partial word 'per-' hyphenated to the next line) so the fragment ends cleanly without an incomplete subject.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0005` &nbsp;·&nbsp; page p0035
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'Against' mistranslates temporal 'ad' (should be 'to/in the year'); 'it is recorded' is an addition inferred from the truncated 'anno-' without textual warrant; 'next-to-last' for 'penultimum' is a mild register lapse (scholarly prose prefers 'penultimate').

**Latin source:**
```
quo ad annum vel ultimum, vel penultimum Tiberii anno-
```

**Prior English:**
```
which, against the last or next-to-last year of Tiberius, it is recorded,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
to the last or penultimate year of Tiberius,
```

**Fixer:** Corrected 'against' to temporal 'to', replaced 'next-to-last' with the scholarly 'penultimate', and removed the unwarranted 'it is recorded' addition inferred from the truncated 'anno-'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0008` &nbsp;·&nbsp; page p0035
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'patrum' means 'fathers/fathers of the church' not 'senators'; 'tera sacra' likely 'sacred land/territory' not 'sacred rites'; otherwise register is appropriately scholarly.

**Latin source:**
```
tera sacra reciperetur. Verum quum ex consulto patrum,
```

**Prior English:**
```
sacred rites. But when, by decree of the senators, it had
```

**Proposed English:** _(model: claude-opus-4-7)_
```
sacred territory might be received. But when, by decree of the fathers, it had
```

**Fixer:** Corrected 'patrum' from 'senators' to 'fathers' and 'tera sacra' from 'sacred rites' to 'sacred territory' per the judge's flag.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0013` &nbsp;·&nbsp; page p0035
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** No Greek or paraphrase issues; content_fidelity docked to 3 because 'news' is added (Latin has only 'annunciatum sibi' = '[it] having been announced to him') and 'when' imposes a temporal reading on a bare participial phrase; register is appropriate scholarly English throughout.

**Latin source:**
```
nomen Christianum in sæculum introivit, annunciatum sibi
```

**Prior English:**
```
the Christian name entered the world, when news had been reported to him
```

**Proposed English:** _(model: claude-opus-4-7)_
```
the Christian name entered the world, having been announced to him
```

**Fixer:** Replaced the added 'when news had been reported to him' with a literal participial 'having been announced to him' to match the bare Latin participle without imposing a temporal clause or adding 'news'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0020` &nbsp;·&nbsp; page p0035
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** Visible Latin words (quod→this, profecto→indeed, divina providentia, ita→so, tunc→then, Cæsaris→Caesar's) are accurately rendered, but 'instilled' is a verb with no antecedent in the visible truncated fragment; register is appropriately scholarly.

**Latin source:**
```
"Quod profecto divina providentia ita tunc Cæsaris sen-
```

**Prior English:**
```
"This indeed divine providence then so instilled into Caesar's
```

**Proposed English:** _(model: claude-opus-4-7)_
```
This indeed divine providence then so disposed Caesar's
```

**Fixer:** Replaced 'instilled into' with 'disposed' since the Latin fragment ends mid-clause at 'sen-' (likely 'sensum' or 'sententiam'); 'disposed' works idiomatically with the truncated object without inventing a preposition or antecedent not present in the source.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0021` &nbsp;·&nbsp; page p0035
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The fragment is a mid-sentence clause and the translation renders the core prepositional logic faithfully, but 'sibus ingessit' (thrust/forced upon minds) is only partially captured by 'mind' with no verb, suggesting truncation rather than a complete rendering.

**Latin source:**
```
sibus ingessit, ut absque ullo obstaculo, in ipsis duntaxat
```

**Prior English:**
```
mind, that, without any obstacle, in the very
```

**Proposed English:** _(model: claude-opus-4-7)_
```
thrust upon their minds, that, without any obstacle, in the very
```

**Fixer:** Added 'thrust upon their' to render 'ingessit' governing 'sibus' (-mentibus), which the prior version omitted as a bare 'mind'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0022` &nbsp;·&nbsp; page p0035
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'initiis' (ablatives of beginning/origin) is rendered loosely as 'first beginnings' (redundant), and the clause lacks its governing preposition 'ab' context, but core vocabulary is preserved in appropriate scholarly register.

**Latin source:**
```
initiis Evangelii sermo usquequaque percurreret. Unde et
```

**Prior English:**
```
first beginnings the word of the Gospel ran everywhere. Whence also
```

**Proposed English:** _(model: claude-opus-4-7)_
```
from its beginnings the word of the Gospel ran everywhere. Hence also
```

**Fixer:** Replaced redundant 'first beginnings' with idiomatic 'from its beginnings' to render the ablative properly, and 'Unde' as 'Hence' for modern scholarly register.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0024` &nbsp;·&nbsp; page p0035
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The translation renders the Latin faithfully but adds 'it lit up' for a finite verb not present in the truncated source (which ends mid-clause with 'claritate su-'), making a content inference; register is appropriately scholarly.

**Latin source:**
```
radius quidam solis erumpens, totum orbem claritate su-
```

**Prior English:**
```
a certain ray of the sun bursting forth, it lit up the whole world with the brightness
```

**Proposed English:** _(model: claude-opus-4-7)_
```
a certain ray of the sun bursting forth, with the brightness of
```

**Fixer:** Removed the inferred finite verb 'it lit up the whole world' since the Latin is truncated mid-clause at 'claritate su-'; rendered only what the fragment actually contains.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0025` &nbsp;·&nbsp; page p0035
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'perni luminis' (of the eternal/everlasting light) is rendered 'from on high' (a directional gloss not in the Latin); 'illustraret' (might illuminate) is lost; 'compleretur' (might be fulfilled) correctly rendered; register is appropriately scholarly.

**Latin source:**
```
perni luminis illustraret: ut compleretur illa prophetia
```

**Prior English:**
```
of the light from on high: so that that prophecy was fulfilled
```

**Proposed English:** _(model: claude-opus-4-7)_
```
might illuminate them with the light of eternity: so that that prophecy was fulfilled
```

**Fixer:** Restored 'illustraret' as 'might illuminate' and corrected 'perni luminis' to 'light of eternity' (aeterni luminis) rather than the directional gloss 'from on high'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0031` &nbsp;·&nbsp; page p0035
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The fragment renders 'congregatio Christianorum in omne hominum genus penetravit' adequately but omits 'congregatio' (assembly/congregation) entirely, reducing content fidelity; register is appropriately scholarly.

**Latin source:**
```
gregatio^w Christianorum in omne hominum penetravit ge-
```

**Prior English:**
```
of the Christians penetrated into every kind of men;^w
```

**Proposed English:** _(model: claude-opus-4-7)_
```
the congregation of the Christians penetrated into every kind of men;^w
```

**Fixer:** Restored the omitted 'congregatio' as 'congregation' to fix the content-fidelity gap the judge flagged.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0035_body_l0032` &nbsp;·&nbsp; page p0035
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The fragment is rendered accurately but the trailing 'that was left without' is incomplete and adds a relative clause not present in the source, which cuts off mid-thought; register is appropriate scholarly English.

**Latin source:**
```
nus; nec ulla natio Romani orbis remansit, quæ cultus
```

**Prior English:**
```
and no nation of the Roman world remained that was left without
```

**Proposed English:** _(model: claude-opus-4-7)_
```
and no nation of the Roman world remained which the worship
```

**Fixer:** Removed the invented 'that was left without' (not in the source) and rendered the trailing 'quæ cultus' literally as a cut-off relative clause, since the unit ends mid-thought.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0007` &nbsp;·&nbsp; page p0036
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'rem' rendered as 'campaign' is a plausible but unsupported contextual guess; without the full sentence 'rem' could mean 'matter/affair/thing', so a minor content liberty is present, though register is appropriately scholarly.

**Latin source:**
```
lii per universum terrarum orbem spargi cœptum est, et rem
```

**Prior English:**
```
began to be scattered throughout the whole world, and the campaign
```

**Proposed English:** _(model: claude-opus-4-7)_
```
began to be scattered throughout the whole world, and the matter
```

**Fixer:** Replaced the unsupported contextual guess 'campaign' with the neutral, semantically faithful 'matter' for 'rem'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0010` &nbsp;·&nbsp; page p0036
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** 'gestam' (accusative feminine participle, referring back to a feminine noun in the prior clause — the deed/event 'accomplished among' the Britons) is silently dropped, a meaningful omission; the remainder ('of which he had just spoken; that is') is accurate and the register is appropriate modern scholarly English.

**Latin source:**
```
Britannos gestam, de qua proxime verba fecerat; hoc est,
```

**Prior English:**
```
the Britons, of which he had just spoken; that is,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
accomplished among the Britons, of which he had just spoken; that is,
```

**Fixer:** Restored the dropped participle 'gestam' as 'accomplished among the Britons' to reflect the feminine accusative referring back to the deed/event in the prior clause.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0014` &nbsp;·&nbsp; page p0036
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'His truth' is an addition not present in the Latin (radios alone, no veritatis); 'significat' (signifies/indicates) and the subject are dropped, losing Ussher's framing clause; register is otherwise appropriate.

**Latin source:**
```
radios Britanniæ primum indulsisse Christum significat.
```

**Prior English:**
```
first granted the rays of his truth to Britain.
```

**Proposed English:** _(model: claude-opus-4-7)_
```
signifies that Christ first granted the rays [of his light] to Britain.
```

**Fixer:** Restored the dropped framing verb 'significat' and its subject 'Christum', and removed the unsupported addition 'of his truth' (Latin has 'radios' alone).

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0030` &nbsp;·&nbsp; page p0036
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'ɴᴏs' (we/us) is dropped entirely, losing Ussher's first-person framing; 'utque semel dicatur' is rendered accurately; register is appropriately scholarly.

**Latin source:**
```
ɴᴏs, Cimmerios et Germanos, utque semel dicatur, omne
```

**Prior English:**
```
Cimmerians, and Germans — and, to say it once, every
```

**Proposed English:** _(model: claude-opus-4-7)_
```
we — Cimmerians, and Germans, and, to say it once, every
```

**Fixer:** Restored the dropped first-person 'we' (ɴᴏs) to preserve Ussher's framing of the speaker as included among these peoples.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0033` &nbsp;·&nbsp; page p0036
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** Greek/paraphrase not applicable; content is partially rendered but 'non eadem est' (the predicate is not the same) is loosely rendered as 'is not on the same point,' adding 'point' without Latin warrant; register is appropriately scholarly.

**Latin source:**
```
ad Britannicas nostras insulas accesserit; non eadem est
```

**Prior English:**
```
came to our British isles is not on the same point
```

**Proposed English:** _(model: claude-opus-4-7)_
```
came to our British isles is not the same
```

**Fixer:** Removed the unwarranted 'on the same point'; rendered 'non eadem est' literally as 'is not the same' to match the Latin predicate without adding content.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0036_body_l0036` &nbsp;·&nbsp; page p0036
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'some report' is added with no Latin warrant (the source is a fragmentary clause with no such attribution); register is appropriate scholarly English, but the unwarranted addition drops content_fidelity to 3.

**Latin source:**
```
isse in occidentem, multaque iis locis fecisse miracula; ex
```

**Prior English:**
```
went into the West and performed many miracles in those places, some report
```

**Proposed English:** _(model: claude-opus-4-7)_
```
went into the West and performed many miracles in those places; from
```

**Fixer:** Removed the unwarranted 'some report' addition and rendered the trailing 'ex' as a semicolon + 'from' to reflect the fragmentary clause without inventing content.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0037_body_l0001` &nbsp;·&nbsp; page p0037
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'tyrum' rendered as 'martyrs' is a partial fragment guess rather than the full word; 'Arabice scripto' correctly rendered; 'quidam referunt' correctly rendered; 'Eundem' correctly rendered; '[Spain]' for 'His-' is a reasonable bracketed editorial completion of a truncated word but speculative.

**Latin source:**
```
tyrum, Arabice scripto, quidam^z referunt. Eundem “His-
```

**Prior English:**
```
martyrs, written in Arabic, as some^z report. That the same man "to [Spain]"
```

**Proposed English:** _(model: claude-opus-4-7)_
```
[mar]tyrs, written in Arabic, as some^z report. That the same man "to [Spain]"
```

**Fixer:** Marked 'tyrum' as a line-initial fragment of '[mar]tyrs' to flag the truncation rather than silently completing it as a full word.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0037_body_l0003` &nbsp;·&nbsp; page p0037
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'dicavisse' (dedicated/devoted) is rendered as 'poured' which shifts the register and meaning; 'in occasum mundi' (to the setting/west of the world) is compressed to 'the west' losing Ussher's cosmic phrasing, but 'light of preaching' is accurate.

**Latin source:**
```
dicavisse, et in occasum mundi lucem prædicationis in-
```

**Prior English:**
```
and poured the light of preaching into the west,"
```

**Proposed English:** _(model: claude-opus-4-7)_
```
and dedicated the light of preaching to the setting of the world,"
```

**Fixer:** Restored 'dicavisse' as 'dedicated' (not 'poured') and rendered 'in occasum mundi' as 'to the setting of the world' to preserve Ussher's cosmic phrasing.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0037_body_l0013` &nbsp;·&nbsp; page p0037
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** 'oppida' (towns/cities) is rendered as '[Vannes]' — a specific toponym substituted for the general Latin noun — losing fidelity, though register is appropriately scholarly.

**Latin source:**
```
oppida, ubi prædicat; ac Hierosolymam revertitur, de
```

**Prior English:**
```
[Vannes], where he preaches; and he returns to Jerusalem,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
towns, where he preaches; and he returns to Jerusalem,
```

**Fixer:** Replaced the unwarranted toponym '[Vannes]' with the literal 'towns' to restore content fidelity to 'oppida'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0037_body_l0019` &nbsp;·&nbsp; page p0037
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** The translation adds 'of Ireland' and 'he is said to have chosen' which are not in this fragment; 'oris appulsus' (arrival at shore) is rendered as context from outside this snippet, and 'ubi sep-' is left as an incomplete clause—moderate content fidelity penalty for additions not present in the fragment.

**Latin source:**
```
oris appulsus, verbum Dei prædicavit intrepidus, ubi sep-
```

**Prior English:**
```
of Ireland, fearlessly preached the word of God, where he is said to have chosen sev-
```

**Proposed English:** _(model: claude-opus-4-7)_
```
having landed on the shore, fearlessly preached the word of God, where sep-
```

**Fixer:** Removed added 'of Ireland' and 'he is said to have chosen' not present in the fragment; rendered 'oris appulsus' as 'having landed on the shore' and left 'ubi sep-' as the incomplete clause it is in the source.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0037_body_l0020` &nbsp;·&nbsp; page p0037
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The translation omits 'item' (likewise/also) and 'elegisse fertur' (is said to have chosen), rendering only the object list; core names preserved but the main verb clause is dropped, reducing content fidelity.

**Latin source:**
```
tem discipulos elegisse fertur: scilicet Torquatum, Secun-
```

**Prior English:**
```
en disciples: namely Torquatus, Secun-
```

**Proposed English:** _(model: claude-opus-4-7)_
```
is likewise said to have chosen disciples: namely Torquatus, Secun-
```

**Fixer:** Restored the dropped 'item' (likewise) and main verb 'elegisse fertur' (is said to have chosen) that the judge flagged as missing.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0037_body_l0021` &nbsp;·&nbsp; page p0037
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** Names are rendered in anglicised/Latinised forms (Indaletius, Tisefon, Euphrasius) that differ from Ussher's Indalecium, Tisephontem, Eufrasium; partial fragment 'dus' vs. 'dum' suggests a truncated rendering of a larger clause.

**Latin source:**
```
dum, Indalecium, Tisephontem, Eufrasium, Cecilium,
```

**Prior English:**
```
dus, Indaletius, Tisefon, Euphrasius, Cecilius,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
dum, Indalecium, Tisephontem, Eufrasium, Cecilium,
```

**Fixer:** Restored the source-form names (Indalecium, Tisephontem, Eufrasium) and the truncated fragment 'dum' to match Ussher's text, since these are obscure names per Rule 3a and the unit is a mid-clause fragment.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0037_body_l0028` &nbsp;·&nbsp; page p0037
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The translation captures the core structure (Turpin, others demonstrate) but adds 'indeed' and 'very' not in the Latin, and 'loquitur Vincentius' (Vincent speaks) is dropped entirely, representing a notable omission.

**Latin source:**
```
Turpino^f loquitur Vincentius) ostendunt alii^g: et quos
```

**Prior English:**
```
Turpin) others demonstrate^f—and indeed^g the very
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Vincent says Turpin^f speaks) others demonstrate^g: and whom
```

**Fixer:** Restored the dropped 'loquitur Vincentius' (Vincent says Turpin speaks), removed added 'indeed' and 'very', and translated 'et quos' as 'and whom' to match the Latin.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_fn_003` &nbsp;·&nbsp; page p0038
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** No Greek present; register is appropriate; but 'al.' (alias/aliter) means 'otherwise [called/known as],' not 'elsewhere spelled' — the translation shifts from an alternative name/identity to an orthographic scribal variant, a moderate content displacement.

**Latin source:**
```
al. Hesychius.
```

**Prior English:**
```
Elsewhere spelled Hesychius.
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Otherwise called Hesychius.
```

**Fixer:** Changed 'Elsewhere spelled' to 'Otherwise called' so 'al.' (aliter) signals an alternative name rather than an orthographic variant.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0005` &nbsp;·&nbsp; page p0038
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** No Greek present; 'Hierosolymis perrexerunt' (they proceeded to Jerusalem) loses its main verb — 'carried' likely belongs to the cut-off continuation, leaving the first clause's movement unrendered; register is appropriately scholarly with 'passion' preserved.

**Latin source:**
```
eo Hierosolymis perrexerunt, ejusque corpus post passi-
```

**Prior English:**
```
him to Jerusalem, and after his passion carried his body
```

**Proposed English:** _(model: claude-opus-4-7)_
```
they proceeded with him to Jerusalem, and after his passion his body
```

**Fixer:** Restored the missing main verb of 'Hierosolymis perrexerunt' ('they proceeded to Jerusalem') and left the trailing 'corpus post passi-' as the subject of the cut-off continuation, since 'carried' belongs to the next unit.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0007` &nbsp;·&nbsp; page p0038
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** No Greek present; 'spoke thus in his martyrology' renders 'sic dixit' and 'in suo martyrologio' accurately, but 'wrote to blessed' adds a verb ('wrote to') absent from 'ac beato', inflating the fragment beyond what Ussher wrote; register is appropriately scholarly though 'spoke thus' is slightly informal.

**Latin source:**
```
beatus Hieronymus in suo martyrologio sic dixit, ac beato
```

**Prior English:**
```
blessed Jerome spoke thus in his martyrology, and wrote to blessed
```

**Proposed English:** _(model: claude-opus-4-7)_
```
blessed Jerome spoke thus in his martyrology, and to blessed
```

**Fixer:** Removed the unwarranted verb 'wrote' so 'ac beato' renders as the bare conjunction + dative 'and to blessed', matching the fragment without inflation.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0009` &nbsp;·&nbsp; page p0038
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** 'corpore' (ablative, likely 'in the body/corporally') is dropped, and 'infulis episcopalibus' rendered as 'episcopal insignia' is acceptable though slightly loose; 'they were ordained at Rome' adds 'ordained' and 'at Rome' which are not in this fragment.

**Latin source:**
```
corpore, ab apostolis Petro et Paulo infulis episcopalibus
```

**Prior English:**
```
they were ordained at Rome by the apostles Peter and Paul with episcopal insignia,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
in person, by the apostles Peter and Paul with episcopal insignia,
```

**Fixer:** Restored 'corpore' as 'in person' and removed the unsupported additions 'they were ordained at Rome' to match the fragment.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0022` &nbsp;·&nbsp; page p0038
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'panias' (likely 'Hispanias' or similar) is rendered as 'provinces' rather than a specific place name, and 'evangelizandi' is paraphrased as 'had evangelized in'; core meaning preserved but referent shifted.

**Latin source:**
```
panias directos esse: cumque diversis urbibus evangeli-
```

**Prior English:**
```
provinces: and when they had evangelized in various cities,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
had been sent to the Spains: and when they were evangelizing in various cities,
```

**Fixer:** Restored '[His]panias' as 'the Spains' (the referent the source names) and rendered 'evangelizandi' as the active gerundive 'were evangelizing' rather than the paraphrastic 'had evangelized in'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0025` &nbsp;·&nbsp; page p0038
**Scores:** cf=3 · rf=5 · gp=na · ph=na  &nbsp;·&nbsp; **NO CHANGE proposed** (fixer disagreed with judge)

**Judge:** 'tere' (likely 'marte' or similar ablative) and the subject noun are missing from the fragment, but the visible content — Roman Church martyrology and 'prefixed' — is accurately rendered in appropriate scholarly register.

**Latin source:**
```
tere Romanæ Ecclesiæ martyrologio, quod suo præfixit
```

**Prior English:**
```
martyrology of the Roman Church, which Ado prefixed to his own,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
martyrology of the Roman Church, which Ado prefixed to his own,
```

**Fixer:** The Latin fragment is truncated ('tere' is a mid-word fragment) and lacks a visible subject; the prior English faithfully renders the visible content (Roman Church martyrology, 'prefixed'), so no minimal correction is possible without inventing material.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0038_body_l0030` &nbsp;·&nbsp; page p0038
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** 'catalogo' (dative 'to the catalogue/list') is rendered as 'which is appended to,' adding the relative clause framing not present in the Latin fragment; register is appropriately scholarly.

**Latin source:**
```
tamen catalogo, qui epistolæ ad Chromatium et Heliodo-
```

**Prior English:**
```
however, which is appended to the epistle to Chromatius and Heliodo-
```

**Proposed English:** _(model: claude-opus-4-7)_
```
however, in the catalogue, which to the epistle to Chromatius and Heliodo-
```

**Fixer:** Replaced the added relative-clause framing ('which is appended to') with a direct rendering of the dative 'catalogo' as 'in the catalogue,' preserving the fragment's syntax.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0039_body_l0002` &nbsp;·&nbsp; page p0039
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'prædicavit' (preached) is omitted entirely, dropping a key verb; otherwise register is appropriate modern scholarly English with no archaisms.

**Latin source:**
```
in occidentalia loca prædicavit: et sub Herode gladio
```

**Prior English:**
```
in the western regions: and under Herod by the sword
```

**Proposed English:** _(model: claude-opus-4-7)_
```
he preached in the western regions: and under Herod by the sword
```

**Fixer:** Restored the omitted verb 'prædicavit' as 'he preached' to capture the key action the judge flagged as missing.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0039_body_l0008` &nbsp;·&nbsp; page p0039
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** Translation adds parenthetical gloss '(the Irish)' and introduces 'instead of Hiberis' — explanatory context absent from the Latin source — though register is appropriately scholarly.

**Latin source:**
```
Hibernis exaratum repererit, aliis conjiciendum relinquo :
```

**Prior English:**
```
found 'Hibernis' (the Irish) written instead of 'Hiberis,' I leave for others to conjecture:
```

**Proposed English:** _(model: claude-opus-4-7)_
```
found written 'Hibernis,' I leave for others to conjecture:
```

**Fixer:** Removed the added parenthetical gloss '(the Irish)' and the inserted contrast 'instead of Hiberis' that were absent from the Latin source.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0039_body_l0012` &nbsp;·&nbsp; page p0039
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'dentalem oceanum' is rendered simply as 'ocean,' dropping the adjective 'dentalem' (likely 'Occidentalem' or similar); 'Britannicasque insulas' is correctly rendered; minor omission lowers content fidelity.

**Latin source:**
```
dentalem oceanum, Britannicasque insulas” pertulisse,
```

**Prior English:**
```
ocean and the British isles"
```

**Proposed English:** _(model: claude-opus-4-7)_
```
western ocean and the British isles"
```

**Fixer:** Restored the dropped adjective; 'dentalem' is a truncation of 'Occidentalem' (western), so the phrase is rendered 'western ocean'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0039_body_l0021` &nbsp;·&nbsp; page p0039
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** Translation renders only 'In martyrologio' as 'In the Roman martyrology, however,' — adding 'Roman' and 'however' not present in this fragment, while dropping 'fidelibus crucifixus, illic sepultus est.'

**Latin source:**
```
fidelibus crucifixus, illic sepultus est.” In martyrologio
```

**Prior English:**
```
In the Roman martyrology, however,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
was crucified by the faithful, [and] was buried there." In the martyrology
```

**Fixer:** Restored the dropped clause 'fidelibus crucifixus, illic sepultus est' and removed the unwarranted insertions 'Roman' and 'however' that were not in this fragment.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0039_body_l0022` &nbsp;·&nbsp; page p0039
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** The translation adds 'the martyrologies of' for 'martyrologiis' which is implied by context but not present in this fragment; 'tamen' (yet/however) is also dropped, and the fragment begins mid-construction, making exact fidelity assessment partial.

**Latin source:**
```
tamen et breviario Romano, ut et in Bedæ, Usuardi,
```

**Prior English:**
```
and in the Roman breviary, as also in the martyrologies of Bede, Usuard,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
yet also in the Roman breviary, as well as in those of Bede, Usuard,
```

**Fixer:** Restored dropped 'tamen' as 'yet' and removed the unsupported insertion 'martyrologies of' since the fragment only has the pronoun-like continuation; kept it as 'those of' to mirror the elided noun from prior context.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0039_body_l0024` &nbsp;·&nbsp; page p0039
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** The ordinal 'vigesimum' (twentieth/twentieth time) is dropped — the Latin specifies he suffered martyrdom for the twentieth time (or in the twentieth [year/instance]), a detail absent from the translation; register is appropriately scholarly.

**Latin source:**
```
et vigesimum in Perside martyrium subiisse legitur.
```

**Prior English:**
```
it is read that he underwent martyrdom in Persia.
```

**Proposed English:** _(model: claude-opus-4-7)_
```
and in the twentieth [year] he is read to have undergone martyrdom in Persia.
```

**Fixer:** Restored the ordinal 'vigesimum' (twentieth), supplying the implied noun [year] in brackets since the substantive being counted is elided in the Latin.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0039_body_l0025` &nbsp;·&nbsp; page p0039
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** The fragment captures 'Simon Peter' and 'twelve years' but adds 'spent' where the Latin has no verb yet (duodecim quidem annos esse is an accusative-infinitive fragment); the implicit verb may be warranted but slightly presupposes the completion.

**Latin source:**
```
Simonem Petrum, “ duodecim quidem annos esse
```

**Prior English:**
```
That Simon Peter "spent twelve years
```

**Proposed English:** _(model: claude-opus-4-7)_
```
That Simon Peter "for twelve years
```

**Fixer:** Removed the presupposed verb 'spent'; the Latin fragment 'duodecim quidem annos esse' is an accusative-infinitive without a completed verb, so a verbless temporal phrase preserves the fragmentary syntax.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0039_body_l0031` &nbsp;·&nbsp; page p0039
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** The translation renders 'multas gentes non nominatas attraxisse ad fidem' accurately, but omits 'ratum' (ratified/confirmed), which is a dropped clause affecting completeness; register is appropriately scholarly.

**Latin source:**
```
ratum, et multas gentes non nominatas attraxisse ad fidem
```

**Prior English:**
```
and drew many unnamed peoples to the faith
```

**Proposed English:** _(model: claude-opus-4-7)_
```
ratified it, and drew many unnamed peoples to the faith
```

**Fixer:** Added 'ratified it' to render the omitted 'ratum' clause flagged by the judge.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0040_body_l0016` &nbsp;·&nbsp; page p0040
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** 'adstitit' (stood by/appeared beside) is dropped entirely; 'confortavit' rendered correctly; 'ut per me prædicatio impleatur' translated accurately — but the missing main verb 'stood by' is a significant omission reducing content fidelity.

**Latin source:**
```
adstitit, et confortavit; ut per me prædicatio impleatur,
```

**Prior English:**
```
by me and strengthened me, so that through me the preaching might be fulfilled,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
stood by me and strengthened me, so that through me the preaching might be fulfilled,
```

**Fixer:** Added the missing main verb 'stood by' to render 'adstitit', which was dropped in the prior English.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0040_body_l0019` &nbsp;·&nbsp; page p0040
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** No Greek present; register is cleanly modern-scholarly; but 'missus est' (he was sent/dispatched) is dropped entirely, and 'set out for' adds volitional departure not in the Latin fragment, which only supplies 'in Hispa[niam]'.

**Latin source:**
```
missus est, defensione audita fuit absolutus, et in Hispa-
```

**Prior English:**
```
and his defense having been heard, he was acquitted, and set out for Spain,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
and was sent, and having been heard in his defense was acquitted, and into Spain
```

**Fixer:** Restored the dropped 'missus est' as 'was sent' and replaced 'set out for Spain' with 'into Spain' to remove the unwarranted volitional verb, matching the truncated Latin fragment.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0040_body_l0020` &nbsp;·&nbsp; page p0040
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The fragment renders the motion and outreach accurately but adds 'the light of' which has no basis in the Latin source (doctrinas/doctrine expected); register is appropriately scholarly.

**Latin source:**
```
niam profectus est, et ad alias gentes excurrens, eis doc-
```

**Prior English:**
```
and, hastening on to other peoples, brought to them the light of
```

**Proposed English:** _(model: claude-opus-4-7)_
```
and, hastening on to other peoples, brought to them the doc-
```

**Fixer:** Removed the unsupported 'light of' gloss; kept the truncated 'doc-' to mirror the source fragment ending in 'doc-' (continuation of doctrinas/doctrine on the next line).

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0040_body_l0021` &nbsp;·&nbsp; page p0040
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** 'trinæ lucem attulit' ('brought light to the triple [islands]') is rendered as 'To the islands' — dropping the key verb and the 'threefold/triple' qualifier — but 'doctrine' for the preceding implied content and the structural connective are handled well; register is appropriate.

**Latin source:**
```
trinæ lucem attulit;” atque, ut alibi addit idem^z, “ Insulis
```

**Prior English:**
```
doctrine;” and, as the same author adds elsewhere^z, “To the islands
```

**Proposed English:** _(model: claude-opus-4-7)_
```
brought light to the threefold [islands];” and, as the same author adds elsewhere^z, “To the islands
```

**Fixer:** Restored the missing clause 'trinæ lucem attulit' as 'brought light to the threefold [islands]' so the verb and the 'threefold' qualifier are no longer dropped.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0041_body_l0006` &nbsp;·&nbsp; page p0041
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** No Greek present. 'Accomplished' is an interpretive addition absent from the Latin ablative phrase; otherwise core content (thirty-five years, gospel contest, for Christ) is faithfully rendered. Register is appropriately scholarly.

**Latin source:**
```
ginta^e et quinque annis evangelico pro Christo certamine
```

**Prior English:**
```
with the gospel contest for Christ accomplished over thirty-five^e years,"
```

**Proposed English:** _(model: claude-opus-4-7)_
```
with the gospel contest for Christ over thirty-five^e years,
```

**Fixer:** Removed interpretive 'accomplished' which was not in the Latin ablative phrase; kept the rest intact.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0042_body_l0003` &nbsp;·&nbsp; page p0042
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'Yet' introduces a mild adversative not in 'multis persuasit'; 'And so, when' renders 'Unde et' acceptably but the fragment cuts off, making full fidelity assessment difficult; register is appropriately scholarly.

**Latin source:**
```
multis persuasit ut Christo se adjungerent. Unde et ec-
```

**Prior English:**
```
yet he persuaded many to join themselves to Christ. And so, when
```

**Proposed English:** _(model: claude-opus-4-7)_
```
he persuaded many to join themselves to Christ. And so, when
```

**Fixer:** Removed the unwarranted adversative 'yet'; 'multis persuasit' has no contrastive force in the Latin.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0042_body_l0006` &nbsp;·&nbsp; page p0042
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** The Latin fragment ('Similiter et apud Dorotheum in synopsi, Aristobulum') contains no main verb and no first-person element; the translation adds 'I read that,' which is an interpolation not present in the source text.

**Latin source:**
```
Similiter et apud Dorotheum in synopsi, Aristobulum
```

**Prior English:**
```
Similarly too, in Dorotheus' Synopsis, I read that Aristobulus
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Similarly too, in Dorotheus' Synopsis, Aristobulus
```

**Fixer:** Removed the interpolated 'I read that,' since the Latin fragment has no main verb and no first-person element.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0042_body_l0024` &nbsp;·&nbsp; page p0042
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** No Greek present. 'Petri' (genitive, 'of Peter') is rendered as nominative 'Peter', obscuring that this describes Peter's wife/relative; 'and also' is added without source warrant; but all named referents and 'socrus' are correctly rendered.

**Latin source:**
```
Petri, filia Aristobuli vel Zebedæi, et Salomes; socrus
```

**Prior English:**
```
Peter, the daughter of Aristobulus (or Zebedee) and of Salome; and also the mother-in-law
```

**Proposed English:** _(model: claude-opus-4-7)_
```
of Peter, the daughter of Aristobulus (or Zebedee) and of Salome; the mother-in-law
```

**Fixer:** Restored the genitive 'of Peter' so the phrase correctly modifies Peter's relative, and dropped the unwarranted 'and also' before 'mother-in-law'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0043_body_l0005` &nbsp;·&nbsp; page p0043
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'Edita' (published/having been published) is dropped entirely, losing the participial frame; 'pectora' (hearts/breasts, plural) rendered as singular 'heart'; otherwise the core meaning is preserved in appropriate scholarly register.

**Latin source:**
```
Edita, cur Latiæ pectora plebis habet?
```

**Prior English:**
```
why does she possess the heart of the Latin people?
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Once published, why does it possess the hearts of the Latin people?
```

**Fixer:** Restored the dropped participle 'Edita' as 'Once published' and corrected 'pectora' to plural 'hearts'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0043_body_l0016` &nbsp;·&nbsp; page p0043
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** Translation renders the sense accurately but omits the verb ('favis' implies honeyed flavoring) and restructures to a fragment; 'Attic honeycombs' correctly interprets 'Thesæis' (Athenian) while 'Massic wines' is exact, but the incomplete syntax reduces fidelity.

**Latin source:**
```
Massica Thesæis tam bene vina favis.
```

**Prior English:**
```
so well are Massic wines with Attic honeycombs.
```

**Proposed English:** _(model: claude-opus-4-7)_
```
so well do Massic wines blend with Attic honeycombs.
```

**Fixer:** Added an explicit verb ('blend') to render the implied action of 'favis' mixing with the wines, completing the syntax rather than leaving a fragment.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0043_body_l0019` &nbsp;·&nbsp; page p0043
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** 'their' is an addition not in the Latin ('lecto' = 'the bed', no possessive); 'fair' for 'Candida' is acceptable but 'White/Bright' would be more literal; otherwise the poetic line is faithfully rendered in appropriate register.

**Latin source:**
```
Candida perpetuo reside Concordia lecto,
```

**Prior English:**
```
Fair Concord, abide upon their everlasting bed,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Fair Concord, abide upon the everlasting bed,
```

**Fixer:** Replaced 'their' with 'the' since 'lecto' has no possessive in the Latin.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0043_body_l0023` &nbsp;·&nbsp; page p0043
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** 'Quod' here is a relative connector ('which epigram'), not a concessive 'although'; treating it as concessive shifts the clause's syntactic role and likely truncates a continuing sentence, reducing content fidelity.

**Latin source:**
```
Quod epigramma cum ad Rufum de Pudente scriptum
```

**Prior English:**
```
Although this epigram was written to Rufus about Pudens,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Since this epigram was written to Rufus about Pudens,
```

**Fixer:** Changed 'Although' to 'Since' to render 'Quod' as a causal/relative connector continuing the sentence rather than a concessive, restoring the clause's syntactic role.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0043_body_l0028` &nbsp;·&nbsp; page p0043
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** No Greek present; 'pari nempe acumine, quo eandem Claudiam inter ma-' is rendered accurately in its visible parts, but 'the same man asserts that' and 'is numbered by Plutarch' are not in the extant fragment—possibly drawn from surrounding context not shown, but as additions to the visible source they lower fidelity; register is appropriately scholarly.

**Latin source:**
```
pari nempe acumine, quo eandem Claudiam “inter ma-
```

**Prior English:**
```
with the same acumen, namely, with which the same man asserts that this same Claudia "is numbered by Plutarch among the ma-
```

**Proposed English:** _(model: claude-opus-4-7)_
```
with the same acumen, namely, with which the same Claudia "among the ma-
```

**Fixer:** Removed unsupported additions ('the same man asserts that' and 'is numbered by Plutarch'); the visible fragment only has 'eandem Claudiam inter ma-' trailing off mid-quotation.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0043_body_l0029` &nbsp;·&nbsp; page p0043
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** No Greek present; register is appropriately scholarly; but 'numerare' (to enumerate/count) is dropped from the fragment, and the truncated 'Plutar-' is silently omitted rather than signalled, reducing content fidelity.

**Latin source:**
```
tronas laude continentiæ clarissimas numerare Plutar-
```

**Prior English:**
```
trons most renowned for the praise of continence":
```

**Proposed English:** _(model: claude-opus-4-7)_
```
to enumerate matrons most renowned for the praise of continence, Plutar[ch
```

**Fixer:** Restored the dropped verb 'numerare' as 'to enumerate' and signalled the truncated 'Plutar-' with a bracketed continuation marker.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0001` &nbsp;·&nbsp; page p0044
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The translation adds 'from this he infers that' with no Latin basis (fragment begins mid-clause with 'faciat'); otherwise register and preserved content are appropriate, but the added inferential framing is an unjustified addition.

**Latin source:**
```
faciat. Et quo Pudentem maritum, centurionem aut pri-
```

**Prior English:**
```
does. And from this he infers that Pudens her husband, a centurion or pri-
```

**Proposed English:** _(model: claude-opus-4-7)_
```
does. And so that her husband Pudens, a centurion or pri-
```

**Fixer:** Removed the unjustified inferential framing 'from this he infers that'; rendered 'Et quo' as a plain connective ('And so that') fitting the mid-clause fragment without adding content.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0002` &nbsp;·&nbsp; page p0044
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** Translation renders the core meaning but adds redundancy ('banished as an exile' for 'exulem') and handles 'mipilarem' as a proper noun prefix rather than the accusative participle form, slightly distorting Ussher's syntax.

**Latin source:**
```
mipilarem in Britannia vel Germania militantem, exulem
```

**Prior English:**
```
-mipilus serving in Britain or Germany, was banished as an exile
```

**Proposed English:** _(model: claude-opus-4-7)_
```
a primipilus serving in Britain or Germany, an exile
```

**Fixer:** Treated 'mipilarem' as the accusative of primipilus (centurion rank) with article, and rendered 'exulem' as simply 'an exile' to remove the redundant 'banished as'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0005` &nbsp;·&nbsp; page p0044
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** Fragment likely ends 'Martialis carmine'; translation captures the author referent but omits 'carmine' (verse/poem), losing a content element; register is appropriately scholarly.

**Latin source:**
```
alis carmine :
```

**Prior English:**
```
of Martial:
```

**Proposed English:** _(model: claude-opus-4-7)_
```
of Martial in verse:
```

**Fixer:** Added 'in verse' to render 'carmine', restoring the omitted content element.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0008` &nbsp;·&nbsp; page p0044
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** The Latin fragment contains no verb; the translation supplies 'conjectures that…is to be substituted,' an interpretive expansion not present in the source, though 'pro Scythici' does imply substitution; register is impeccably scholarly throughout.

**Latin source:**
```
Ubi argutissimus criticus Scotici vocabulum, pro Scythici,
```

**Prior English:**
```
Here the most ingenious critic conjectures that the word 'Scotici' is to be substituted for 'Scythici',
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Here the most ingenious critic [reads] 'Scotici' for 'Scythici',
```

**Fixer:** Removed the unsupported verb 'conjectures that...is to be substituted'; the Latin has no verb, so I supplied a minimal bracketed '[reads]' to carry the implied substitution signaled by 'pro'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0009` &nbsp;·&nbsp; page p0044
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The translation renders 'oblitus' as 'having forgotten that' and preserves 'in Claudian,' but drops 'reponendum esse conjicit' ('he conjectures is to be restored'), losing Ussher's main verb and scholarly judgment entirely.

**Latin source:**
```
reponendum esse conjicit: oblitus, apud Claudianum,
```

**Prior English:**
```
having forgotten that, in Claudian,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
he conjectures should be restored, having forgotten that, in Claudian,
```

**Fixer:** Restored the dropped main verb 'reponendum esse conjicit' as 'he conjectures should be restored' to recover Ussher's scholarly judgment.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0015` &nbsp;·&nbsp; page p0044
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The fragment is rendered accurately but 'rave with the madness of' is an interpretive expansion of the implied elliptical Latin ('quasi quisquam eam Dempsteri [furore insanire putaret]'); the ellipsis makes a clean 5 unachievable, but register is appropriately scholarly.

**Latin source:**
```
potuisse esse Anglam,” quasi quisquam eam Dempsteri
```

**Prior English:**
```
have been an Englishwoman" — as though anyone would rave with the madness of Dempster
```

**Proposed English:** _(model: claude-opus-4-7)_
```
have been an Englishwoman" — as though anyone would share Dempster's madness
```

**Fixer:** Tightened the elliptical supplement: replaced the expansive 'rave with the madness of Dempster' with the leaner 'share Dempster's madness', keeping the implied verb minimal while preserving sense and scholarly register.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0017` &nbsp;·&nbsp; page p0044
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The fragment 'reret in Britannia' (likely 'maneret in Britannia') is omitted — 'in Britain' drops out entirely — but the 'argument' rendering and scholarly register are sound.

**Latin source:**
```
reret in Britannia: aut id argumentatione sua conficere non
```

**Prior English:**
```
or as though Persons were not endeavoring to make out, by his argument,
```

**Proposed English:** _(model: claude-opus-4-7)_
```
or as though Persons were not endeavoring to make out, by his argument, [that he remained] in Britain;
```

**Fixer:** Restored the omitted 'in Britannia' by adding a bracketed '[that he remained] in Britain' to capture the fragmentary 'reret in Britannia' clause.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0018` &nbsp;·&nbsp; page p0044
**Scores:** cf=3 · rf=5 · gp=na · ph=na

**Judge:** 'conaretur Personius' (Persons was attempting) is dropped, leaving only the subordinate clause; register is appropriate scholarly English with correct Latinate phrasing.

**Latin source:**
```
conaretur Personius, B. Claudiam cujus Paulus meminit,
```

**Prior English:**
```
that the blessed Claudia whom Paul mentions
```

**Proposed English:** _(model: claude-opus-4-7)_
```
Persons was attempting [to deny] that the blessed Claudia whom Paul mentions
```

**Fixer:** Restored the dropped main clause 'conaretur Personius' as 'Persons was attempting' so the subordinate clause has its governing verb.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

### `seg_p0044_body_l0026` &nbsp;·&nbsp; page p0044
**Scores:** cf=3 · rf=4 · gp=na · ph=na

**Judge:** The translation renders the fragment naturally but omits 'latu conscripta' (composed broadly/at large) and reframes as a question ('will it follow') where the Latin is declarative; register is appropriately scholarly.

**Latin source:**
```
latu conscripta carmina; sequetur, et reliqua omnia eodem
```

**Prior English:**
```
will it follow that all the rest too were composed at the same
```

**Proposed English:** _(model: claude-opus-4-7)_
```
poems composed broadly; it will follow that all the rest too were composed in the same
```

**Fixer:** Restored the omitted 'latu conscripta' as 'composed broadly' and converted the rendering from interrogative to declarative to match 'sequetur'.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---


## cf = 4 — borderline (flagged on rf/gp/ph)

### `seg_p0040_body_l0014` &nbsp;·&nbsp; page p0040
**Scores:** cf=4 · rf=3 · gp=na · ph=na

**Judge:** Content is faithful to the Latin fragment but the translation is incomplete (cuts off mid-sentence); 'forsook' is slightly archaic (KJV register) where 'abandoned' or 'deserted' would suit modern scholarly prose.

**Latin source:**
```
prima mea defensione nemo mihi adfuit; sed omnes me de-
```

**Prior English:**
```
my first defense no one stood with me; but all forsook
```

**Proposed English:** _(model: claude-opus-4-7)_
```
at my first defense no one stood with me; but all deserted
```

**Fixer:** Replaced KJV-register 'forsook' with modern scholarly 'deserted' and added 'at' to render 'prima mea defensione' more naturally; the line is a fragment in the source, so the trailing 'de-' break is preserved as incompleteness.

**Decision:** [ ] accept   [ ] reject (keep prior)   [ ] edit (write below)

---

