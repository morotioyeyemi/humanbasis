"""Basis Brain: synthetic neural node (v1).

A Brain replays real recorded EEG motor-imagery segments and emits them, one at a
time, as SNP messages. It does not generate signal. Each Brain instance is one
node (one subject's epoch stream) with a distinct ``node_id``.

Design notes:
- Output shape is defined entirely by the SNP encoding (``mi.c3czc4.mubeta.v1``).
- Every emitted message is validated through ``snp.validate`` before it leaves.
- Brain writes timing to Basis TRACE from day one (principle 6.6).
- v1 does not consume inbound perception updates (closed loop is out of scope).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

import snp

from .features import band_power_vector
from .loader import EpochSet, load_mi_epochs

PARADIGM_MI_LR = "motor_imagery_lr"


class Brain:
    """A synthetic neural node that replays real EEG as SNP messages.

    Args:
        node_id: This node's identity, e.g. ``"brain_1"``.
        epochs: Labeled epochs to replay. Use ``Brain.from_subject`` to load
            EEGMMIDB, or pass a prepared ``EpochSet`` (e.g. for tests).
        encoding: SNP encoding id defining the output vector shape.
        trace: Optional Basis TRACE recorder; if given, each emit is timed.
        loop: If ``True``, ``emit`` wraps around to the first epoch after the
            last; if ``False``, it raises ``StopIteration`` when exhausted.
    """

    def __init__(
        self,
        node_id: str,
        epochs: EpochSet,
        *,
        encoding: str = "mi.c3czc4.mubeta.v1",
        trace: Optional[Any] = None,
        loop: bool = True,
    ) -> None:
        layout = snp.get_layout(encoding)
        if tuple(epochs.channels) != tuple(layout.channels):
            raise ValueError(
                f"epoch channels {epochs.channels} do not match encoding "
                f"{encoding!r} channels {layout.channels}"
            )
        self.node_id = node_id
        self.encoding = encoding
        self.paradigm = PARADIGM_MI_LR
        self.signal_type = layout.signal_type
        self._epochs = epochs
        self._trace = trace
        self._loop = loop
        self._cursor = 0

    @classmethod
    def from_subject(
        cls,
        node_id: str,
        subject: int,
        *,
        encoding: str = "mi.c3czc4.mubeta.v1",
        trace: Optional[Any] = None,
        loop: bool = True,
    ) -> "Brain":
        """Build a Brain by loading one EEGMMIDB subject's MI epochs."""
        epochs = load_mi_epochs(subject, encoding=encoding)
        return cls(node_id, epochs, encoding=encoding, trace=trace, loop=loop)

    def __len__(self) -> int:
        return len(self._epochs.labels)

    @property
    def labels(self) -> List[str]:
        """The left/right label of each epoch, in order."""
        return list(self._epochs.labels)

    def _next_index(self) -> int:
        if self._cursor >= len(self):
            if not self._loop:
                raise StopIteration("Brain epoch stream exhausted")
            self._cursor = 0
        idx = self._cursor
        self._cursor += 1
        return idx

    def emit(self) -> Dict[str, Any]:
        """Emit the next epoch as a validated SNP message dict.

        Returns:
            A canonical SNP message dict (validated) for the next epoch.
        """
        idx = self._next_index()
        epoch = self._epochs.data[idx]

        def _build() -> Dict[str, Any]:
            vector = band_power_vector(epoch, self.encoding, self._epochs.rate_hz)
            message = {
                "node_id": self.node_id,
                "timestamp": int(time.time() * 1000),
                "signal_type": self.signal_type,
                "payload": {
                    "vector": vector,
                    "confidence": 1.0,  # replayed ground truth
                    "paradigm": self.paradigm,
                    "encoding": self.encoding,
                },
            }
            return snp.normalize_validated(message)

        if self._trace is not None:
            with self._trace.span("brain", "emit", node_id=self.node_id):
                msg = _build()
            self._trace.record(
                "brain",
                "emit_meta",
                node_id=self.node_id,
                meta={"label": self._epochs.labels[idx], "encoding": self.encoding},
            )
            return msg
        return _build()

    def emit_labeled(self) -> Tuple[Dict[str, Any], str]:
        """Emit the next message together with its ground-truth label."""
        idx = self._cursor if self._cursor < len(self) else 0
        label = self._epochs.labels[idx]
        return self.emit(), label
