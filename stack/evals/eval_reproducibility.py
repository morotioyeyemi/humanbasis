"""Eval: deterministic seeding produces stable, independent sub-streams."""

from __future__ import annotations

import numpy as np

from core import derive_seed, rng_for


def test_same_seed_same_stream():
    a = rng_for(42, "brain_1").standard_normal(20)
    b = rng_for(42, "brain_1").standard_normal(20)
    assert np.array_equal(a, b)


def test_different_keys_independent():
    a = rng_for(42, "brain_1").standard_normal(20)
    b = rng_for(42, "brain_2").standard_normal(20)
    assert not np.array_equal(a, b)


def test_seed_is_order_independent():
    # Deriving node_2 before node_1 must not change node_1's stream.
    _ = rng_for(1, "node_2").standard_normal(5)
    first = rng_for(1, "node_1").standard_normal(5)
    _ = rng_for(1, "node_9").standard_normal(5)
    again = rng_for(1, "node_1").standard_normal(5)
    assert np.array_equal(first, again)


def test_derive_seed_stable():
    assert derive_seed(0, "a", 1) == derive_seed(0, "a", 1)
    assert derive_seed(0, "a", 1) != derive_seed(0, "a", 2)
