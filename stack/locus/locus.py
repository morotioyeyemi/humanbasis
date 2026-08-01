"""Basis Locus: shared environment state manager.

Locus owns the world (a WhiteRoom), applies incoming node signals as actions,
and produces each node's first-person perception as an SNP message. It is the
consumption boundary for neural vectors (it decodes them); everything upstream
(SNP/Fabric/TRACE) treats the vector as opaque.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import snp

from . import decoders
from .environment import ROOM_MAX, WhiteRoom

PERCEPTION_ENCODING = "env.room.pose_visible.v1"
PERCEPTION_PARADIGM = "locus_room_v1"


class Locus:
    """Shared environment state manager for the white room.

    Args:
        room: The environment to manage. If omitted, a fresh room of side
            ``size`` is created.
        size: Side length for the auto-created room (ignored if ``room`` given).
        trace: Optional Basis TRACE recorder; if given, decode/apply/perceive
            are timed.
    """

    def __init__(
        self,
        room: Optional[WhiteRoom] = None,
        *,
        size: float = ROOM_MAX,
        trace: Optional[Any] = None,
    ) -> None:
        self.room = room or WhiteRoom(size=size)
        self._trace = trace

    def add_node(self, node_id: str, x: float, y: float, heading: float = 0.0) -> None:
        """Register a node in the environment."""
        self.room.add_node(node_id, x, y, heading)

    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Apply one inbound node signal and return its perception update.

        Steps: validate the inbound message, decode its vector into an action
        (the consumption boundary), apply the action to the shared world, then
        compute and return this node's perception as a validated SNP message.
        """
        msg = snp.validate(message)
        node_id = msg.node_id
        encoding = msg.payload.encoding

        if self._trace is not None:
            with self._trace.span("locus", "decode", node_id=node_id):
                action = decoders.decode(encoding, msg.payload.vector)
            with self._trace.span("locus", "apply", node_id=node_id):
                self.room.apply_action(node_id, action)
        else:
            action = decoders.decode(encoding, msg.payload.vector)
            self.room.apply_action(node_id, action)

        return self._perception(node_id)

    def _perception(self, node_id: str) -> Dict[str, Any]:
        vector = self.room.perceive(node_id)
        message = {
            "node_id": node_id,
            "timestamp": int(time.time() * 1000),
            "signal_type": snp.signal_type_for(PERCEPTION_ENCODING),
            "payload": {
                "vector": vector,
                "confidence": 1.0,
                "paradigm": PERCEPTION_PARADIGM,
                "encoding": PERCEPTION_ENCODING,
            },
        }
        if self._trace is not None:
            with self._trace.span("locus", "perceive", node_id=node_id):
                return snp.normalize_validated(message)
        return snp.normalize_validated(message)

    def snapshot(self) -> Dict[str, Any]:
        """Return a plain-data snapshot of the world (for rendering)."""
        return self.room.snapshot()
