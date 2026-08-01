"""Basis Fabric: distributed state consensus engine.

Fabric is the consistency layer beneath Basis Locus. When many node authorities
propose writes to shared state (e.g. two nodes claiming the same resource in the
same tick), Fabric resolves the conflict deterministically according to a
pluggable policy, so every observer agrees on one committed state.

Policies:
- ``lww``          last-write-wins by timestamp (tie-break: greater node_id).
- ``vector_clock`` causal ordering; concurrent writes tie-break by node_id.
- ``quorum``       a value commits only with a majority of the replication factor.
- ``crdt_merge``   commutative merge (max), inherently order-independent.

Fabric never interprets a neural vector (the opaque-vector rule); it operates on
explicit state writes with keys, values, timestamps, and vector clocks. All
policies are deterministic and order-independent given explicit metadata, which
is what the consistency evals assert.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

Clock = Dict[str, int]


@dataclass
class Write:
    """A proposed write to shared state.

    Attributes:
        key: The state key being written (e.g. a shared resource id).
        value: The proposed value (e.g. the claiming node id).
        node_id: The proposing authority/node.
        ts: A logical/physical timestamp (unix ms or tick counter).
        clock: Optional vector clock for causal resolution.
    """

    key: str
    value: Any
    node_id: str
    ts: int = 0
    clock: Optional[Clock] = None


@dataclass
class Record:
    """A committed state record."""

    value: Any
    ts: int
    node_id: str
    clock: Clock = field(default_factory=dict)


def _merge_clocks(*clocks: Optional[Clock]) -> Clock:
    merged: Clock = {}
    for c in clocks:
        if not c:
            continue
        for k, v in c.items():
            merged[k] = max(merged.get(k, 0), v)
    return merged


def _dominates(a: Clock, b: Clock) -> bool:
    """True if clock a causally dominates b (a >= b on all keys, and a != b)."""
    a = a or {}
    b = b or {}
    keys = set(a) | set(b)
    ge = all(a.get(k, 0) >= b.get(k, 0) for k in keys)
    gt = any(a.get(k, 0) > b.get(k, 0) for k in keys)
    return ge and gt


class Fabric:
    """Distributed state consensus engine with pluggable resolution policies.

    Args:
        policy: One of ``lww``/``vector_clock``/``quorum``/``crdt_merge``.
        replication_factor: Number of replicas per key (used by ``quorum``).
        trace: Optional Basis TRACE recorder; if given, commit is timed.
    """

    POLICIES = ("lww", "vector_clock", "quorum", "crdt_merge")

    def __init__(self, policy: str = "lww", *, replication_factor: int = 1, trace: Optional[Any] = None) -> None:
        if policy not in self.POLICIES:
            raise ValueError(f"unknown policy {policy!r}; expected one of {self.POLICIES}")
        self.policy = policy
        self.replication_factor = replication_factor
        self._trace = trace
        self.state: Dict[str, Record] = {}
        self._pending: List[Write] = []
        self.metrics: Dict[str, int] = {"commits": 0, "conflicts": 0, "unresolved": 0}

    def propose(self, write: Write) -> None:
        """Queue a write for the next commit."""
        self._pending.append(write)

    def commit(self) -> Dict[str, Any]:
        """Resolve all pending writes per policy; update and return committed state.

        Returns a mapping of key -> committed value for keys touched this commit.
        """
        if self._trace is not None:
            with self._trace.span("fabric", "commit", meta={"pending": len(self._pending)}):
                return self._commit()
        return self._commit()

    def _commit(self) -> Dict[str, Any]:
        by_key: Dict[str, List[Write]] = defaultdict(list)
        for w in self._pending:
            by_key[w.key].append(w)
        self._pending = []

        committed: Dict[str, Any] = {}
        for key, writes in by_key.items():
            distinct_proposers = {w.node_id for w in writes}
            if len(distinct_proposers) > 1:
                self.metrics["conflicts"] += 1
            record = self._resolve(key, writes)
            if record is None:
                self.metrics["unresolved"] += 1
                continue
            self.state[key] = record
            committed[key] = record.value
            self.metrics["commits"] += 1
        return committed

    def _resolve(self, key: str, writes: List[Write]) -> Optional[Record]:
        current = self.state.get(key)
        if self.policy == "lww":
            candidates = writes + ([_write_of(current, key)] if current else [])
            best = max(candidates, key=lambda w: (w.ts, str(w.node_id)))
            return Record(best.value, best.ts, best.node_id, best.clock or {})

        if self.policy == "crdt_merge":
            values = [w.value for w in writes] + ([current.value] if current else [])
            merged = max(values)
            ts = max([w.ts for w in writes] + ([current.ts] if current else [0]))
            clock = _merge_clocks(*[w.clock for w in writes], current.clock if current else None)
            winner = max([w for w in writes], key=lambda w: (str(w.value), str(w.node_id)))
            return Record(merged, ts, winner.node_id, clock)

        if self.policy == "vector_clock":
            candidates = list(writes) + ([_write_of(current, key)] if current else [])
            # Keep only writes not dominated by another (the causal frontier).
            frontier = [
                w for w in candidates
                if not any(_dominates(o.clock or {}, w.clock or {}) for o in candidates if o is not w)
            ]
            best = max(frontier, key=lambda w: str(w.node_id))
            clock = _merge_clocks(*[w.clock for w in candidates])
            return Record(best.value, best.ts, best.node_id, clock)

        if self.policy == "quorum":
            need = self.replication_factor // 2 + 1
            counts: Dict[Any, int] = defaultdict(int)
            for w in writes:
                counts[w.value] += 1
            if current is not None:
                counts[current.value] += 0  # current does not vote, but may persist
            eligible = {v: c for v, c in counts.items() if c >= need}
            if not eligible:
                return current  # no majority: state unchanged (persists if present)
            value = max(eligible, key=lambda v: (eligible[v], str(v)))
            rep = max([w for w in writes if w.value == value], key=lambda w: (w.ts, str(w.node_id)))
            return Record(value, rep.ts, rep.node_id, rep.clock or {})

        raise AssertionError(f"unhandled policy {self.policy}")

    def snapshot(self) -> Dict[str, Any]:
        """Return the committed value of every key."""
        return {k: r.value for k, r in self.state.items()}


def _write_of(record: Record, key: str) -> Write:
    return Write(key=key, value=record.value, node_id=record.node_id, ts=record.ts, clock=record.clock)
