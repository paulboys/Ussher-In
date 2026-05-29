# Author-Fidelity Report — Chapter 1 (ussher_v5) — pages 32–45

Source: `08_working_scratch\phase3b\ch1_fidelity_scores.jsonl`  
Units: **473**

## Aggregate scores

| Rubric | Mean | Min | Max | n (scored) | na | err |
|---|---:|---:|---:|---:|---:|---:|
| content_fidelity | 4.108 | 1 | 5 | 473 | 0 | 0 |
| register_fidelity | 4.723 | 1 | 5 | 473 | 0 | 0 |
| greek_preservation | 4.879 | 1 | 5 | 33 | 440 | 0 |
| paraphrase_handling | 5.000 | 5 | 5 | 5 | 468 | 0 |

## Score distribution

| Rubric | 1 | 2 | 3 | 4 | 5 | na |
|---|---:|---:|---:|---:|---:|---:|
| content_fidelity | 10 | 42 | 74 | 108 | 239 | 0 |
| register_fidelity | 2 | 0 | 9 | 105 | 357 | 0 |
| greek_preservation | 1 | 0 | 0 | 0 | 32 | 440 |
| paraphrase_handling | 0 | 0 | 0 | 0 | 5 | 468 |

## Per-page aggregates

| Page | n | cf mean | rf mean | gp (when applic.) | ph (when applic.) |
|---|---:|---:|---:|---:|---:|
| p0032 | 24 | 4.38 | 4.88 | — | — |
| p0033 | 39 | 4.49 | 4.67 | — | — |
| p0034 | 39 | 4.10 | 4.74 | 5.00 (n=2) | 5.00 (n=1) |
| p0035 | 39 | 4.03 | 4.56 | 5.00 (n=3) | — |
| p0036 | 38 | 3.89 | 4.50 | 5.00 (n=9) | — |
| p0037 | 40 | 4.10 | 4.78 | — | — |
| p0038 | 37 | 3.76 | 4.76 | — | — |
| p0039 | 35 | 4.00 | 4.80 | 5.00 (n=3) | — |
| p0040 | 36 | 4.36 | 4.86 | 5.00 (n=3) | 5.00 (n=2) |
| p0041 | 24 | 4.00 | 4.75 | 5.00 (n=11) | 5.00 (n=1) |
| p0042 | 38 | 4.45 | 4.87 | — | — |
| p0043 | 39 | 4.15 | 4.69 | 5.00 (n=1) | 5.00 (n=1) |
| p0044 | 32 | 3.66 | 4.59 | 1.00 (n=1) | — |
| p0045 | 13 | 4.15 | 4.77 | — | — |

## Content-fidelity review queue (cf ≤ 3) — 126 unit(s)

