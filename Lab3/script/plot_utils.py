"""Shared layout helpers for the Task 3 figures (CLAUDE.md 4.12 and 5.1).

Holds the grid builder, per-model line styles, the number format and the zoom
rule used by ``plots_metrics``, ``plots_confusion``, ``plots_training`` and
``roc_curves``. Only the object-oriented matplotlib API is used (no pyplot).
"""
from __future__ import annotations

import math
from typing import Any

from matplotlib.axes import Axes
from matplotlib.figure import Figure

import common

GRID_COLS = 4
PANEL_W, PANEL_H = 4.2, 3.8       # inches per grid panel
FONT_TITLE, FONT_LABEL, FONT_TICK, FONT_ANNOT = 14, 12, 11, 10
LINE_WIDTH = 2.0
LINESTYLES = {"ML": "-", "DL": "--"}  # ML solid, DL dashed (CLAUDE.md 4.12)
DECIMALS = 4                      # user decision 2026-11-13: decimals, not percent
ZOOM_PAD = 0.5                    # floor sits this fraction of the gap below the minimum
ZOOM_MIN_SPAN = 0.002             # minimum gap so identical scores still get headroom
AXIS_TOP_PAD = 0.001              # headroom above 1.0 on the dot plot (axis must not run on)
GRID_ALPHA = 0.3                  # light grid lines
BAR_LABEL_PAD = 3                 # points between a bar end and its value label
MAX_SCORE = 1.0                   # scores never exceed 1, neither do their ticks
# Paul Tol "bright" qualitative set (colour-blind safe, grey dropped). Used for metric series
# and train/val lines; no entry equals a colour of common.MODEL_COLORS.
SERIES_COLORS = ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377"]
LEGEND_ANCHOR = (1.02, 1.0)       # legend outside the axes so it never hides data

SCORE_KEYS = ["accuracy", "precision", "recall", "f1", "macro_f1", "roc_auc"]
SCORE_LABELS = ["Accuracy", "Precision", "Recall", "F1", "Macro-F1", "ROC-AUC"]


def fmt(value: float) -> str:
    """Format a metric value with the agreed number of decimals.

    Args:
        value: Metric value.

    Returns:
        String such as "0.9999".
    """
    return f"{value:.{DECIMALS}f}"


def model_color(key: str) -> str:
    """Return the fixed colour of a model.

    Args:
        key: Registry key.

    Returns:
        Hex colour from ``common.MODEL_COLORS``.
    """
    return common.MODEL_COLORS[key]


def line_style(family: str) -> str:
    """Return the matplotlib line style of a model family.

    Args:
        family: "ML" or "DL".

    Returns:
        "-" for ML, "--" for DL.
    """
    return LINESTYLES[family]


def axis_floor(values: list[float]) -> float:
    """Pick a lower axis limit just below the smallest value.

    Args:
        values: Scores in [0, 1].

    Returns:
        Floor so near-perfect scores are not squashed against 1.0.
    """
    low = min(values)
    gap = max(1.0 - low, ZOOM_MIN_SPAN)
    return max(0.0, low - ZOOM_PAD * gap)


def cap_score_ticks(ax: Axes, axis: str) -> None:
    """Drop the ticks above 1.0 on a score axis (headroom may extend past 1.0).

    Args:
        ax: Target axes.
        axis: "x" or "y".
    """
    ticks = ax.get_xticks() if axis == "x" else ax.get_yticks()
    kept = [t for t in ticks if t <= MAX_SCORE + 1e-9]  # tolerance for float noise
    if axis == "x":
        ax.set_xticks(kept)
    else:
        ax.set_yticks(kept)


def make_grid(n_panels: int, **subplot_kw: Any) -> tuple[Figure, list[Axes]]:
    """Create a figure with a 4-column grid; unused panels are removed.

    Args:
        n_panels: Number of panels needed (>= 1).
        **subplot_kw: Passed to ``add_subplot`` (e.g. ``projection``).

    Returns:
        The figure and exactly ``n_panels`` axes in reading order.
    """
    cols = min(GRID_COLS, n_panels)
    rows = math.ceil(n_panels / GRID_COLS)
    fig = Figure(figsize=(PANEL_W * cols, PANEL_H * rows), layout="constrained")
    axes = [fig.add_subplot(rows, cols, i + 1, **subplot_kw) for i in range(n_panels)]
    return fig, axes


def style_axis(ax: Axes, title: str, xlabel: str = "", ylabel: str = "") -> None:
    """Apply the common title, labels, tick size and light grid.

    Args:
        ax: Target axes.
        title: Axes title.
        xlabel: X-axis label.
        ylabel: Y-axis label.
    """
    ax.set_title(title, fontsize=FONT_TITLE)
    ax.set_xlabel(xlabel, fontsize=FONT_LABEL)
    ax.set_ylabel(ylabel, fontsize=FONT_LABEL)
    ax.tick_params(labelsize=FONT_TICK)
    ax.grid(alpha=GRID_ALPHA)
    ax.set_axisbelow(True)
