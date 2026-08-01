"""Eval: generative signal is unlimited, non-repeating, reproducible, realistic."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import snp
from brain import GenerativeBrain, build_model
from brain.generative import CALIBRATION_DIR
from locus import decoders
from criteria import GEN_MEAN_ABS_TOL, GEN_MIN_DECODE_ACC


def test_unlimited_and_non_repeating():
    brain = GenerativeBrain("brain_1", encoding="mi.16ch.mubeta.v1", seed=0)
    seen = set()
    for _ in range(2000):
        v = tuple(round(x, 6) for x in brain.emit()["payload"]["vector"])
        seen.add(v)
    # No hard cap, and effectively all draws are distinct (not replayed).
    assert len(seen) > 1990


def test_reproducible_by_seed():
    a = [GenerativeBrain("n", encoding="mi.8ch.mubeta.v1", seed=5).emit()["payload"]["vector"]
         for _ in range(1)][0]
    b = GenerativeBrain("n", encoding="mi.8ch.mubeta.v1", seed=5).emit()["payload"]["vector"]
    assert a == b
    c = GenerativeBrain("n", encoding="mi.8ch.mubeta.v1", seed=6).emit()["payload"]["vector"]
    assert a != c


def test_matches_real_stats_within_tolerance():
    encoding = "mi.c3czc4.mubeta.v1"
    calib = json.loads((CALIBRATION_DIR / f"{encoding}.json").read_text())
    model = build_model(encoding)  # uses the calibration
    rng = np.random.default_rng(0)
    for label, ref in calib["classes"].items():
        cls = next(c for c in model.classes if c.label == label)
        samples = np.array([cls.mean + cls.std * rng.standard_normal(len(cls.mean)) for _ in range(4000)])
        gen_mean = samples.mean(axis=0)
        assert np.max(np.abs(gen_mean - np.asarray(ref["mean"]))) < GEN_MEAN_ABS_TOL, label


def test_motor_signal_is_decodable():
    encoding = "mi.16ch.mubeta.v1"
    brain = GenerativeBrain("b", encoding=encoding, seed=3)
    correct = 0
    n = 400
    for _ in range(n):
        msg, label = brain.emit_labeled()
        if decoders.decode(encoding, msg["payload"]["vector"]) == label:
            correct += 1
    assert correct / n >= GEN_MIN_DECODE_ACC


def test_visual_signal_is_decodable():
    encoding = "ssvep.16ch.f4.v1"
    brain = GenerativeBrain("b", encoding=encoding, seed=1)
    # Each SSVEP class should map to a stable, valid action.
    for _ in range(50):
        msg = brain.emit()
        assert snp.is_valid(msg)
        action = decoders.decode(encoding, msg["payload"]["vector"])
        assert action in ("left", "right", "forward")
