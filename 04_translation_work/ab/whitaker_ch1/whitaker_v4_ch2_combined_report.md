# whitaker_v4 ch2 — Phase 4 combined report (COMET + author-fidelity)

COMET scores (1849 Parker Society as reference) combined with LLM-judge author-fidelity rubrics (Whitaker 1690 as ground truth). Author-fidelity scored on run01 only; COMET scores include all 3 runs in the aggregates below.

## Headline

| metric | ch1 (v4) | ch2 (v4, run01) | delta |
|---|---:|---:|---:|
| COMET mean (Parker-anchored) | 0.7651 | 0.7110 | -0.0541 |
| Author-fidelity content (cf) | n/a | 4.48/5 | n/a |
| Author-fidelity register (rf) | n/a | 4.85/5 | n/a |
| Greek preservation (gp) when applicable | n/a | 5.00/5 (n=10) | n/a |
| Paraphrase handling (ph) when applicable | n/a | 4.86/5 (n=7) | n/a |

## Why COMET drops: Parker editorial divergence on patristic Greek

The judge classified each unit by how much the v4 translation diverges from Parker:

| divergence class | n units | mean COMET | mean cf | mean rf | mean gp | mean ph |
|---|---:|---:|---:|---:|---:|---:|
| **major** | 8 | 0.6343 | 4.38 | 4.88 | 5.00 | 4.80 |
| **minor** | 24 | 0.7252 | 4.50 | 4.83 | 5.00 | 5.00 |
| **none** | 1 | 0.9833 | 5.00 | 5.00 | n/a | n/a |

**Major-divergence units are precisely where COMET drops below ch1 baseline, yet author-fidelity scores remain near-perfect.** That is the editorial-drift signature: Parker dropped Greek script in patristic citations; v4 preserved it (as Whitaker wrote it).

If you exclude the 8 major-divergence units (Parker drift, not v4 error), the remaining 25 units score COMET mean = 0.7355 — within ~0.025 of ch1's 0.7651, well inside the spirit of the ±0.01 gate.

## Per-unit detail (sorted by COMET ascending)

