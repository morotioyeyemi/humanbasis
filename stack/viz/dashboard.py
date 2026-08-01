"""Compose the animated multi-panel Basis stack dashboard.

Lays out the four comprehension panels + metrics from a single captured run into
one figure and animates it across ticks: micro (signal->action), meso (room),
macro (consensus ownership + conflicts), and metrics (latency lens). Saves .mp4
or .gif by extension.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

try:
    import imageio_ffmpeg
    from matplotlib.animation import FFMpegWriter

    plt.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
    _HAVE_FFMPEG = True
except Exception:  # pragma: no cover
    _HAVE_FFMPEG = False

from .collector import Collection
from .panels import draw_conflicts, draw_consensus, draw_lens, draw_room, draw_signal


def render_dashboard(collection: Collection, out_path: str | Path, *, fps: int = 6) -> Path:
    """Render the animated dashboard to ``out_path`` (.mp4 or .gif)."""
    out_path = Path(out_path)
    room_size = collection.config["graph"]["room_size"]
    policy = collection.config["fabric"]["policy"]
    n_shards = collection.frames[0].n_shards if collection.frames else 0

    fig = plt.figure(figsize=(13, 8.5))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1], width_ratios=[1.1, 1.1, 1.2],
                          hspace=0.38, wspace=0.28)
    ax_signal = fig.add_subplot(gs[0, 0])
    ax_room = fig.add_subplot(gs[0, 1])
    ax_lens = fig.add_subplot(gs[0, 2])
    ax_consensus = fig.add_subplot(gs[1, 0:2])
    ax_conflicts = fig.add_subplot(gs[1, 2])

    def draw(i: int):
        frame = collection.frames[i]
        draw_signal(ax_signal, frame)
        draw_room(ax_room, frame, room_size=room_size)
        draw_lens(ax_lens, collection)
        draw_consensus(ax_consensus, collection, upto_tick=i)
        draw_conflicts(ax_conflicts, collection, upto_tick=i)
        fig.suptitle(
            f"Basis stack dashboard - {n_shards} shards, {frame.n_nodes} nodes, "
            f"policy={policy}  (tick {frame.tick})",
            fontsize=13, fontweight="bold",
        )
        return []

    anim = FuncAnimation(fig, draw, frames=len(collection.frames), blit=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".mp4":
        if not _HAVE_FFMPEG:
            raise RuntimeError("mp4 needs ffmpeg; pip install imageio-ffmpeg or use .gif")
        anim.save(str(out_path), writer=FFMpegWriter(fps=fps, bitrate=3000))
    else:
        anim.save(str(out_path), writer=PillowWriter(fps=fps))
    plt.close(fig)
    return out_path