| Unit | cf | rf | gp | ph | Reason |
|---|---:|---:|---:|---:|---|
| seg_p0033_body_l0025 | 1 | 1 | na | na | Candidate is a bare em-dash offering no translation of the Latin fragment 'multitudines,' so content fidelity is completely absent and register cannot be assessed. |
| seg_p0036_body_l0009 | 1 | 4 | na | na | 'cladem illam maximam' (that greatest disaster/calamity) is wholly omitted, and 'Lioness' has no basis in the Latin fragment; only 'treacherous' (dolosam) is correctly rendered. |
| seg_p0036_body_l0019 | 1 | 1 | 5 | na | Greek is preserved verbatim; however, the candidate provides no English translation whatsoever—it is a bare repetition of the Greek source fragment, so content_fidelity and register_fidelity both scor… |
| seg_p0036_body_l0026 | 1 | 3 | na | na | 'torque' (twisted metal neck-ornament/collar) is rendered as 'leather-worker' — a fundamental lexical error; 'legem' (law) is softened to 'teaching'; and a finite verb is introduced with no Latin basi… |
| seg_p0038_body_l0010 | 1 | 4 | na | na | The Latin specifies ordination at Rome ('apud Romam ordinantur') before sending to preach, but the translation omits the Roman ordination entirely, reducing two distinct clauses to one; register is ap… |
| seg_p0039_body_l0023 | 1 | 4 | na | na | Two compounding errors: 'martyrologiis' (martyrologies) is silently dropped, and 'octavum' (eighth) is rendered as 'twenty-eighth'—a factual mistranslation that changes the calendrical reference. |
| seg_p0041_body_l0012 | 1 | 4 | 5 | na | "quintum diem" (fifth day) is rendered as "fifteenth day" — a clear mistranslation; the bracketed "[This—" has no visible counterpart in the Latin source; Greek "Οὗ-" is preserved verbatim. |
| seg_p0044_fn_003 | 1 | 3 | 1 | na | The candidate renders only the citation header, omitting the entire Martial verse, the prose sentence on Trajan/Nerva, and the Greek quotation from Aelian (Ἐπεὶ δὲ τῷ Θεῷ…), so content_fidelity and gr… |
| seg_p0045_body_l0005 | 1 | 3 | na | na | The main verb 'Rexerat' (he had ruled/reigned) is entirely dropped, leaving only the relative clause; 'hallowed' for 'sacer' carries KJV resonance rather than neutral scholarly register. |
| seg_p0045_body_l0010 | 1 | 4 | na | na | The translation adds 'and Claudia' which is absent from the Latin source ('Pudens et Linus' only); register is appropriate scholarly English. |
| seg_p0032_body_l0016 | 2 | 4 | na | na | No Greek present. 'barbarous' and 'round about' are not in the Latin fragment ('omnesque' = 'and all'); these additions materially expand Ussher's text. Register is appropriately scholarly throughout. |
| seg_p0032_body_l0017 | 2 | 5 | na | na | The fragment 'circuitum barbaræ nationes' (the surrounding barbarian nations) is entirely absent from the translation, which renders only the verb and its objects; register is modern scholarly and app… |
| seg_p0034_body_l0010 | 2 | 5 | 5 | na | Greek preserved verbatim with accurate bracketed gloss; however 'non insulas' is entirely omitted from the translation, dropping Ussher's contrasting qualification ('not islands') that is integral to … |
| seg_p0034_body_l0026 | 2 | 4 | na | na | The key ablative 'secessu' (withdrawal/retreat) is wholly absent from the translation, and 'merely temporal' is added with no basis in the Latin fragment; 'de firma-' supports only 'firmament,' not a … |
| seg_p0034_body_l0027 | 2 | 3 | na | na | 'temporali' (temporal) is dropped entirely from the translation, and 'citadel' is added with no Latin warrant — 'summa cœlorum' means 'summit/heights of the heavens'; 'citadel' inflates the register t… |
| seg_p0034_body_l0031 | 2 | 4 | na | na | 'religio' (the subject) is entirely absent from the translation, and the verb 'gabatur' is unrendered; 'comminata' is rendered as 'death being threatened' (supplying 'morte' not present in the fragmen… |
| seg_p0034_body_l0032 | 2 | 4 | na | na | 'morte' (death/by death) is entirely dropped; 'ejusdem' (of the same) is expanded to 'that same faith' with 'faith' having no Latin warrant; register is otherwise appropriate for a scholarly fragment. |
| seg_p0035_body_l0027 | 2 | 3 | na | na | 'listarum scilicet' (roughly 'of these, namely') is entirely unrendered, and 'their words' is inserted without warrant from this fragment; 'unto' is a KJV archaism the rubric disallows, though it may … |
| seg_p0035_body_l0033 | 2 | 4 | 5 | na | Greek is preserved verbatim with accents; no visible Latin paraphrase in source so paraphrase_handling is na; 'its worship' badly misrenders 'ejus expers relinqueretur' (verbal passive subjunctive and… |
| seg_p0036_body_l0002 | 2 | 4 | na | na | 'in sola Judæa' (in Judea alone) is silently dropped—a key limiting phrase—and 'God' is supplied from context but absent from this clause; register is appropriately scholarly but the content loss is s… |
| seg_p0036_body_l0003 | 2 | 4 | na | na | The candidate translates 'Deus' as 'in Judaea alone' — a serious content failure introducing an absent phrase and dropping 'God' as the subject — though the rest of the fragment ('now within a few yea… |
| seg_p0036_body_l0008 | 2 | 4 | na | na | 'Leænam' (the Lioness) is dropped entirely from the candidate, and 'that very great disaster' inserts 'very great' with no Latin warrant in the fragment; register is otherwise appropriately scholarly. |
| seg_p0036_body_l0013 | 2 | 4 | na | na | The ablative absolute (cæsis Britannorum octoginta millibus) is correctly rendered, but veritatis suæ ('of his truth') is dropped entirely and 'Christ, he indicates,' is inserted without basis in the … |
| seg_p0036_body_l0031 | 2 | 3 | na | na | 'induxerunt' means 'led into/brought to' (a belief), not 'persuaded to accept teachings' — the object of crucifixi (of the crucified one) is dropped entirely, a significant content omission; register … |
| seg_p0037_body_l0008 | 2 | 4 | na | na | 'Circumfertur nomine' ('is circulated/known under the name') is dropped and 'That [James preached]' inserts content entirely absent from the source; 'Saragossa' is an acceptable vernacular rendering o… |
| seg_p0037_body_l0009 | 2 | 4 | na | na | The translation inserts 'affirms; that he preached to the Irish' which has no basis in the Latin fragment ('larvam induit, Hibernis Vin-'); 'dons the mask' renders 'larvam induit' acceptably; register… |
| seg_p0037_body_l0017 | 2 | 4 | na | na | 'oratore' (envoy/ambassador) and 'productus' (brought forward/presented) are both dropped; 'writes' is added with no Latin warrant; 'Apostolis diversa' is expanded to 'the apostles were going to' — th… |
| seg_p0037_body_l0018 | 2 | 4 | na | na | 'cosmi climata adeuntibus' means 'for those approaching the regions of the world/cosmos' (a participial clause), but the translation adds 'driven to the shores' which invents content not in the Latin;… |
| seg_p0038_body_l0004 | 2 | 4 | na | na | The Latin is an ablative absolute ('duobus remanentibus') meaning 'two having remained'; the translation renders the noun clause correctly but appends 'went with' which has no source and misrepresents… |
| seg_p0038_body_l0016 | 2 | 4 | na | na | 'we read' is added without Latin basis; 'Baronius' from footnote ^m is imported as main-clause subject; 'once published under the name of' substantially expands the bare genitive 'Hieronymi'; register… |
| seg_p0038_body_l0017 | 2 | 4 | na | na | Translation omits 'nomine olim editum' (formerly published under the name) and 'supposita' (spurious/supposititious), while adding 'the epistle' and 'Jerome' not present in this fragment; register of … |
| seg_p0038_body_l0021 | 2 | 4 | na | na | The translation renders 'et ad prædicandum verbum Dei in His-' adequately but omits 'copos ordinatos' (ordained bishops), a substantive clause present in the Latin fragment; register is appropriate mo… |
| seg_p0038_body_l0028 | 2 | 5 | na | na | Two unsupported additions: 'son of' interprets the genitive patronymic rather than rendering it, and 'bishop' is wholly absent from the Latin — Menevensis is a locative adjective with no episcopal tit… |
| seg_p0038_body_l0029 | 2 | 4 | na | na | 'episcopi filius' (son of a bishop) is entirely dropped from the translation, a significant content omission; the addition of 'catalogue' is a reasonable inferential gloss but cannot compensate; regis… |
| seg_p0039_body_l0006 | 2 | 4 | na | na | The Latin fragment 'primum fidem et religionem' means 'first the faith and religion' (accusative objects), not 'first preached the faith and religion'; 'preached' is an addition not in this clause, sh… |
| seg_p0039_body_l0019 | 2 | 4 | 5 | na | Greek preserved verbatim; content_fidelity penalised because the bracketed rendering adds 'enlightened many by the word of the gospel' and 'by the unbelievers'—content absent from the visible source f… |
| seg_p0040_body_l0023 | 2 | 5 | na | na | 'nantius' (likely a participial fragment, e.g. part of 'pronuntians'/'enuntians') is silently dropped, while 'writes' is added with no Latin warrant; register is appropriate modern scholarly English. |
| seg_p0040_body_l0027 | 2 | 4 | na | na | The translation invents 'indicates that Paul preached the gospel' — the Latin fragment only says 'concerning the birthday of the apostles, Paul [preached] to the Spanish and Britons'; 'Hispanis et Bri… |
| seg_p0040_body_l0028 | 2 | 4 | na | na | The core verb phrase 'evangelium prædicasse significat' (signifies that [he] preached the gospel) is entirely absent from the translation, while 'to the Spaniards and the Britons' appears with no basi… |
| seg_p0041_body_l0003 | 2 | 4 | na | na | The Latin says Pentecost [attests] that he went from Spain 'into the farthest parts' of the earth, but the translation inverts the direction ('ran from Spain') and introduces 'suggests' for an implied… |
| seg_p0041_body_l0010 | 2 | 4 | na | na | 'meminit' (3rd-person singular: 'he mentions/records') is mistranslated as 1st-person 'I find,' shifting both person and verb sense; word order and other elements are otherwise acceptable and register… |
| seg_p0041_body_l0020 | 2 | 3 | 5 | na | Greek preserved verbatim; however the Latin clause 'E septuaginta discipulis erat' is entirely dropped, and the bracketed gloss '[it, he was perfected]' is a garbled partial rendering rather than a pr… |
| seg_p0042_body_l0034 | 2 | 5 | na | na | The candidate inserts 'Pseudo-Clement intimates that' — an agent and reporting verb absent from the visible Latin fragment — while otherwise correctly rendering 'Linum, primum Ecclesiæ Romanæ episcopu… |
| seg_p0042_body_l0035 | 2 | 4 | na | na | Translation drops the attributing source ('Pseudo-Clemens suggests') and the verb 'innuit', rendering only the bare propositional content while omitting Ussher's scholarly hedging via citation. |
| seg_p0043_body_l0006 | 2 | 4 | na | na | 'Romanam' (Roman) is rendered 'Italian,' a clear content substitution; 'is hers' is added with no Latin warrant; and the translation appears truncated, dropping the infinitive clause that completes th… |
| seg_p0043_body_l0007 | 2 | 4 | na | na | The Latin names 'Italides' (Italian women) and 'Atthides' (Attic women) are replaced by 'Roman' and 'women of Attica'; 'Italides' specifically means Italian, not Roman, shifting the referent, and the … |
| seg_p0043_body_l0031 | 2 | 5 | na | na | 'diæ illius priscæ' ('of that ancient goddess/divine one') is entirely dropped; the translation renders only 'Vestalis utique illius nominatissimæ,' omitting a full adjectival-genitive phrase Ussher w… |
| seg_p0044_body_l0010 | 2 | 4 | na | na | The translation renders 'primam Scotici' as 'the first syllable of the name Scoti-' but the Latin fragment ends mid-phrase (likely 'primam Scotici nominis syllabam' or similar), so the expansion adds … |
| seg_p0044_body_l0011 | 2 | 5 | na | na | No Greek present; register is appropriately scholarly; but 'nominis syllabam' (the syllable of the name) is silently dropped, leaving only the predicate 'semper productam legi' rendered, a meaningful … |
| seg_p0044_body_l0016 | 2 | 4 | na | na | The figura etymologica 'insaniret insaniam' (the core expression of madness) is entirely absent from the translation, and 'in Britain' is added without basis in the given Latin fragment; register is o… |
| seg_p0044_body_l0025 | 2 | 4 | na | na | 'aliqua' means 'certain things/some matters' but the translation inserts 'poems composed,' an interpretive addition absent from the Latin fragment; register is appropriately scholarly otherwise. |
| seg_p0044_body_l0027 | 2 | 5 | na | na | 'fuisse composita' (to have been composed) is dropped entirely from the first clause, and 'the poet met his' is added with no basis in the Latin fragment, where only 'mortem' (death) appears without a… |
| seg_p0032_body_l0005 | 3 | 4 | na | na | The fragment is a mid-sentence carry-over ('tish isles' truncating 'British isles') that omits the main verb phrase 'evangelium primi prædicasse dicuntur' (are said to have first preached the gospel);… |
| seg_p0032_body_l0009 | 3 | 4 | na | na | The fragment renders the core nominal phrase accurately but adds 'our' (not in source) and drops the verb 'præcesserunt' (preceded/came before), losing the predicate entirely; register is appropriate … |
| seg_p0033_body_l0012 | 3 | 3 | na | na | 'manum genus' rendered as 'man race' (awkward; 'humanum genus'/'mankind' expected), 'obligabatur adstrictum' adequately as 'held fast in bondage' though slightly redundant, 'nec enumerans' correctly l… |
| seg_p0033_body_l0013 | 3 | 4 | na | na | 'My' is added to patriæ (no possessive pronoun in the Latin) and 'exceeding' is inserted without warrant, shifting the neutral pene numero Egyptiaca ('almost Egyptian in number') into a claim of surpa… |
| seg_p0033_body_l0015 | 3 | 4 | na | na | Translation is incomplete — 'torvis' (fierce/grim looks) is cut off mid-phrase, leaving the ablative of manner unresolved; 'solito more' rendered as 'in their customary fashion' adds 'their' with no L… |
| seg_p0033_body_l0024 | 3 | 4 | na | na | No Greek present. 'Multitudes of' is added for 'tantarum gentium' (which is simply 'of so many nations'), and 'oceani' as a genitive loses its syntactic relationship via the em-dash; register is other… |
| seg_p0034_body_l0002 | 3 | 5 | na | na | Translation adds 'placed' (not in source) and renders only a sentence fragment ending abruptly; 'darkness and the shadow of death' is accurate but the interpolated verb and truncated clause reduce con… |
| seg_p0034_body_l0008 | 3 | 5 | na | na | No Greek present. Register is appropriately scholarly throughout. Content loses a point because 'to remain hidden from' is an interpretive expansion absent from the Latin fragment (nullum locum cœlest… |
| seg_p0034_body_l0009 | 3 | 4 | 5 | 5 | Greek preserved verbatim with accents; bracketed English gloss renders the paraphrase meaning correctly; content_fidelity docked because the Latin preamble 'occultum esse sinerent' is dropped entirely… |
| seg_p0034_body_l0013 | 3 | 4 | na | na | 'God had formerly foretold' adds theological elaboration absent from the terse Latin ('senex loquitur. Atque ita completum est quod per Esaiam'); 'says' drops 'senex loquitur' (the old man speaks) con… |
| seg_p0034_body_l0029 | 3 | 4 | na | na | 'coruscum' (gleaming/shining) rendered adequately but 'summo' (highest/greatest) is translated as 'last period' — a significant semantic shift that loses Ussher's superlative sense; register is approp… |
| seg_p0034_fn_006 | 3 | 5 | na | na | 'al. Sol.' is exactly rendered as 'another reading: Sol' but the translation appends '[Sun]'—an English gloss for the Latin word Sol—which is not present in Ussher's text; minor addition, core meaning… |
| seg_p0035_body_l0002 | 3 | 4 | na | na | The fragment is rendered accurately but ends mid-sentence with a dangling 'they', suggesting an incomplete segment; 'less so' is a reasonable rendering of 'minus' and register is appropriately scholar… |
| seg_p0035_body_l0005 | 3 | 4 | na | na | 'Against' mistranslates temporal 'ad' (should be 'to/in the year'); 'it is recorded' is an addition inferred from the truncated 'anno-' without textual warrant; 'next-to-last' for 'penultimum' is a mi… |
| seg_p0035_body_l0008 | 3 | 4 | na | na | 'patrum' means 'fathers/fathers of the church' not 'senators'; 'tera sacra' likely 'sacred land/territory' not 'sacred rites'; otherwise register is appropriately scholarly. |
| seg_p0035_body_l0013 | 3 | 4 | na | na | No Greek or paraphrase issues; content_fidelity docked to 3 because 'news' is added (Latin has only 'annunciatum sibi' = '[it] having been announced to him') and 'when' imposes a temporal reading on a… |
| seg_p0035_body_l0020 | 3 | 4 | na | na | Visible Latin words (quod→this, profecto→indeed, divina providentia, ita→so, tunc→then, Cæsaris→Caesar's) are accurately rendered, but 'instilled' is a verb with no antecedent in the visible truncated… |
| seg_p0035_body_l0021 | 3 | 4 | na | na | The fragment is a mid-sentence clause and the translation renders the core prepositional logic faithfully, but 'sibus ingessit' (thrust/forced upon minds) is only partially captured by 'mind' with no … |
| seg_p0035_body_l0022 | 3 | 4 | na | na | 'initiis' (ablatives of beginning/origin) is rendered loosely as 'first beginnings' (redundant), and the clause lacks its governing preposition 'ab' context, but core vocabulary is preserved in approp… |
| seg_p0035_body_l0024 | 3 | 4 | na | na | The translation renders the Latin faithfully but adds 'it lit up' for a finite verb not present in the truncated source (which ends mid-clause with 'claritate su-'), making a content inference; regist… |
| seg_p0035_body_l0025 | 3 | 4 | na | na | 'perni luminis' (of the eternal/everlasting light) is rendered 'from on high' (a directional gloss not in the Latin); 'illustraret' (might illuminate) is lost; 'compleretur' (might be fulfilled) corre… |
| seg_p0035_body_l0031 | 3 | 4 | na | na | The fragment renders 'congregatio Christianorum in omne hominum genus penetravit' adequately but omits 'congregatio' (assembly/congregation) entirely, reducing content fidelity; register is appropriat… |
| seg_p0035_body_l0032 | 3 | 4 | na | na | The fragment is rendered accurately but the trailing 'that was left without' is incomplete and adds a relative clause not present in the source, which cuts off mid-thought; register is appropriate sch… |
| seg_p0036_body_l0007 | 3 | 4 | na | na | 'rem' rendered as 'campaign' is a plausible but unsupported contextual guess; without the full sentence 'rem' could mean 'matter/affair/thing', so a minor content liberty is present, though register i… |
| seg_p0036_body_l0010 | 3 | 5 | na | na | 'gestam' (accusative feminine participle, referring back to a feminine noun in the prior clause — the deed/event 'accomplished among' the Britons) is silently dropped, a meaningful omission; the remai… |
| seg_p0036_body_l0014 | 3 | 4 | na | na | 'His truth' is an addition not present in the Latin (radios alone, no veritatis); 'significat' (signifies/indicates) and the subject are dropped, losing Ussher's framing clause; register is otherwise … |
| seg_p0036_body_l0030 | 3 | 4 | na | na | 'ɴᴏs' (we/us) is dropped entirely, losing Ussher's first-person framing; 'utque semel dicatur' is rendered accurately; register is appropriately scholarly. |
| seg_p0036_body_l0033 | 3 | 4 | na | na | Greek/paraphrase not applicable; content is partially rendered but 'non eadem est' (the predicate is not the same) is loosely rendered as 'is not on the same point,' adding 'point' without Latin warra… |
| seg_p0036_body_l0036 | 3 | 4 | na | na | 'some report' is added with no Latin warrant (the source is a fragmentary clause with no such attribution); register is appropriate scholarly English, but the unwarranted addition drops content_fideli… |
| seg_p0037_body_l0001 | 3 | 4 | na | na | 'tyrum' rendered as 'martyrs' is a partial fragment guess rather than the full word; 'Arabice scripto' correctly rendered; 'quidam referunt' correctly rendered; 'Eundem' correctly rendered; '[Spain]' … |
| seg_p0037_body_l0003 | 3 | 4 | na | na | 'dicavisse' (dedicated/devoted) is rendered as 'poured' which shifts the register and meaning; 'in occasum mundi' (to the setting/west of the world) is compressed to 'the west' losing Ussher's cosmic … |
| seg_p0037_body_l0013 | 3 | 5 | na | na | 'oppida' (towns/cities) is rendered as '[Vannes]' — a specific toponym substituted for the general Latin noun — losing fidelity, though register is appropriately scholarly. |
| seg_p0037_body_l0019 | 3 | 5 | na | na | The translation adds 'of Ireland' and 'he is said to have chosen' which are not in this fragment; 'oris appulsus' (arrival at shore) is rendered as context from outside this snippet, and 'ubi sep-' is… |
| seg_p0037_body_l0020 | 3 | 4 | na | na | The translation omits 'item' (likewise/also) and 'elegisse fertur' (is said to have chosen), rendering only the object list; core names preserved but the main verb clause is dropped, reducing content … |
| seg_p0037_body_l0021 | 3 | 4 | na | na | Names are rendered in anglicised/Latinised forms (Indaletius, Tisefon, Euphrasius) that differ from Ussher's Indalecium, Tisephontem, Eufrasium; partial fragment 'dus' vs. 'dum' suggests a truncated r… |
| seg_p0037_body_l0028 | 3 | 4 | na | na | The translation captures the core structure (Turpin, others demonstrate) but adds 'indeed' and 'very' not in the Latin, and 'loquitur Vincentius' (Vincent speaks) is dropped entirely, representing a n… |
| seg_p0038_body_l0005 | 3 | 4 | na | na | No Greek present; 'Hierosolymis perrexerunt' (they proceeded to Jerusalem) loses its main verb — 'carried' likely belongs to the cut-off continuation, leaving the first clause's movement unrendered; r… |
| seg_p0038_body_l0007 | 3 | 4 | na | na | No Greek present; 'spoke thus in his martyrology' renders 'sic dixit' and 'in suo martyrologio' accurately, but 'wrote to blessed' adds a verb ('wrote to') absent from 'ac beato', inflating the fragme… |
| seg_p0038_body_l0009 | 3 | 5 | na | na | 'corpore' (ablative, likely 'in the body/corporally') is dropped, and 'infulis episcopalibus' rendered as 'episcopal insignia' is acceptable though slightly loose; 'they were ordained at Rome' adds 'o… |
| seg_p0038_body_l0022 | 3 | 4 | na | na | 'panias' (likely 'Hispanias' or similar) is rendered as 'provinces' rather than a specific place name, and 'evangelizandi' is paraphrased as 'had evangelized in'; core meaning preserved but referent s… |
| seg_p0038_body_l0025 | 3 | 5 | na | na | 'tere' (likely 'marte' or similar ablative) and the subject noun are missing from the fragment, but the visible content — Roman Church martyrology and 'prefixed' — is accurately rendered in appropriat… |
| seg_p0038_body_l0030 | 3 | 5 | na | na | 'catalogo' (dative 'to the catalogue/list') is rendered as 'which is appended to,' adding the relative clause framing not present in the Latin fragment; register is appropriately scholarly. |
| seg_p0038_fn_003 | 3 | 5 | na | na | No Greek present; register is appropriate; but 'al.' (alias/aliter) means 'otherwise [called/known as],' not 'elsewhere spelled' — the translation shifts from an alternative name/identity to an orthog… |
| seg_p0039_body_l0002 | 3 | 4 | na | na | 'prædicavit' (preached) is omitted entirely, dropping a key verb; otherwise register is appropriate modern scholarly English with no archaisms. |
| seg_p0039_body_l0008 | 3 | 4 | na | na | Translation adds parenthetical gloss '(the Irish)' and introduces 'instead of Hiberis' — explanatory context absent from the Latin source — though register is appropriately scholarly. |
| seg_p0039_body_l0012 | 3 | 4 | na | na | 'dentalem oceanum' is rendered simply as 'ocean,' dropping the adjective 'dentalem' (likely 'Occidentalem' or similar); 'Britannicasque insulas' is correctly rendered; minor omission lowers content fi… |
| seg_p0039_body_l0021 | 3 | 5 | na | na | Translation renders only 'In martyrologio' as 'In the Roman martyrology, however,' — adding 'Roman' and 'however' not present in this fragment, while dropping 'fidelibus crucifixus, illic sepultus est… |
| seg_p0039_body_l0022 | 3 | 5 | na | na | The translation adds 'the martyrologies of' for 'martyrologiis' which is implied by context but not present in this fragment; 'tamen' (yet/however) is also dropped, and the fragment begins mid-constru… |
| seg_p0039_body_l0024 | 3 | 5 | na | na | The ordinal 'vigesimum' (twentieth/twentieth time) is dropped — the Latin specifies he suffered martyrdom for the twentieth time (or in the twentieth [year/instance]), a detail absent from the transla… |
| seg_p0039_body_l0025 | 3 | 5 | na | na | The fragment captures 'Simon Peter' and 'twelve years' but adds 'spent' where the Latin has no verb yet (duodecim quidem annos esse is an accusative-infinitive fragment); the implicit verb may be warr… |
| seg_p0039_body_l0031 | 3 | 5 | na | na | The translation renders 'multas gentes non nominatas attraxisse ad fidem' accurately, but omits 'ratum' (ratified/confirmed), which is a dropped clause affecting completeness; register is appropriatel… |
| seg_p0040_body_l0016 | 3 | 5 | na | na | 'adstitit' (stood by/appeared beside) is dropped entirely; 'confortavit' rendered correctly; 'ut per me prædicatio impleatur' translated accurately — but the missing main verb 'stood by' is a signific… |
| seg_p0040_body_l0019 | 3 | 5 | na | na | No Greek present; register is cleanly modern-scholarly; but 'missus est' (he was sent/dispatched) is dropped entirely, and 'set out for' adds volitional departure not in the Latin fragment, which only… |
| seg_p0040_body_l0020 | 3 | 4 | na | na | The fragment renders the motion and outreach accurately but adds 'the light of' which has no basis in the Latin source (doctrinas/doctrine expected); register is appropriately scholarly. |
| seg_p0040_body_l0021 | 3 | 5 | na | na | 'trinæ lucem attulit' ('brought light to the triple [islands]') is rendered as 'To the islands' — dropping the key verb and the 'threefold/triple' qualifier — but 'doctrine' for the preceding implied … |
| seg_p0041_body_l0006 | 3 | 4 | na | na | No Greek present. 'Accomplished' is an interpretive addition absent from the Latin ablative phrase; otherwise core content (thirty-five years, gospel contest, for Christ) is faithfully rendered. Regis… |
| seg_p0042_body_l0003 | 3 | 4 | na | na | 'Yet' introduces a mild adversative not in 'multis persuasit'; 'And so, when' renders 'Unde et' acceptably but the fragment cuts off, making full fidelity assessment difficult; register is appropriate… |
| seg_p0042_body_l0006 | 3 | 5 | na | na | The Latin fragment ('Similiter et apud Dorotheum in synopsi, Aristobulum') contains no main verb and no first-person element; the translation adds 'I read that,' which is an interpolation not present … |
| seg_p0042_body_l0024 | 3 | 5 | na | na | No Greek present. 'Petri' (genitive, 'of Peter') is rendered as nominative 'Peter', obscuring that this describes Peter's wife/relative; 'and also' is added without source warrant; but all named refer… |
| seg_p0043_body_l0005 | 3 | 4 | na | na | 'Edita' (published/having been published) is dropped entirely, losing the participial frame; 'pectora' (hearts/breasts, plural) rendered as singular 'heart'; otherwise the core meaning is preserved in… |
| seg_p0043_body_l0016 | 3 | 4 | na | na | Translation renders the sense accurately but omits the verb ('favis' implies honeyed flavoring) and restructures to a fragment; 'Attic honeycombs' correctly interprets 'Thesæis' (Athenian) while 'Mass… |
| seg_p0043_body_l0019 | 3 | 4 | na | na | 'their' is an addition not in the Latin ('lecto' = 'the bed', no possessive); 'fair' for 'Candida' is acceptable but 'White/Bright' would be more literal; otherwise the poetic line is faithfully rende… |
| seg_p0043_body_l0023 | 3 | 5 | na | na | 'Quod' here is a relative connector ('which epigram'), not a concessive 'although'; treating it as concessive shifts the clause's syntactic role and likely truncates a continuing sentence, reducing co… |
| seg_p0043_body_l0028 | 3 | 5 | na | na | No Greek present; 'pari nempe acumine, quo eandem Claudiam inter ma-' is rendered accurately in its visible parts, but 'the same man asserts that' and 'is numbered by Plutarch' are not in the extant f… |
| seg_p0043_body_l0029 | 3 | 5 | na | na | No Greek present; register is appropriately scholarly; but 'numerare' (to enumerate/count) is dropped from the fragment, and the truncated 'Plutar-' is silently omitted rather than signalled, reducing… |
| seg_p0044_body_l0001 | 3 | 4 | na | na | The translation adds 'from this he infers that' with no Latin basis (fragment begins mid-clause with 'faciat'); otherwise register and preserved content are appropriate, but the added inferential fram… |
| seg_p0044_body_l0002 | 3 | 4 | na | na | Translation renders the core meaning but adds redundancy ('banished as an exile' for 'exulem') and handles 'mipilarem' as a proper noun prefix rather than the accusative participle form, slightly dist… |
| seg_p0044_body_l0005 | 3 | 4 | na | na | Fragment likely ends 'Martialis carmine'; translation captures the author referent but omits 'carmine' (verse/poem), losing a content element; register is appropriately scholarly. |
| seg_p0044_body_l0008 | 3 | 5 | na | na | The Latin fragment contains no verb; the translation supplies 'conjectures that…is to be substituted,' an interpretive expansion not present in the source, though 'pro Scythici' does imply substitutio… |
| seg_p0044_body_l0009 | 3 | 4 | na | na | The translation renders 'oblitus' as 'having forgotten that' and preserves 'in Claudian,' but drops 'reponendum esse conjicit' ('he conjectures is to be restored'), losing Ussher's main verb and schol… |
| seg_p0044_body_l0015 | 3 | 4 | na | na | The fragment is rendered accurately but 'rave with the madness of' is an interpretive expansion of the implied elliptical Latin ('quasi quisquam eam Dempsteri [furore insanire putaret]'); the ellipsis… |
| seg_p0044_body_l0017 | 3 | 4 | na | na | The fragment 'reret in Britannia' (likely 'maneret in Britannia') is omitted — 'in Britain' drops out entirely — but the 'argument' rendering and scholarly register are sound. |
| seg_p0044_body_l0018 | 3 | 5 | na | na | 'conaretur Personius' (Persons was attempting) is dropped, leaving only the subordinate clause; register is appropriate scholarly English with correct Latinate phrasing. |
| seg_p0044_body_l0026 | 3 | 4 | na | na | The translation renders the fragment naturally but omits 'latu conscripta' (composed broadly/at large) and reframes as a question ('will it follow') where the Latin is declarative; register is appropr… |

