"""Eval: the metrics lens and reproducible raw logs."""

from __future__ import annotations

from core import BasisConfig
from nexus import build_graph
from trace import Lens, Trace, message_bytes


def test_lens_latency_percentiles_and_bandwidth():
    trace = Trace()
    for i in range(50):
        with trace.span("brain", "emit", node_id="n"):
            pass
        trace.record("snp", "wire", bytes=120 + i)
    lens = Lens.from_trace(trace)
    summ = lens.latency_summary()
    assert summ["emit"]["count"] == 50
    for k in ("mean_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"):
        assert k in summ["emit"]
    bw = lens.bandwidth()
    assert bw["total_bytes"] > 0 and bw["messages"] == 50


def test_lens_reads_jsonl(tmp_path):
    path = tmp_path / "trace.jsonl"
    trace = Trace(jsonl_path=path)
    for _ in range(5):
        trace.record("nexus", "tick", latency_ms=1.0)
    lens = Lens.from_jsonl(path)
    assert lens.latency_summary()["tick"]["count"] == 5


def test_message_bytes_is_positive():
    msg = {"node_id": "n", "timestamp": 1, "signal_type": "motor",
           "payload": {"vector": [0.1] * 6, "confidence": 1.0,
                       "paradigm": "p", "encoding": "mi.c3czc4.mubeta.v1"}}
    assert message_bytes(msg) > 20


def test_raw_run_logs_are_reproducible(tmp_path):
    cfg = BasisConfig.from_dict({
        "seed": 11,
        "graph": {"n_shards": 6, "nodes_per_shard": [2, 8], "n_shared_resources": 5},
        "signal": {"encoding": "mi.8ch.mubeta.v1"},
    })
    a = tmp_path / "run_a.jsonl"
    b = tmp_path / "run_b.jsonl"
    g1 = build_graph_with_log(cfg, str(a))
    g1.run(8)
    g1.close()
    g2 = build_graph_with_log(cfg, str(b))
    g2.run(8)
    g2.close()
    assert a.read_text() == b.read_text()  # same seed -> identical raw logs


def build_graph_with_log(cfg, path):
    from nexus.graph import Graph

    return Graph(cfg, run_log_path=path)
