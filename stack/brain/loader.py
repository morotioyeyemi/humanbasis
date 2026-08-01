"""EEGMMIDB loader for Basis Brain v1.

Downloads and prepares the PhysioNet EEG Motor Movement/Imagery Dataset via
``mne.datasets.eegbci``, extracts labeled left/right-hand motor-imagery epochs
for the channels and sample rate declared by the SNP encoding.

Ground truth (verified empirically):
- Motor imagery of left vs right fist = Task 2 = runs [4, 8, 12].
- Annotations: T0 = rest (ignored), T1 = left fist, T2 = right fist.
- Native sfreq 160 Hz, 64 channels; standardize() gives clean 10-10 names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

import snp

MI_LR_RUNS = [4, 8, 12]
LABEL_LEFT = "left"
LABEL_RIGHT = "right"


@dataclass
class EpochSet:
    """Labeled motor-imagery epochs ready for feature extraction.

    Attributes:
        data: Array shaped ``(n_epochs, n_channels, n_samples)``; channel order
            matches ``channels``.
        labels: One of ``"left"``/``"right"`` per epoch.
        channels: Channel names, in order.
        rate_hz: Sampling rate of ``data``.
        subject: The subject id these epochs came from.
    """

    data: np.ndarray
    labels: List[str]
    channels: Tuple[str, ...]
    rate_hz: float
    subject: int


def load_mi_epochs(subject: int, encoding: str = "mi.c3czc4.mubeta.v1") -> EpochSet:
    """Load left/right-hand motor-imagery epochs for one subject.

    Channels, sample rate, and window length are taken from the SNP encoding so
    the loader stays in lock-step with the contract.

    Args:
        subject: EEGMMIDB subject number (1-109).
        encoding: SNP encoding id defining channels/rate/window.

    Returns:
        An ``EpochSet`` with labeled epochs.
    """
    import mne
    from mne.datasets import eegbci
    from mne.io import concatenate_raws, read_raw_edf

    mne.set_log_level("ERROR")
    layout = snp.get_layout(encoding)

    files = eegbci.load_data(subject, MI_LR_RUNS, update_path=True)
    raw = concatenate_raws([read_raw_edf(f, preload=True) for f in files])
    eegbci.standardize(raw)

    if float(raw.info["sfreq"]) != layout.rate_hz:
        raw.resample(layout.rate_hz)

    raw.pick(list(layout.channels))

    events, event_id = mne.events_from_annotations(raw)
    # T1 -> left fist, T2 -> right fist. Map to our labels via the annotation ids.
    wanted = {}
    if "T1" in event_id:
        wanted[event_id["T1"]] = LABEL_LEFT
    if "T2" in event_id:
        wanted[event_id["T2"]] = LABEL_RIGHT

    tmin = 0.0
    tmax = layout.window_s
    epochs = mne.Epochs(
        raw,
        events,
        event_id={k: v for k, v in event_id.items() if k in ("T1", "T2")},
        tmin=tmin,
        tmax=tmax,
        baseline=None,
        preload=True,
    )

    n_samples = int(round(layout.window_s * layout.rate_hz))
    data = epochs.get_data(copy=True)[:, :, :n_samples]
    labels = [wanted[code] for code in epochs.events[:, 2]]

    return EpochSet(
        data=data,
        labels=labels,
        channels=layout.channels,
        rate_hz=layout.rate_hz,
        subject=subject,
    )
