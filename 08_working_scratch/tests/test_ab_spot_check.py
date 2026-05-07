"""Tests for the Phase 5 spot-check picker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

sc = pytest.importorskip(
    "ab_spot_check",
    reason="A/B helper scripts are not present in this branch.",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _judgment(
    seg_id: str,
    *,
    swapped: bool,
    a_text: str,
    b_text: str,
    latin: str,
    decoded_winner: str,
    decoded_rubric: dict,
    reason: str = "because",
    error: str = "",
) -> dict:
    return {
        "segment_id": seg_id,
        "swapped": swapped,
        "a_text": a_text,
        "b_text": b_text,
        "latin": latin,
        "raw_winner": "A" if (decoded_winner == "v0" and not swapped) or (decoded_winner == "v1" and swapped) else "B",
        "raw_rubric": {},
        "reason": reason,
        "decoded_winner": decoded_winner,
        "decoded_rubric": decoded_rubric,
        "error": error,
    }


def _write(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as h:
        for r in records:
            h.write(json.dumps(r) + "\n")


@pytest.fixture
def ab_tree(tmp_path: Path) -> Path:
    """Build a small ab/<page> tree with three pairings.

    Segments:
      seg_swing_v1: v1 wins all 3, dominates rubrics (max swing toward v1).
      seg_swing_v0: v0 wins all 3, dominates rubrics (max swing toward v0).
      seg_tied_a:   1 v0 / 1 v1 / 1 tie -> pooled v0==v1, mild swing.
      seg_tied_b:   1 v0 / 1 v1 / 1 tie -> pooled v0==v1.
      seg_mixed:    2 v1 / 1 v0, modest swing.
    """
    base = tmp_path / "ab" / "p9999"
    jdir = base / "judgments"

    rubric_v1 = {r: "v1" for r in sc.RUBRICS}
    rubric_v0 = {r: "v0" for r in sc.RUBRICS}
    rubric_eq = {r: "equal" for r in sc.RUBRICS}
    rubric_mix = {"fluency": "v1", "accuracy": "v0", "proper_nouns": "equal", "titles": "equal", "register": "v1"}

    pairings = {
        "run01": [
            _judgment("seg_swing_v1", swapped=False, a_text="v0-1", b_text="v1-1", latin="L1", decoded_winner="v1", decoded_rubric=rubric_v1),
            _judgment("seg_swing_v0", swapped=True,  a_text="v1-1", b_text="v0-1", latin="L2", decoded_winner="v0", decoded_rubric=rubric_v0),
            _judgment("seg_tied_a",   swapped=False, a_text="v0-1", b_text="v1-1", latin="L3", decoded_winner="v0", decoded_rubric=rubric_mix),
            _judgment("seg_tied_b",   swapped=True,  a_text="v1-1", b_text="v0-1", latin="L4", decoded_winner="v1", decoded_rubric=rubric_mix),
            _judgment("seg_mixed",    swapped=False, a_text="v0-1", b_text="v1-1", latin="L5", decoded_winner="v1", decoded_rubric=rubric_mix),
        ],
        "run02": [
            _judgment("seg_swing_v1", swapped=True,  a_text="v1-2", b_text="v0-2", latin="L1", decoded_winner="v1", decoded_rubric=rubric_v1),
            _judgment("seg_swing_v0", swapped=False, a_text="v0-2", b_text="v1-2", latin="L2", decoded_winner="v0", decoded_rubric=rubric_v0),
            _judgment("seg_tied_a",   swapped=False, a_text="v0-2", b_text="v1-2", latin="L3", decoded_winner="v1", decoded_rubric=rubric_mix),
            _judgment("seg_tied_b",   swapped=False, a_text="v0-2", b_text="v1-2", latin="L4", decoded_winner="v0", decoded_rubric=rubric_mix),
            _judgment("seg_mixed",    swapped=True,  a_text="v1-2", b_text="v0-2", latin="L5", decoded_winner="v1", decoded_rubric=rubric_mix),
        ],
        "run03": [
            _judgment("seg_swing_v1", swapped=False, a_text="v0-3", b_text="v1-3", latin="L1", decoded_winner="v1", decoded_rubric=rubric_v1),
            _judgment("seg_swing_v0", swapped=False, a_text="v0-3", b_text="v1-3", latin="L2", decoded_winner="v0", decoded_rubric=rubric_v0),
            _judgment("seg_tied_a",   swapped=True,  a_text="v1-3", b_text="v0-3", latin="L3", decoded_winner="equal", decoded_rubric=rubric_eq),
            _judgment("seg_tied_b",   swapped=True,  a_text="v1-3", b_text="v0-3", latin="L4", decoded_winner="equal", decoded_rubric=rubric_eq),
            _judgment("seg_mixed",    swapped=False, a_text="v0-3", b_text="v1-3", latin="L5", decoded_winner="v0", decoded_rubric=rubric_mix),
        ],
    }
    for name, recs in pairings.items():
        _write(jdir / f"{name}.jsonl", recs)
    # Also drop a stray *_summary.json to confirm the glob excludes it.
    (jdir / "run01_summary.json").write_text("{}", encoding="utf-8")
    return base


# ---------------------------------------------------------------------------
# Loading + decoding
# ---------------------------------------------------------------------------


def test_load_judgment_rows_uses_pair_stem_and_excludes_summary(ab_tree: Path):
    rows = sc.load_judgment_rows(ab_tree / "judgments")
    pair_names = {r.pair_name for r in rows}
    assert pair_names == {"run01", "run02", "run03"}
    assert len(rows) == 15  # 5 segments x 3 pairings


def test_v0_v1_text_respects_swap(ab_tree: Path):
    rows = sc.load_judgment_rows(ab_tree / "judgments")
    swap_row = next(r for r in rows if r.swapped)
    nosw_row = next(r for r in rows if not r.swapped)
    # When swapped, A=v1 and B=v0
    assert swap_row.v1_text == swap_row.a_text
    assert swap_row.v0_text == swap_row.b_text
    # When not swapped, A=v0 and B=v1
    assert nosw_row.v0_text == nosw_row.a_text
    assert nosw_row.v1_text == nosw_row.b_text


# ---------------------------------------------------------------------------
# Pooling + selection
# ---------------------------------------------------------------------------


def test_pool_aggregates_three_pairings(ab_tree: Path):
    rows = sc.load_judgment_rows(ab_tree / "judgments")
    pools = sc.pool_by_segment(rows)
    assert set(pools) == {"seg_swing_v1", "seg_swing_v0", "seg_tied_a", "seg_tied_b", "seg_mixed"}
    assert all(len(p.pairings) == 3 for p in pools.values())
    assert pools["seg_swing_v1"].n_v1() == 3
    assert pools["seg_swing_v0"].n_v0() == 3
    assert pools["seg_tied_a"].n_v0() == pools["seg_tied_a"].n_v1() == 1
    assert pools["seg_tied_a"].n_tie() == 1


def test_rubric_swing_signs(ab_tree: Path):
    pools = sc.pool_by_segment(sc.load_judgment_rows(ab_tree / "judgments"))
    # 3 pairings * 5 rubrics, all v1 -> +15
    assert pools["seg_swing_v1"].rubric_swing() == 15
    assert pools["seg_swing_v0"].rubric_swing() == -15
    # mixed rubric: per pairing v1=2, v0=1, equal=2 -> +1; x3 -> +3
    assert pools["seg_mixed"].rubric_swing() == 3


def test_pick_high_swing_orders_by_abs_swing(ab_tree: Path):
    pools = sc.pool_by_segment(sc.load_judgment_rows(ab_tree / "judgments"))
    swing = sc.pick_high_swing(pools, n=3)
    assert [p.segment_id for p in swing] == ["seg_swing_v0", "seg_swing_v1", "seg_mixed"]


def test_pick_tied_excludes_swing_and_only_pooled_ties(ab_tree: Path):
    pools = sc.pool_by_segment(sc.load_judgment_rows(ab_tree / "judgments"))
    swing = sc.pick_high_swing(pools, n=2)
    tied = sc.pick_tied(pools, n=10, seed=0, exclude={p.segment_id for p in swing})
    ids = {p.segment_id for p in tied}
    assert ids == {"seg_tied_a", "seg_tied_b"}
    # seg_mixed is 2v1/1v0 -> not pooled-tied
    assert "seg_mixed" not in ids
    # No overlap with swing bucket
    assert ids.isdisjoint({p.segment_id for p in swing})


def test_pick_tied_is_deterministic_for_seed(ab_tree: Path):
    pools = sc.pool_by_segment(sc.load_judgment_rows(ab_tree / "judgments"))
    a = [p.segment_id for p in sc.pick_tied(pools, n=2, seed=0, exclude=set())]
    b = [p.segment_id for p in sc.pick_tied(pools, n=2, seed=0, exclude=set())]
    assert a == b


# ---------------------------------------------------------------------------
# Rendering + CLI
# ---------------------------------------------------------------------------


def test_render_markdown_contains_picks_and_form(ab_tree: Path):
    md, swing, tied = sc.build(
        ab_tree, page="p9999", n_swing=2, n_tied=2, seed=0
    )
    assert "# A/B spot-check — p9999" in md
    assert "## High-swing picks" in md
    assert "## Tied picks" in md
    assert "**Reviewer verdict:**" in md
    assert "**Latin source:**" in md
    # Greek-handling rule preamble is included for the human reviewer.
    assert "embedded Greek" in md
    assert "Latin paraphrase" in md
    assert "id est" in md
    # Both buckets actually rendered.
    for pool in swing + tied:
        assert pool.segment_id in md
    # v0 / v1 labels appear unswapped regardless of judge swap.
    assert "**v0:**" in md
    assert "**v1:**" in md


def test_main_writes_default_output(tmp_path, ab_tree: Path):
    rc = sc.main([str(ab_tree), "--n-swing", "2", "--n-tied", "1", "--seed", "0"])
    assert rc == 0
    out = ab_tree / "spot_check.md"
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "spot-check" in text.lower()
    assert "seg_swing_v0" in text  # highest |swing|
