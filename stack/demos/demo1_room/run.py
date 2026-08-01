"""Demo 1: real EEG driving nodes in the shared white room.

Spins up N Basis Brains (replaying real EEGMMIDB motor imagery), runs them
through the Nexus signal loop into a single shared Locus, and renders a top-down
animation of the white room: each node is a dot whose motion is driven by its
own real motor-imagery signal (left/right hand -> turn left/right). Basis TRACE
observes every step; a latency summary is printed at the end.

Usage:
    python demos/demo1_room/run.py --nodes 4 --ticks 120 --subjects 1,2,3 --out demo1.gif
    python demos/demo1_room/run.py --synthetic          # offline, no download
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

# Make the stack packages importable when run as a script.
STACK_ROOT = Path(__file__).resolve().parents[2]
if str(STACK_ROOT) not in sys.path:
    sys.path.insert(0, str(STACK_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

import snp
from brain import Brain, EpochSet
from locus import CHAIR_XY, ROOM_MAX, ROOM_MIN, WALL_OBJECT_XY, Locus
from nexus import Nexus
from trace import Trace

ENCODING = "mi.c3czc4.mubeta.v1"


def _synthetic_epochs(seed: int) -> EpochSet:
    layout = snp.get_layout(ENCODING)
    n_ch = len(layout.channels)
    n_samples = int(round(layout.window_s * layout.rate_hz))
    rng = np.random.default_rng(seed)
    n_epochs = 40
    data = rng.standard_normal((n_epochs, n_ch, n_samples))
    # Bias half the epochs toward C3 vs C4 power so decoded actions vary.
    for i in range(n_epochs):
        if i % 2 == 0:
            data[i, 0:2] *= 1.6  # more C3 power -> decodes "left"
        else:
            data[i, 4:6] *= 1.6  # more C4 power -> decodes "right"
    labels = ["left" if i % 2 == 0 else "right" for i in range(n_epochs)]
    return EpochSet(data=data, labels=labels, channels=layout.channels, rate_hz=layout.rate_hz, subject=-1)


def build_brains(n_nodes: int, subjects: list[int], synthetic: bool, trace: Trace) -> list[Brain]:
    brains: list[Brain] = []
    for i in range(n_nodes):
        node_id = f"brain_{i + 1}"
        if synthetic:
            brains.append(Brain(node_id, _synthetic_epochs(seed=i), encoding=ENCODING, trace=trace))
        else:
            subject = subjects[i % len(subjects)]
            brains.append(Brain.from_subject(node_id, subject=subject, encoding=ENCODING, trace=trace))
    return brains


def place_nodes(locus: Locus, brains: list[Brain]) -> None:
    n = len(brains)
    cx, cy = (ROOM_MAX + ROOM_MIN) / 2, (ROOM_MAX + ROOM_MIN) / 2
    r = (ROOM_MAX - ROOM_MIN) * 0.3
    for i, brain in enumerate(brains):
        theta = 2 * math.pi * i / max(n, 1)
        x = cx + r * math.cos(theta)
        y = cy + r * math.sin(theta)
        locus.add_node(brain.node_id, x, y, heading=theta + math.pi)


def render(results, brains, out_path: Path) -> None:
    node_ids = [b.node_id for b in brains]
    colors = plt.cm.tab10(np.linspace(0, 1, max(len(node_ids), 1)))
    color_of = {nid: colors[i] for i, nid in enumerate(node_ids)}
    trails = {nid: ([], []) for nid in node_ids}

    fig, ax = plt.subplots(figsize=(6, 6))

    def draw(frame_idx: int):
        ax.clear()
        ax.set_xlim(ROOM_MIN - 0.5, ROOM_MAX + 0.5)
        ax.set_ylim(ROOM_MIN - 0.5, ROOM_MAX + 0.5)
        ax.set_aspect("equal")
        ax.set_facecolor("white")
        # Room walls.
        ax.add_patch(plt.Rectangle((ROOM_MIN, ROOM_MIN), ROOM_MAX - ROOM_MIN, ROOM_MAX - ROOM_MIN,
                                   fill=False, edgecolor="black", linewidth=2))
        # Chair and wall object.
        ax.scatter(*CHAIR_XY, marker="s", s=140, c="tan", edgecolors="black", label="chair", zorder=2)
        ax.scatter(*WALL_OBJECT_XY, marker="*", s=220, c="crimson", edgecolors="black", label="wall object", zorder=2)

        snap = results[frame_idx].snapshot
        for nid in node_ids:
            x, y, h = snap[nid]
            trails[nid][0].append(x)
            trails[nid][1].append(y)
            ax.plot(trails[nid][0], trails[nid][1], color=color_of[nid], alpha=0.35, linewidth=1)
            ax.scatter(x, y, s=90, color=color_of[nid], edgecolors="black", zorder=3)
            ax.arrow(x, y, 0.6 * math.cos(h), 0.6 * math.sin(h), head_width=0.2,
                     color=color_of[nid], zorder=3)
        ax.set_title(f"Basis Demo 1 - white room, real EEG driving {len(node_ids)} nodes  (tick {results[frame_idx].tick})")
        ax.legend(loc="upper left", fontsize=8)
        return []

    # Reset trails then animate.
    for nid in node_ids:
        trails[nid] = ([], [])
    anim = FuncAnimation(fig, draw, frames=len(results), blit=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    anim.save(str(out_path), writer=PillowWriter(fps=12))
    plt.close(fig)


def trace_summary(trace: Trace) -> str:
    def mean_latency(event: str) -> float:
        vals = [r.latency_ms for r in trace.records if r.event == event and r.latency_ms is not None]
        return sum(vals) / len(vals) if vals else 0.0

    return (
        f"TRACE: records={len(trace.records)} | "
        f"emit={mean_latency('emit'):.3f}ms decode={mean_latency('decode'):.3f}ms "
        f"apply={mean_latency('apply'):.3f}ms perceive={mean_latency('perceive'):.3f}ms"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Basis Demo 1: real EEG driving nodes in the white room.")
    parser.add_argument("--nodes", type=int, default=4)
    parser.add_argument("--ticks", type=int, default=120)
    parser.add_argument("--subjects", type=str, default="1,2,3")
    parser.add_argument("--synthetic", action="store_true", help="use synthetic signal (no download)")
    parser.add_argument("--out", type=str, default=str(Path(__file__).parent / "demo1.gif"))
    args = parser.parse_args()

    subjects = [int(s) for s in args.subjects.split(",") if s.strip()]
    trace = Trace()

    print(f"Building {args.nodes} brains ({'synthetic' if args.synthetic else 'EEGMMIDB subjects ' + str(subjects)})...")
    brains = build_brains(args.nodes, subjects, args.synthetic, trace)
    locus = Locus(trace=trace)
    place_nodes(locus, brains)
    nexus = Nexus(brains, locus, trace=trace)

    print(f"Running {args.ticks} ticks through the Nexus signal loop...")
    results = nexus.run(args.ticks)

    out_path = Path(args.out)
    print(f"Rendering {len(results)} frames -> {out_path} ...")
    render(results, brains, out_path)

    print(trace_summary(trace))
    print(f"Done. Open {out_path} to watch real brain signals move the nodes.")


if __name__ == "__main__":
    main()
