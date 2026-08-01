"""Canonical normalization for SNP messages.

Normalization puts a message into the single canonical form every component
speaks: exact field ordering, coerced scalar types (timestamp -> int, vector
values and confidence -> float). It is bidirectional and used the same way for
Brain -> infra and Locus -> Brain messages.

Normalization does not validate; run ``snp.validate`` first (or use
``normalize_validated``) to guarantee a conforming message.
"""

from __future__ import annotations

from typing import Any, Dict, Union

from .schema import SNPMessage
from .validate import validate

MessageLike = Union[SNPMessage, Dict[str, Any]]


def normalize(message: MessageLike) -> Dict[str, Any]:
    """Return the canonical plain-dict form of a message.

    Fields are emitted in canonical order with coerced scalar types. Assumes a
    structurally sound message; call ``validate`` first if unsure.
    """
    data = message.to_dict() if isinstance(message, SNPMessage) else message
    payload = data["payload"]
    return {
        "node_id": str(data["node_id"]),
        "timestamp": int(data["timestamp"]),
        "signal_type": str(data["signal_type"]),
        "payload": {
            "vector": [float(v) for v in payload["vector"]],
            "confidence": float(payload["confidence"]),
            "paradigm": str(payload["paradigm"]),
            "encoding": str(payload["encoding"]),
        },
    }


def normalize_validated(message: MessageLike) -> Dict[str, Any]:
    """Validate then normalize, returning the canonical plain-dict form."""
    return normalize(validate(message))
