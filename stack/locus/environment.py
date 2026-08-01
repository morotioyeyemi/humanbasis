"""The white-room environment for Basis Locus v1.

A minimal, structured world (no game engine, no rendering): a square room with a
chair and one object on a wall. Each node has a 2D pose (x, y, heading). The
environment is the single source of truth; it applies node actions and computes
each node's first-person perception as a structured vector.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# Room geometry (metres, arbitrary units).
ROOM_MIN = 0.0
ROOM_MAX = 10.0
CHAIR_XY = (5.0, 5.0)
WALL_OBJECT_XY = (9.8, 5.0)  # on the right wall

STEP = 0.4          # forward distance per applied action
TURN = 0.45         # radians turned per left/right action
FOV_HALF = 0.6      # half field-of-view (radians) for object visibility
VIEW_RANGE = 12.0   # max distance the wall object is considered visible


@dataclass
class Pose:
    """A node's position and heading in the room."""

    x: float
    y: float
    heading: float  # radians, 0 = +x axis


@dataclass
class WhiteRoom:
    """Shared environment state: the single source of truth for the world.

    Attributes:
        poses: Node id -> Pose. The authoritative world state.
    """

    poses: Dict[str, Pose] = field(default_factory=dict)

    # --- state mutation ---------------------------------------------------
    def add_node(self, node_id: str, x: float, y: float, heading: float = 0.0) -> None:
        """Place a node in the room."""
        self.poses[node_id] = Pose(_clamp(x), _clamp(y), heading)

    def apply_action(self, node_id: str, action: str) -> None:
        """Apply a decoded action ("left"/"right"/"forward") to a node.

        A single authority (this room) applies actions in the order given, so
        same-cell collisions are resolved locally: a node that would leave the
        room or land on another node's cell simply does not advance. No
        distributed consensus is required at this scale.
        """
        pose = self.poses[node_id]
        if action == "left":
            pose.heading += TURN
        elif action == "right":
            pose.heading -= TURN
        # "forward" (and left/right after turning) step ahead.
        nx = pose.x + STEP * math.cos(pose.heading)
        ny = pose.y + STEP * math.sin(pose.heading)
        nx, ny = _clamp(nx), _clamp(ny)
        if not self._occupied(node_id, nx, ny):
            pose.x, pose.y = nx, ny

    def _occupied(self, mover: str, x: float, y: float, radius: float = 0.35) -> bool:
        for nid, p in self.poses.items():
            if nid == mover:
                continue
            if math.hypot(p.x - x, p.y - y) < radius:
                return True
        return False

    # --- perception -------------------------------------------------------
    def perceive(self, node_id: str) -> List[float]:
        """Compute a node's first-person perception vector.

        Layout matches SNP encoding ``env.room.pose_visible.v1``:
        ``[pose_x, pose_y, heading, distance_to_object, object_visible]``.
        """
        p = self.poses[node_id]
        dx = WALL_OBJECT_XY[0] - p.x
        dy = WALL_OBJECT_XY[1] - p.y
        distance = math.hypot(dx, dy)
        angle_to_obj = math.atan2(dy, dx)
        visible = 1.0 if (distance <= VIEW_RANGE and abs(_wrap(angle_to_obj - p.heading)) <= FOV_HALF) else 0.0
        return [p.x, p.y, _wrap(p.heading), distance, visible]

    def snapshot(self) -> Dict[str, Tuple[float, float, float]]:
        """Return a plain-data snapshot of all node poses (for rendering)."""
        return {nid: (p.x, p.y, p.heading) for nid, p in self.poses.items()}


def _clamp(v: float) -> float:
    return max(ROOM_MIN, min(ROOM_MAX, v))


def _wrap(a: float) -> float:
    """Wrap an angle to (-pi, pi]."""
    return (a + math.pi) % (2 * math.pi) - math.pi
