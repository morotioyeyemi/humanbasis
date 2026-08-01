"""Tests for Basis TRACE recorder."""

from __future__ import annotations

import json
import time

from trace import Trace


def test_record_appends_and_reads():
    trace = Trace()
    trace.record("brain", "emit", node_id="brain_1", bytes=128)
    assert len(trace.records) == 1
    rec = trace.records[0]
    assert rec.component == "brain"
    assert rec.event == "emit"
    assert rec.node_id == "brain_1"
    assert rec.bytes == 128
    assert isinstance(rec.t_unix_ms, int)


def test_span_measures_latency():
    trace = Trace()
    with trace.span("brain", "work", node_id="brain_1"):
        time.sleep(0.005)
    rec = trace.records[0]
    assert rec.event == "work"
    assert rec.latency_ms is not None and rec.latency_ms >= 4.0


def test_jsonl_backing(tmp_path):
    path = tmp_path / "trace.jsonl"
    trace = Trace(jsonl_path=path)
    trace.record("snp", "validate")
    trace.record("brain", "emit")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["component"] == "snp"


def test_as_dicts_and_clear():
    trace = Trace()
    trace.record("brain", "emit")
    assert trace.as_dicts()[0]["event"] == "emit"
    trace.clear()
    assert trace.records == []
