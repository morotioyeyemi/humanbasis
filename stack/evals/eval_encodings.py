"""Eval: encodings are parameterized across channel widths 6..256 floats."""

from __future__ import annotations

import snp


def test_motor_family_widths():
    # Expected motor encodings and their vector lengths (channels x 2 bands).
    expected = {
        "mi.c3czc4.mubeta.v1": 6,
        "mi.8ch.mubeta.v1": 16,
        "mi.16ch.mubeta.v1": 32,
        "mi.32ch.mubeta.v1": 64,
        "mi.64ch.mubeta.v1": 128,
        "mi.128ch.mubeta.v1": 256,
    }
    for enc, length in expected.items():
        assert snp.is_registered(enc), enc
        layout = snp.get_layout(enc)
        assert layout.length == length, enc
        assert layout.signal_type == "motor"


def test_visual_family_exists():
    for enc in ("ssvep.8ch.f4.v1", "ssvep.64ch.f4.v1"):
        assert snp.is_registered(enc), enc
        assert snp.signal_type_for(enc) == "visual"


def test_min_and_max_widths_present():
    lengths = {snp.get_layout(e).length for e in snp.REGISTRY}
    assert 6 in lengths      # minimum motor vector
    assert 256 in lengths    # maximum motor vector


def test_registry_self_consistent():
    for enc, layout in snp.REGISTRY.items():
        if layout.bands:
            assert layout.length == len(layout.channels) * len(layout.bands), enc
        else:
            assert layout.length == len(layout.channels), enc
