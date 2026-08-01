"""Vector decoders for Basis Locus.

Locus is the consumption boundary for neural vectors: it is the one place a
signal becomes a world action, so it is the only component that interprets the
vector's meaning (the opaque-vector rule). Decoders are keyed by SNP encoding id,
so adding a modality/encoding means registering a new decoder here without
touching transport, Fabric, or TRACE.
"""

from __future__ import annotations

from typing import Callable, Dict, List

import snp

# An action the environment understands. Kept intentionally small for v1.
Action = str  # "left" | "right" | "forward"

Decoder = Callable[[List[float]], Action]

_DECODERS: Dict[str, Decoder] = {}


def register(encoding: str, decoder: Decoder) -> None:
    """Register a decoder for an encoding id."""
    _DECODERS[encoding] = decoder


def decode(encoding: str, vector: List[float]) -> Action:
    """Decode a vector into a world action using the encoding's decoder.

    Raises:
        KeyError: If no decoder is registered for the encoding.
    """
    return _DECODERS[encoding](vector)


def has_decoder(encoding: str) -> bool:
    """Return whether a decoder is registered for an encoding id."""
    return encoding in _DECODERS


def _decode_mi_lr(vector: List[float]) -> Action:
    """Decode left/right-hand motor imagery from C3/Cz/C4 mu/beta band power.

    Vector layout (mi.c3czc4.mubeta.v1):
        [C3-mu, C3-beta, Cz-mu, Cz-beta, C4-mu, C4-beta]

    Motor-imagery lateralization: imagining the RIGHT hand desynchronizes
    (lowers power in) the LEFT motor cortex (C3); imagining the LEFT hand lowers
    power over the RIGHT cortex (C4). So the side with LESS power indicates the
    imagined hand. Lower power over C3 -> right hand -> turn right; lower over
    C4 -> left hand -> turn left.
    """
    c3 = vector[0] + vector[1]
    c4 = vector[4] + vector[5]
    return "right" if c3 < c4 else "left"


# Register v1 decoders. Layout is validated against the registry on registration.
_layout = snp.get_layout("mi.c3czc4.mubeta.v1")
assert _layout.length == 6
register("mi.c3czc4.mubeta.v1", _decode_mi_lr)
