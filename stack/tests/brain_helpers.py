"""Synthetic helpers for Brain tests (no network)."""

from __future__ import annotations

import numpy as np

import snp
from brain import EpochSet


def synthetic_epochs(n_epochs: int = 5, encoding: str = "mi.c3czc4.mubeta.v1") -> EpochSet:
    """Build a small labeled EpochSet with random signal, matching the encoding."""
    layout = snp.get_layout(encoding)
    n_channels = len(layout.channels)
    n_samples = int(round(layout.window_s * layout.rate_hz))
    rng = np.random.default_rng(0)
    data = rng.standard_normal((n_epochs, n_channels, n_samples))
    labels = ["left" if i % 2 == 0 else "right" for i in range(n_epochs)]
    return EpochSet(
        data=data,
        labels=labels,
        channels=layout.channels,
        rate_hz=layout.rate_hz,
        subject=0,
    )
