# Basis Brain (v1)

A synthetic neural **node**. Each `Brain` instance replays real recorded EEG
motor-imagery segments and emits them, one at a time, as SNP messages. It does
**not** generate signal (v1 replays real data).

- **Source:** PhysioNet EEGMMIDB via `mne.datasets.eegbci` (auto-download).
- **Task:** motor imagery, left vs right hand (runs 4/8/12; T1=left, T2=right).
- **Output:** the SNP encoding `mi.c3czc4.mubeta.v1` — log mu/beta band power for
  channels C3, Cz, C4 → a 6-float vector, channel-major.
- **Contract:** every emitted message is run through `snp.validate` before it
  leaves; output shape is read from the SNP registry so Brain can't drift.
- **Instrumentation:** writes timing to Basis TRACE from day one.
- **Scope:** v1 does not consume inbound perception updates (closed loop is out
  of scope).

## Usage

```python
from brain import Brain
from trace import Trace

trace = Trace()
brain = Brain.from_subject("brain_1", subject=1, trace=trace)  # downloads EEGMMIDB
msg = brain.emit()            # -> validated SNP message dict
msg, label = brain.emit_labeled()  # message + ground-truth "left"/"right"
```

For tests or custom data, construct with a prepared `EpochSet` instead of
`from_subject` (see `tests/brain_helpers.py`).

## Test

```bash
pytest -q                                   # unit tests (synthetic, no network)
BASIS_RUN_INTEGRATION=1 pytest -q \
  tests/test_brain_integration.py           # real EEGMMIDB download + emit
```
