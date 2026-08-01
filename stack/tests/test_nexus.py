"""Tests for the Basis Nexus signal loop (synthetic brains, no network)."""

from __future__ import annotations

import math

import snp
from brain import Brain
from brain_helpers import synthetic_epochs
from locus import Locus
from nexus import Nexus
from trace import Trace


def _nexus(n_nodes=3, trace=None):
    brains = [Brain(f"brain_{i+1}", synthetic_epochs(6), trace=trace) for i in range(n_nodes)]
    locus = Locus(trace=trace)
    for i, b in enumerate(brains):
        locus.add_node(b.node_id, 2.0 + i, 5.0, heading=0.0)
    return Nexus(brains, locus, trace=trace), brains


def test_tick_returns_snapshot_and_perceptions():
    nexus, brains = _nexus(3)
    result = nexus.tick()
    assert result.tick == 0
    assert set(result.snapshot.keys()) == {b.node_id for b in brains}
    assert set(result.perceptions.keys()) == {b.node_id for b in brains}
    # Every perception is a valid SNP perception message.
    for msg in result.perceptions.values():
        v = snp.validate(msg)
        assert v.payload.encoding == "env.room.pose_visible.v1"
    # Every outbound signal is a valid motor message.
    for msg in result.signals.values():
        assert snp.is_valid(msg)


def test_run_advances_ticks_and_moves_world():
    nexus, brains = _nexus(3)
    results = nexus.run(10)
    assert [r.tick for r in results] == list(range(10))
    # At least one node should have moved from its start over 10 ticks.
    start = results[0].snapshot
    end = results[-1].snapshot
    moved = any(
        math.hypot(end[nid][0] - start[nid][0], end[nid][1] - start[nid][1]) > 1e-6
        for nid in start
    )
    assert moved


def test_trace_observes_every_stage():
    trace = Trace()
    nexus, _ = _nexus(2, trace=trace)
    nexus.tick()
    events = {r.event for r in trace.records}
    for stage in ("emit", "decode", "apply", "perceive", "tick"):
        assert stage in events, stage
