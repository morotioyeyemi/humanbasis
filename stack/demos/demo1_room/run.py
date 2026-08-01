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
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter

try:  # optional: bundled ffmpeg for .mp4 output
    import imageio_ffmpeg

    plt.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
    _HAVE_FFMPEG = True
except Exception:  # pragma: no cover - mp4 is optional
    _HAVE_FFMPEG = False

import snp
from brain import Brain, EpochSet
from locus import Locus
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
    size = locus.room.size
    cx, cy = size / 2, size / 2
    rng = np.random.default_rng(7)
    # Ring for small N (clear), scattered fill for large N.
    for i, brain in enumerate(brains):
        if n <= 24:
            theta = 2 * math.pi * i / max(n, 1)
            r = size * 0.3
            x, y = cx + r * math.cos(theta), cy + r * math.sin(theta)
            heading = theta + math.pi
        else:
            x, y = rng.uniform(0.05 * size, 0.95 * size, size=2)
            heading = rng.uniform(-math.pi, math.pi)
        locus.add_node(brain.node_id, float(x), float(y), heading=float(heading))


def render(results, brains, locus: Locus, out_path: Path) -> None:
    node_ids = [b.node_id for b in brains]
    n = len(node_ids)
    size = locus.room.size
    chair_xy = locus.room.chair_xy
    wall_object_xy = locus.room.wall_object_xy
    colors = plt.cm.tab20(np.linspace(0, 1, max(n, 1)))
    color_of = {nid: colors[i % 20] for i, nid in enumerate(node_ids)}
    trails = {nid: ([], []) for nid in node_ids}

    big = n > 40
    dot_size = max(8, 90 - n // 3) if not big else 46
    draw_arrows = not big
    draw_trails = True
    trail_alpha = 0.35 if not big else 0.16

    fig, ax = plt.subplots(figsize=(7, 7))

    def draw(frame_idx: int):
        ax.clear()
        ax.set_xlim(-0.05 * size, 1.05 * size)
        ax.set_ylim(-0.05 * size, 1.05 * size)
        ax.set_aspect("equal")
        ax.set_facecolor("white")
        ax.add_patch(plt.Rectangle((0, 0), size, size, fill=False, edgecolor="black", linewidth=2))
        ax.scatter(*chair_xy, marker="s", s=140, c="tan", edgecolors="black", label="chair", zorder=2)
        ax.scatter(*wall_object_xy, marker="*", s=240, c="crimson", edgecolors="black", label="wall object", zorder=2)

        snap = results[frame_idx].snapshot
        xs, ys, cs = [], [], []
        for nid in node_ids:
            x, y, h = snap[nid]
            if draw_trails:
                trails[nid][0].append(x)
                trails[nid][1].append(y)
                ax.plot(trails[nid][0], trails[nid][1], color=color_of[nid], alpha=trail_alpha, linewidth=1)
            if draw_arrows:
                ax.arrow(x, y, 0.02 * size * math.cos(h), 0.02 * size * math.sin(h),
                         head_width=0.01 * size, color=color_of[nid], zorder=3)
            xs.append(x)
            ys.append(y)
            cs.append(color_of[nid])
        ax.scatter(xs, ys, s=dot_size, color=cs, edgecolors="black",
                   linewidths=0.5, zorder=3)
        ax.set_title(f"Basis Demo 1 - {size:g}x{size:g} room, {n} nodes  (tick {results[frame_idx].tick})")
        ax.legend(loc="upper left", fontsize=8)
        return []

    for nid in node_ids:
        trails[nid] = ([], [])
    anim = FuncAnimation(fig, draw, frames=len(results), blit=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".mp4":
        if not _HAVE_FFMPEG:
            raise RuntimeError("mp4 output needs ffmpeg; pip install imageio-ffmpeg (or use a .gif path)")
        anim.save(str(out_path), writer=FFMpegWriter(fps=15, bitrate=2400))
    else:
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
    parser.add_argument("--room-size", type=float, default=10.0, help="side length of the square room")
    parser.add_argument("--synthetic", action="store_true", help="use synthetic signal (no download)")
    parser.add_argument("--no-render", action="store_true", help="run the loop only, skip the gif (scale test)")
    parser.add_argument("--out", type=str, default=str(Path(__file__).parent / "outputs" / "demo1.gif"),
                        help="output path; extension picks the format (.gif or .mp4)")
    args = parser.parse_args()

    import time as _time

    subjects = [int(s) for s in args.subjects.split(",") if s.strip()]
    trace = Trace()

    print(f"Building {args.nodes} brains ({'synthetic' if args.synthetic else 'EEGMMIDB subjects ' + str(subjects)})...")
    t0 = _time.perf_counter()
    brains = build_brains(args.nodes, subjects, args.synthetic, trace)
    locus = Locus(size=args.room_size, trace=trace)
    place_nodes(locus, brains)
    nexus = Nexus(brains, locus, trace=trace)
    build_s = _time.perf_counter() - t0

    print(f"Running {args.ticks} ticks x {args.nodes} nodes in a {args.room_size:g}x{args.room_size:g} room...")
    t1 = _time.perf_counter()
    results = nexus.run(args.ticks)
    loop_s = _time.perf_counter() - t1
    node_ticks = args.ticks * args.nodes
    print(f"Loop: {loop_s:.2f}s for {node_ticks} node-ticks "
          f"({node_ticks / loop_s:,.0f} node-ticks/s, {loop_s / args.ticks * 1000:.1f} ms/tick). "
          f"Build: {build_s:.2f}s.")

    if not args.no_render:
        out_path = Path(args.out)
        print(f"Rendering {len(results)} frames -> {out_path} ...")
        render(results, brains, locus, out_path)
        print(f"Done. Open {out_path} to watch the room.")

    print(trace_summary(trace))


if __name__ == "__main__":
    main()
