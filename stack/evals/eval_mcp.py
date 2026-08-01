"""Eval: MCP tools honor their contract (inspect/run/scale/tune the stack)."""

from __future__ import annotations

import json

from service import BasisController, BasisMCPServer

SMALL = {
    "seed": 0,
    "graph": {"n_shards": 5, "nodes_per_shard": [2, 6], "n_shared_resources": 4},
    "signal": {"source": "generative", "encoding": "mi.8ch.mubeta.v1"},
    "fabric": {"policy": "lww"},
}


# --- controller contract ----------------------------------------------------

def test_controller_build_tick_and_scale():
    c = BasisController(enable_trace=True)
    summ = c.build(SMALL)
    assert summ["n_shards"] == 5
    n0 = summ["n_nodes"]

    t = c.tick(3)
    assert t["last_tick"]["tick"] == 2
    assert t["node_ticks_per_sec"] > 0

    up = c.add_shard(2)
    assert up["n_shards"] == 7
    node = c.add_node(up["added_shards"][0])
    assert node["node_id"] is not None
    assert c.summary()["n_nodes"] > n0

    assert c.remove_node(node["node_id"])["removed"] is True
    assert c.remove_shard(up["added_shards"][0])["removed"] is True


def test_controller_tune_policy_live():
    c = BasisController()
    c.build(SMALL)
    assert c.set_policy("crdt_merge")["policy"] == "crdt_merge"
    assert c.graph.fabric.policy == "crdt_merge"
    c.tick(2)  # runs under the new policy
    try:
        c.set_policy("bogus")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_controller_inspect_and_metrics():
    c = BasisController(enable_trace=True)
    c.build(SMALL)
    c.tick(2)
    assert "holders" in c.holders()
    mods = c.list_encodings()["modalities"]
    assert "motor" in mods and "visual" in mods
    metrics = c.metrics()
    assert "latency" in metrics


# --- MCP JSON-RPC server contract -------------------------------------------

def test_mcp_initialize_and_list_tools():
    srv = BasisMCPServer()
    init = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init["result"]["serverInfo"]["name"] == "basis"

    listed = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    names = {t["name"] for t in listed["result"]["tools"]}
    for expected in ("basis_build", "basis_tick", "basis_add_shard", "basis_set_policy",
                     "basis_summary", "basis_metrics", "basis_list_encodings"):
        assert expected in names
    # Every tool advertises a JSON schema.
    for t in listed["result"]["tools"]:
        assert t["inputSchema"]["type"] == "object"


def test_mcp_call_tool_dispatches():
    srv = BasisMCPServer()
    srv.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "basis_build", "arguments": {"config": SMALL}}})
    resp = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                       "params": {"name": "basis_tick", "arguments": {"n": 2}}})
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["last_tick"]["tick"] == 1
    assert resp["result"]["isError"] is False


def test_mcp_unknown_method_and_tool_errors():
    srv = BasisMCPServer()
    bad_method = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "does/not/exist", "params": {}})
    assert bad_method["error"]["code"] == -32601
    bad_tool = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                           "params": {"name": "nope", "arguments": {}}})
    assert "error" in bad_tool


def test_mcp_notification_returns_none():
    srv = BasisMCPServer()
    assert srv.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
