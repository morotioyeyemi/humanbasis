"""Tests for the SNP schema round-trip."""

from __future__ import annotations

import snp
from helpers import valid_motor_message, valid_perception_message


def test_from_dict_to_dict_roundtrip():
    for factory in (valid_motor_message, valid_perception_message):
        data = factory()
        msg = snp.SNPMessage.from_dict(data)
        assert msg.to_dict() == data


def test_message_fields():
    msg = snp.SNPMessage.from_dict(valid_motor_message())
    assert msg.node_id == "brain_1"
    assert msg.timestamp == 1730000000000
    assert msg.signal_type == "motor"
    assert msg.payload.encoding == "mi.c3czc4.mubeta.v1"
    assert len(msg.payload.vector) == 6
