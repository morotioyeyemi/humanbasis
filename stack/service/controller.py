"""BasisController: the agent-facing control surface over the whole stack.

Every capability an agent needs to inspect, run, scale, and tune the Basis stack
is a plain method here returning JSON-serializable data. The MCP server (see
server.py) is a thin transport that exposes these methods as tools; keeping the
substance here makes it directly testable without any transport.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import snp
from core import CONSENSUS_POLICIES, BasisConfig
from nexus.graph import Graph
from trace import Lens, Trace


class BasisController:
    """A live, mutable Basis run that agents drive.

    Args:
        enable_trace: If True, a Trace is attached so the metrics lens is
            available (adds per-step overhead; fine for interactive control).
    """

    def __init__(self, enable_trace: bool = True) -> None:
        self._enable_trace = enable_trace
        self.config = BasisConfig()
        self.trace: Optional[Trace] = Trace() if enable_trace else None
        self.graph: Optional[Graph] = None

    # --- lifecycle --------------------------------------------------------
    def build(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build (or rebuild) the graph from a config dict; returns the summary."""
        if config is not None:
            self.config = BasisConfig.from_dict(config).validate()
        if self.trace is not None:
            self.trace.clear()
        self.graph = Graph(self.config, trace=self.trace)
        return self.summary()

    def reset(self) -> Dict[str, Any]:
        """Rebuild the graph from the current config."""
        return self.build(self.config.to_dict())

    def _require_graph(self) -> Graph:
        if self.graph is None:
            self.build(self.config.to_dict())
        assert self.graph is not None
        return self.graph

    # --- run --------------------------------------------------------------
    def tick(self, n: int = 1) -> Dict[str, Any]:
        """Advance the simulation ``n`` ticks; return the last tick + timing."""
        g = self._require_graph()
        t0 = time.perf_counter()
        last = None
        for _ in range(max(1, n)):
            last = g.tick()
        elapsed = time.perf_counter() - t0
        assert last is not None
        return {
            "last_tick": last.to_dict(),
            "elapsed_s": elapsed,
            "node_ticks_per_sec": (g.n_nodes() * max(1, n)) / elapsed if elapsed > 0 else 0.0,
        }

    # --- structure (scale live) -------------------------------------------
    def add_shard(self, count: int = 1) -> Dict[str, Any]:
        """Add ``count`` shards at runtime."""
        g = self._require_graph()
        added = [g.add_shard().index for _ in range(max(1, count))]
        return {"added_shards": added, "n_shards": len(g.shards), "n_nodes": g.n_nodes()}

    def remove_shard(self, index: int) -> Dict[str, Any]:
        """Remove a shard by index."""
        g = self._require_graph()
        ok = g.remove_shard(index)
        return {"removed": ok, "n_shards": len(g.shards), "n_nodes": g.n_nodes()}

    def add_node(self, shard_index: int) -> Dict[str, Any]:
        """Add a node to a shard at runtime."""
        g = self._require_graph()
        node_id = g.add_node(shard_index)
        return {"node_id": node_id, "n_nodes": g.n_nodes()}

    def remove_node(self, node_id: str) -> Dict[str, Any]:
        """Remove a node by id."""
        g = self._require_graph()
        return {"removed": g.remove_node(node_id), "n_nodes": g.n_nodes()}

    # --- tune -------------------------------------------------------------
    def set_policy(self, policy: str) -> Dict[str, Any]:
        """Change the Fabric consensus policy live."""
        if policy not in CONSENSUS_POLICIES:
            raise ValueError(f"policy must be one of {list(CONSENSUS_POLICIES)}")
        g = self._require_graph()
        g.fabric.policy = policy
        self.config.fabric.policy = policy
        return {"policy": policy}

    def set_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Replace the config (takes effect on the next build/reset)."""
        self.config = BasisConfig.from_dict(config).validate()
        return {"config": self.config.to_dict()}

    def get_config(self) -> Dict[str, Any]:
        """Return the current config."""
        return {"config": self.config.to_dict()}

    # --- inspect ----------------------------------------------------------
    def summary(self) -> Dict[str, Any]:
        """Return the graph summary (shape + consensus metrics)."""
        return self._require_graph().summary()

    def holders(self) -> Dict[str, Any]:
        """Return the current committed holder of every shared resource."""
        return {"holders": self._require_graph().fabric.snapshot()}

    def metrics(self) -> Dict[str, Any]:
        """Return the metrics lens summary (requires trace enabled)."""
        if self.trace is None:
            return {"error": "trace disabled; construct with enable_trace=True"}
        return Lens.from_trace(self.trace).summary()

    def list_encodings(self) -> Dict[str, Any]:
        """List available encodings grouped by modality (signal_type)."""
        out: Dict[str, List[Dict[str, Any]]] = {}
        for enc, layout in snp.REGISTRY.items():
            out.setdefault(layout.signal_type, []).append({"encoding": enc, "length": layout.length})
        return {"modalities": out}
