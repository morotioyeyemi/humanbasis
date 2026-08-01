"""The white-room environment for Basis Locus v1.

A minimal, structured world (no game engine, no rendering): a square room with a
chair and one object on a wall. Each node has a 2D pose (x, y, heading). The
environment is the single source of truth; it applies node actions and computes
each node's first-person perception as a structured vector.

The room is size-parameterized: movement step, collision radius, and view range
scale with the room so behaviour is consistent across sizes. Defaults reproduce
the original 10x10 room.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Defaults for the original 10x10 room (kept for tests and simple callers).
ROOM_MIN = 0.0
ROOM_MAX = 10.0
CHAIR_XY = (5.0, 5.0)
WALL_OBJECT_XY = (9.8, 5.0)  # on the right wall


@dataclass
class Pose:
    """A node's position and heading in the room."""

    x: float
    y: float
    heading: float  # radians, 0 = +x axis


class WhiteRoom:
    """Shared environment state: the single source of truth for the world.

    Args:
        size: Side length of the square room. Chair, wall object, step size,
            collision radius, and view range all scale from this.

    Attributes:
        size: Side length of the room (min corner is 0, max corner is ``size``).
        chair_xy: Chair position.
        wall_object_xy: Wall-object position (on the right wall).
        step: Forward distance per applied action.
        turn: Radians turned per left/right action.
        collision_radius: Minimum separation enforced between nodes.
        view_range: Max distance at which the wall object is visible.
        poses: Node id -> Pose. The authoritative world state.
    """

    FOV_HALF = 0.6  # half field-of-view (radians) for object visibility

    def __init__(self, size: float = ROOM_MAX) -> None:
        self.size = float(size)
        self.chair_xy: Tuple[float, float] = (self.size * 0.5, self.size * 0.5)
        self.wall_object_xy: Tuple[float, float] = (self.size * 0.98, self.size * 0.5)
        self.step = self.size / 25.0             # 0.4 at size 10
        self.turn = 0.45
        self.collision_radius = self.size * 0.035  # 0.35 at size 10
        self.view_range = self.size * 1.2          # 12 at size 10
        self.poses: Dict[str, Pose] = {}

    # --- state mutation ---------------------------------------------------
    def add_node(self, node_id: str, x: float, y: float, heading: float = 0.0) -> None:
        """Place a node in the room."""
        self.poses[node_id] = Pose(self._clamp(x), self._clamp(y), heading)

    def apply_action(self, node_id: str, action: str) -> None:
        """Apply a decoded action ("left"/"right"/"forward") to a node.

        A single authority (this room) applies actions in the order given, so
        same-cell collisions are resolved locally: a node that would leave the
        room or land on another node's cell simply does not advance. No
        distributed consensus is required at this scale.
        """
        pose = self.poses[node_id]
        if action == "left":
            pose.heading += self.turn
        elif action == "right":
            pose.heading -= self.turn
        nx = pose.x + self.step * math.cos(pose.heading)
        ny = pose.y + self.step * math.sin(pose.heading)
        nx, ny = self._clamp(nx), self._clamp(ny)
        if not self._occupied(node_id, nx, ny):
            pose.x, pose.y = nx, ny

    def _occupied(self, mover: str, x: float, y: float) -> bool:
        r = self.collision_radius
        for nid, p in self.poses.items():
            if nid == mover:
                continue
            if math.hypot(p.x - x, p.y - y) < r:
                return True
        return False

    # --- perception -------------------------------------------------------
    def perceive(self, node_id: str) -> List[float]:
        """Compute a node's first-person perception vector.

        Layout matches SNP encoding ``env.room.pose_visible.v1``:
        ``[pose_x, pose_y, heading, distance_to_object, object_visible]``.
        """
        p = self.poses[node_id]
        dx = self.wall_object_xy[0] - p.x
        dy = self.wall_object_xy[1] - p.y
        distance = math.hypot(dx, dy)
        angle_to_obj = math.atan2(dy, dx)
        visible = 1.0 if (distance <= self.view_range and abs(_wrap(angle_to_obj - p.heading)) <= self.FOV_HALF) else 0.0
        return [p.x, p.y, _wrap(p.heading), distance, visible]

    def snapshot(self) -> Dict[str, Tuple[float, float, float]]:
        """Return a plain-data snapshot of all node poses (for rendering)."""
        return {nid: (p.x, p.y, p.heading) for nid, p in self.poses.items()}

    def _clamp(self, v: float) -> float:
        return max(0.0, min(self.size, v))


def _wrap(a: float) -> float:
    """Wrap an angle to (-pi, pi]."""
    return (a + math.pi) % (2 * math.pi) - math.pi
