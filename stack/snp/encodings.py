"""SNP encoding registry.

The registry maps a short, versioned ``encoding`` id to the layout of the bare
float ``vector`` it labels. It is intentionally a set of static definitions, not
a service or shared mutable state: there is no runtime lookup on the transport
path beyond a dict access, no coordination, and no negotiation.

Encoding ids follow the grammar ``domain.specifics.layout.version`` and are
namespaced by their authoritative producer:

* ``mi.*``  -> Basis Brain is the authoritative producer (motor imagery).
* ``env.*`` -> Basis Locus is the authoritative producer (environment perception).

These definitions live in the neutral SNP contract package so that producers and
consumers both depend downward on the contract and never import one another.

Only the consuming boundary of a vector interprets it (the opaque-vector rule):
Basis Locus decodes ``mi.*`` neural vectors into world actions; Basis Brain would
decode ``env.*`` perception vectors in a future closed loop. SNP, Basis Fabric,
and Basis TRACE treat the vector as opaque floats and only ever check its length.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Layout:
    """The declared shape and meaning of a labeled float vector.

    Attributes:
        layout: The kind of encoding, e.g. ``"channel_band_power"``.
        channels: Ordered channel names the vector is built from.
        bands: Mapping of band name to its ``[low_hz, high_hz]`` range.
        order: How channels and bands are flattened, e.g. ``"channel_major"``.
        rate_hz: Sampling rate the source signal was resampled to.
        window_s: Window length, in seconds, of one emitted segment.
        length: The exact number of floats in a conforming vector.
    """

    layout: str
    channels: Tuple[str, ...]
    bands: Tuple[Tuple[str, Tuple[float, float]], ...]
    order: str
    rate_hz: float
    window_s: float
    length: int


# --- Registry -------------------------------------------------------------
# Add an entry here to scale channels or add a modality; nothing downstream
# changes because the infra treats the vector as opaque and reads only length.

REGISTRY: Dict[str, Layout] = {
    # Basis Brain v1: motor imagery, binary left/right hand.
    # 3 channels (C3, Cz, C4) x 2 bands (mu, beta) = 6 floats.
    "mi.c3czc4.mubeta.v1": Layout(
        layout="channel_band_power",
        channels=("C3", "Cz", "C4"),
        bands=(("mu", (8.0, 13.0)), ("beta", (13.0, 30.0))),
        order="channel_major",
        rate_hz=128.0,
        window_s=2.0,
        length=6,
    ),
    # Basis Locus v1: white-room perception update.
    # Illustrative layout; consumed only by Brain in a future closed loop.
    "env.room.pose_visible.v1": Layout(
        layout="pose_visible",
        channels=("pose_x", "pose_y", "heading", "distance_to_object", "object_visible"),
        bands=(),
        order="field_order",
        rate_hz=0.0,
        window_s=0.0,
        length=5,
    ),
}


def get_layout(encoding: str) -> Layout:
    """Return the ``Layout`` for an encoding id.

    Raises:
        KeyError: If the encoding id is not registered. Callers that want a
            typed SNP error should use ``snp.validate`` instead.
    """
    return REGISTRY[encoding]


def is_registered(encoding: str) -> bool:
    """Return whether an encoding id exists in the registry."""
    return encoding in REGISTRY


def expected_length(encoding: str) -> int:
    """Return the declared vector length for an encoding id."""
    return REGISTRY[encoding].length
