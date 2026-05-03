"""Tests for the anonymized A/B judge.

The CLI transport is mocked via a callable judge so the tests run
offline and are deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ab_judge


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


def _write_jsonl(path: Path, records) -> None:
    with path.open("w", encoding="utf-8") as h:
        for r in records:
            h.write(json.dumps(r) + "\n")


# ---------------------------------------------------------------------------
# Side-swap + decode
# ---------------------------------------------------------------------------


def test_assign_swap_is_deterministic_per_seed():
    seg = "seg_p0039_body_l0001"
    a = ab_judge.assign_swap(seg, seed=0)
    b = ab_judge.assign_swap(seg, seed=0)
    assert a == b


def test_assign_swap_changes_with_seed():
    """Different seeds must (with high probability) flip at least one
    segment's assignment in a small set."""
    segs = [f"seg_{i}" for i in range(20)]
    s0 = [ab_judge.assign_swap(s, seed=0) for s in segs]
    s1 = [ab_judge.assign_swap(s, seed=1) for s in segs]
    assert s0 != s1


def test_decode_winner_no_swap():
    assert ab_judge.decode_winner("A", swapped=False) == "v0"
    assert ab_judge.decode_winner("B", swapped=False) == "v1"
    assert ab_judge.decode_winner("tie", swapped=False) == "tie"


def test_decode_winner_swapped():
    assert ab_judge.decode_winner("A", swapped=True) == "v1"
    assert ab_judge.decode_winner("B", swapped=True) == "v0"


def test_decode_winner_invalid_returns_invalid():
    assert ab_judge.decode_winner("Q", swapped=False) == "invalid"
    assert ab_judge.decode_winner("", swapped=True) == "invalid"


def test_decode_rubric_round_trips_when_unswapped():
    rubric = {"fluency": "A", "accuracy": "B", "register": "equal"}
    out = ab_judge.decode_rubric(rubric, swapped=False)
    assert out == {"fluency": "v0", "accuracy": "v1", "register": "equal"}


def test_decode_rubric_inverts_when_swapped():
    rubric = {"fluency": "A", "accuracy": "B", "register": "equal"}
    out = ab_judge.decode_rubric(rubric, swapped=True)
    assert out == {"fluency": "v1", "accuracy": "v0", "register": "equal"}


# ---------------------------------------------------------------------------
# Prompt + parser
# ---------------------------------------------------------------------------


def test_build_judge_prompt_contains_both_candidates_and_latin():
    prompt = ab_judge.build_judge_prompt(
        segment_id="seg1",
        latin="Hinc Arnobius dixit.",
        a_text="Hence Arnobius said.",
        b_text="Hence said Arnobius.",
    )
    assert "Hinc Arnobius dixit." in prompt
    assert "Hence Arnobius said." in prompt
    assert "Hence said Arnobius." in prompt
    assert "Translation A:" in prompt and "Translation B:" in prompt
    # Output contract is appended verbatim and forbids code fences.
    assert '"winner"' in prompt


def test_parse_judge_response_accepts_clean_json():
    raw = json.dumps({
        "rubric": {"fluency": "A", "accuracy": "A", "proper_nouns": "equal",
                   "titles": "equal", "register": "A"},
        "winner": "A",
        "reason": "A is more idiomatic.",
    })
    parsed = ab_judge.parse_judge_response(raw)
    assert parsed["winner"] == "A"
    assert parsed["rubric"]["fluency"] == "A"


def test_parse_judge_response_strips_code_fence():
    payload = {"rubric": {}, "winner": "tie", "reason": "x"}
    raw = "```json\n" + json.dumps(payload) + "\n```"
    parsed = ab_judge.parse_judge_response(raw)
    assert parsed["winner"] == "tie"


def test_parse_judge_response_rejects_non_object():
    with pytest.raises(ValueError):
        ab_judge.parse_judge_response("not json")
    with pytest.raises(ValueError):
        ab_judge.parse_judge_response("[1,2,3]")
    with pytest.raises(ValueError):
        ab_judge.parse_judge_response('{"winner": "A"}')  # missing rubric


# ---------------------------------------------------------------------------
# judge_pair end-to-end (with a mock judge callable)
# ---------------------------------------------------------------------------


def _judge_callable_returning(payload: dict):
    """Build a JudgeCallable that always returns the same JSON."""
    raw = json.dumps(payload)

    def call(_prompt: str) -> str:
        return raw

    return call


def test_judge_pair_decodes_v1_when_judge_picks_v1_unswapped():
    """When swap=False: A=v0, B=v1. Judge picks B -> decoded v1."""
    seg_id = "seg_for_no_swap"
    # Find a seg_id that hashes to no-swap so we don't have to mock.
    for candidate in (f"seg_{i:04d}" for i in range(200)):
        if not ab_judge.assign_swap(candidate, seed=0):
            seg_id = candidate
            break
    assert ab_judge.assign_swap(seg_id, seed=0) is False

    call = _judge_callable_returning({
        "rubric": {"fluency": "B", "accuracy": "B", "proper_nouns": "B",
                   "titles": "equal", "register": "B"},
        "winner": "B",
        "reason": "B is more modern.",
    })
    j = ab_judge.judge_pair(
        segment_id=seg_id,
        latin="Hinc Arnobius dixit.",
        v0_text="He hath spoken.",
        v1_text="He spoke.",
        seed=0,
        call_judge=call,
    )
    assert j.error == ""
    assert j.swapped is False
    assert j.decoded_winner == "v1"
    # Rubric: B verdict -> v1 (since swap=False)
    assert j.decoded_rubric["fluency"] == "v1"
    assert j.decoded_rubric["titles"] == "equal"


