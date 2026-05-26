"""Compute §7.3 exemplar-injection ablation verdict.

Reads v5_base and v5_ex fidelity_scores.jsonl, extracts content_fidelity
(cf) and register_fidelity (rf) per unit, recovers scores from a row's
`raw` blob if a JSONDecodeError left `scores` null, computes group means
and per-unit deltas, and applies the >= 0.10 acceptance gate.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path("04_translation_work/ab/p0036/ussher_v5/v5_base/fidelity_scores.jsonl")
EX = Path("04_translation_work/ab/p0036/ussher_v5_exemplars/v5_ex/fidelity_scores.jsonl")
GATE = 0.10


def _recover(raw: str, key: str):
    m = re.search(rf'"{key}"\s*:\s*("?\w+"?)', raw or "")
    if not m:
        return None
    tok = m.group(1).strip('"')
    return int(tok) if tok.isdigit() else None


def load(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        scores = rec.get("scores") or {}
        cf = scores.get("content_fidelity")
        rf = scores.get("register_fidelity")
        if cf is None and rec.get("raw"):
            cf = _recover(rec["raw"], "content_fidelity")
        if rf is None and rec.get("raw"):
            rf = _recover(rec["raw"], "register_fidelity")
        out[rec["unit_id"]] = {"cf": cf, "rf": rf}
    return out


def mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else float("nan")


def main() -> int:
    base = load(BASE)
    ex = load(EX)

    shared = sorted(set(base) & set(ex))
    print(f"base units: {len(base)}  ex units: {len(ex)}  shared: {len(shared)}")
    missing_base = sorted(set(ex) - set(base))
    missing_ex = sorted(set(base) - set(ex))
    if missing_base:
        print(f"  in ex only: {missing_base}")
    if missing_ex:
        print(f"  in base only: {missing_ex}")

    base_cf = [base[u]["cf"] for u in shared if base[u]["cf"] is not None]
    base_rf = [base[u]["rf"] for u in shared if base[u]["rf"] is not None]
    ex_cf = [ex[u]["cf"] for u in shared if ex[u]["cf"] is not None]
    ex_rf = [ex[u]["rf"] for u in shared if ex[u]["rf"] is not None]

    print("\n=== group means (shared units) ===")
    print(f"content_fidelity : base {mean(base_cf):.3f}  ex {mean(ex_cf):.3f}  "
          f"delta {mean(ex_cf) - mean(base_cf):+.3f}")
    print(f"register_fidelity: base {mean(base_rf):.3f}  ex {mean(ex_rf):.3f}  "
          f"delta {mean(ex_rf) - mean(base_rf):+.3f}")

    print("\n=== per-unit changes (cf, rf) ===")
    for u in shared:
        b, e = base[u], ex[u]
        dcf = (e["cf"] - b["cf"]) if (e["cf"] is not None and b["cf"] is not None) else None
        drf = (e["rf"] - b["rf"]) if (e["rf"] is not None and b["rf"] is not None) else None
        if dcf or drf:
            print(f"  {u}: cf {b['cf']}->{e['cf']} ({dcf:+d})  "
                  f"rf {b['rf']}->{e['rf']} ({drf:+d})")

    dcf = mean(ex_cf) - mean(base_cf)
    drf = mean(ex_rf) - mean(base_rf)
    best = max(dcf, drf)
    print(f"\n=== VERDICT (gate >= {GATE:+.2f} on cf OR rf) ===")
    print(f"cf delta {dcf:+.3f} | rf delta {drf:+.3f} | best {best:+.3f}")
    if best >= GATE:
        print("ACCEPT: exemplars earn their place; keep the fork.")
    else:
        print("REJECT: gain below gate; ablate the fork, keep plain ussher_v5.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
