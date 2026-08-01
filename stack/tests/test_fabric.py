"""Tests for Basis Fabric consensus engine (unit level)."""

from __future__ import annotations

import pytest

from fabric import Fabric, Write


def test_lww_latest_wins_and_persists():
    fab = Fabric(policy="lww")
    fab.propose(Write("k", "a", "n1", ts=1))
    fab.propose(Write("k", "b", "n2", ts=3))
    fab.propose(Write("k", "c", "n3", ts=2))
    committed = fab.commit()
    assert committed["k"] == "b"
    assert fab.state["k"].value == "b"
    assert fab.metrics["conflicts"] == 1


def test_uncontended_is_not_a_conflict():
    fab = Fabric(policy="lww")
    fab.propose(Write("k", "a", "n1", ts=1))
    fab.commit()
    assert fab.metrics["conflicts"] == 0
    assert fab.metrics["commits"] == 1


def test_unknown_policy_rejected():
    with pytest.raises(ValueError):
        Fabric(policy="nope")


def test_snapshot_reflects_committed_state():
    fab = Fabric(policy="crdt_merge")
    fab.propose(Write("a", "x", "n1", ts=1))
    fab.propose(Write("b", "y", "n2", ts=1))
    fab.commit()
    assert fab.snapshot() == {"a": "x", "b": "y"}
