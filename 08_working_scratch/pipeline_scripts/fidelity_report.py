"""Per-chapter author-fidelity report from author_fidelity_judge.py output.

Aggregates ``ch*_fidelity_scores.jsonl`` into a reviewer-facing summary:
overall means per rubric, score distributions, per-page aggregates, and
the cf-low review list. Prints to stdout and writes a Markdown report.

Robust to the rare JSONDecodeError row where ``scores`` is null but the
raw judge response is recoverable (same approach as ablation_verdict.py).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_RUBRICS = ("content_fidelity", "register_fidelity",
            "greek_preservation", "paraphrase_handling")
_RUBRIC_SHORT = {"content_fidelity": "cf", "register_fidelity": "rf",
                 "greek_preservation": "gp", "paraphrase_handling": "ph"}


def _recover(raw: str, key: str):
    if not raw:
        return None
    m = re.search(rf'"{key}"\s*:\s*("?\w+"?)', raw)
    if not m:
        return None
    tok = m.group(1).strip('"')
    if tok.isdigit():
        return int(tok)
    if tok.lower() == "na":
        return "na"
    return None


def _page_of(uid: str) -> int | None:
    m = re.search(r"p(\d+)", uid or "")
    return int(m.group(1)) if m else None


def load_scores(path: Path, start: int | None, end: int | None) -> list[dict]:
    rows: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        rec = json.loads(raw)
        uid = str(rec.get("unit_id") or "")
        pn = _page_of(uid)
        if start is not None and (pn is None or pn < start):
            continue
        if end is not None and (pn is None or pn > end):
            continue
        scores = rec.get("scores") or {}
        # Recover from raw if scores is missing (JSON parse failure)
        if not scores and rec.get("raw"):
            scores = {k: _recover(rec["raw"], k) for k in _RUBRICS}
            scores = {k: v for k, v in scores.items() if v is not None}
        rows.append({
            "unit_id": uid, "page": pn,
            "cf": scores.get("content_fidelity"),
            "rf": scores.get("register_fidelity"),
            "gp": scores.get("greek_preservation"),
            "ph": scores.get("paraphrase_handling"),
            "reason": rec.get("reason") or "",
            "error": rec.get("error"),
        })
    return rows


def _intvals(rows: list[dict], key: str) -> list[int]:
    return [r[key] for r in rows if isinstance(r[key], int)]


def _aggregate_table(rows: list[dict]) -> str:
    lines = ["| Rubric | Mean | Min | Max | n (scored) | na | err |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for rk in _RUBRICS:
        short = _RUBRIC_SHORT[rk]
        vals = _intvals(rows, short)
        na = sum(1 for r in rows if r[short] == "na")
        err = sum(1 for r in rows if r[short] is None)
        m = f"{mean(vals):.3f}" if vals else "—"
        mn = min(vals) if vals else "—"
        mx = max(vals) if vals else "—"
        lines.append(f"| {rk} | {m} | {mn} | {mx} | {len(vals)} | {na} | {err} |")
    return "\n".join(lines)


def _distribution_table(rows: list[dict]) -> str:
    lines = ["| Rubric | 1 | 2 | 3 | 4 | 5 | na |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for rk in _RUBRICS:
        short = _RUBRIC_SHORT[rk]
        c: Counter = Counter()
        for r in rows:
            v = r[short]
            if v == "na":
                c["na"] += 1
            elif isinstance(v, int):
                c[v] += 1
        lines.append(f"| {rk} | {c[1]} | {c[2]} | {c[3]} | {c[4]} | {c[5]} | {c['na']} |")
    return "\n".join(lines)


def _per_page_table(rows: list[dict]) -> str:
    by: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        if r["page"] is not None:
            by[r["page"]].append(r)
    lines = ["| Page | n | cf mean | rf mean | gp (when applic.) | ph (when applic.) |",
             "|---|---:|---:|---:|---:|---:|"]
    for pn in sorted(by):
        prows = by[pn]
        cf = _intvals(prows, "cf"); rf = _intvals(prows, "rf")
        gp = _intvals(prows, "gp"); ph = _intvals(prows, "ph")
        cm = f"{mean(cf):.2f}" if cf else "—"
        rm = f"{mean(rf):.2f}" if rf else "—"
        gm = f"{mean(gp):.2f} (n={len(gp)})" if gp else "—"
        pm = f"{mean(ph):.2f} (n={len(ph)})" if ph else "—"
        lines.append(f"| p{pn:04d} | {len(prows)} | {cm} | {rm} | {gm} | {pm} |")
    return "\n".join(lines)


def _low_cf_table(rows: list[dict], threshold: int = 3) -> tuple[str, int]:
    lows = [r for r in rows if isinstance(r["cf"], int) and r["cf"] <= threshold]
    lows.sort(key=lambda r: (r["cf"], r["page"] or 0, r["unit_id"]))
    if not lows:
        return ("_(none)_", 0)
    lines = ["| Unit | cf | rf | gp | ph | Reason |",
             "|---|---:|---:|---:|---:|---|"]
    for r in lows:
        reason = (r["reason"] or "").replace("|", "\\|").replace("\n", " ")
        reason = reason[:200] + ("…" if len(reason) > 200 else "")
        lines.append(f"| {r['unit_id']} | {r['cf']} | {r['rf']} | "
                     f"{r['gp']} | {r['ph']} | {reason} |")
    return ("\n".join(lines), len(lows))


def build_report(rows: list[dict], *, label: str,
                 source: Path, start: int | None, end: int | None) -> str:
    rng = ""
    if start is not None or end is not None:
        rng = f" — pages {start}–{end}"
    parts = [f"# Author-Fidelity Report — {label}{rng}", "",
             f"Source: `{source}`  ", f"Units: **{len(rows)}**", ""]
    parts += ["## Aggregate scores", "", _aggregate_table(rows), ""]
    parts += ["## Score distribution", "", _distribution_table(rows), ""]
    parts += ["## Per-page aggregates", "", _per_page_table(rows), ""]
    low_table, n_low = _low_cf_table(rows)
    parts += [f"## Content-fidelity review queue (cf ≤ 3) — {n_low} unit(s)",
              "", low_table, ""]
    return "\n".join(parts) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scores-jsonl", required=True, type=Path)
    p.add_argument("--label", required=True,
                   help="report header label, e.g. 'Chapter 1 (ussher_v5)'")
    p.add_argument("--output", required=True, type=Path,
                   help="path to write the Markdown report")
    p.add_argument("--start-page", type=int, default=None)
    p.add_argument("--end-page", type=int, default=None)
    args = p.parse_args()

    rows = load_scores(args.scores_jsonl, args.start_page, args.end_page)
    md = build_report(rows, label=args.label, source=args.scores_jsonl,
                      start=args.start_page, end=args.end_page)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")

    cf = _intvals(rows, "cf"); rf = _intvals(rows, "rf")
    gp = _intvals(rows, "gp"); ph = _intvals(rows, "ph")
    n_low = sum(1 for r in rows if isinstance(r["cf"], int) and r["cf"] <= 3)
    print(f"Wrote {args.output}  ({len(rows)} units)")
    print(f"  cf mean {mean(cf):.3f}  rf mean {mean(rf):.3f}  "
          f"gp {mean(gp):.2f} (n={len(gp)})  ph {mean(ph):.2f} (n={len(ph)})")
    print(f"  cf<=3 review queue: {n_low}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
