"""Basis Fabric: distributed state consensus engine (v1 pass-through seam).

The real Fabric resolves concurrent, conflicting state updates across a
distributed/replicated world. That is only needed when there is no single
authority for the state. Basis v1 runs a single Locus on a single machine, where
sequential application by one owner is its own trivial consensus, so no real
consensus is required yet.

This module is a deliberate pass-through seam that preserves the architecture's
loop topology (Brain -> SNP -> Fabric -> Locus) and gives the real engine a
place to slot in when the world becomes replicated. It applies updates in
arrival order and never interprets the vector (the opaque-vector rule).
"""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional


class Fabric:
    """Pass-through consensus seam: FIFO ordering, no conflict resolution.

    Args:
        trace: Optional Basis TRACE recorder; if given, submit is timed.
    """

    def __init__(self, *, trace: Optional[Any] = None) -> None:
        self._queue: Deque[Dict[str, Any]] = deque()
        self._trace = trace

    def submit(self, message: Dict[str, Any]) -> None:
        """Accept a message into the ordered queue."""
        if self._trace is not None:
            with self._trace.span("fabric", "submit", node_id=message.get("node_id")):
                self._queue.append(message)
        else:
            self._queue.append(message)

    def drain(self) -> List[Dict[str, Any]]:
        """Return and clear all queued messages, in arrival (FIFO) order.

        In v1 this is the identity ordering. A real Fabric would reconcile
        conflicting updates here before releasing them to Locus.
        """
        drained = list(self._queue)
        self._queue.clear()
        return drained

    def __len__(self) -> int:
        return len(self._queue)
