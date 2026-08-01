"""Basis dashboard demo: one command -> the animated stack dashboard + figures.

Runs a small, capture-enabled graph and renders the four-panel + metrics
dashboard (micro signal -> action, meso room, macro consensus, metrics lens),
then the static policy/scale tradeoff figures.

Examples:
    python demos/dashboard/run.py --shards 12 --ticks 40
    python demos/dashboard/run.py --shards 12 --ticks 40 --policy quorum --out outputs/dash.mp4
    python demos/dashboard/run.py --figures-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

STACK_ROOT = Path(__file__).resolve().parents[2]
if str(STACK_ROOT) not in sys.path:
    sys.path.insert(0, str(STACK_ROOT))

from core import BasisConfig
from viz import collect, figure_policy_tradeoff, figure_scaling, render_dashboard

OUT = Path(__file__).parent / "outputs"


def main() -> None:
    p = argparse.ArgumentParser(description="Render the Basis stack dashboard + paper figures.")
    p.add_argument("--shards", type=int, default=12)
    p.add_argument("--min-nodes", type=int, default=2)
    p.add_argument("--max-nodes", type=int, default=8)
    p.add_argument("--resources", type=int, default=8)
    p.add_argument("--ticks", type=int, default=40)
    p.add_argument("--policy", type=str, default="lww")
    p.add_argument("--encoding", type=str, default="mi.8ch.mubeta.v1")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", type=str, default=str(OUT / "dashboard.gif"))
    p.add_argument("--figures-only", action="store_true")
    p.add_argument("--no-figures", action="store_true")
    args = p.parse_args()

    if not args.figures_only:
        cfg = BasisConfig.from_dict({
            "seed": args.seed,
            "ticks": args.ticks,
            "graph": {"n_shards": args.shards, "nodes_per_shard": [args.min_nodes, args.max_nodes],
                      "n_shared_resources": args.resources},
            "signal": {"source": "generative", "encoding": args.encoding},
            "fabric": {"policy": args.policy},
        })
        print(f"Collecting {args.ticks} ticks from {args.shards} shards (policy={args.policy}) ...")
        collection = collect(cfg)
        print(f"Rendering dashboard -> {args.out} ...")
        render_dashboard(collection, args.out)
        print(f"  nodes={collection.frames[-1].n_nodes} "
              f"resources={len(collection.resources)} "
              f"final_conflicts/tick={collection.frames[-1].conflicts_this_tick}")

    if not args.no_figures:
        f1 = figure_policy_tradeoff(OUT / "fig_policy_tradeoff.png")
        print(f"Wrote {f1}")
        f2 = figure_scaling(OUT / "fig_scaling.png")
        print(f"Wrote {f2}")

    print("Done.")


if __name__ == "__main__":
    main()
