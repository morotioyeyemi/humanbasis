# Basis service — agent-facing control (MCP)

Lets AI agents inspect, run, scale, and tune the entire Basis stack — the
AI-first pillar (human-basis 1.4, basis-stack 6.7). Two layers:

- **`BasisController`** — the substance: plain Python methods over a live graph,
  each returning JSON-serializable data. Directly usable and testable.
- **`BasisMCPServer`** — a self-contained, protocol-compliant MCP server
  (JSON-RPC 2.0 over stdio) that exposes the controller methods as MCP tools. No
  third-party SDK dependency, so it is robust and fully testable via `handle()`.

## Run

```bash
python -m service.mcp_server      # or: python service/mcp_server.py
```

An agent host launches this over stdio and speaks MCP: `initialize`,
`tools/list`, `tools/call`.

## Tools

| Tool | Purpose |
| ---- | ------- |
| `basis_build` | Build/rebuild the graph from a `BasisConfig`. |
| `basis_reset` | Rebuild from the current config. |
| `basis_summary` | Graph shape + Fabric consensus metrics. |
| `basis_tick` | Advance `n` ticks; returns last tick + throughput. |
| `basis_add_shard` / `basis_remove_shard` | Scale Locus authorities live. |
| `basis_add_node` / `basis_remove_node` | Scale nodes live. |
| `basis_set_policy` | Switch consensus policy (`lww`/`vector_clock`/`quorum`/`crdt_merge`) live. |
| `basis_get_config` / `basis_set_config` | Read/replace the run config. |
| `basis_holders` | Current committed holder of every shared resource. |
| `basis_metrics` | Metrics lens: latency percentiles, bandwidth, throughput. |
| `basis_list_encodings` | Available modalities/encodings and vector widths. |

## Programmatic use

```python
from service import BasisController
c = BasisController()
c.build({"graph": {"n_shards": 100, "nodes_per_shard": [2, 20]}})
c.tick(10)
c.set_policy("quorum")     # tune consensus live
c.add_shard(50)            # scale up mid-run
print(c.summary(), c.metrics())
```
