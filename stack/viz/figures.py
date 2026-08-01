"""Static paper-style figures: consensus/latency tradeoffs across policy and scale.

Sweeps the graph over consensus policies and scale, then plots the tradeoff
curves a systems paper needs: conflicts-per-tick and per-tick latency vs policy,
and throughput vs node count. Uses the metrics lens and deterministic runs.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from core import BasisConfig
from nexus.graph import Graph
from trace import Lens, Trace

POLICIES = ["lww", "vector_clock", "quorum", "crdt_merge"]


def _run(shards: int, policy: str, resources: int, ticks: int, seed: int = 0, trace: bool = False):
    cfg = BasisConfig.from_dict({
        "seed": seed,
        "graph": {"n_shards": shards, "nodes_per_shard": [2, 20], "n_shared_resources": resources},
        "signal": {"source": "generative", "encoding": "mi.8ch.mubeta.v1"},
        "fabric": {"policy": policy},
    })
    tr = Trace() if trace else None
    g = Graph(cfg, trace=tr)
    n = g.n_nodes()
    t0 = time.perf_counter()
    results = g.run(ticks)
    elapsed = time.perf_counter() - t0
    conflicts = [r.conflicts_this_tick for r in results]
    lens = Lens.from_trace(tr).summary() if tr else {}
    return {"n_nodes": n, "elapsed": elapsed, "ticks": ticks,
            "avg_conflicts": sum(conflicts) / len(conflicts), "lens": lens}


def figure_policy_tradeoff(out_path: Path, *, shards: int = 200, resources: int = 100, ticks: int = 10) -> Path:
    """Conflicts/tick and mean commit latency per consensus policy."""
    avg_conflicts: List[float] = []
    commit_latency: List[float] = []
    for p in POLICIES:
        r = _run(shards, p, resources, ticks, trace=True)
        avg_conflicts.append(r["avg_conflicts"])
        commit = r["lens"].get("latency", {}).get("commit", {})
        commit_latency.append(commit.get("mean_ms", 0.0))

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    a1.bar(POLICIES, avg_conflicts, color="#d62728")
    a1.set_title(f"Conflicts resolved / tick ({shards} shards, {resources} resources)")
    a1.set_ylabel("avg conflicts / tick")
    a1.tick_params(axis="x", rotation=20)
    a2.bar(POLICIES, commit_latency, color="#1f77b4")
    a2.set_title("Mean Fabric commit latency")
    a2.set_ylabel("ms")
    a2.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path


def figure_scaling(out_path: Path, *, shard_counts=(50, 100, 200, 400, 800), ticks: int = 6) -> Path:
    """Throughput (node-ticks/s) and per-tick latency vs node count."""
    ns: List[int] = []
    throughput: List[float] = []
    per_tick_ms: List[float] = []
    for shards in shard_counts:
        r = _run(shards, "lww", max(shards // 2, 1), ticks)
        ns.append(r["n_nodes"])
        throughput.append(r["n_nodes"] * ticks / r["elapsed"])
        per_tick_ms.append(r["elapsed"] / ticks * 1000)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    a1.plot(ns, throughput, "o-", color="#2ca02c")
    a1.set_title("Throughput vs scale")
    a1.set_xlabel("nodes")
    a1.set_ylabel("node-ticks / s")
    a1.grid(alpha=0.3)
    a2.plot(ns, per_tick_ms, "o-", color="#ff7f0e")
    a2.set_title("Per-tick latency vs scale")
    a2.set_xlabel("nodes")
    a2.set_ylabel("ms / tick")
    a2.grid(alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path
