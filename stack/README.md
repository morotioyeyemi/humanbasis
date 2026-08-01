# Basis Nexus (stack)

The Basis stack: many neural nodes connected into a shared real-time environment,
with a distributed consistency layer and passive instrumentation, driveable by AI
agents. v1 is single-machine and Python-only; nodes replay real open EEG or emit
unlimited lightweight-generative signal across multiple modalities.

## Components

| Package | Role | Status |
| ------- | ---- | ------ |
| `snp/`     | **SNP** — the canonical message contract everything speaks (library, not a service). Parameterized encodings 6..256 floats across modalities. | done |
| `brain/`   | **Basis Brain** — node; replays real EEGMMIDB motor imagery or emits lightweight generative motor/visual signal (seeded, unlimited, non-repeating). | done |
| `locus/`   | **Basis Locus** — shared room state; decodes neural vectors into actions and emits perception. The vector consumption boundary. | done |
| `fabric/`  | **Basis Fabric** — real distributed state consensus engine; pluggable policies (lww/vector_clock/quorum/crdt_merge) + replication. | done |
| `nexus/`   | **Nexus** — integration: the single-room signal loop and the sharded multi-authority **graph** (`nexus/graph.py`). | done |
| `trace/`   | **Basis TRACE** — passive metrics + the **lens** (latency percentiles, throughput, bandwidth) over live traces or JSONL raw logs. | done |
| `core/`    | Cross-cutting: parameterized `BasisConfig`, deterministic seeding, montage convention. | done |
| `service/` | Agent control surface + **MCP server** to inspect/run/scale/tune the whole stack. | done |
| `evals/`   | Acceptance-criteria harness (eval-driven): conformance, consistency, generative quality, reproducibility, scaling, performance, MCP. | done |

## The signal loop

```
Brain.emit() -> SNP -> Locus (decode + apply) -> perception -> SNP
        Fabric resolves concurrent shared-state writes across authorities
                     \____________ TRACE observes every step ____________/
```

- **Opaque-vector rule:** SNP, Fabric, and TRACE never interpret the vector.
  Only **Locus** (the consumption boundary) decodes it into a world action.
- **Encoding by reference:** each message carries a short `encoding` id; the
  layout lives in the SNP registry. Adding a modality or scaling channel width
  (6..256 floats) is a registry edit, with no downstream change.
- **Fabric = distributed consensus:** a single Locus is one authority (sequential
  application is trivial consensus). Fabric earns its keep in the **graph**, where
  many Locus authorities host nodes that contend for shared resources; concurrent
  claims are resolved deterministically per the chosen policy.

## Basis at scale (the graph)

A sharded, multi-authority world: many Locus shards, nodes contending for shared
resources, Fabric resolving conflicts each tick. Everything is config-driven and
reproducible (same seed -> byte-identical raw logs), and scale can be ramped
live.

```bash
python demos/graph/run.py --shards 3000 --min-nodes 2 --max-nodes 20 --ticks 10
```

Reference: ~33k nodes across 3000 shards at ~29-31k node-ticks/s (~1.1 s/tick),
Fabric resolving ~2000 conflicts/tick. See [`demos/graph/`](demos/graph/README.md).

## Agent control (MCP)

Agents inspect, run, scale, and tune the stack via an MCP server (JSON-RPC over
stdio) — the AI-first pillar. See [`service/`](service/README.md).

```bash
python -m service.mcp_server
```

## Demo 1 (the visual)

The first visual milestone: real EEG driving nodes in the shared white room. It
produces no committed media — generate it yourself:

```bash
pip install -e ".[viz]"
python demos/demo1_room/run.py --nodes 4 --ticks 100 --subjects 1,2,3,4
# output -> demos/demo1_room/outputs/demo1.gif   (open it to watch)
```

Full options, more examples (mp4, 200-node scale run), and troubleshooting are in
[`demos/demo1_room/README.md`](demos/demo1_room/README.md).

## Quickstart

```bash
# from the repo root: humanbasis/stack
python -m venv .venv && . .venv/Scripts/activate    # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev,viz]"                         # core + tests + rendering
pytest -q                                           # unit tests (synthetic, no network)
python demos/demo1_room/run.py --synthetic          # a first render, offline
```

Requirements: Python >= 3.10. Core deps (numpy, scipy, mne) install with the
package; `viz` adds matplotlib/pillow/imageio-ffmpeg for the demo renderer.

## Repository layout

```
stack/
  snp/       # SNP contract: schema, encoding registry (6..256), validate, normalize
  brain/     # Basis Brain: EEG replay + generative multi-modality signal source
  locus/     # Basis Locus: room environment, decoders (motor/visual), boundary
  fabric/    # Basis Fabric: distributed consensus (lww/vector_clock/quorum/crdt)
  nexus/     # integration: single-room loop + sharded multi-authority graph
  trace/     # Basis TRACE: metrics recorder + lens (percentiles/throughput/bandwidth)
  core/      # config (parameterized), deterministic seeding, montage convention
  service/   # agent control surface + MCP server (JSON-RPC over stdio)
  demos/     # demos/demo1_room (visual), demos/graph (scale)
  evals/     # acceptance-criteria harness (eval-driven)
  tests/     # unit tests
  pyproject.toml
```

Each component is an independent, importable package with its own README. Demos
and the service are separate consumers; they never re-implement component wiring.

## Develop / test

```bash
pip install -e ".[dev,viz]"
pytest -q                                   # unit tests + evals (synthetic, no network)
pytest evals -q                             # just the acceptance suites
BASIS_RUN_INTEGRATION=1 pytest -q \
  tests/test_brain_integration.py           # real EEGMMIDB download + emit
```

See `../README.md` and the reference docs for the vision and architecture.