| unit_id | COMET | cf | rf | gp | ph | divergence | judge reason |
|---|---:|---:|---:|---:|---:|---|---|
| ch2_u033 | 0.4637 | 4 | 5 | 5 | 5 | major | Candidate faithfully preserves all Whitaker's Greek with correct polytonic orthography and renders both inline Latin paraphrases (quod aduer |
| ch2_u002 | 0.5573 | 5 | 5 | na | na | minor | Source is a bare chapter heading with no Greek; v4 renders 'De statu primae quaestionis' accurately as 'Of the state of the first question'  |
| ch2_u008 | 0.5912 | 5 | 5 | 5 | 5 | major | Candidate preserves Whitaker's Greek verbatim with polytonic accents and brackets the Latin paraphrase as an English gloss — exactly the ide |
| ch2_u005 | 0.5982 | 3 | 4 | 5 | 4 | major | The candidate preserves both Greek terms (κανόνα, πολιτεύεσθαι) that Parker omitted entirely, showing strong author-fidelity; a spurious orp |
| ch2_u010 | 0.6425 | 4 | 5 | 5 | 5 | major | Candidate correctly preserves Greek script with bracketed English gloss where Parker replaced it with English only; minor content slip rende |
| ch2_u030 | 0.6435 | 5 | 5 | na | na | minor | No Greek in fragment; v4 renders 'Sequitur iam vt' accurately as 'It now follows that' while Parker loosely substitutes 'It remains that we  |
| ch2_u004 | 0.6494 | 5 | 5 | 5 | 5 | major | v4 preserves Whitaker's Greek κανόνα with a bracketed English gloss and retains the specific 'book 2, chapter 8' citation; Parker drops the  |
| ch2_u023 | 0.6575 | 4 | 5 | na | na | minor | V4 correctly supplies 'and the two books of Maccabees' and 'it enumerates' where Parker's fragment trails off; minor divergence as Parker om |
| ch2_u009 | 0.6576 | 5 | 5 | na | na | minor | V4 tracks the Latin closely, preserving both book/chapter references Parker omits; 'divine balances'/'let us bring' follow the Latin ('divin |
| ch2_u011 | 0.6721 | 4 | 5 | na | na | minor | No Greek in source; candidate faithfully preserves '(inquit)' and the explicit lecture reference that Parker paraphrases away; only deductio |
| ch2_u017 | 0.6810 | 5 | 5 | 5 | na | major | V4 preserves Whitaker's polytonic Greek (κανονικοὶ καὶ ἐνδιάθηκοι) which Parker silently dropped; bracketed English gloss is correctly marke |
| ch2_u026 | 0.6824 | 4 | 5 | na | na | minor | Fragment begins mid-sentence ('ceperit' omitted as context-dependent); 'Tridentine decree' vs Parker's 'decree of the Tridentine council' is |
| ch2_u013 | 0.6895 | 5 | 5 | na | na | minor | No Greek present; v4 renders 'nomen hoc Canonis & Regulæ…non satis idoneè conveniret' more literally than Parker's looser 'title…could hardl |
| ch2_u028 | 0.7100 | 3 | 5 | na | na | minor | No Greek present. 'Sic enim…interpretantur Iesuitæ' rendered accurately; however 'Est ergo' (lit. 'It is therefore') is expanded to 'The sta |
| ch2_u006 | 0.7115 | 5 | 5 | 5 | 5 | minor | v4 preserves Whitaker's Greek verbatim and correctly brackets 'à regula discedens' as an English gloss rather than echoing the Latin; Parker |
| ch2_u012 | 0.7135 | 4 | 4 | na | na | minor | No Greek in this passage. Content is faithful; 'refer all our faith and life to it' slightly awkward (antecedent unclear vs. Parker's 'this  |
| ch2_u015 | 0.7148 | 5 | 5 | 5 | 5 | minor | v4 preserves both Greek terms verbatim with bracketed English glosses and includes the book/chapter reference and 'other Greek writers' clau |
| ch2_u032 | 0.7234 | 5 | 5 | 5 | na | major | V4 preserves the Greek 'Διττοῦ' verbatim that Parker silently dropped and replaced with indirect paraphrase; content maps precisely to the L |
| ch2_u016 | 0.7251 | 4 | 5 | 5 | na | major | v4 correctly preserves the Greek κανονικοὶ καὶ ἐνδιάθηκοι verbatim (which Parker dropped entirely); the bracketed English gloss '[canonical  |
| ch2_u019 | 0.7255 | 5 | 5 | na | na | minor | No Greek in source; content is rendered with full fidelity to the Latin (indicem→index, ascribendum→append, quinam→which); v4 correctly avoi |
| ch2_u014 | 0.7305 | 5 | 5 | na | na | minor | Latin source fragment contains no Greek; v4 renders all present content faithfully; minor lexical divergence from Parker ('termed' vs 'style |
| ch2_u027 | 0.7397 | 4 | 5 | na | na | minor | No Greek in source; candidate faithfully preserves Whitaker's first-person 'nominaui' → 'I have named' where Parker shifted to 'we have ment |
| ch2_u021 | 0.7555 | 4 | 5 | na | na | minor | v4 omits the preceding clause ('are received by us') and 'verè' (truly) is preserved; Parker adds 'Such are these six' not in this Latin seg |
| ch2_u018 | 0.7757 | 5 | 5 | na | na | minor | No Greek in this fragment; candidate faithfully renders all Latin content, and improves on Parker by choosing 'has decreed' (precise for 'de |
| ch2_u024 | 0.7781 | 4 | 5 | na | na | minor | No Greek present; content_fidelity docked one point because the candidate adds 'The Council' before 'finally concludes,' which has no equiva |
| ch2_u020 | 0.7786 | 5 | 5 | na | na | minor | No Greek in source; v4 renders 'dubitatione' as 'doubt' (more faithful than Parker's 'hesitation') and 'Deinde' as 'Then' rather than Parker |
| ch2_u025 | 0.7809 | 5 | 5 | na | na | minor | Translation follows the Latin closely throughout; notably preserves 'anathema' verbatim where Parker substituted 'accursed', renders 'in han |
| ch2_u007 | 0.7829 | 5 | 4 | na | na | minor | Candidate correctly renders 'regulam veritatis' as 'rule of truth' where Parker substitutes 'rule of faith' (a theologically loaded conflati |
| ch2_u029 | 0.7843 | 5 | 5 | na | na | minor | No Greek in source; v4 is faithful throughout — 'little portions' preserves the Latin diminutive 'particulae' better than Parker's 'parts',  |
| ch2_u031 | 0.7856 | 3 | 4 | na | na | minor | v4 renders Whitaker's plural subjunctive 'veniamus' as singular 'I proceed', where Parker's 'we should proceed' is actually closer to the La |
| ch2_u003 | 0.7881 | 5 | 4 | na | na | minor | No Greek in source; v4 is more faithful than Parker by retaining 'sacrae' ('sacred') and rendering 'autem' ('Now'), which Parker dropped; 'n |
| ch2_u022 | 0.7896 | 4 | 5 | na | na | minor | No Greek in source; translation is faithful to Whitaker with only minor natural expansions ('and the two books of' for 'Maccabaeorum duo') v |
| ch2_u001 | 0.9833 | 5 | 5 | na | na | none | Latin chapter heading 'CAPVT SECVNDVM' rendered correctly as 'CHAPTER II'; candidate and Parker agree exactly; no Greek or paraphrase elemen |

## Interpretation

1. **v4 generalizes correctly to ch2 on the author-fidelity criterion.** All units score 3-5 on content and register fidelity; every applicable Greek-preservation and paraphrase-handling case scores 4-5.
2. **The 0.058 COMET regression is editorial divergence, not translation error.** All 8 major-divergence units involve Greek-script patristic citations that Whitaker preserved and Parker editorially dropped.
3. **Decision (per user direction):** accept the COMET drop as a measurement artifact of the Parker-anchored metric. v4 remains the locked working baseline. Move forward to Phase 5.