def test_judge_pair_decodes_v1_when_judge_picks_a_swapped():
    """When swap=True: A=v1, B=v0. Judge picks A -> decoded v1."""
    seg_id = "seg_for_swap"
    for candidate in (f"seg_{i:04d}" for i in range(200)):
        if ab_judge.assign_swap(candidate, seed=0):
            seg_id = candidate
            break
    assert ab_judge.assign_swap(seg_id, seed=0) is True

    call = _judge_callable_returning({
        "rubric": {"fluency": "A", "accuracy": "A", "proper_nouns": "equal",
                   "titles": "equal", "register": "A"},
        "winner": "A",
        "reason": "A is more modern.",
    })
    j = ab_judge.judge_pair(
        segment_id=seg_id,
        latin="Hinc Arnobius dixit.",
        v0_text="He hath spoken.",
        v1_text="He spoke.",
        seed=0,
        call_judge=call,
    )
    assert j.error == ""
    assert j.swapped is True
    assert j.decoded_winner == "v1"
    assert j.decoded_rubric["fluency"] == "v1"


def test_judge_pair_records_parse_error():
    call = lambda _p: "not json at all"  # noqa: E731
    j = ab_judge.judge_pair(
        segment_id="s1", latin="x", v0_text="a", v1_text="b",
        seed=0, call_judge=call,
    )
    assert "parse failed" in j.error


def test_judge_pair_records_call_error():
    def boom(_p: str) -> str:
        raise RuntimeError("connection refused")

    j = ab_judge.judge_pair(
        segment_id="s1", latin="x", v0_text="a", v1_text="b",
        seed=0, call_judge=boom,
    )
    assert "judge call failed" in j.error


# ---------------------------------------------------------------------------
# judge_run end-to-end
# ---------------------------------------------------------------------------


def test_judge_run_pairs_only_shared_segments(tmp_path: Path):
    v0_path = tmp_path / "v0.jsonl"
    v1_path = tmp_path / "v1.jsonl"
    _write_jsonl(v0_path, [_seg("a", "He hath spoken."),
                           _seg("b", "Boadicia rebelled."),
                           _seg("c_only_v0", "x")])
    _write_jsonl(v1_path, [_seg("a", "He spoke."),
                           _seg("b", "Boudica rebelled."),
                           _seg("d_only_v1", "y")])

    # Always-tie judge so we just verify pairing + counts.
    call = _judge_callable_returning({
        "rubric": {"fluency": "equal", "accuracy": "equal",
                   "proper_nouns": "equal", "titles": "equal",
                   "register": "equal"},
        "winner": "tie",
        "reason": "no difference.",
    })
    judgments = ab_judge.judge_run(
        v0_path=v0_path, v1_path=v1_path, call_judge=call, seed=0,
    )
    assert sorted(j.segment_id for j in judgments) == ["a", "b"]
    assert all(j.decoded_winner == "tie" for j in judgments)


def test_judge_run_marks_missing_english(tmp_path: Path):
    v0 = tmp_path / "v0.jsonl"
    v1 = tmp_path / "v1.jsonl"
    _write_jsonl(v0, [_seg("a", "")])      # empty english on v0
    _write_jsonl(v1, [_seg("a", "He spoke.")])

    call = _judge_callable_returning({
        "rubric": {"fluency": "equal", "accuracy": "equal",
                   "proper_nouns": "equal", "titles": "equal",
                   "register": "equal"},
        "winner": "tie",
        "reason": "x",
    })
    judgments = ab_judge.judge_run(
        v0_path=v0, v1_path=v1, call_judge=call, seed=0,
    )
    assert len(judgments) == 1
    assert judgments[0].error == "missing english on one side"


def test_aggregate_judgments_counts_correctly():
    j1 = ab_judge.Judgment(segment_id="a", swapped=False, a_text="", b_text="",
                           latin="", decoded_winner="v1",
                           decoded_rubric={"fluency": "v1", "titles": "equal"})
    j2 = ab_judge.Judgment(segment_id="b", swapped=True, a_text="", b_text="",
                           latin="", decoded_winner="v0",
                           decoded_rubric={"fluency": "v0", "titles": "v0"})
    j3 = ab_judge.Judgment(segment_id="c", swapped=False, a_text="", b_text="",
                           latin="", decoded_winner="tie",
                           decoded_rubric={"fluency": "equal"})
    j4 = ab_judge.Judgment(segment_id="d", swapped=False, a_text="", b_text="",
                           latin="", error="boom")

    summary = ab_judge.aggregate_judgments([j1, j2, j3, j4])
    assert summary["n"] == 4
    assert summary["overall"] == {"v0": 1, "v1": 1, "tie": 1, "invalid": 0,
                                  "error": 1}
    assert summary["rubric"]["fluency"]["v1"] == 1
    assert summary["rubric"]["fluency"]["v0"] == 1
    assert summary["rubric"]["fluency"]["equal"] == 1
    assert summary["rubric"]["titles"]["v0"] == 1
    assert summary["rubric"]["titles"]["equal"] == 1
