"""Basis MCP server: expose the whole stack to agents as MCP tools.

A self-contained, protocol-compliant MCP server over JSON-RPC 2.0 on stdio. It
implements the MCP methods ``initialize``, ``tools/list``, and ``tools/call``,
dispatching each tool to a ``BasisController`` method. Kept dependency-free (no
third-party MCP SDK) so it is robust and fully testable via ``handle()``.

Run it (an agent host launches this over stdio):

    python -m service.mcp_server        # or: python service/mcp_server.py
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, Dict, List

from .controller import BasisController

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "basis", "version": "1.0.0"}


def _tools(controller: BasisController) -> List[Dict[str, Any]]:
    """Tool specifications (name, description, inputSchema) + handlers."""
    def obj(props: Dict[str, Any], required: List[str] | None = None) -> Dict[str, Any]:
        return {"type": "object", "properties": props, "required": required or []}

    return [
        {"name": "basis_build", "description": "Build/rebuild the graph from a BasisConfig (optional).",
         "inputSchema": obj({"config": {"type": "object"}}),
         "handler": lambda a: controller.build(a.get("config"))},
        {"name": "basis_reset", "description": "Rebuild the graph from the current config.",
         "inputSchema": obj({}), "handler": lambda a: controller.reset()},
        {"name": "basis_summary", "description": "Graph shape + Fabric consensus metrics.",
         "inputSchema": obj({}), "handler": lambda a: controller.summary()},
        {"name": "basis_tick", "description": "Advance the simulation n ticks (default 1).",
         "inputSchema": obj({"n": {"type": "integer", "minimum": 1}}),
         "handler": lambda a: controller.tick(int(a.get("n", 1)))},
        {"name": "basis_add_shard", "description": "Add count shards (Locus authorities) live.",
         "inputSchema": obj({"count": {"type": "integer", "minimum": 1}}),
         "handler": lambda a: controller.add_shard(int(a.get("count", 1)))},
        {"name": "basis_remove_shard", "description": "Remove a shard by index.",
         "inputSchema": obj({"index": {"type": "integer"}}, ["index"]),
         "handler": lambda a: controller.remove_shard(int(a["index"]))},
        {"name": "basis_add_node", "description": "Add a node to a shard live.",
         "inputSchema": obj({"shard_index": {"type": "integer"}}, ["shard_index"]),
         "handler": lambda a: controller.add_node(int(a["shard_index"]))},
        {"name": "basis_remove_node", "description": "Remove a node by id.",
         "inputSchema": obj({"node_id": {"type": "string"}}, ["node_id"]),
         "handler": lambda a: controller.remove_node(str(a["node_id"]))},
        {"name": "basis_set_policy", "description": "Change the Fabric consensus policy live "
                                                    "(lww/vector_clock/quorum/crdt_merge).",
         "inputSchema": obj({"policy": {"type": "string"}}, ["policy"]),
         "handler": lambda a: controller.set_policy(str(a["policy"]))},
        {"name": "basis_get_config", "description": "Return the current BasisConfig.",
         "inputSchema": obj({}), "handler": lambda a: controller.get_config()},
        {"name": "basis_set_config", "description": "Replace the config (applies on next build/reset).",
         "inputSchema": obj({"config": {"type": "object"}}, ["config"]),
         "handler": lambda a: controller.set_config(a["config"])},
        {"name": "basis_holders", "description": "Current committed holder of every shared resource.",
         "inputSchema": obj({}), "handler": lambda a: controller.holders()},
        {"name": "basis_metrics", "description": "Metrics lens: latency percentiles, bandwidth, throughput.",
         "inputSchema": obj({}), "handler": lambda a: controller.metrics()},
        {"name": "basis_list_encodings", "description": "Available modalities/encodings and vector widths.",
         "inputSchema": obj({}), "handler": lambda a: controller.list_encodings()},
    ]


class BasisMCPServer:
    """MCP JSON-RPC server exposing the Basis stack.

    Args:
        controller: The control surface tools dispatch to (a fresh one by default).
    """

    def __init__(self, controller: BasisController | None = None) -> None:
        self.controller = controller or BasisController()
        self._tools = _tools(self.controller)
        self._by_name: Dict[str, Callable[[Dict[str, Any]], Any]] = {
            t["name"]: t["handler"] for t in self._tools
        }

    def tool_specs(self) -> List[Dict[str, Any]]:
        """Public tool specs (without handlers) as returned by tools/list."""
        return [{k: t[k] for k in ("name", "description", "inputSchema")} for t in self._tools]

    # --- JSON-RPC dispatch (pure, testable) -------------------------------
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any] | None:
        """Handle one JSON-RPC request; return a response (or None for notifications)."""
        rpc_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}
        try:
            if method == "initialize":
                result: Any = {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": SERVER_INFO,
                }
            elif method == "notifications/initialized":
                return None
            elif method == "tools/list":
                result = {"tools": self.tool_specs()}
            elif method == "tools/call":
                result = self._call_tool(params)
            elif method == "ping":
                result = {}
            else:
                return self._error(rpc_id, -32601, f"method not found: {method}")
        except Exception as exc:  # noqa: BLE001 - surface as JSON-RPC error
            return self._error(rpc_id, -32000, str(exc))
        return {"jsonrpc": "2.0", "id": rpc_id, "result": result}

    def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        args = params.get("arguments") or {}
        if name not in self._by_name:
            raise ValueError(f"unknown tool: {name}")
        value = self._by_name[name](args)
        text = json.dumps(value)
        return {"content": [{"type": "text", "text": text}], "isError": False}

    @staticmethod
    def _error(rpc_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}

    # --- stdio transport --------------------------------------------------
    def serve_stdio(self) -> None:  # pragma: no cover - I/O loop
        """Serve MCP over stdin/stdout (one JSON-RPC message per line)."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue
            response = self.handle(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()


def main() -> None:  # pragma: no cover
    BasisMCPServer().serve_stdio()


if __name__ == "__main__":  # pragma: no cover
    main()
