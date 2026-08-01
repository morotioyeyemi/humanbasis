"""Basis Brain: synthetic neural node that replays real EEG as SNP messages."""

from __future__ import annotations

from .brain import PARADIGM_MI_LR, Brain
from .features import band_power_vector
from .generative import (
    ClassModel,
    GenerativeBrain,
    GenerativeModel,
    build_model,
)
from .loader import EpochSet, MI_LR_RUNS, load_mi_epochs

__all__ = [
    "Brain",
    "PARADIGM_MI_LR",
    "band_power_vector",
    "EpochSet",
    "MI_LR_RUNS",
    "load_mi_epochs",
    "GenerativeBrain",
    "GenerativeModel",
    "ClassModel",
    "build_model",
]
