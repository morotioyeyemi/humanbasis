"""The SNP message schema: the single canonical format every component speaks.

The schema is deliberately small. A message has an envelope (routing/metadata)
and a payload (the labeled signal). The ``vector`` is a bare list of floats; its
meaning is described by reference via ``encoding`` (see ``snp.encodings``), never
inline, so messages stay small and SNP stays stateless.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

# Documented vocabulary of top-level signal categories. This is intent-only:
# the encoding REGISTRY (snp.encodings) is the single source of truth, and
# validation checks a message's signal_type against its encoding's declared
# signal_type. Adding a modality is a registry edit, not a change here.
SIGNAL_TYPES = ("motor", "visual", "cognitive", "emotional", "perception")

ENVELOPE_FIELDS = ("node_id", "timestamp", "signal_type", "payload")
PAYLOAD_FIELDS = ("vector", "confidence", "paradigm", "encoding")


@dataclass
class Payload:
    """The labeled signal carried by a message.

    Attributes:
        vector: Bare positional floats. Meaning is given by ``encoding``.
        confidence: Producer confidence in ``[0.0, 1.0]``. Replayed ground
            truth uses ``1.0``.
        paradigm: The experimental task, e.g. ``"motor_imagery_lr"``. Kept
            separate from ``encoding`` so channel count can scale without
            changing task identity.
        encoding: Versioned id naming the vector layout, e.g.
            ``"mi.c3czc4.mubeta.v1"``.
    """

    vector: List[float]
    confidence: float
    paradigm: str
    encoding: str


@dataclass
class SNPMessage:
    """A single SNP message: envelope + payload.

    Attributes:
        node_id: Producing node identity, e.g. ``"brain_1"``.
        timestamp: Unix milliseconds.
        signal_type: One of ``SIGNAL_TYPES``.
        payload: The labeled signal.
    """

    node_id: str
    timestamp: int
    signal_type: str
    payload: Payload

    def to_dict(self) -> Dict[str, Any]:
        """Return the plain-dict / JSON-serializable form of the message."""
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "signal_type": self.signal_type,
            "payload": {
                "vector": list(self.payload.vector),
                "confidence": self.payload.confidence,
                "paradigm": self.payload.paradigm,
                "encoding": self.payload.encoding,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SNPMessage":
        """Build a message from a plain dict.

        This does not validate; call ``snp.validate`` for schema and
        length-vs-encoding checks.
        """
        payload = data["payload"]
        return cls(
            node_id=data["node_id"],
            timestamp=data["timestamp"],
            signal_type=data["signal_type"],
            payload=Payload(
                vector=list(payload["vector"]),
                confidence=payload["confidence"],
                paradigm=payload["paradigm"],
                encoding=payload["encoding"],
            ),
        )
