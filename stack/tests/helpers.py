"""Shared fixtures/helpers for SNP tests."""

from __future__ import annotations

from typing import Any, Dict


def valid_motor_message() -> Dict[str, Any]:
    """A canonical, conforming Brain -> infra motor message."""
    return {
        "node_id": "brain_1",
        "timestamp": 1730000000000,
        "signal_type": "motor",
        "payload": {
            "vector": [0.42, 0.15, 0.38, 0.19, 0.41, 0.22],
            "confidence": 1.0,
            "paradigm": "motor_imagery_lr",
            "encoding": "mi.c3czc4.mubeta.v1",
        },
    }


def valid_perception_message() -> Dict[str, Any]:
    """A canonical, conforming Locus -> Brain perception message."""
    return {
        "node_id": "brain_1",
        "timestamp": 1730000000050,
        "signal_type": "perception",
        "payload": {
            "vector": [1.0, 0.0, 0.0, 3.2, 0.5],
            "confidence": 1.0,
            "paradigm": "locus_room_v1",
            "encoding": "env.room.pose_visible.v1",
        },
    }
