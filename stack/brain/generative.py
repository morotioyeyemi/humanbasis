"""Lightweight generative signal source for Basis Brain.

Replaces finite real-EEG replay with cheap, parametric, seeded generators. This
removes the 109-subject cap and produces unlimited, non-repeating signal while
keeping realistic structure (motor-imagery lateralization; SSVEP frequency
peaks). A generator is fully determined by (encoding, node seed), so runs are
reproducible.

For the calibrated motor encoding (mi.c3czc4.mubeta.v1) the per-class feature
statistics are fit to real EEGMMIDB data (see build_calibration.py); wider
montages and the visual family use parametric statistics that preserve the
discriminative structure a decoder relies on.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

import snp
from core import hemisphere_labels
from core.montage import LEFT, MIDDLE, RIGHT

CALIBRATION_DIR = Path(__file__).parent / "calibration"

# Strength of the class effect (in the normalized log-power feature space).
_MOTOR_ERD = 1.6
_MOTOR_STD = 0.8
_SSVEP_PEAK = 2.0
_SSVEP_STD = 0.7


@dataclass
class ClassModel:
    """Per-class feature distribution: sample ~ Normal(mean, std)."""

    label: str
    mean: np.ndarray
    std: np.ndarray


class GenerativeModel:
    """A per-encoding generator with labeled classes.

    Args:
        encoding: SNP encoding id the model produces vectors for.
        classes: The labeled class distributions.
    """

    def __init__(self, encoding: str, classes: List[ClassModel]) -> None:
        self.encoding = encoding
        self.classes = classes
        self.signal_type = snp.signal_type_for(encoding)
        self._length = snp.get_layout(encoding).length

    def sample(self, rng: np.random.Generator) -> Tuple[List[float], str]:
        """Draw one (vector, label) from a uniformly chosen class."""
        c = self.classes[int(rng.integers(len(self.classes)))]
        vec = c.mean + c.std * rng.standard_normal(self._length)
        return vec.astype(float).tolist(), c.label


# --- model builders ---------------------------------------------------------

def _motor_model(encoding: str) -> GenerativeModel:
    layout = snp.get_layout(encoding)
    hemis = hemisphere_labels(layout.channels)
    n_bands = len(layout.bands)
    dim = layout.length
    std = np.full(dim, _MOTOR_STD)

    left_mean = np.zeros(dim)   # imagine LEFT hand -> right-hemisphere ERD
    right_mean = np.zeros(dim)  # imagine RIGHT hand -> left-hemisphere ERD
    for ci, hemi in enumerate(hemis):
        for bi in range(n_bands):
            idx = ci * n_bands + bi
            if hemi == RIGHT:
                left_mean[idx] -= _MOTOR_ERD
            elif hemi == LEFT:
                right_mean[idx] -= _MOTOR_ERD
    return GenerativeModel(encoding, [
        ClassModel("left", left_mean, std),
        ClassModel("right", right_mean, std),
    ])


def _visual_model(encoding: str) -> GenerativeModel:
    layout = snp.get_layout(encoding)
    n_channels = len(layout.channels)
    n_bands = len(layout.bands)
    dim = layout.length
    std = np.full(dim, _SSVEP_STD)

    classes: List[ClassModel] = []
    for target_bi, (band_name, _range) in enumerate(layout.bands):
        mean = np.zeros(dim)
        for ci in range(n_channels):
            mean[ci * n_bands + target_bi] += _SSVEP_PEAK
        classes.append(ClassModel(band_name, mean, std))
    return GenerativeModel(encoding, classes)


def _load_calibration(encoding: str) -> Optional[GenerativeModel]:
    path = CALIBRATION_DIR / f"{encoding}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    classes = [
        ClassModel(label, np.asarray(d["mean"]), np.asarray(d["std"]))
        for label, d in data["classes"].items()
    ]
    return GenerativeModel(encoding, classes)


def build_model(encoding: str, *, use_calibration: bool = True) -> GenerativeModel:
    """Build the generative model for an encoding.

    Motor encodings use calibrated real-EEG statistics when available (and
    ``use_calibration`` is True), else a parametric lateralized model. Visual
    encodings use a parametric frequency-peak model.
    """
    signal_type = snp.signal_type_for(encoding)
    if signal_type == "motor":
        if use_calibration:
            calibrated = _load_calibration(encoding)
            if calibrated is not None:
                return calibrated
        return _motor_model(encoding)
    if signal_type == "visual":
        return _visual_model(encoding)
    raise ValueError(f"no generative model for signal_type {signal_type!r} ({encoding})")


class GenerativeBrain:
    """A node that emits unlimited, seeded, generated signal as SNP messages.

    Same interface as ``brain.Brain`` (emit / emit_labeled / node_id) so Nexus
    treats them interchangeably.

    Args:
        node_id: Node identity.
        encoding: SNP encoding id defining the output shape/modality.
        seed: Master seed; combined with node_id for a stable per-node stream.
        model: Optional prebuilt model (else built from the encoding).
        trace: Optional Basis TRACE recorder.
    """

    def __init__(
        self,
        node_id: str,
        *,
        encoding: str = "mi.c3czc4.mubeta.v1",
        seed: int = 0,
        model: Optional[GenerativeModel] = None,
        trace: Optional[Any] = None,
    ) -> None:
        from core import rng_for  # local import to avoid cycles at import time

        self.node_id = node_id
        self.encoding = encoding
        self.model = model or build_model(encoding)
        self.signal_type = self.model.signal_type
        self.paradigm = f"generative_{self.signal_type}"
        self._rng = rng_for(seed, "node", node_id)
        self._trace = trace
        self._last_label = ""

    def _build(self) -> Dict[str, Any]:
        vector, label = self.model.sample(self._rng)
        self._last_label = label
        message = {
            "node_id": self.node_id,
            "timestamp": int(time.time() * 1000),
            "signal_type": self.signal_type,
            "payload": {
                "vector": vector,
                "confidence": 1.0,
                "paradigm": self.paradigm,
                "encoding": self.encoding,
            },
        }
        return snp.normalize_validated(message)

    def emit(self) -> Dict[str, Any]:
        """Emit the next generated signal as a validated SNP message dict."""
        if self._trace is not None:
            with self._trace.span("brain", "emit", node_id=self.node_id):
                return self._build()
        return self._build()

    def emit_labeled(self) -> Tuple[Dict[str, Any], str]:
        """Emit the next message together with its ground-truth class label."""
        msg = self.emit()
        return msg, self._last_label
