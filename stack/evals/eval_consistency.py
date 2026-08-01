"""Eval: Fabric consensus resolves contention deterministically per policy."""

from __future__ import annotations

import random

import pytest

from fabric import Fabric, Write
from criteria import CONSISTENCY_REPEATS


def _claims():
    # Three nodes contend for one shared resource "obj"; one contends for "obj2".
    return [
        Write(key="obj", value="s0_n1", node_id="s0_n1", ts=10, clock={"s0_n1": 1}),
        Write(key="obj", value="s1_n2", node_id="s1_n2", ts=12, clock={"s1_n2": 1}),
        Write(key="obj", value="s2_n0", node_id="s2_n0", ts=11, clock={"s2_n0": 1}),
        Write(key="obj2", value="s3_n0", node_id="s3_n0", ts=5, clock={"s3_n0": 1}),
    ]


@pytest.mark.parametrize("policy", ["lww", "vector_clock", "quorum", "crdt_merge"])
def test_resolution_is_order_independent(policy):
    results = []
    for _ in range(CONSISTENCY_REPEATS):
        fab = Fabric(policy=policy, replication_factor=1)
        claims = _claims()
        random.shuffle(claims)
        for w in claims:
            fab.propose(w)
        results.append(fab.commit())
    # Same committed state regardless of submission order.
    for r in results[1:]:
        assert r == results[0], policy


def test_lww_picks_latest_timestamp():
    fab = Fabric(policy="lww")
    for w in _claims():
        fab.propose(w)
    committed = fab.commit()
    assert committed["obj"] == "s1_n2"  # ts=12 is latest


def test_conflict_metrics_counted():
    fab = Fabric(policy="lww")
    for w in _claims():
        fab.propose(w)
    fab.commit()
    # "obj" had 3 distinct proposers -> 1 conflict key; "obj2" uncontended.
    assert fab.metrics["conflicts"] == 1
    assert fab.metrics["commits"] >= 1


def test_crdt_merge_is_commutative():
    fab = Fabric(policy="crdt_merge")
    for w in _claims():
        fab.propose(w)
    committed = fab.commit()
    # Deterministic commutative merge (max) over the contenders for "obj".
    assert committed["obj"] == max(["s0_n1", "s1_n2", "s2_n0"])


def test_quorum_requires_majority():
    fab = Fabric(policy="quorum", replication_factor=3)
    # Two replicas agree on value A, one on B -> A wins (majority).
    fab.propose(Write(key="k", value="A", node_id="r1", ts=1))
    fab.propose(Write(key="k", value="A", node_id="r2", ts=1))
    fab.propose(Write(key="k", value="B", node_id="r3", ts=2))
    committed = fab.commit()
    assert committed["k"] == "A"


def test_state_persists_across_commits():
    fab = Fabric(policy="lww")
    fab.propose(Write(key="k", value="v1", node_id="a", ts=1))
    fab.commit()
    fab.propose(Write(key="k", value="v2", node_id="b", ts=2))
    fab.commit()
    assert fab.state["k"].value == "v2"
