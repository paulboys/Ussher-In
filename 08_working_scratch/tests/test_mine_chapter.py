"""Tests for the per-chapter mining harness.

The harness itself just wires the miner into the curator, so the only logic
worth pinning is boundary resolution: a known chapter key must map to its
inclusive page span, and a custom span must demand explicit --start/--end.
"""
from __future__ import annotations

import argparse

import mine_chapter as h
import pytest


def _args(**kw):
    ns = argparse.Namespace(start=None, end=None, name=None)
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def test_known_chapter_resolves_to_its_span():
    name, start, end, label = h._resolve("ch2", _args())
    assert (name, start, end) == ("ch2", 46, 68)
    assert "Chapter 2" in label


def test_chapter_table_spans_are_ordered_and_inclusive():
    # every single-chapter entry is a forward, non-empty inclusive range
    for key, (start, end, _label) in h.CHAPTERS.items():
        assert start <= end, key


def test_custom_span_needs_start_and_end():
    with pytest.raises(SystemExit):
        h._resolve("ch99", _args())


def test_custom_span_uses_name_and_range():
    name, start, end, label = h._resolve(
        "whatever", _args(start=100, end=120, name="lucius"))
    assert (name, start, end) == ("lucius", 100, 120)
    assert "100" in label and "120" in label


def test_custom_span_default_name_from_pages():
    name, start, end, _ = h._resolve("x", _args(start=100, end=120))
    assert name == "p0100_0120"
