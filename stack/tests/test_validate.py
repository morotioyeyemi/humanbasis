"""Tests for SNP validation: structure, types, and length-vs-encoding."""

from __future__ import annotations

import copy

import pytest

import snp
from helpers import valid_motor_message, valid_perception_message


def test_valid_messages_pass():
    for factory in (valid_motor_message, valid_perception_message):
        msg = snp.validate(factory())
        assert isinstance(msg, snp.SNPMessage)
    assert snp.is_valid(valid_motor_message())


def test_missing_envelope_field():
    data = valid_motor_message()
    del data["node_id"]
    with pytest.raises(snp.SchemaError):
        snp.validate(data)


def test_unexpected_envelope_field():
    data = valid_motor_message()
    data["extra"] = 1
    with pytest.raises(snp.SchemaError):
        snp.validate(data)


def test_bad_timestamp_type():
    data = valid_motor_message()
    data["timestamp"] = "not-an-int"
    with pytest.raises(snp.SchemaError):
        snp.validate(data)


def test_bool_timestamp_rejected():
    data = valid_motor_message()
    data["timestamp"] = True  # bool is a subclass of int; must be rejected
    with pytest.raises(snp.SchemaError):
        snp.validate(data)


def test_unknown_signal_type():
    data = valid_motor_message()
    data["signal_type"] = "telepathy"
    with pytest.raises(snp.SchemaError):
        snp.validate(data)


def test_missing_payload_field():
    data = valid_motor_message()
    del data["payload"]["confidence"]
    with pytest.raises(snp.SchemaError):
        snp.validate(data)


def test_unexpected_payload_field():
    data = valid_motor_message()
    data["payload"]["surprise"] = 9
    with pytest.raises(snp.SchemaError):
        snp.validate(data)


def test_confidence_out_of_range():
    data = valid_motor_message()
    data["payload"]["confidence"] = 1.5
    with pytest.raises(snp.SchemaError):
        snp.validate(data)


def test_non_numeric_vector():
    data = valid_motor_message()
    data["payload"]["vector"] = [0.1, "x", 0.3, 0.4, 0.5, 0.6]
    with pytest.raises(snp.SchemaError):
        snp.validate(data)


def test_unknown_encoding_raises():
    data = valid_motor_message()
    data["payload"]["encoding"] = "mi.does.not.exist.v9"
    with pytest.raises(snp.UnknownEncodingError):
        snp.validate(data)


def test_wrong_vector_length_raises():
    data = valid_motor_message()
    data["payload"]["vector"] = [0.1, 0.2, 0.3]  # encoding declares length 6
    with pytest.raises(snp.VectorLengthError):
        snp.validate(data)


def test_is_valid_false_on_bad_message():
    data = valid_motor_message()
    data["payload"]["vector"] = []
    assert not snp.is_valid(data)


def test_validate_does_not_mutate_input():
    data = valid_motor_message()
    snapshot = copy.deepcopy(data)
    snp.validate(data)
    assert data == snapshot
