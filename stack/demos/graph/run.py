"""Basis graph runner: drive a sharded multi-authority world at scale.

Builds a Graph from a config (CLI-parameterized or a JSON file), runs it for a
number of ticks, and prints the machine-readable metrics lens + graph summary.
Optionally writes a deterministic JSONL raw log for reproducibility.

Examples:
    python demos/graph/run.py --shards 3000 --min-nodes 2 --max-nodes 20
    python demos/graph/run.py --shards 500 --policy crdt_merge --encoding mi.16ch.mubeta.v1
    python demos/graph/run.py --config myrun.json --raw-log outputs/run.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

STACK_ROOT = Path(__file__).resolve().parents[2]
if str(STACK_ROOT) not in sys.path:
    sys.path.insert(0, str(STACK_ROOT))

from core import BasisConfig
from nexus.graph import Graph
from trace import Lens, Trace


def build_config(args) -> BasisConfig:
    if args.config:
        return BasisConfig.load(args.config)
    return BasisConfig.from_dict({
        "seed": args.seed,
        "ticks": args.ticks,
        "graph": {
            "n_shards": args.shards,
            "nodes_per_shard": [args.min_nodes, args.max_nodes],
            "room_size": args.room_size,
            "n_shared_resources": args.resources,
        },
        "signal": {"source": args.source, "encoding": args.encoding},
        "fabric": {"policy": args.policy, "replication_factor": args.replication},
        "log": {"raw_log_path": args.raw_log},
    })


def main() -> None:
    p = argparse.ArgumentParser(description="Run a Basis sharded graph at scale.")
    p.add_argument("--config", type=str, default=None, help="load a BasisConfig JSON (overrides flags)")
    p.add_argument("--shards", type=int, default=1000)
    p.add_argument("--min-nodes", type=int, default=2)
    p.add_argument("--max-nodes", type=int, default=20)
    p.add_argument("--resources", type=int, default=1000)
    p.add_argument("--room-size", type=float, default=10.0)
    p.add_argument("--encoding", type=str, default="mi.8ch.mubeta.v1")
    p.add_argument("--source", type=str, default="generative")
    p.add_argument("--policy", type=str, default="lww")
    p.add_argument("--replication", type=int, default=1)
    p.add_argument("--ticks", type=int, default=20)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--raw-log", type=str, default=None)
    p.add_argument("--trace", action="store_true", help="enable TRACE (slower; enables the lens)")
    args = p.parse_args()

    cfg = build_config(args)
    trace = Trace() if args.trace else None

    print(f"Building graph: {cfg.graph.n_shards} shards x {cfg.graph.nodes_per_shard} nodes, "
          f"policy={cfg.fabric.policy}, encoding={cfg.signal.encoding} ...")
    t0 = time.perf_counter()
    g = Graph(cfg, trace=trace, run_log_path=cfg.log.raw_log_path)
    n = g.n_nodes()
    build_s = time.perf_counter() - t0

    print(f"Running {cfg.ticks} ticks over {n:,} nodes ...")
    t1 = time.perf_counter()
    results = g.run(cfg.ticks)
    loop_s = time.perf_counter() - t1
    g.close()

    node_ticks = n * cfg.ticks
    last = results[-1]
    print(f"\n=== graph summary ===\n{json.dumps(g.summary(), indent=2)}")
    print(f"\nbuild={build_s:.2f}s  loop={loop_s:.2f}s  "
          f"per_tick={loop_s / cfg.ticks * 1000:.0f}ms  "
          f"throughput={node_ticks / loop_s:,.0f} node-ticks/s")
    print(f"conflicts_last_tick={last.conflicts_this_tick}  "
          f"total_conflicts={last.fabric_metrics['conflicts']}  "
          f"committed_keys={len(last.holders)}")
    if trace is not None:
        print(f"\n=== lens ===\n{json.dumps(Lens.from_trace(trace).summary(), indent=2)}")


if __name__ == "__main__":
    main()
