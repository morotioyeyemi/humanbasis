"""Central, parameterized configuration for the Basis stack.

Everything that varies at runtime lives here so runs are reproducible and
scriptable: seeds, graph shape (shards and nodes), modality/encoding, signal
source, consensus policy, and logging. A config plus a seed fully determines a
run.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Consensus policies understood by Basis Fabric.
CONSENSUS_POLICIES = ("lww", "vector_clock", "quorum", "crdt_merge")
# Signal sources understood by a node.
SIGNAL_SOURCES = ("generative", "replay")


@dataclass
class GraphConfig:
    """Shape of the world graph.

    Attributes:
        n_shards: Number of Locus authorities (rooms).
        nodes_per_shard: Inclusive (min, max) nodes placed per shard; the exact
            count per shard is drawn deterministically from the seed.
        room_size: Side length of each shard's square room.
    """

    n_shards: int = 1
    nodes_per_shard: Tuple[int, int] = (2, 20)
    room_size: float = 10.0


@dataclass
class SignalConfig:
    """How nodes produce signal.

    Attributes:
        source: "generative" (unlimited, parametric) or "replay" (real EEG).
        encoding: SNP encoding id defining the output vector shape.
        modalities: Encoding ids to mix across nodes (round-robin). If empty,
            all nodes use ``encoding``.
        replay_subjects: EEGMMIDB subjects to cycle through in replay mode.
    """

    source: str = "generative"
    encoding: str = "mi.c3czc4.mubeta.v1"
    modalities: List[str] = field(default_factory=list)
    replay_subjects: List[int] = field(default_factory=lambda: [1, 2, 3])


@dataclass
class FabricConfig:
    """Consensus/consistency parameters.

    Attributes:
        policy: One of ``CONSENSUS_POLICIES``.
        replication_factor: How many shard replicas hold each key (>=1).
    """

    policy: str = "lww"
    replication_factor: int = 1


@dataclass
class LogConfig:
    """Raw logging + metrics parameters.

    Attributes:
        raw_log_path: If set, TRACE mirrors every record to this JSONL file.
        enabled: Whether TRACE records at all.
    """

    raw_log_path: Optional[str] = None
    enabled: bool = True


@dataclass
class BasisConfig:
    """Top-level run configuration. A config + seed fully determines a run."""

    seed: int = 0
    ticks: int = 100
    graph: GraphConfig = field(default_factory=GraphConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    fabric: FabricConfig = field(default_factory=FabricConfig)
    log: LogConfig = field(default_factory=LogConfig)

    # --- (de)serialization ------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Return the plain-dict form (JSON-serializable)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BasisConfig":
        """Build a config from a plain dict (missing keys take defaults)."""
        data = dict(data)
        graph = GraphConfig(**{**asdict(GraphConfig()), **data.pop("graph", {})})
        graph.nodes_per_shard = tuple(graph.nodes_per_shard)  # JSON gives a list
        signal = SignalConfig(**{**asdict(SignalConfig()), **data.pop("signal", {})})
        fabric = FabricConfig(**{**asdict(FabricConfig()), **data.pop("fabric", {})})
        log = LogConfig(**{**asdict(LogConfig()), **data.pop("log", {})})
        return cls(graph=graph, signal=signal, fabric=fabric, log=log, **data)

    @classmethod
    def load(cls, path: str | Path) -> "BasisConfig":
        """Load a config from a JSON file."""
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def save(self, path: str | Path) -> None:
        """Write the config to a JSON file."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def validate(self) -> "BasisConfig":
        """Validate parameter ranges; return self. Raises ValueError on bad input."""
        if self.graph.n_shards < 1:
            raise ValueError("graph.n_shards must be >= 1")
        lo, hi = self.graph.nodes_per_shard
        if lo < 0 or hi < lo:
            raise ValueError("graph.nodes_per_shard must be (min<=max, min>=0)")
        if self.signal.source not in SIGNAL_SOURCES:
            raise ValueError(f"signal.source must be one of {SIGNAL_SOURCES}")
        if self.fabric.policy not in CONSENSUS_POLICIES:
            raise ValueError(f"fabric.policy must be one of {CONSENSUS_POLICIES}")
        if self.fabric.replication_factor < 1:
            raise ValueError("fabric.replication_factor must be >= 1")
        return self
