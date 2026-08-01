"""Tests for SNP normalization and validate+normalize round-trips."""

from __future__ import annotations

import snp
from helpers import valid_motor_message


def test_normalize_coerces_scalar_types():
    data = valid_motor_message()
    data["timestamp"] = 1730000000000  # already int
    data["payload"]["vector"] = [0, 0, 0, 0, 0, 0]  # ints -> floats
    data["payload"]["confidence"] = 1  # int -> float
    out = snp.normalize(data)
    assert out["timestamp"] == 1730000000000
    assert all(isinstance(v, float) for v in out["payload"]["vector"])
    assert isinstance(out["payload"]["confidence"], float)


def test_normalize_is_stable():
    data = valid_motor_message()
    once = snp.normalize(data)
    twice = snp.normalize(once)
    assert once == twice


def test_canonical_field_order():
    data = valid_motor_message()
    out = snp.normalize(data)
    assert list(out.keys()) == ["node_id", "timestamp", "signal_type", "payload"]
    assert list(out["payload"].keys()) == [
        "vector",
        "confidence",
        "paradigm",
        "encoding",
    ]


def test_normalize_validated_returns_canonical_dict():
    data = valid_motor_message()
    out = snp.normalize_validated(data)
    assert out == snp.normalize(data)
