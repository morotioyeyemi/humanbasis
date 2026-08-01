"""Collect a series of frames from a graph run for visualization.

Runs a Basis graph with per-tick capture and packages exactly what the four
dashboard panels need into plain, JSON-serializable frames: one focus shard's
node signals + decoded actions (micro), that shard's room snapshot (meso),
resource ownership + conflicts across the whole graph (macro), and the TRACE
metrics lens (metrics). Deterministic given the config seed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core import BasisConfig
from nexus.graph import Graph
from trace import Lens, Trace


@dataclass
class Frame:
    """One tick's worth of visualization data."""

    tick: int
    n_shards: int
    n_nodes: int
    conflicts_this_tick: int
    holders: Dict[str, Any]
    focus_shard: Optional[int]
    focus_signals: Dict[str, Any] = field(default_factory=dict)
    focus_room: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Collection:
    """A full captured run: frames + config + final lens metrics."""

    config: Dict[str, Any]
    frames: List[Frame]
    resources: List[str]
    metrics: Dict[str, Any]

    def conflict_series(self) -> List[int]:
        return [f.conflicts_this_tick for f in self.frames]

    def ownership_matrix(self) -> List[List[int]]:
        """resources x ticks matrix of owner node index (-1 = unowned this tick).

        Owner ids are mapped to small integers for coloring; the mapping is
        stable across the run.
        """
        owner_ids: Dict[str, int] = {}

        def idx(nid: str) -> int:
            if nid not in owner_ids:
                owner_ids[nid] = len(owner_ids)
            return owner_ids[nid]

        matrix: List[List[int]] = []
        for res in self.resources:
            row = []
            for f in self.frames:
                holder = f.holders.get(res)
                row.append(idx(holder) if holder is not None else -1)
            matrix.append(row)
        return matrix


def collect(config: BasisConfig, ticks: Optional[int] = None) -> Collection:
    """Run a graph with capture and return a Collection for rendering.

    Args:
        config: The run configuration (small graphs recommended for capture).
        ticks: Override the number of ticks (else uses config.ticks).
    """
    trace = Trace()
    graph = Graph(config.validate(), trace=trace)
    n = ticks if ticks is not None else config.ticks

    frames: List[Frame] = []
    resources_seen: List[str] = []
    for _ in range(n):
        r = graph.tick(capture=True)
        for res in sorted(r.holders):
            if res not in resources_seen:
                resources_seen.append(res)
        frames.append(Frame(
            tick=r.tick,
            n_shards=r.n_shards,
            n_nodes=r.n_nodes,
            conflicts_this_tick=r.conflicts_this_tick,
            holders=dict(r.holders),
            focus_shard=r.focus_shard,
            focus_signals=r.focus_signals or {},
            focus_room=r.focus_room or {},
        ))

    return Collection(
        config=config.to_dict(),
        frames=frames,
        resources=sorted(resources_seen),
        metrics=Lens.from_trace(trace).summary(),
    )
