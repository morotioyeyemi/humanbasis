# Demo 1 — real EEG driving nodes in the shared white room

The first visual milestone of the Basis stack. N Basis Brains replay real
recorded EEG motor-imagery signals; each signal flows through the **full stack
loop** and moves that node inside one shared room. You watch real recorded human
brain activity drive agents in a shared space.

This demo produces no committed media — you generate it yourself with the command
below. Output is written to `demos/demo1_room/outputs/` (git-ignored).

---

## TL;DR

```bash
# from the repo root: humanbasis/stack
pip install -e ".[viz]"

# real EEG, 4 nodes (downloads a few EEGMMIDB subjects on first run)
python demos/demo1_room/run.py --nodes 4 --ticks 100 --subjects 1,2,3,4

# offline scale demo: 200 nodes in a 30x-area room, as mp4
python demos/demo1_room/run.py --synthetic --nodes 200 --room-size 55 --ticks 80 \
    --out demos/demo1_room/outputs/scale.mp4
```

Open the file printed at the end (default `demos/demo1_room/outputs/demo1.gif`).

---

## What you are seeing

- A top-down **white room** (basis-stack section 5) with a chair (square) and one
  object on the right wall (star).
- Each **dot** is a node (one EEGMMIDB subject in real mode); the arrow is its
  heading, the faint line its trail. For large node counts, arrows are dropped
  and trails are faded for legibility.
- Motion is **decoded from real motor-imagery band power**: left-hand imagery
  turns a node left, right-hand imagery turns it right. The decoder compares C3
  vs C4 mu/beta power (motor-imagery lateralization); see `locus/decoders.py`.

## The loop behind every frame

Each tick, for every node:

```
Brain.emit()  ->  SNP.validate  ->  Fabric (pass-through)  ->  Locus (decode + apply)  ->  perception  ->  SNP
        \______________________________ Basis TRACE times every stage ______________________________/
```

- Only **Locus** interprets the vector (the consumption boundary). SNP, Fabric,
  and TRACE treat it as opaque floats — this is why scaling nodes or channels
  never touches transport.
- **Fabric is a pass-through seam here.** A single Locus is one authority, so no
  distributed consensus is needed yet (see the stack README).

A latency/throughput summary from Basis TRACE is printed when the run finishes.

## Options

| Flag | Default | Meaning |
| ---- | ------- | ------- |
| `--nodes N` | `4` | Number of nodes (Brains). |
| `--ticks T` | `120` | Number of signal-loop cycles to run. |
| `--subjects a,b,c` | `1,2,3` | EEGMMIDB subject ids (real mode); nodes cycle through them. |
| `--room-size S` | `10` | Side length of the square room; geometry scales with it. |
| `--synthetic` | off | Use synthetic signal instead of downloading EEG (offline, instant). |
| `--no-render` | off | Run the loop only and print timings; skip media (pure scale test). |
| `--out PATH` | `outputs/demo1.gif` | Output path; `.gif` or `.mp4` selects the format. |

Notes:
- **Real data caps at 109 subjects** (all EEGMMIDB has). For more nodes than
  subjects, ids are reused; for pure scale tests use `--synthetic`.
- `.mp4` output needs ffmpeg. The `viz` extra installs a bundled one
  (`imageio-ffmpeg`); no system install required. `.gif` needs only Pillow.

## Examples

```bash
# the flagship visual: real EEG, small and clear
python demos/demo1_room/run.py --nodes 4 --ticks 100 --subjects 1,2,3,4 \
    --out demos/demo1_room/outputs/demo1.gif

# bigger room, more nodes, smooth mp4
python demos/demo1_room/run.py --synthetic --nodes 200 --room-size 55 --ticks 80 \
    --out demos/demo1_room/outputs/scale.mp4

# headless throughput benchmark (no media)
python demos/demo1_room/run.py --synthetic --nodes 1000 --room-size 120 --ticks 40 --no-render
```

## Troubleshooting

- **First real run is slow / downloads files:** EEGMMIDB is fetched via MNE to
  `~/mne_data` on first use and cached thereafter.
- **`mp4 output needs ffmpeg`:** install the viz extra (`pip install -e ".[viz]"`)
  or output a `.gif` instead.
- **Import errors when running the script directly:** run from the repo root
  (`humanbasis/stack`); `run.py` adds the stack root to `sys.path` automatically.
