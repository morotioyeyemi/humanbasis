"""Basis TRACE lens: derive metrics from raw instrumentation.

The lens turns the flat stream of TRACE records into the machine-readable
metrics the infrastructure thesis needs: per-stage latency percentiles,
throughput, and bandwidth. It reads either a live Trace or a JSONL raw log, so
analysis is reproducible from persisted logs alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


class Lens:
    """Compute metrics over TRACE records.

    Args:
        records: TRACE records as plain dicts (component/event/latency_ms/...).
    """

    def __init__(self, records: List[Dict[str, Any]]) -> None:
        self._records = records

    @classmethod
    def from_trace(cls, trace: Any) -> "Lens":
        """Build a lens from a live Trace."""
        return cls(trace.as_dicts())

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "Lens":
        """Build a lens from a JSONL raw log."""
        lines = Path(path).read_text(encoding="utf-8").strip().splitlines()
        return cls([json.loads(line) for line in lines if line])

    def events(self) -> List[str]:
        """Distinct event names present."""
        return sorted({r["event"] for r in self._records})

    def latency_summary(self) -> Dict[str, Dict[str, float]]:
        """Per-event latency stats: count, mean, p50, p95, p99, max (ms)."""
        out: Dict[str, Dict[str, float]] = {}
        by_event: Dict[str, List[float]] = {}
        for r in self._records:
            lat = r.get("latency_ms")
            if lat is not None:
                by_event.setdefault(r["event"], []).append(lat)
        for event, lats in by_event.items():
            arr = np.asarray(lats, dtype=float)
            out[event] = {
                "count": int(arr.size),
                "mean_ms": float(arr.mean()),
                "p50_ms": float(np.percentile(arr, 50)),
                "p95_ms": float(np.percentile(arr, 95)),
                "p99_ms": float(np.percentile(arr, 99)),
                "max_ms": float(arr.max()),
            }
        return out

    def throughput(self, event: str) -> float:
        """Events/sec of ``event`` over the observed wall-clock span."""
        ts = [r["t_unix_ms"] for r in self._records if r["event"] == event and "t_unix_ms" in r]
        if len(ts) < 2:
            return 0.0
        span_s = (max(ts) - min(ts)) / 1000.0
        return (len(ts) - 1) / span_s if span_s > 0 else 0.0

    def bandwidth(self) -> Dict[str, float]:
        """Total bytes and bytes/sec across records that recorded a size."""
        sized = [(r["t_unix_ms"], r["bytes"]) for r in self._records
                 if r.get("bytes") is not None and "t_unix_ms" in r]
        total = float(sum(b for _, b in sized))
        if len(sized) < 2:
            return {"total_bytes": total, "bytes_per_sec": 0.0, "messages": float(len(sized))}
        span_s = (max(t for t, _ in sized) - min(t for t, _ in sized)) / 1000.0
        return {
            "total_bytes": total,
            "bytes_per_sec": total / span_s if span_s > 0 else 0.0,
            "messages": float(len(sized)),
        }

    def summary(self) -> Dict[str, Any]:
        """A single machine-readable metrics summary (for agents/dashboards)."""
        return {
            "n_records": len(self._records),
            "events": self.events(),
            "latency": self.latency_summary(),
            "bandwidth": self.bandwidth(),
        }


def message_bytes(message: Dict[str, Any]) -> int:
    """Serialized size of an SNP message in bytes (compact JSON)."""
    return len(json.dumps(message, separators=(",", ":")).encode("utf-8"))
