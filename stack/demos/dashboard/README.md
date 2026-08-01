# Basis stack dashboard + paper figures

The best way to *see* what the stack is doing. From a single captured run this
renders one animated figure that connects all four levels of the stack, plus the
static tradeoff figures a systems paper needs. No media is committed; generate it
yourself into `outputs/` (git-ignored).

```bash
pip install -e ".[viz]"
python demos/dashboard/run.py --shards 12 --ticks 40            # dashboard.gif + figures
python demos/dashboard/run.py --policy quorum --out outputs/dash.mp4
python demos/dashboard/run.py --figures-only                    # just the paper figures
```

## The dashboard (animated)

One figure, five panels, all from the same tick so you see cause -> effect:

- **micro - node signals -> action:** one focus shard's band-power vectors as an
  equalizer, each bar tinted by its decoded action (left/right/forward). This is
  "brain signal becomes behavior."
- **meso - shared room:** that shard's room with nodes (dot + heading), tinted by
  the same action. This is nodes acting in a shared world.
- **macro - resource ownership:** a heatmap of which node holds each shared
  resource over time. This is Basis Fabric consensus, made visible.
- **macro - conflicts/tick:** how many concurrent claims Fabric resolved each
  tick (the consistency workload under contention).
- **metrics - per-stage latency:** p50/p95/p99 for emit/decode/apply/perceive/
  commit from the TRACE lens (the infrastructure cost).

Why this layout: the macro system (thousands of shards, tens of thousands of
nodes) is not legible as dots on a map; consensus ownership + conflicts + latency
are what actually tell the story. One representative room and one node's signal
make the micro/meso concrete.

## Static figures (paper-ready)

- `fig_policy_tradeoff.png` - conflicts/tick and mean commit latency across the
  four consensus policies (same contention, different cost).
- `fig_scaling.png` - throughput (node-ticks/s) and per-tick latency vs node
  count.

Everything is deterministic given `--seed`, so figures and the dashboard
reproduce exactly.
