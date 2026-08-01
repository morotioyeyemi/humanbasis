"""Basis Nexus: the integration layer that runs the signal loop.

Nexus wires the components into one cycle, following basis-stack section 3:

    Brain.emit() -> SNP -> Fabric -> Locus -> perception update -> SNP

It owns no domain logic of its own; it orchestrates the components and lets
Basis TRACE observe every step. Demos and experiments drive Nexus and render the
world snapshot; they do not re-implement the wiring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from brain import Brain
from locus import Locus


@dataclass
class TickResult:
    """The outcome of one signal-loop tick.

    Attributes:
        tick: The 0-based tick index.
        snapshot: Plain-data world snapshot (node_id -> (x, y, heading)).
        perceptions: Per-node perception SNP messages produced this tick.
        signals: Per-node outbound signal SNP messages emitted this tick.
    """

    tick: int
    snapshot: Dict[str, Any]
    perceptions: Dict[str, Any] = field(default_factory=dict)
    signals: Dict[str, Any] = field(default_factory=dict)


class Nexus:
    """Orchestrates one or more Brains through Fabric into a shared Locus.

    Args:
        brains: The nodes to drive.
        locus: The shared environment manager. Every brain must be registered
            in it (see the demo for placement).
        trace: Optional Basis TRACE recorder passed through for observation.
    """

    def __init__(
        self,
        brains: List[Brain],
        locus: Locus,
        *,
        trace: Optional[Any] = None,
    ) -> None:
        self.brains = list(brains)
        self.locus = locus
        self._trace = trace
        self._tick = 0

    def tick(self) -> TickResult:
        """Run one full signal-loop cycle for all brains and return the result."""
        signals: Dict[str, Any] = {}
        perceptions: Dict[str, Any] = {}

        # Each Brain emits (validated by SNP inside emit); Locus decodes the
        # vector into an action, applies it, and produces the node's perception.
        # Fabric operates at the shared-state layer (see nexus.graph), not on the
        # single-authority signal path, so a lone Locus needs no consensus.
        for brain in self.brains:
            msg = brain.emit()
            signals[brain.node_id] = msg
            perceptions[brain.node_id] = self.locus.process(msg)

        if self._trace is not None:
            self._trace.record(
                "nexus", "tick", meta={"tick": self._tick, "n_nodes": len(self.brains)}
            )

        result = TickResult(
            tick=self._tick,
            snapshot=self.locus.snapshot(),
            perceptions=perceptions,
            signals=signals,
        )
        self._tick += 1
        return result

    def run(self, ticks: int) -> List[TickResult]:
        """Run ``ticks`` cycles and return the per-tick results."""
        return [self.tick() for _ in range(ticks)]
