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

Real EEG driving nodes in the shared white room — see
[`demos/demo1_room/`](demos/demo1_room/README.md).

![Demo 1](demos/demo1_room/demo1.gif)

## Develop / test

```bash
pip install -e ".[dev,viz]"
pytest -q                                   # unit tests (synthetic, no network)
BASIS_RUN_INTEGRATION=1 pytest -q \
  tests/test_brain_integration.py           # real EEGMMIDB download + emit
```

See `../README.md` and the reference docs for the vision and architecture.
