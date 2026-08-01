"""Eval: the graph sustains the throughput SLO at scale."""

from __future__ import annotations

import time

from core import BasisConfig
from nexus import build_graph
from criteria import MIN_NODE_TICKS_PER_SEC


def test_throughput_meets_slo():
    cfg = BasisConfig.from_dict({
        "seed": 0,
        "graph": {"n_shards": 150, "nodes_per_shard": [2, 20], "n_shared_resources": 100},
        "signal": {"source": "generative", "encoding": "mi.8ch.mubeta.v1"},
        "fabric": {"policy": "lww"},
    })
    g = build_graph(cfg)
    n = g.n_nodes()
    g.tick()  # warm-up
    ticks = 3
    t0 = time.perf_counter()
    for _ in range(ticks):
        g.tick()
    elapsed = time.perf_counter() - t0
    node_ticks_per_sec = n * ticks / elapsed
    assert node_ticks_per_sec >= MIN_NODE_TICKS_PER_SEC, (
        f"{node_ticks_per_sec:,.0f} < SLO {MIN_NODE_TICKS_PER_SEC:,}"
    )


def test_wide_encoding_still_conforms_at_scale():
    # 256-float vectors (128ch x 2 bands) still validate through the pipeline.
    cfg = BasisConfig.from_dict({
        "seed": 1,
        "graph": {"n_shards": 20, "nodes_per_shard": [2, 6], "n_shared_resources": 10},
        "signal": {"source": "generative", "encoding": "mi.128ch.mubeta.v1"},
    })
    g = build_graph(cfg)
    r = g.run(3)[-1]
    assert r.n_nodes > 0
    assert r.fabric_metrics["commits"] > 0
