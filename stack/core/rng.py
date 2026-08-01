"""Deterministic RNG helpers for reproducible runs.

A single master seed derives independent, stable sub-streams keyed by a string
(e.g. a node id), so the same seed always yields the same signals regardless of
iteration order or how many nodes exist.
"""

from __future__ import annotations

import hashlib

import numpy as np


def derive_seed(master_seed: int, *keys: str | int) -> int:
    """Derive a stable 63-bit sub-seed from a master seed and string/int keys."""
    h = hashlib.sha256()
    h.update(str(master_seed).encode())
    for k in keys:
        h.update(b"\x00")
        h.update(str(k).encode())
    return int.from_bytes(h.digest()[:8], "big") & ((1 << 63) - 1)


def rng_for(master_seed: int, *keys: str | int) -> np.random.Generator:
    """Return a numpy Generator seeded deterministically from master + keys."""
    return np.random.default_rng(derive_seed(master_seed, *keys))
