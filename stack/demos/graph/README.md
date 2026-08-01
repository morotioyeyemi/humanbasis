# Graph runner — Basis at scale

Drives a sharded, multi-authority world: many Basis Locus shards (each a small
room with a few nodes), nodes contending for shared resources, with Basis Fabric
resolving concurrent claims per a chosen consensus policy. Prints the
machine-readable metrics lens and graph summary; can write a deterministic JSONL
raw log.

```bash
# ~3000 authorities x 2-20 nodes (~30k nodes)
python demos/graph/run.py --shards 3000 --min-nodes 2 --max-nodes 20 --resources 2000 --ticks 10

# different consensus policy + wider modality, with a reproducible raw log
python demos/graph/run.py --shards 500 --policy crdt_merge \
    --encoding mi.16ch.mubeta.v1 --raw-log outputs/run.jsonl

# enable TRACE to get the full latency/bandwidth lens (slower)
python demos/graph/run.py --shards 200 --trace
```

Key flags: `--shards`, `--min-nodes/--max-nodes`, `--resources` (fewer than nodes
=> more contention), `--policy` (`lww`/`vector_clock`/`quorum`/`crdt_merge`),
`--replication`, `--encoding` (any registered modality/width), `--source`
(`generative`/`replay`), `--seed`, `--ticks`, `--raw-log`, `--config` (load a
`BasisConfig` JSON). Outputs go to `outputs/` (git-ignored).

Reference numbers (single-process dev machine, generative `mi.8ch.mubeta.v1`):
~33k nodes across 3000 shards at ~29-31k node-ticks/s (~1.1 s/tick), Fabric
resolving ~2000 conflicts/tick. Throughput is near-linear in node count; the raw
log is byte-identical across runs with the same seed.
