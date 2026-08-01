"""Acceptance thresholds for the Basis eval suites (single source of truth)."""

from __future__ import annotations

# --- performance SLOs (single-process, synthetic generative signal) ---------
# Minimum sustained throughput in node-ticks per second on a dev machine.
MIN_NODE_TICKS_PER_SEC = 20_000
# The scale graph target used by eval_scaling / eval_performance.
SCALE_SHARDS = 3_000
SCALE_NODES_PER_SHARD = (2, 20)

# --- generative quality tolerances ------------------------------------------
# Per-feature mean of generated band power must match the real reference within
# this absolute tolerance (in the calibrated feature space).
GEN_MEAN_ABS_TOL = 0.35
# Fraction of held-out generated epochs the lateralization decoder must classify
# correctly (generative signal must be decodable, not noise).
GEN_MIN_DECODE_ACC = 0.75

# --- consistency ------------------------------------------------------------
# A deterministic policy must produce identical resolved state across repeats.
CONSISTENCY_REPEATS = 3
