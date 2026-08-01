"""Panel renderers for the Basis stack dashboard.

Each function draws one panel onto a matplotlib Axes for a given frame, so the
same panels are reused by the animated dashboard and by static figures. Panels:
signal (micro), room (meso), consensus (macro), lens (metrics).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np

ACTION_COLORS = {"left": "#1f77b4", "right": "#d62728", "forward": "#2ca02c"}
_STAGE_ORDER = ["emit", "decode", "apply", "perceive", "commit"]


def draw_signal(ax, frame, *, max_nodes: int = 8) -> None:
    """Micro: focus-shard node signal vectors as an equalizer, tinted by action."""
    ax.clear()
    signals = list(frame.focus_signals.items())[:max_nodes]
    if not signals:
        ax.set_title("signal - (no focus data)")
        ax.axis("off")
        return
    length = len(signals[0][1]["vector"])
    ax.set_title(f"micro: node signals -> action  (shard {frame.focus_shard})", fontsize=9)
    width = 0.8 / max(len(signals), 1)
    x = np.arange(length)
    for i, (nid, s) in enumerate(signals):
        color = ACTION_COLORS.get(s["action"], "#555555")
        ax.bar(x + i * width, s["vector"], width=width, color=color, edgecolor="none", alpha=0.85)
    ax.set_xlabel("feature (channel x band)", fontsize=8)
    ax.set_ylabel("band power", fontsize=8)
    handles = [ax.plot([], [], color=c, lw=6)[0] for c in ACTION_COLORS.values()]
    ax.legend(handles, list(ACTION_COLORS.keys()), fontsize=7, loc="upper right", title="decoded action", title_fontsize=7)
    ax.tick_params(labelsize=7)


def draw_room(ax, frame, *, room_size: float = 10.0) -> None:
    """Meso: the focus shard's room with nodes (dots + heading), tinted by action."""
    ax.clear()
    ax.set_title(f"meso: shared room  (shard {frame.focus_shard}, {len(frame.focus_room)} nodes)", fontsize=9)
    ax.set_xlim(-0.05 * room_size, 1.05 * room_size)
    ax.set_ylim(-0.05 * room_size, 1.05 * room_size)
    ax.set_aspect("equal")
    ax.add_patch(_rect(room_size))
    actions = {nid: s["action"] for nid, s in frame.focus_signals.items()}
    for nid, (x, y, h) in frame.focus_room.items():
        color = ACTION_COLORS.get(actions.get(nid, ""), "#555555")
        ax.scatter(x, y, s=80, color=color, edgecolors="black", zorder=3)
        ax.arrow(x, y, 0.05 * room_size * math.cos(h), 0.05 * room_size * math.sin(h),
                 head_width=0.02 * room_size, color=color, zorder=3)
    ax.tick_params(labelsize=7)


def draw_consensus(ax, collection, upto_tick: int) -> None:
    """Macro: resource-ownership heatmap (resources x time) up to a tick."""
    ax.clear()
    matrix = np.asarray(collection.ownership_matrix(), dtype=float)
    if matrix.size == 0:
        ax.set_title("macro: consensus - (no data)")
        ax.axis("off")
        return
    shown = matrix[:, : upto_tick + 1]
    masked = np.ma.masked_less(shown, 0)
    cmap = _get_cmap("tab20").copy()
    cmap.set_bad(color="#eeeeee")
    ax.imshow(masked, aspect="auto", cmap=cmap, interpolation="nearest",
              extent=[0, shown.shape[1], shown.shape[0], 0])
    ax.set_title("macro: resource ownership (color = holding node)", fontsize=9)
    ax.set_xlabel("tick", fontsize=8)
    ax.set_ylabel("shared resource", fontsize=8)
    ax.tick_params(labelsize=7)


def draw_conflicts(ax, collection, upto_tick: int) -> None:
    """Macro companion: conflicts resolved per tick (the Fabric workload)."""
    ax.clear()
    series = collection.conflict_series()[: upto_tick + 1]
    ax.plot(range(len(series)), series, color="#d62728", lw=1.5)
    ax.fill_between(range(len(series)), series, color="#d62728", alpha=0.2)
    ax.set_title("macro: conflicts resolved / tick", fontsize=9)
    ax.set_xlabel("tick", fontsize=8)
    ax.set_ylabel("conflicts", fontsize=8)
    total = collection.frames[0].n_shards if collection.frames else 0
    ax.set_xlim(0, max(len(collection.conflict_series()) - 1, 1))
    ax.tick_params(labelsize=7)


def draw_lens(ax, collection) -> None:
    """Metrics: per-stage latency percentiles (p50/p95/p99) from the TRACE lens."""
    ax.clear()
    latency = collection.metrics.get("latency", {})
    stages = [s for s in _STAGE_ORDER if s in latency]
    if not stages:
        ax.set_title("metrics: lens - (no latency)")
        ax.axis("off")
        return
    x = np.arange(len(stages))
    p50 = [latency[s]["p50_ms"] for s in stages]
    p95 = [latency[s]["p95_ms"] for s in stages]
    p99 = [latency[s]["p99_ms"] for s in stages]
    ax.bar(x - 0.25, p50, width=0.25, label="p50", color="#2ca02c")
    ax.bar(x, p95, width=0.25, label="p95", color="#ff7f0e")
    ax.bar(x + 0.25, p99, width=0.25, label="p99", color="#d62728")
    ax.set_title("metrics: per-stage latency (ms)", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(stages, fontsize=7)
    ax.set_ylabel("ms", fontsize=8)
    ax.legend(fontsize=7)
    ax.tick_params(labelsize=7)


# --- small helpers ----------------------------------------------------------

def _rect(size):
    import matplotlib.pyplot as plt

    return plt.Rectangle((0, 0), size, size, fill=False, edgecolor="black", linewidth=2)


def _get_cmap(name):
    import matplotlib as mpl

    try:
        return mpl.colormaps[name]
    except Exception:  # pragma: no cover - older matplotlib
        import matplotlib.pyplot as plt

        return plt.cm.get_cmap(name)
