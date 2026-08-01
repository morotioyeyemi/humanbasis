# Basis Nexus (stack)

The Basis stack: many synthetic neural nodes connected into a shared real-time
environment, with a consistency seam and passive instrumentation. v1 is
single-machine, Python-only, and fed by real open EEG data (nodes replay, they
do not generate).

Build order: **Basis Brain → SNP → Basis Locus → Basis Fabric → Basis TRACE →
integration.**

## Components

| Package | Role | Status |
| ------- | ---- | ------ |
| `snp/`    | **SNP** — the canonical message contract everything speaks (library, not a service). | done |
| `brain/`  | **Basis Brain** — synthetic node; replays real EEGMMIDB motor imagery as SNP messages. | done |
| `locus/`  | **Basis Locus** — shared white-room state; decodes neural vectors into actions and emits perception. | done |
| `fabric/` | **Basis Fabric** — consensus seam beneath Locus; pass-through in v1. | seam |
| `nexus/`  | **Nexus** — integration layer; runs one signal-loop cycle wiring the components. | done |
| `trace/`  | **Basis TRACE** — passive, machine-readable metrics; every component writes to it. | done |

## The signal loop

```
Brain.emit() -> SNP -> Fabric -> Locus (decode + apply) -> perception -> SNP
                     \_________________ TRACE observes every step _________________/
```

- **Opaque-vector rule:** SNP, Fabric, and TRACE never interpret the vector.
  Only **Locus** (the consumption boundary) decodes it into a world action.
- **Encoding by reference:** each message carries a short `encoding` id; the
  layout lives in the SNP registry. Adding a modality or scaling channels is a
  registry edit, with no downstream change.
- **Why Fabric is a seam in v1:** a single Locus is one authority, so sequential
  application is its own trivial consensus. Real Fabric is needed only when the
  world is replicated across authorities (the "at scale" story).

## Demo 1

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
  snp/       # SNP contract: schema, encoding registry, validate, normalize
  brain/     # Basis Brain: EEGMMIDB loader, band-power features, Brain node
  locus/     # Basis Locus: white-room environment, decoders, Locus boundary
  fabric/    # Basis Fabric: pass-through consensus seam (v1)
  nexus/     # Nexus: integration layer that runs the signal loop
  trace/     # Basis TRACE: passive metrics recorder
  demos/     # runnable demos (consumers); demos/demo1_room is Demo 1
  tests/     # pytest suite (synthetic; one guarded real-download integration test)
  pyproject.toml
```

Each component is an independent, importable package with its own README. Demos
are separate consumers that drive `nexus` and render; they never re-implement
component wiring.

## Develop / test

```bash
pip install -e ".[dev,viz]"
pytest -q                                   # unit tests (synthetic, no network)
BASIS_RUN_INTEGRATION=1 pytest -q \
  tests/test_brain_integration.py           # real EEGMMIDB download + emit
```

See `../README.md` and the reference docs for the vision and architecture.
