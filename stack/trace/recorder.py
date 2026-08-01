"""Basis TRACE: minimal real-time infrastructure metrics engine.

Passive instrumentation for the stack. Every component writes to TRACE from day
one (basis-stack principle 6.6). v1 is intentionally tiny: an in-memory recorder
of structured metric records, optionally appended to a JSONL file, exposing a
machine-readable list so AI agents can read and act on it.

TRACE never interprets signal content. It records metadata only: which
component, what event, how long it took, how big the message was.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TraceRecord:
    """A single instrumentation record.

    Attributes:
        component: Emitting component, e.g. ``"brain"``.
        event: What happened, e.g. ``"emit"``.
        t_unix_ms: Wall-clock time of the record, unix milliseconds.
        latency_ms: Optional duration of the measured operation.
        node_id: Optional producing node identity.
        bytes: Optional serialized message size in bytes.
        meta: Optional free-form machine-readable extras.
    """

    component: str
    event: str
    t_unix_ms: int
    latency_ms: Optional[float] = None
    node_id: Optional[str] = None
    bytes: Optional[int] = None
    meta: Dict[str, Any] = field(default_factory=dict)


class Trace:
    """In-memory (optionally JSONL-backed) metrics recorder.

    Args:
        jsonl_path: If given, each record is also appended as one JSON line.
    """

    def __init__(self, jsonl_path: Optional[str | Path] = None) -> None:
        self._records: List[TraceRecord] = []
        self._jsonl_path = Path(jsonl_path) if jsonl_path else None
        if self._jsonl_path:
            self._jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        component: str,
        event: str,
        *,
        latency_ms: Optional[float] = None,
        node_id: Optional[str] = None,
        bytes: Optional[int] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> TraceRecord:
        """Append a metric record and return it."""
        rec = TraceRecord(
            component=component,
            event=event,
            t_unix_ms=int(time.time() * 1000),
            latency_ms=latency_ms,
            node_id=node_id,
            bytes=bytes,
            meta=meta or {},
        )
        self._records.append(rec)
        if self._jsonl_path:
            with self._jsonl_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(asdict(rec)) + "\n")
        return rec

    def span(self, component: str, event: str, **fields: Any) -> "_Span":
        """Context manager that records ``event`` with measured ``latency_ms``.

        Example::

            with trace.span("brain", "emit", node_id="brain_1"):
                ...
        """
        return _Span(self, component, event, fields)

    @property
    def records(self) -> List[TraceRecord]:
        """All records captured so far (machine-readable)."""
        return list(self._records)

    def as_dicts(self) -> List[Dict[str, Any]]:
        """All records as plain dicts."""
        return [asdict(r) for r in self._records]

    def clear(self) -> None:
        """Drop all in-memory records."""
        self._records.clear()


class _Span:
    def __init__(self, trace: Trace, component: str, event: str, fields: Dict[str, Any]) -> None:
        self._trace = trace
        self._component = component
        self._event = event
        self._fields = fields
        self._t0 = 0.0

    def __enter__(self) -> "_Span":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc: Any) -> None:
        latency_ms = (time.perf_counter() - self._t0) * 1000.0
        self._trace.record(
            self._component, self._event, latency_ms=latency_ms, **self._fields
        )
