"""Eval: the graph runs multi-shard and ramps scale while preserving invariants."""

from __future__ import annotations

from core import BasisConfig
from nexus import build_graph


def _cfg(n_shards=10, policy="lww", seed=0):
    return BasisConfig.from_dict({
        "seed": seed,
        "graph": {"n_shards": n_shards, "nodes_per_shard": [2, 20], "n_shared_resources": 8},
        "signal": {"source": "generative", "encoding": "mi.8ch.mubeta.v1"},
        "fabric": {"policy": policy},
    })


def test_multi_shard_runs_and_produces_consensus():
    g = build_graph(_cfg(n_shards=20))
    results = g.run(5)
    assert results[-1].n_shards == 20
    assert results[-1].n_nodes >= 40
    # With more nodes than shared resources, Fabric resolves real contention.
    assert results[-1].fabric_metrics["conflicts"] > 0
    # Every shared resource has exactly one committed holder.
    assert len(results[-1].holders) <= 8


def test_dynamic_ramp_up_and_down():
    g = build_graph(_cfg(n_shards=5))
    n0 = g.n_nodes()
    g.tick()
    # Ramp up mid-run.
    for _ in range(10):
        g.add_shard()
    assert len(g.shards) == 15
    new_node = g.add_node(g.shards[0].index)
    assert new_node is not None
    up = g.tick()
    assert up.n_nodes > n0

    # Ramp down mid-run.
    assert g.remove_node(new_node)
    assert g.remove_shard(g.shards[-1].index)
    down = g.tick()
    assert down.n_shards == 14


def test_determinism_same_seed_same_holders():
    a = build_graph(_cfg(seed=3)).run(4)[-1].holders
    b = build_graph(_cfg(seed=3)).run(4)[-1].holders
    assert a == b


def test_summary_is_machine_readable():
    g = build_graph(_cfg(n_shards=3))
    g.tick()
    s = g.summary()
    assert set(["tick", "n_shards", "n_nodes", "policy", "fabric_metrics"]).issubset(s)
