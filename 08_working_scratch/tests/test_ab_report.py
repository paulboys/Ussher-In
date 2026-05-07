"""Tests for the A/B aggregator + decision gate.

Builds tiny synthetic A/B trees in tmp_path so every test exercises
discovery, mechanical scoring, judge pooling, and the verdict gate
end-to-end.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ab_report = pytest.importorskip(
    "ab_report",
    reason="A/B helper scripts are not present in this branch.",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seg(seg_id: str, english: str, latin: str = "Hinc Arnobius dixit.") -> dict:
    return {
        "segment_id": seg_id,
        "page_id": "p9999",
        "segment_type": "body",
        "latin_text": latin,
        "markers": [],
        "translation_history": [
            {
                "version": 1,
                "stage": "machine_draft",
                "english": english,
                "notes": "",
                "uncertain": False,
                "model": "claude-opus-4-7",
                "lexicon_profile": "auto",
            }
        ],
        "final_english": "",
        "translation_status": "machine_draft",
    }


def _write_run(base: Path, version: str, run_tag: str, records) -> Path:
    run_dir = base / version / run_tag
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "segments_with_translations.jsonl"
    with path.open("w", encoding="utf-8") as h:
        for r in records:
            h.write(json.dumps(r) + "\n")
    return path


def _write_judgments(base: Path, name: str, judgments) -> Path:
    jdir = base / "judgments"
    jdir.mkdir(parents=True, exist_ok=True)
    path = jdir / name
    with path.open("w", encoding="utf-8") as h:
        for j in judgments:
            h.write(json.dumps(j) + "\n")
    return path


def _judgment(seg_id: str, *, swapped: bool, raw_winner: str,
              decoded_winner: str, decoded_rubric: dict | None = None,
              error: str = "") -> dict:
    return {
        "segment_id": seg_id,
        "swapped": swapped,
        "latin": "x",
        "a_text": "a",
        "b_text": "b",
        "raw_winner": raw_winner,
        "raw_rubric": {},
        "reason": "",
        "decoded_winner": decoded_winner,
        "decoded_rubric": decoded_rubric or {},
        "error": error,
    }


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def test_discover_runs_finds_both_versions(tmp_path: Path):
    _write_run(tmp_path, "v0", "run01", [_seg("a", "x")])
    _write_run(tmp_path, "v0", "run02", [_seg("a", "x")])
    _write_run(tmp_path, "v1", "run01", [_seg("a", "x")])
    runs = ab_report.discover_runs(tmp_path)
    assert sorted((r.version, r.run_tag) for r in runs) == [
        ("v0", "run01"), ("v0", "run02"), ("v1", "run01"),
    ]


def test_discover_runs_skips_dirs_without_jsonl(tmp_path: Path):
    (tmp_path / "v0" / "empty").mkdir(parents=True)
    runs = ab_report.discover_runs(tmp_path)
    assert runs == []


def test_discover_judgments_finds_files(tmp_path: Path):
    _write_judgments(tmp_path, "run01.jsonl", [])
    _write_judgments(tmp_path, "run02.jsonl", [])
    paths = ab_report.discover_judgments(tmp_path)
    assert len(paths) == 2


# ---------------------------------------------------------------------------
# Mechanical pooling
# ---------------------------------------------------------------------------


def test_pool_rule_counts_sums_across_runs(tmp_path: Path):
    _write_run(tmp_path, "v0", "run01", [
        _seg("a", "He hath spoken."),     # archaism
        _seg("b", "Boadicia rebelled."),  # proper_noun
    ])
    _write_run(tmp_path, "v0", "run02", [
        _seg("a", "He doth speak."),      # archaism
    ])
    runs = ab_report.discover_runs(tmp_path)
    ab_report.score_runs_mechanical(runs)
    pooled = ab_report.pool_rule_counts(runs, "v0")
    assert pooled.get("archaism") == 2
    assert pooled.get("proper_noun") == 1


def test_normalize_rule_counts_is_per_segment(tmp_path: Path):
    """3 archaisms across 6 segments should normalize to 0.5/seg."""
    _write_run(tmp_path, "v0", "run01", [
        _seg("a", "He hath spoken."),
        _seg("b", "He doth speak."),
        _seg("c", "modern prose."),
    ])
    _write_run(tmp_path, "v0", "run02", [
        _seg("a", "verily, I say."),
        _seg("b", "modern."),
        _seg("c", "modern."),
    ])
    runs = ab_report.discover_runs(tmp_path)
    ab_report.score_runs_mechanical(runs)
    pooled = ab_report.pool_rule_counts(runs, "v0")
    rate = ab_report.normalize_rule_counts(pooled, runs, "v0")
    assert rate["archaism"] == pytest.approx(3 / 6)


# ---------------------------------------------------------------------------
# Judgment loading + pooling
# ---------------------------------------------------------------------------


def test_load_judgments_counts_a_b_tie(tmp_path: Path):
    path = _write_judgments(tmp_path, "x.jsonl", [
        _judgment("s1", swapped=False, raw_winner="A", decoded_winner="v0"),
        _judgment("s2", swapped=True,  raw_winner="A", decoded_winner="v1"),
        _judgment("s3", swapped=False, raw_winner="B", decoded_winner="v1"),
        _judgment("s4", swapped=False, raw_winner="tie", decoded_winner="tie"),
        _judgment("s5", swapped=False, raw_winner="?", decoded_winner="invalid"),
        _judgment("s6", swapped=False, raw_winner="", decoded_winner="",
                  error="judge call failed"),
    ])
    batch = ab_report.load_judgments(path)
    assert batch.a_picked == 2
    assert batch.b_picked == 1
    assert batch.tie == 1
    assert batch.invalid == 1
    assert batch.error == 1


def test_pool_judgments_aggregates_across_batches(tmp_path: Path):
    p1 = _write_judgments(tmp_path, "j1.jsonl", [
        _judgment("s1", swapped=False, raw_winner="A", decoded_winner="v0",
                  decoded_rubric={"fluency": "v0"}),
        _judgment("s2", swapped=True,  raw_winner="A", decoded_winner="v1",
                  decoded_rubric={"fluency": "v1"}),
    ])
    p2 = _write_judgments(tmp_path, "j2.jsonl", [
        _judgment("s3", swapped=False, raw_winner="B", decoded_winner="v1",
                  decoded_rubric={"fluency": "v1"}),
    ])
    batches = [ab_report.load_judgments(p1), ab_report.load_judgments(p2)]
    pool = ab_report.pool_judgments(batches)
    assert pool["overall"]["v1"] == 2
    assert pool["overall"]["v0"] == 1
    assert pool["a_picked"] == 2
    assert pool["b_picked"] == 1
    assert pool["rubric"]["fluency"]["v1"] == 2


# ---------------------------------------------------------------------------
# Decision gate
# ---------------------------------------------------------------------------


def _good_pool(*, n: int = 100, v1: int = 60, v0: int = 20, tie: int = 20,
               a_picks: int = 50, b_picks: int = 50) -> dict:
    """Build a synthetic judge pool that satisfies all five gates."""
    return {
        "n": n,
        "overall": {"v0": v0, "v1": v1, "tie": tie, "invalid": 0, "error": 0},
        "a_picked": a_picks,
        "b_picked": b_picks,
        "rubric": {
            rk: {"v0": 1, "v1": 5, "equal": 1, "invalid": 0}
            for rk in ("fluency", "accuracy", "proper_nouns", "titles", "register")
        },
    }


def test_verdict_pass_when_all_gates_met():
    v = ab_report.evaluate_verdict(
        rule_delta={"archaism": -0.05, "proper_noun": -0.10},
        judge_pool=_good_pool(),
    )
    assert v.label == "PASS"


def test_verdict_fail_on_mechanical_regression():
    v = ab_report.evaluate_verdict(
        rule_delta={"archaism": +0.10},
        judge_pool=_good_pool(),
    )
    assert v.label == "FAIL"
    assert any("mechanical regression" in r for r in v.reasons)


def test_verdict_fail_on_low_win_rate():
    pool = _good_pool(v1=40, v0=40, tie=20)  # 40 % win-rate
    v = ab_report.evaluate_verdict(rule_delta={}, judge_pool=pool)
    assert v.label == "FAIL"
    assert any("win-rate" in r for r in v.reasons)


def test_verdict_fail_on_high_tie_rate():
    pool = _good_pool(v1=55, v0=10, tie=35)  # 35 % tie-rate
    v = ab_report.evaluate_verdict(rule_delta={}, judge_pool=pool)
    assert v.label == "FAIL"
    assert any("tie-rate" in r for r in v.reasons)


def test_verdict_fail_on_rubric_loss():
    pool = _good_pool()
    pool["rubric"]["fluency"] = {"v0": 5, "v1": 1, "equal": 1, "invalid": 0}
    v = ab_report.evaluate_verdict(rule_delta={}, judge_pool=pool)
    assert v.label == "FAIL"
    assert any("rubric" in r and "fluency" in r for r in v.reasons)


def test_verdict_fail_on_position_bias():
    pool = _good_pool(a_picks=70, b_picks=30)  # 20 pp bias
    v = ab_report.evaluate_verdict(rule_delta={}, judge_pool=pool)
    assert v.label == "FAIL"
    assert any("position bias" in r for r in v.reasons)


def test_verdict_insufficient_when_no_judgments():
    v = ab_report.evaluate_verdict(rule_delta={}, judge_pool={"n": 0})
    assert v.label == "INSUFFICIENT"


def test_verdict_insufficient_on_high_invalid_rate():
    pool = _good_pool(n=100)
    pool["overall"]["invalid"] = 12  # 12 % invalid -> gate 5 trips
    v = ab_report.evaluate_verdict(rule_delta={}, judge_pool=pool)
    assert v.label == "INSUFFICIENT"


# ---------------------------------------------------------------------------
# End-to-end: build_summary + render_markdown
# ---------------------------------------------------------------------------


def test_build_summary_end_to_end_pass(tmp_path: Path):
    # Two v0 runs (more archaisms), two v1 runs (clean prose).
    _write_run(tmp_path, "v0", "run01", [
        _seg("a", "He hath spoken."),
        _seg("b", "Boadicia rebelled."),
    ])
    _write_run(tmp_path, "v0", "run02", [
        _seg("a", "He doth speak."),
        _seg("b", "Boadicia rebelled."),
    ])
    _write_run(tmp_path, "v1", "run01", [
        _seg("a", "He spoke clearly."),
        _seg("b", "Boudica rebelled."),
    ])
    _write_run(tmp_path, "v1", "run02", [
        _seg("a", "He spoke."),
        _seg("b", "Boudica rebelled."),
    ])
    # Construct judgments that satisfy gates.
    judgments = []
    for i in range(60):
        judgments.append(_judgment(
            f"s{i:03d}", swapped=(i % 2 == 0),
            raw_winner=("A" if i % 2 == 0 else "B"),
            decoded_winner="v1",
            decoded_rubric={
                "fluency": "v1", "accuracy": "v1", "proper_nouns": "v1",
                "titles": "v1", "register": "v1",
            },
        ))
    for i in range(60, 80):
        judgments.append(_judgment(
            f"s{i:03d}", swapped=(i % 2 == 0),
            raw_winner=("B" if i % 2 == 0 else "A"),
            decoded_winner="v0",
            decoded_rubric={"fluency": "v0", "accuracy": "v0",
                            "proper_nouns": "v0", "titles": "v0",
                            "register": "v0"},
        ))
    for i in range(80, 100):
        judgments.append(_judgment(
            f"s{i:03d}", swapped=False, raw_winner="tie",
            decoded_winner="tie",
            decoded_rubric={"fluency": "equal", "accuracy": "equal",
                            "proper_nouns": "equal", "titles": "equal",
                            "register": "equal"},
        ))
    _write_judgments(tmp_path, "run01.jsonl", judgments)

    runs = ab_report.discover_runs(tmp_path)
    paths = ab_report.discover_judgments(tmp_path)
    batches = [ab_report.load_judgments(p) for p in paths]
    summary = ab_report.build_summary(base_dir=tmp_path, runs=runs, batches=batches)

    assert summary["verdict"]["label"] == "PASS"
    # v1 should have negative deltas on archaism and proper_noun.
    delta = summary["mechanical"]["delta_per_segment_v1_minus_v0"]
    assert delta.get("archaism", 0) < 0
    assert delta.get("proper_noun", 0) < 0

    md = ab_report.render_markdown(summary, page="p9999")
    assert "Verdict:** **PASS**" in md
    assert "## Mechanical" in md
    assert "## Judge — pooled" in md


def test_render_markdown_marks_mechanical_regression(tmp_path: Path):
    _write_run(tmp_path, "v0", "run01", [_seg("a", "modern.")])
    _write_run(tmp_path, "v1", "run01", [_seg("a", "He hath spoken.")])
    runs = ab_report.discover_runs(tmp_path)
    summary = ab_report.build_summary(base_dir=tmp_path, runs=runs, batches=[])
    md = ab_report.render_markdown(summary, page="p9999")
    # v1 has +1.000/seg archaism (regression). Should be flagged with ⚠.
    assert "⚠" in md
    # Without judgments, verdict is INSUFFICIENT.
    assert "INSUFFICIENT" in md
