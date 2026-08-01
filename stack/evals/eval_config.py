"""Eval: configuration is parameterized, serializable, and validated."""

from __future__ import annotations

import pytest

from core import BasisConfig


def test_defaults_validate():
    BasisConfig().validate()


def test_roundtrip_json(tmp_path):
    cfg = BasisConfig(seed=7, ticks=50)
    cfg.graph.n_shards = 12
    cfg.graph.nodes_per_shard = (3, 9)
    cfg.signal.encoding = "mi.c3czc4.mubeta.v1"
    cfg.fabric.policy = "quorum"
    path = tmp_path / "cfg.json"
    cfg.save(path)
    loaded = BasisConfig.load(path)
    assert loaded.to_dict() == cfg.to_dict()
    assert loaded.graph.nodes_per_shard == (3, 9)


def test_validation_rejects_bad_values():
    with pytest.raises(ValueError):
        BasisConfig.from_dict({"graph": {"n_shards": 0}}).validate()
    with pytest.raises(ValueError):
        BasisConfig.from_dict({"fabric": {"policy": "nonsense"}}).validate()
    with pytest.raises(ValueError):
        BasisConfig.from_dict({"signal": {"source": "telepathy"}}).validate()
