"""Message validation for the SNP contract.

Validation is strictly message-level and preserves the opaque-vector rule: SNP
checks structure, field types, and that ``len(vector)`` matches the referenced
encoding's declared ``length``. It never inspects individual vector values or
infers their meaning.
"""

from __future__ import annotations

from typing import Any, Dict, Union

from .encodings import expected_length, is_registered
from .errors import SchemaError, UnknownEncodingError, VectorLengthError
from .schema import (
    ENVELOPE_FIELDS,
    PAYLOAD_FIELDS,
    SIGNAL_TYPES,
    SNPMessage,
)

MessageLike = Union[SNPMessage, Dict[str, Any]]


def _as_dict(message: MessageLike) -> Dict[str, Any]:
    if isinstance(message, SNPMessage):
        return message.to_dict()
    if isinstance(message, dict):
        return message
    raise SchemaError(f"message must be an SNPMessage or dict, got {type(message).__name__}")


def validate(message: MessageLike) -> SNPMessage:
    """Validate a message and return it as a normalized ``SNPMessage``.

    Checks, in order:
      1. Envelope has exactly the required fields.
      2. Field types are correct (node_id str, timestamp int, signal_type known).
      3. Payload has exactly the required fields with correct types.
      4. ``encoding`` is registered.
      5. ``len(vector)`` equals the encoding's declared ``length``.

    Raises:
        SchemaError: On any structural or type problem.
        UnknownEncodingError: If ``encoding`` is not in the registry.
        VectorLengthError: If the vector length disagrees with the encoding.
    """
    data = _as_dict(message)

    missing = [f for f in ENVELOPE_FIELDS if f not in data]
    if missing:
        raise SchemaError(f"envelope missing fields: {missing}")
    extra = [f for f in data if f not in ENVELOPE_FIELDS]
    if extra:
        raise SchemaError(f"envelope has unexpected fields: {extra}")

    if not isinstance(data["node_id"], str) or not data["node_id"]:
        raise SchemaError("node_id must be a non-empty string")
    if isinstance(data["timestamp"], bool) or not isinstance(data["timestamp"], int):
        raise SchemaError("timestamp must be an int (unix ms)")
    if data["signal_type"] not in SIGNAL_TYPES:
        raise SchemaError(
            f"signal_type must be one of {SIGNAL_TYPES}, got {data['signal_type']!r}"
        )

    payload = data["payload"]
    if not isinstance(payload, dict):
        raise SchemaError("payload must be an object")
    p_missing = [f for f in PAYLOAD_FIELDS if f not in payload]
    if p_missing:
        raise SchemaError(f"payload missing fields: {p_missing}")
    p_extra = [f for f in payload if f not in PAYLOAD_FIELDS]
    if p_extra:
        raise SchemaError(f"payload has unexpected fields: {p_extra}")

    vector = payload["vector"]
    if not isinstance(vector, list) or not all(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in vector
    ):
        raise SchemaError("vector must be a list of numbers")
    confidence = payload["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise SchemaError("confidence must be a number")
    if not 0.0 <= float(confidence) <= 1.0:
        raise SchemaError("confidence must be within [0.0, 1.0]")
    if not isinstance(payload["paradigm"], str) or not payload["paradigm"]:
        raise SchemaError("paradigm must be a non-empty string")
    if not isinstance(payload["encoding"], str) or not payload["encoding"]:
        raise SchemaError("encoding must be a non-empty string")

    encoding = payload["encoding"]
    if not is_registered(encoding):
        raise UnknownEncodingError(f"unknown encoding id: {encoding!r}")

    declared = expected_length(encoding)
    if len(vector) != declared:
        raise VectorLengthError(
            f"vector length {len(vector)} does not match encoding "
            f"{encoding!r} declared length {declared}"
        )

    return SNPMessage.from_dict(data)


def is_valid(message: MessageLike) -> bool:
    """Return ``True`` if the message passes ``validate``, else ``False``."""
    from .errors import SNPError

    try:
        validate(message)
    except SNPError:
        return False
    return True
