"""Tests for Basis Fabric pass-through seam."""

from __future__ import annotations

from fabric import Fabric


def test_passthrough_preserves_fifo_order():
    fab = Fabric()
    fab.submit({"node_id": "a", "n": 1})
    fab.submit({"node_id": "b", "n": 2})
    fab.submit({"node_id": "c", "n": 3})
    assert len(fab) == 3
    drained = fab.drain()
    assert [m["node_id"] for m in drained] == ["a", "b", "c"]
    assert len(fab) == 0


def test_drain_clears_queue():
    fab = Fabric()
    fab.submit({"node_id": "a"})
    fab.drain()
    assert fab.drain() == []
