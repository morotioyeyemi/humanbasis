"""SNP: Signal Normalization Protocol.

The single canonical message format for the Basis stack. Everything passes
through SNP; nothing talks directly to anything else. SNP is a library (not a
service in v1): a schema, a static encoding registry, and validate/normalize
functions. It does message-level work only and never interprets vector meaning.
"""

from __future__ import annotations

from .encodings import (
    REGISTRY,
    Layout,
    expected_length,
    get_layout,
    is_registered,
    known_signal_types,
    register_band_power,
    signal_type_for,
)
from .errors import (
    SchemaError,
    SNPError,
    UnknownEncodingError,
    VectorLengthError,
)
from .normalize import normalize, normalize_validated
from .schema import (
    PAYLOAD_FIELDS,
    SIGNAL_TYPES,
    Payload,
    SNPMessage,
)
from .validate import is_valid, validate

__all__ = [
    "REGISTRY",
    "Layout",
    "expected_length",
    "get_layout",
    "is_registered",
    "known_signal_types",
    "signal_type_for",
    "register_band_power",
    "SNPError",
    "SchemaError",
    "UnknownEncodingError",
    "VectorLengthError",
    "normalize",
    "normalize_validated",
    "Payload",
    "SNPMessage",
    "SIGNAL_TYPES",
    "PAYLOAD_FIELDS",
    "validate",
    "is_valid",
]
