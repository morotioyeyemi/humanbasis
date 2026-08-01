"""Basis graph: a sharded, multi-authority world.

The world is partitioned into many Locus shards (each a small room with a few
nodes). Nodes contend for a pool of globally shared resources; concurrent claims
in the same tick are resolved by Basis Fabric per the configured consensus
policy. This is where the distributed-consistency thesis becomes real: many
authorities, one consistent committed state.

The graph is mutable at runtime (add/remove shards and nodes) so scale can be
ramped up or down while the simulation runs.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from brain import Brain, GenerativeBrain
from core import BasisConfig, rng_for
from fabric import Fabric, Write
from locus import Locus


def _stable_index(text: str, mod: int) -> int:
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big") % max(mod, 1)


@dataclass
class Shard:
    """One Locus authority and the nodes it hosts."""

    index: int
    locus: Locus
    brains: List[Any] = field(default_factory=list)

    def node_ids(self) -> List[str]:
        return [b.node_id for b in self.brains]


@dataclass
class GraphTickResult:
    """Outcome of one graph tick."""

    tick: int
    n_shards: int
    n_nodes: int
    holders: Dict[str, Any]
    conflicts_this_tick: int
    fabric_metrics: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic, JSON-serializable form (no wall-clock)."""
        return {
            "tick": self.tick,
            "n_shards": self.n_shards,
            "n_nodes": self.n_nodes,
            "holders": {k: self.holders[k] for k in sorted(self.holders)},
            "conflicts_this_tick": self.conflicts_this_tick,
            "fabric_metrics": dict(self.fabric_metrics),
        }


