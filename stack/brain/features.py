"""Band-power feature extraction for Basis Brain.

Turns a windowed multi-channel EEG epoch into the flat float vector described by
the SNP encoding ``mi.c3czc4.mubeta.v1``: log power in the mu (8-13 Hz) and beta
(13-30 Hz) bands for channels C3, Cz, C4, flattened channel-major:

    [C3-mu, C3-beta, Cz-mu, Cz-beta, C4-mu, C4-beta]

The band definitions and channel order are read from the SNP registry so this
producer can never drift from the contract.
"""

from __future__ import annotations

from typing import List

import numpy as np
from scipy.signal import welch

import snp


def band_power_vector(epoch: np.ndarray, encoding: str, rate_hz: float) -> List[float]:
    """Compute the log band-power feature vector for one epoch.

    Args:
        epoch: Array shaped ``(n_channels, n_samples)`` whose channel order
            matches the encoding's ``channels``.
        encoding: The SNP encoding id, e.g. ``"mi.c3czc4.mubeta.v1"``.
        rate_hz: Sampling rate of ``epoch`` in Hz.

    Returns:
        A list of floats, channel-major over the encoding's bands, length equal
        to the encoding's declared ``length``.

    Raises:
        ValueError: If the epoch channel count disagrees with the encoding.
    """
    layout = snp.get_layout(encoding)
    n_channels = len(layout.channels)
    if epoch.shape[0] != n_channels:
        raise ValueError(
            f"epoch has {epoch.shape[0]} channels, encoding {encoding!r} "
            f"expects {n_channels}"
        )

    nperseg = min(epoch.shape[1], int(rate_hz))  # ~1 s segments, capped by window
    freqs, psd = welch(epoch, fs=rate_hz, nperseg=nperseg, axis=1)

    features: List[float] = []
    for ch_idx in range(n_channels):
        for _band_name, (low, high) in layout.bands:
            mask = (freqs >= low) & (freqs < high)
            power = float(np.trapezoid(psd[ch_idx, mask], freqs[mask])) if mask.any() else 0.0
            features.append(float(np.log(power + 1e-12)))
    return features
