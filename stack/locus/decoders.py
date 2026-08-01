"""Vector decoders for Basis Locus.

Locus is the consumption boundary for neural vectors: it is the one place a
signal becomes a world action, so it is the only component that interprets the
vector's meaning (the opaque-vector rule). Decoders are keyed by SNP encoding id.

Decoders are registered for whole modality families programmatically:
- motor (``mi.*``): left/right by hemisphere band-power (motor-imagery
  lateralization) - the side with less power is the imagined hand.
- visual (``ssvep.*``): the dominant frequency band maps to an action.

Adding a modality/encoding means registering a decoder here; transport, Fabric,
and TRACE never interpret the vector.
"""

from __future__ import annotations

from typing import Callable, Dict, List

import snp
from core import hemisphere_labels
from core.montage import LEFT, RIGHT

Action = str  # "left" | "right" | "forward"
Decoder = Callable[[List[float]], Action]

_DECODERS: Dict[str, Decoder] = {}

# Visual dominant-frequency -> action mapping (by band index).
_VISUAL_ACTIONS = ["left", "right", "forward", "left"]


def register(encoding: str, decoder: Decoder) -> None:
    """Register a decoder for an encoding id."""
    _DECODERS[encoding] = decoder


def decode(encoding: str, vector: List[float]) -> Action:
    """Decode a vector into a world action using the encoding's decoder."""
    return _DECODERS[encoding](vector)


def has_decoder(encoding: str) -> bool:
    """Return whether a decoder is registered for an encoding id."""
    return encoding in _DECODERS


def _make_motor_decoder(encoding: str) -> Decoder:
    layout = snp.get_layout(encoding)
    n_bands = len(layout.bands)
    hemis = hemisphere_labels(layout.channels)
    left_idx = [ci * n_bands + bi for ci, h in enumerate(hemis) if h == LEFT for bi in range(n_bands)]
    right_idx = [ci * n_bands + bi for ci, h in enumerate(hemis) if h == RIGHT for bi in range(n_bands)]

    def decoder(vector: List[float]) -> Action:
        left_power = sum(vector[i] for i in left_idx)
        right_power = sum(vector[i] for i in right_idx)
        # Less power over a hemisphere => imagined the contralateral hand.
        return "right" if left_power < right_power else "left"

    return decoder


def _make_visual_decoder(encoding: str) -> Decoder:
    layout = snp.get_layout(encoding)
    n_channels = len(layout.channels)
    n_bands = len(layout.bands)

    def decoder(vector: List[float]) -> Action:
        band_power = [
            sum(vector[ci * n_bands + bi] for ci in range(n_channels))
            for bi in range(n_bands)
        ]
        dominant = max(range(n_bands), key=lambda bi: band_power[bi])
        return _VISUAL_ACTIONS[dominant % len(_VISUAL_ACTIONS)]

    return decoder


def _register_all() -> None:
    for encoding, layout in snp.REGISTRY.items():
        if layout.signal_type == "motor":
            register(encoding, _make_motor_decoder(encoding))
        elif layout.signal_type == "visual":
            register(encoding, _make_visual_decoder(encoding))


_register_all()
