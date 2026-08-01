"""Eval: the viz collector captures coherent, deterministic dashboard data."""

from __future__ import annotations

from core import BasisConfig
from viz import collect

CFG = BasisConfig.from_dict({
    "seed": 0,
    "ticks": 12,
    "graph": {"n_shards": 6, "nodes_per_shard": [2, 6], "n_shared_resources": 4},
    "signal": {"source": "generative", "encoding": "mi.8ch.mubeta.v1"},
    "fabric": {"policy": "lww"},
})


def test_collector_captures_all_levels():
    c = collect(CFG)
    assert len(c.frames) == 12
    f = c.frames[-1]
    # micro: focus-shard node signals with decoded actions.
    assert f.focus_signals, "expected focus-shard signals"
    any_sig = next(iter(f.focus_signals.values()))
    assert len(any_sig["vector"]) == 16  # mi.8ch.mubeta.v1
    assert any_sig["action"] in ("left", "right", "forward")
    # meso: room snapshot for the focus shard.
    assert f.focus_room and all(len(v) == 3 for v in f.focus_room.values())
    # macro: ownership matrix (resources x ticks) + conflicts series.
    matrix = c.ownership_matrix()
    assert len(matrix) == len(c.resources)
    assert all(len(row) == len(c.frames) for row in matrix)
    assert len(c.conflict_series()) == 12
    # metrics: lens summary present.
    assert "latency" in c.metrics


def test_collector_is_deterministic():
    a = collect(CFG)
    b = collect(CFG)
    assert a.conflict_series() == b.conflict_series()
    assert [f.holders for f in a.frames] == [f.holders for f in b.frames]


def test_focus_shard_is_single_room():
    c = collect(CFG)
    shards = {f.focus_shard for f in c.frames}
    assert shards == {0}  # focus is stable on the first shard
