"""Montage conventions shared across the stack (neutral, no peer coupling).

Both the generative signal source (Brain side) and the motor decoder (Locus
side) need to agree on which channels sit over the left vs right motor cortex.
This convention lives in ``core`` so neither package imports the other.

Convention:
- Known 10-10 names starting with an odd number are left hemisphere, even are
  right, midline (``z``) is middle (e.g. C3 -> L, C4 -> R, Cz -> M).
- Generic channels (EEG001..) split by index: first half left, second half
  right, and the exact middle channel (for odd counts) is middle.
"""

from __future__ import annotations

from typing import List, Sequence

LEFT = "L"
RIGHT = "R"
MIDDLE = "M"


def _named_hemisphere(ch: str) -> str | None:
    if ch.endswith("z") or ch.endswith("Z"):
        return MIDDLE
    for c in reversed(ch):
        if c.isdigit():
            return LEFT if int(c) % 2 == 1 else RIGHT
    return None


def hemisphere_labels(channels: Sequence[str]) -> List[str]:
    """Return an 'L'/'R'/'M' label per channel, in order."""
    n = len(channels)
    labels: List[str] = []
    for i, ch in enumerate(channels):
        named = _named_hemisphere(ch)
        if named is not None:
            labels.append(named)
            continue
        # Generic: split by index.
        if n % 2 == 1 and i == n // 2:
            labels.append(MIDDLE)
        elif i < n / 2:
            labels.append(LEFT)
        else:
            labels.append(RIGHT)
    return labels
