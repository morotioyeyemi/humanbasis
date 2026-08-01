# Basis TRACE (v1)

Passive, machine-readable **instrumentation** for the stack. Every component
writes to TRACE from day one (basis-stack principle 6.6). v1 is intentionally
tiny: an in-memory recorder of structured `TraceRecord`s, optionally mirrored to
a JSONL file.

TRACE never interprets signal content — it records metadata only: component,
event, latency, node, message size.

## Usage

```python
from trace import Trace

trace = Trace()                     # or Trace(jsonl_path="trace.jsonl")
with trace.span("brain", "emit", node_id="brain_1"):
    ...                             # records event with measured latency_ms
trace.record("snp", "validate", bytes=128)

trace.records     # list[TraceRecord]
trace.as_dicts()  # list[dict], machine-readable for agents
```
