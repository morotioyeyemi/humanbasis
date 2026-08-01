"""Tests for Brain band-power feature extraction (synthetic, no network)."""

from __future__ import annotations

import math

import numpy as np

import snp
from brain import band_power_vector


def test_vector_length_matches_encoding():
    layout = snp.get_layout("mi.c3czc4.mubeta.v1")
    epoch = np.random.default_rng(1).standard_normal((3, 256))
    vec = band_power_vector(epoch, "mi.c3czc4.mubeta.v1", 128.0)
    assert len(vec) == layout.length == 6
    assert all(isinstance(v, float) and math.isfinite(v) for v in vec)


def test_wrong_channel_count_raises():
    epoch = np.zeros((4, 256))  # encoding expects 3 channels
    try:
        band_power_vector(epoch, "mi.c3czc4.mubeta.v1", 128.0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_stronger_beta_shows_in_features():
    # A 20 Hz sinusoid (beta band) should raise beta power above mu power.
    fs = 128.0
    t = np.arange(256) / fs
    sig = np.sin(2 * np.pi * 20 * t)
    epoch = np.vstack([sig, sig, sig])
    vec = band_power_vector(epoch, "mi.c3czc4.mubeta.v1", fs)
    # order is [C3-mu, C3-beta, ...]; beta (idx 1) > mu (idx 0) for a 20 Hz tone.
    assert vec[1] > vec[0]
