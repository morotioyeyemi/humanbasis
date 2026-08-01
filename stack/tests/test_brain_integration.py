"""Integration test: real EEGMMIDB download + emit.

Skipped by default (downloads data and needs mne/scipy). Enable with:

    BASIS_RUN_INTEGRATION=1 pytest -q tests/test_brain_integration.py
"""

from __future__ import annotations

import os

import pytest

import snp

RUN = os.environ.get("BASIS_RUN_INTEGRATION") == "1"


@pytest.mark.skipif(not RUN, reason="set BASIS_RUN_INTEGRATION=1 to run (downloads EEGMMIDB)")
def test_real_subject_emit():
    from brain import Brain

    brain = Brain.from_subject("brain_1", subject=1)
    assert len(brain) > 0
    assert set(brain.labels) <= {"left", "right"}
    for _ in range(min(5, len(brain))):
        msg = brain.emit()
        validated = snp.validate(msg)
        assert len(validated.payload.vector) == 6
        assert validated.signal_type == "motor"