class Graph:
    """A sharded, multi-authority world driven through Fabric.

    Args:
        config: The run configuration (graph shape, signal, fabric, seed).
        trace: Optional Basis TRACE recorder passed to every component.
        fabric: Optional preconstructed Fabric (else built from config).
    """

    def __init__(self, config: BasisConfig, *, trace: Optional[Any] = None, fabric: Optional[Fabric] = None,
                 run_log_path: Optional[str] = None) -> None:
        self.config = config.validate()
        self._trace = trace
        self.fabric = fabric or Fabric(
            config.fabric.policy, replication_factor=config.fabric.replication_factor, trace=trace
        )
        self.shards: List[Shard] = []
        self._tick = 0
        self._next_shard_index = 0
        self._encodings = config.signal.modalities or [config.signal.encoding]
        self._run_log_path = run_log_path or config.log.raw_log_path
        self._run_log = None
        if self._run_log_path:
            import io
            from pathlib import Path as _Path

            _Path(self._run_log_path).parent.mkdir(parents=True, exist_ok=True)
            self._run_log = open(self._run_log_path, "w", encoding="utf-8")  # noqa: SIM115
        for _ in range(config.graph.n_shards):
            self.add_shard()

    # --- structure (dynamic at runtime) -----------------------------------
    def add_shard(self) -> Shard:
        """Add a new shard with a seed-determined number of nodes."""
        idx = self._next_shard_index
        self._next_shard_index += 1
        locus = Locus(size=self.config.graph.room_size, trace=self._trace)
        shard = Shard(index=idx, locus=locus)
        self.shards.append(shard)
        lo, hi = self.config.graph.nodes_per_shard
        count = int(rng_for(self.config.seed, "shard_count", idx).integers(lo, hi + 1))
        for i in range(count):
            self._add_node_to(shard, i)
        return shard

    def remove_shard(self, index: int) -> bool:
        """Remove the shard with the given index. Returns True if removed."""
        for i, shard in enumerate(self.shards):
            if shard.index == index:
                del self.shards[i]
                return True
        return False

    def add_node(self, shard_index: int) -> Optional[str]:
        """Add one node to a shard at runtime; returns its node id."""
        for shard in self.shards:
            if shard.index == shard_index:
                return self._add_node_to(shard, len(shard.brains)).node_id
        return None

    def remove_node(self, node_id: str) -> bool:
        """Remove a node by id from wherever it lives. Returns True if removed."""
        for shard in self.shards:
            for i, b in enumerate(shard.brains):
                if b.node_id == node_id:
                    del shard.brains[i]
                    shard.locus.room.poses.pop(node_id, None)
                    return True
        return False

    def _add_node_to(self, shard: Shard, i: int):
        node_id = f"s{shard.index}_n{i}"
        encoding = self._encodings[self._stable_encoding_index(node_id)]
        brain = self._make_brain(node_id, encoding)
        shard.brains.append(brain)
        rng = rng_for(self.config.seed, "place", node_id)
        size = self.config.graph.room_size
        shard.locus.add_node(node_id, float(rng.uniform(0, size)), float(rng.uniform(0, size)),
                             heading=float(rng.uniform(-3.14159, 3.14159)))
        return brain

    def _stable_encoding_index(self, node_id: str) -> int:
        return _stable_index(node_id, len(self._encodings))

    def _make_brain(self, node_id: str, encoding: str):
        if self.config.signal.source == "replay":
            subjects = self.config.signal.replay_subjects
            subject = subjects[_stable_index(node_id, len(subjects))]
            return Brain.from_subject(node_id, subject=subject, encoding=encoding, trace=self._trace)
        return GenerativeBrain(node_id, encoding=encoding, seed=self.config.seed, trace=self._trace)

    # --- runtime ----------------------------------------------------------
    def _resource_of(self, node_id: str) -> str:
        return f"res_{_stable_index(node_id, self.config.graph.n_shared_resources)}"

    def tick(self) -> GraphTickResult:
        """Run one graph tick: per-shard signal loops + Fabric consensus."""
        conflicts_before = self.fabric.metrics["conflicts"]
        n_nodes = 0

        for shard in self.shards:
            for brain in shard.brains:
                n_nodes += 1
                msg = brain.emit()
                shard.locus.process(msg)  # decode -> action -> apply -> perceive
                # Contend for a globally shared resource (cross-authority write).
                self.fabric.propose(Write(
                    key=self._resource_of(brain.node_id),
                    value=brain.node_id,
                    node_id=brain.node_id,
                    ts=self._tick,
                    clock={brain.node_id: self._tick + 1},
                ))

        holders = self.fabric.commit()

        if self._trace is not None:
            self._trace.record("nexus", "graph_tick", meta={
                "tick": self._tick, "n_shards": len(self.shards), "n_nodes": n_nodes,
            })

        result = GraphTickResult(
            tick=self._tick,
            n_shards=len(self.shards),
            n_nodes=n_nodes,
            holders=holders,
            conflicts_this_tick=self.fabric.metrics["conflicts"] - conflicts_before,
            fabric_metrics=dict(self.fabric.metrics),
        )
        if self._run_log is not None:
            import json as _json

            self._run_log.write(_json.dumps(result.to_dict()) + "\n")
            self._run_log.flush()
        self._tick += 1
        return result

    def close(self) -> None:
        """Close the raw run log if one is open."""
        if self._run_log is not None:
            self._run_log.close()
            self._run_log = None

    def run(self, ticks: int) -> List[GraphTickResult]:
        """Run ``ticks`` graph ticks and return the per-tick results."""
        return [self.tick() for _ in range(ticks)]

    # --- introspection ----------------------------------------------------
    def n_nodes(self) -> int:
        """Total node count across all shards."""
        return sum(len(s.brains) for s in self.shards)

    def summary(self) -> Dict[str, Any]:
        """A machine-readable snapshot of graph shape and consensus state."""
        return {
            "tick": self._tick,
            "n_shards": len(self.shards),
            "n_nodes": self.n_nodes(),
            "policy": self.fabric.policy,
            "n_shared_resources": self.config.graph.n_shared_resources,
            "fabric_metrics": dict(self.fabric.metrics),
        }


def build_graph(config: BasisConfig, *, trace: Optional[Any] = None) -> Graph:
    """Build a Graph from a config."""
    return Graph(config, trace=trace)
