"""One-off analysis: how many of ch1's cf<=3 units would the two proposed
validators (non-translation detection + numeral preservation) catch?

Loads the bridged input (Latin + English) and the judge scores, filters to
cf<=3, runs the heuristics, prints a breakdown by score bucket.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCORES = Path("08_working_scratch/phase3b/ch1_fidelity_scores.jsonl")
INPUTS = Path("08_working_scratch/phase3b/ch1_fidelity_input.jsonl")

# ---- non-translation detection ----
_TRIVIAL = {"—", "–", "-", ".", ",", ":", ";", "!", "?"}
_GREEK_RE = re.compile(r"[Ͱ-Ͽἀ-῿]")
_ASCII_AL = re.compile(r"[A-Za-z]")

def non_translation(latin: str, english: str) -> str | None:
    e = english.strip()
    if not e:
        return "empty"
    if e in _TRIVIAL:
        return "trivial-punct"
    # Only-Greek English when the Latin has substantial Latin letters
    eng_ascii = len(_ASCII_AL.findall(e))
    eng_greek = len(_GREEK_RE.findall(e))
    lat_ascii = len(_ASCII_AL.findall(latin))
    if eng_ascii == 0 and eng_greek > 0 and lat_ascii > 5:
        return "greek-without-gloss"
    # English is essentially the Latin source repeated (e.g. Greek copied)
    if e == latin.strip():
        return "source-repeated"
    return None

# ---- numeral preservation ----
# Latin ordinal stems -> integer.  Word-boundary + at least one trailing
# letter so 'non' (=not) and bare 'prim' don't collide.
ORD_STEMS = {
    "prim": 1, "secund": 2, "terti": 3, "quart": 4, "quint": 5,
    "sext": 6, "septim": 7, "octav": 8, "non": 9, "decim": 10,
    "undecim": 11, "duodecim": 12,
}
_ORD_RES = [(re.compile(rf"\b{s}\w+\b", re.IGNORECASE), n)
            for s, n in ORD_STEMS.items()]
# Roman numeral: any 2+ consecutive Roman letters (loose but bounded).
_ROMAN_RE = re.compile(r"\b[IVXLCDM]{2,}\b", re.IGNORECASE)

def roman_to_int(r: str) -> int:
    vals = {"I":1,"V":5,"X":10,"L":50,"C":100,"D":500,"M":1000}
    r = r.upper(); total = 0; prev = 0
    for ch in reversed(r):
        v = vals[ch]
        total += -v if v < prev else v
        prev = v
    return total

# Compound and simple number-word inventory
_TENS = {"twenty":20,"thirty":30,"forty":40,"fifty":50,"sixty":60,
         "seventy":70,"eighty":80,"ninety":90}
_ONES_ORD = {"first":1,"second":2,"third":3,"fourth":4,"fifth":5,
             "sixth":6,"seventh":7,"eighth":8,"ninth":9}
_ONES_CARD = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,
              "seven":7,"eight":8,"nine":9}
_SIMPLE = {**_ONES_CARD, **_ONES_ORD,
           "ten":10,"eleven":11,"twelve":12,"thirteen":13,"fourteen":14,
           "fifteen":15,"sixteen":16,"seventeen":17,"eighteen":18,
           "nineteen":19,"twenty":20,
           "tenth":10,"eleventh":11,"twelfth":12,"thirteenth":13,
           "fourteenth":14,"fifteenth":15,"sixteenth":16,
           "seventeenth":17,"eighteenth":18,"nineteenth":19,
           "twentieth":20,"thirtieth":30}

_TENS_RE = re.compile(
    r"\b(" + "|".join(_TENS) + r")[- ](\w+)\b", re.IGNORECASE)

def extract_english_numbers(english: str) -> set[int]:
    """All numbers present in the English: compound ordinals/cardinals,
    simple words, digits, Roman numerals. Compound matches are masked out
    first so 'twenty-eighth' contributes 28 (not 8 from 'eighth')."""
    e = english.lower()
    nums: set[int] = set()

    def _repl(m: re.Match) -> str:
        tens = _TENS[m.group(1).lower()]
        ones_w = m.group(2).lower()
        if ones_w in _ONES_ORD:
            nums.add(tens + _ONES_ORD[ones_w])
        elif ones_w in _ONES_CARD:
            nums.add(tens + _ONES_CARD[ones_w])
        else:
            return m.group(0)  # not a compound number; leave alone
        return " " * (m.end() - m.start())

    e_masked = _TENS_RE.sub(_repl, e)

    for m in re.finditer(r"\b(\d+)(?:st|nd|rd|th)?\b", e_masked):
        nums.add(int(m.group(1)))
    for w, n in _SIMPLE.items():
        if re.search(rf"\b{w}\b", e_masked):
            nums.add(n)
    for m in _ROMAN_RE.finditer(e_masked):
        try:
            v = roman_to_int(m.group(0))
            if v > 0:
                nums.add(v)
        except KeyError:
            pass
    return nums

def english_has_number(english: str, n: int) -> bool:
    return n in extract_english_numbers(english)

def numeral_check(latin: str, english: str) -> list[str]:
    """Return descriptions of Latin numerals/ordinals NOT carried into English."""
    misses = []
    seen = set()
    for rx, n in _ORD_RES:
        for m in rx.finditer(latin):
            key = (m.group(0).lower(), n)
            if key in seen:
                continue
            seen.add(key)
            if not english_has_number(english, n):
                misses.append(f"ordinal {m.group(0)}={n}")
    for m in _ROMAN_RE.finditer(latin):
        tok = m.group(0)
        try:
            n = roman_to_int(tok)
        except KeyError:
            continue
        if n <= 0:
            continue
        if (tok.lower(), n) in seen:
            continue
        seen.add((tok.lower(), n))
        if not english_has_number(english, n):
            misses.append(f"roman {tok}={n}")
    return misses


def main() -> int:
    inputs = {}
    for line in INPUTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line: continue
        r = json.loads(line)
        inputs[r["unit_id"]] = (r["latin_concat"], r["english_concat"])

    buckets = {1: [], 2: [], 3: []}
    for line in SCORES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line: continue
        r = json.loads(line)
        cf = (r.get("scores") or {}).get("content_fidelity")
        if not isinstance(cf, int) or cf > 3:
            continue
        uid = r["unit_id"]
        lat, eng = inputs.get(uid, ("", ""))
        nt = non_translation(lat, eng)
        nm = numeral_check(lat, eng)
        buckets[cf].append((uid, nt, nm))

    print(f"{'bucket':<10}{'n':>5}{'non-trans':>12}{'numeral':>10}"
          f"{'either':>10}{'neither':>10}")
    tot = {"n":0,"nt":0,"nm":0,"either":0,"neither":0}
    for cf in (1,2,3):
        b = buckets[cf]; n = len(b)
        nt = sum(1 for _,x,_ in b if x)
        nm = sum(1 for _,_,y in b if y)
        either = sum(1 for _,x,y in b if x or y)
        neither = n - either
        for k,v in (("n",n),("nt",nt),("nm",nm),("either",either),("neither",neither)):
            tot[k]+=v
        print(f"cf={cf:<8}{n:>5}{nt:>12}{nm:>10}{either:>10}{neither:>10}")
    print(f"{'TOTAL':<10}{tot['n']:>5}{tot['nt']:>12}{tot['nm']:>10}"
          f"{tot['either']:>10}{tot['neither']:>10}")

    print("\n--- catches in cf=1 (with reasons) ---")
    for uid, nt, nm in buckets[1]:
        if nt or nm:
            print(f"  {uid}  non-trans={nt}  numeral={nm}")
    print("\n--- cf=1 NOT caught by either ---")
    for uid, nt, nm in buckets[1]:
        if not nt and not nm:
            print(f"  {uid}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
