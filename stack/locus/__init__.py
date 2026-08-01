"""Basis Locus: shared environment state manager + neural-vector decoders."""

from __future__ import annotations

from . import decoders
from .environment import (
    CHAIR_XY,
    ROOM_MAX,
    ROOM_MIN,
    WALL_OBJECT_XY,
    Pose,
    WhiteRoom,
)
from .locus import PERCEPTION_ENCODING, PERCEPTION_PARADIGM, Locus

__all__ = [
    "Locus",
    "WhiteRoom",
    "Pose",
    "decoders",
    "PERCEPTION_ENCODING",
    "PERCEPTION_PARADIGM",
    "ROOM_MIN",
    "ROOM_MAX",
    "CHAIR_XY",
    "WALL_OBJECT_XY",
]
