"""Tests for the Brain node (synthetic epochs, no network)."""

from __future__ import annotations

import pytest

import snp
from brain import Brain
from brain_helpers import synthetic_epochs
from trace import Trace


def test_emit_produces_valid_snp_message():
    brain = Brain("brain_1", synthetic_epochs(4))
    msg = brain.emit()
    # Must pass the SNP contract unchanged.
    validated = snp.validate(msg)
    assert validated.node_id == "brain_1"
    assert validated.signal_type == "motor"
    assert validated.payload.encoding == "mi.c3czc4.mubeta.v1"
    assert validated.payload.paradigm == "motor_imagery_lr"
    assert validated.payload.confidence == 1.0
    assert len(validated.payload.vector) == 6


def test_emit_advances_and_loops():
    epochs = synthetic_epochs(3)
    brain = Brain("brain_1", epochs, loop=True)
    first = brain.emit()
    for _ in range(2):
        brain.emit()
    # 4th emit wraps to epoch 0; timestamp differs but shape holds.
    wrapped = brain.emit()
    assert len(wrapped["payload"]["vector"]) == 6
    assert snp.is_valid(first) and snp.is_valid(wrapped)


def test_no_loop_raises_when_exhausted():
    brain = Brain("brain_1", synthetic_epochs(2), loop=False)
    brain.emit()
    brain.emit()
    with pytest.raises(StopIteration):
        brain.emit()


def test_channel_mismatch_rejected_at_construction():
    epochs = synthetic_epochs(2)
    object.__setattr__(epochs, "channels", ("C3", "Cz"))  # wrong channel set
    with pytest.raises(ValueError):
        Brain("brain_1", epochs)


def test_labels_exposed():
    epochs = synthetic_epochs(4)
    brain = Brain("brain_1", epochs)
    assert brain.labels == ["left", "right", "left", "right"]
    assert len(brain) == 4


def test_emit_writes_to_trace():
    trace = Trace()
    brain = Brain("brain_1", synthetic_epochs(3), trace=trace)
    brain.emit()
    events = [r.event for r in trace.records]
    assert "emit" in events  # timed span
    assert "emit_meta" in events
    emit_rec = next(r for r in trace.records if r.event == "emit")
    assert emit_rec.component == "brain"
    assert emit_rec.node_id == "brain_1"
    assert emit_rec.latency_ms is not None and emit_rec.latency_ms >= 0.0
