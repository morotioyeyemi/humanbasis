"""Tests for the SNP encoding registry."""

from __future__ import annotations

import snp


def test_v1_motor_encoding_shape():
    layout = snp.get_layout("mi.c3czc4.mubeta.v1")
    assert layout.channels == ("C3", "Cz", "C4")
    assert layout.length == 6
    assert layout.length == len(layout.channels) * len(layout.bands)
    assert layout.rate_hz == 128.0
    assert layout.window_s == 2.0


def test_env_encoding_registered():
    assert snp.is_registered("env.room.pose_visible.v1")
    assert snp.expected_length("env.room.pose_visible.v1") == 5


def test_unknown_encoding():
    assert not snp.is_registered("nope.not.real.v1")


def test_registry_lengths_are_self_consistent():
    # channel_band_power layouts must have length == channels * bands.
    for enc, layout in snp.REGISTRY.items():
        if layout.layout == "channel_band_power":
            assert layout.length == len(layout.channels) * len(layout.bands), enc


def test_length_is_derived_not_hand_entered():
    # bands present -> channels * bands; no bands -> channels.
    mi = snp.get_layout("mi.c3czc4.mubeta.v1")
    assert mi.length == len(mi.channels) * len(mi.bands) == 6
    env = snp.get_layout("env.room.pose_visible.v1")
    assert env.bands == ()
    assert env.length == len(env.channels) == 5


def test_encoding_declares_signal_type():
    assert snp.signal_type_for("mi.c3czc4.mubeta.v1") == "motor"
    assert snp.signal_type_for("env.room.pose_visible.v1") == "perception"


def test_known_signal_types_from_registry():
    assert snp.known_signal_types() == frozenset({"motor", "perception", "visual"})
