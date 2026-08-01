# Basis evals

Acceptance-criteria harness for Basis v1. Eval-driven: each workstream has an
eval suite here that encodes what "correct" means; implementation is written to
turn these green. Evals run under pytest alongside the unit tests.

```bash
pytest evals -q            # just the acceptance suites
pytest -q                  # unit tests + evals
```

Suites (by workstream):

| File | What it asserts |
| ---- | --------------- |
| `eval_config.py` | Config is parameterized, (de)serializes, validates ranges. |
| `eval_reproducibility.py` | Same seed -> identical signals and identical raw logs. |
| `eval_encodings.py` | Encodings parameterized 6..256 floats; registry self-consistent. |
| `eval_generative.py` | Generative signals are unlimited, non-repeating, and match real EEG stats within tolerance; decodable. |
| `eval_consistency.py` | Fabric consensus resolves contention deterministically per policy. |
| `eval_scaling.py` | Dynamic ramp of shards/nodes preserves invariants; graph runs at target scale. |
| `eval_performance.py` | Throughput/latency stay within SLO budgets. |
| `eval_mcp.py` | MCP tools honor their contract (inspect/spawn/scale/tune). |

`criteria.py` holds the numeric SLOs and tolerances so thresholds live in one
place.
