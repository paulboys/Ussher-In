from __future__ import annotations

import annals_chunked_comet_score as score


def _segment(line_id: str, english: str, latin: str | None = None) -> score.RunSegment:
    return score.RunSegment(
        segment_id=f"seg_{line_id}",
        line_id=line_id,
        page_id=line_id.split("_", 1)[0],
        seq=int(line_id.rsplit("l", 1)[-1]),
        latin=latin if latin is not None else f"latin {line_id}",
        english=english,
    )


def _reference(line_id: str, text: str) -> score.ReferenceLine:
    return score.ReferenceLine(
        page_id=line_id.split("_", 1)[0],
        line_id=line_id,
        text=text,
        source_text=text,
    )


def test_normalize_tokens_handles_early_modern_spellings():
    assert score.normalize_tokens("Cae\u017far & C\u00e6sar") == [
        "caesar",
        "and",
        "caesar",
    ]


def test_bridge_mapping_is_monotonic_and_interpolates_empty_lines():
    bridge = [
        _segment("p0001_body_l0001", "Cyrene and Crete were granted"),
        _segment("p0001_body_l0002", ""),
        _segment("p0001_body_l0003", "Cassius and Bithynia"),
        _segment("p0001_body_l0004", "Appian book four"),
    ]
    refs = [
        _reference("p1000_body_l0001", "Cyrene and the Isle of Crete"),
        _reference("p1000_body_l0002", "Cassius and Bithynia"),
        _reference("p1000_body_l0003", "Appian lib. 4"),
    ]

    mapping, votes = score.map_bridge_to_reference(bridge, refs)

    assert len(mapping) == len(bridge)
    assert mapping == sorted(mapping)
    assert mapping[0] == 0
    assert mapping[-1] == 2
    assert votes[1] == 0


def test_build_chunks_uses_reference_windows_and_source_continuity():
    bridge = [
        _segment("p0001_body_l0001", "a"),
        _segment("p0001_body_l0002", "b"),
        _segment("p0001_body_l0003", "c"),
        _segment("p0001_body_l0004", "d"),
    ]
    refs = [
        _reference("p1000_body_l0001", "a"),
        _reference("p1000_body_l0002", "b"),
        _reference("p1000_body_l0003", "c"),
        _reference("p1000_body_l0004", "d"),
    ]

    chunks = score.build_chunks(
        bridge,
        refs,
        mapping=[0, 1, 2, 3],
        chunk_ref_lines=2,
    )

    assert [chunk.chunk_id for chunk in chunks] == [
        "annals_chunk_001",
        "annals_chunk_002",
    ]
    assert chunks[0].latin_line_ids == ["p0001_body_l0001", "p0001_body_l0002"]
    assert chunks[1].reference_line_ids == [
        "p1000_body_l0003",
        "p1000_body_l0004",
    ]


def test_summarize_no_score_marks_rows_pending_not_errored():
    chunk = score.Chunk(
        chunk_id="annals_chunk_001",
        latin_line_ids=["p0001_body_l0001"],
        segment_ids=["seg_p0001_body_l0001"],
        reference_line_ids=["p1000_body_l0001"],
        latin_concat="latin",
        bridge_english_concat="machine",
        reference_concat="reference",
        latin_start_index=0,
        latin_end_index=0,
        reference_start_index=0,
        reference_end_index=0,
    )
    rows = [
        {"chunk_id": "annals_chunk_001", "run": "run01", "score": None},
        {"chunk_id": "annals_chunk_001", "run": "run02", "score": None},
    ]

    summary = score.summarize_scores(
        rows,
        chunks=[chunk],
        model="Unbabel/wmt22-comet-da",
        no_score=True,
    )

    assert summary["run_summaries"]["run01"]["n_pending"] == 1
    assert summary["run_summaries"]["run01"]["n_errored"] == 0
