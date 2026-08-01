"""Tests for Basis Locus: environment, decoders, and the Locus boundary."""

from __future__ import annotations

import math

import snp
from locus import Locus, WhiteRoom, decoders
from locus.environment import ROOM_MAX, ROOM_MIN


def test_decoder_registered_for_v1_encoding():
    assert decoders.has_decoder("mi.c3czc4.mubeta.v1")


def test_decode_left_vs_right_by_lateralization():
    # Vector layout: [C3-mu, C3-beta, Cz-mu, Cz-beta, C4-mu, C4-beta].
    # Lower C3 power -> right hand -> "right".
    right_vec = [0.0, 0.0, 0.5, 0.5, 5.0, 5.0]  # C3 low, C4 high
    left_vec = [5.0, 5.0, 0.5, 0.5, 0.0, 0.0]   # C4 low, C3 high
    assert decoders.decode("mi.c3czc4.mubeta.v1", right_vec) == "right"
    assert decoders.decode("mi.c3czc4.mubeta.v1", left_vec) == "left"


def test_apply_action_stays_in_room():
    room = WhiteRoom()
    room.add_node("n1", ROOM_MAX, ROOM_MAX, heading=0.0)
    for _ in range(20):
        room.apply_action("n1", "forward")
    x, y, _ = room.snapshot()["n1"]
    assert ROOM_MIN <= x <= ROOM_MAX and ROOM_MIN <= y <= ROOM_MAX


def test_collision_blocks_move_single_authority():
    room = WhiteRoom()
    room.add_node("n1", 5.0, 5.0, heading=0.0)
    room.add_node("n2", 5.3, 5.0, heading=math.pi)  # facing n1, adjacent
    before = room.snapshot()["n2"]
    room.apply_action("n2", "forward")  # would step onto n1's cell
    after = room.snapshot()["n2"]
    assert before[:2] == after[:2]  # blocked, did not advance


def test_perception_vector_matches_env_encoding():
    locus = Locus()
    locus.add_node("n1", 2.0, 2.0, heading=0.0)
    msg = {
        "node_id": "n1",
        "timestamp": 1730000000000,
        "signal_type": "motor",
        "payload": {
            "vector": [5.0, 5.0, 0.5, 0.5, 0.0, 0.0],  # decodes "left"
            "confidence": 1.0,
            "paradigm": "motor_imagery_lr",
            "encoding": "mi.c3czc4.mubeta.v1",
        },
    }
    perception = locus.process(msg)
    validated = snp.validate(perception)
    assert validated.payload.encoding == "env.room.pose_visible.v1"
    assert validated.signal_type == "perception"
    assert len(validated.payload.vector) == 5
