"""Basis viz: comprehension panels, animated dashboard, and paper figures."""

from __future__ import annotations

from .collector import Collection, Frame, collect
from .dashboard import render_dashboard
from .figures import figure_policy_tradeoff, figure_scaling

__all__ = [
    "collect",
    "Collection",
    "Frame",
    "render_dashboard",
    "figure_policy_tradeoff",
    "figure_scaling",
]
